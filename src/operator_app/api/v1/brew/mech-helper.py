import asyncio
import websockets
import json
import os
import logging
from typing import Any, List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketRelayServer:
    def __init__(self, websocket_port: int = 8765, unix_socket_path: str = "/tmp/mech-control.sock"):
        self.websocket_port = websocket_port
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

    async def handle_websocket(self, websocket: websockets.WebSocketServerProtocol) -> None:
        try:
            async for message in websocket:
                try:
                    # Parse the incoming message
                    data = json.loads(message)
                    logger.info(f"Received WebSocket message: {data}")

                    # Ensure commands are in a list format
                    if not isinstance(data, list):
                        commands = [data]  # Wrap single command into a list
                    else:
                        commands = data

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
                            # Valid response formats:
                            # - Regular completion: status in ["both_done", "zero_done", "cone_done", "spout_done"]
                            # - Controlled stop: status == "completed"
                            # - Actual error: status == "error"
                            status = resp.get("status", "")
                            
                            # Command is considered successful if it completed normally OR was stopped in a controlled way
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
                            
                            # Add info field if `data` exists in the response
                            if "data" in resp and resp["data"]:
                                command_entry["info"] = resp["data"]
                        else:
                            command_entry["status"] = "error"
                            command_entry["info"] = "Invalid response format"
                            logger.error(f"Invalid response format: {resp}")

                        command_status.append(command_entry)

                    # Determine batch-level status
                    # Batch is "ok" if any command was successful or completed due to controlled stop
                    batch_status = "ok" if any_successful else "error"

                    # Prepare batch-level acknowledgment message
                    acknowledgment = {
                        "status": batch_status,
                        "total_commands": len(commands),
                        "completed_commands": completed_count,
                        "commands": command_status,
                    }

                    # Send acknowledgment back to the WebSocket client
                    await websocket.send(json.dumps(acknowledgment))

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    error_response = json.dumps({'status': 'error', 'message': str(e)})
                    await websocket.send(error_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"WebSocket connection closed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in WebSocket handler: {e}", exc_info=True)

    # only listen to local interface
    # async def start_server(self) -> None:
    #     async with websockets.serve(self.handle_websocket, "localhost", self.websocket_port):
    #         logger.info(f"WebSocket server started on ws://localhost:{self.websocket_port}")
    #         await asyncio.Future()  # Run forever

    # listen on all interfaces, only for development
    async def start_server(self) -> None:
        async with websockets.serve(self.handle_websocket, "0.0.0.0", self.websocket_port):
            logger.info(f"WebSocket server started on port {self.websocket_port}")
            # or if you want to show the IP:
            # logger.info(f"WebSocket server started on ws://0.0.0.0:{self.websocket_port}")
            await asyncio.Future()  # Run forever

if __name__ == "__main__":
    server = WebSocketRelayServer()
    
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Shutting down WebSocket server...")