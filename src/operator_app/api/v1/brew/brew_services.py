import asyncio
import json
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

class BrewService:
    def __init__(self, unix_socket_path: str = "/tmp/mech-control.sock"):
        self.unix_socket_path = unix_socket_path

    async def send_to_unix_socket(self, message: str) -> str:
        try:
            reader, writer = await asyncio.open_unix_connection(self.unix_socket_path)
            try:
                writer.write((message + '\n').encode())
                await writer.drain()

                response = await reader.readline()
                if not response:
                    raise ConnectionError("No response from UNIX socket")
                return response.decode().strip()
            finally:
                writer.close()
                await writer.wait_closed()
        except Exception as e:
            logger.error(f"Error communicating with UNIX socket: {e}", exc_info=True)
            raise

    async def process_message(self, websocket, message: str) -> None:
        try:
            # Parse the incoming message
            data = json.loads(message)
            logger.info(f"Received WebSocket message: {data}")

            # Ensure commands are in a list format
            commands = [data] if not isinstance(data, list) else data

            # Forward the commands to the UNIX socket
            response = await self.send_to_unix_socket(json.dumps(commands))
            logger.info(f"Received response from UNIX socket: {response}")

            # Parse the response from the UNIX socket
            try:
                response_data = json.loads(response)
            except json.JSONDecodeError:
                response_data = [response] if isinstance(response, str) else response

            # Process responses and determine batch completion status
            completed_count = 0
            any_successful = False
            command_status = []
            
            for cmd, resp in zip(commands, response_data):
                command_entry = {"command": cmd.get("command"), "info": ""}
                
                if isinstance(resp, dict):
                    status = resp.get("status", "")
                    
                    if status in ["both_done", "zero_done", "cone_done", "spout_done", "completed"]:
                        command_entry["status"] = "ok"
                        completed_count += 1
                        any_successful = True
                    elif status == "error":
                        command_entry["status"] = "error"
                        logger.error(f"Error response: {resp}")
                    else:
                        command_entry["status"] = "error"
                        logger.error(f"Unexpected response status: {status}")
                    
                    if "data" in resp and resp["data"]:
                        command_entry["info"] = resp["data"]
                else:
                    command_entry["status"] = "error"
                    command_entry["info"] = "Invalid response format"
                    logger.error(f"Invalid response format: {resp}")

                command_status.append(command_entry)

            # Determine batch-level status
            batch_status = "ok" if any_successful else "error"

            # Prepare batch-level acknowledgment message
            acknowledgment = {
                "status": batch_status,
                "total_commands": len(commands),
                "completed_commands": completed_count,
                "commands": command_status,
            }

            # Send acknowledgment back to the WebSocket client
            await websocket.send_text(json.dumps(acknowledgment))

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            error_response = json.dumps({'status': 'error', 'message': str(e)})
            await websocket.send_text(error_response)