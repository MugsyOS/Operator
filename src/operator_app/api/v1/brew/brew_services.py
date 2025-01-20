import asyncio
import json
import logging
from typing import Dict, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class BrewOrchestrator:
    def __init__(
        self,
        mech_socket_path: str = "/tmp/mech-control.sock",
        weight_socket_path: str = "/tmp/mug_scale_service.sock",
        pump_socket_path: str = "/tmp/pump-control.sock"
    ):
        self.mech_socket_path = mech_socket_path
        self.weight_socket_path = weight_socket_path
        self.pump_socket_path = pump_socket_path
        self.monitoring = False
        self.websocket = None

    async def send_to_socket(self, socket_path: str, message: str) -> str:
        """Send message to unix socket and get response"""
        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)
            try:
                writer.write((message + '\n').encode())
                await writer.drain()

                response = await reader.readline()
                if not response:
                    raise ConnectionError(f"No response from socket: {socket_path}")
                return response.decode().strip()
            finally:
                writer.close()
                await writer.wait_closed()
        except Exception as e:
            logger.error(f"Error communicating with socket {socket_path}: {e}", exc_info=True)
            raise

    # async def get_weight(self) -> Optional[float]:
    #     """Get current weight reading"""
    #     try:
    #         response = await self.send_to_socket(self.weight_socket_path, "single_read")
    #         data = json.loads(response)
    #         if "error" in data:
    #             logger.error(f"Error reading weight: {data['error']}")
    #             return None
    #         return data.get('weight')
    #     except Exception as e:
    #         logger.error(f"Failed to get weight: {e}")
    #         return None

    # async def monitor_weight(self):
    #     """Background task for weight monitoring"""
    #     logger.info("Starting weight monitoring")
    #     self.monitoring = True
        
    #     while self.monitoring:
    #         try:
    #             weight = await self.get_weight()
    #             if weight is not None:
    #                 logger.info(f"Current weight: {weight}g")
    #                 if weight > 300:
    #                     await self.send_stop_command(reason="Overweight")
    #                     break
    #         except Exception as e:
    #             logger.error(f"Error in weight monitoring: {e}")
            
    #         await asyncio.sleep(.1)

    #     logger.info("Weight monitoring stopped")
    
    # async def send_stop_command(state: bool = True, reason: str = "Manual stop", socket_path: str = "/tmp/mech-control.sock"):
    #     try:
    #         # Connect to the Unix socket
    #         reader, writer = await asyncio.open_unix_connection(socket_path)
            
    #         # Create command
    #         command = {
    #             "command": "stop_mechanism",
    #             "state": True,
    #             "reason": 'Overweight'
    #         }
            
    #         # Send command
    #         writer.write((json.dumps(command) + '\n').encode())
    #         await writer.drain()
            
    #         # Get response
    #         response = await reader.readline()
    #         print(f"Response: {response.decode().strip()}")
            
    #         # Close connection
    #         writer.close()
    #         await writer.wait_closed()
        
    #     except Exception as e:
    #         print(f"Error: {e}")

    async def process_commands(self, commands: list) -> dict:
        """Process a list of commands"""
        try:
            # Send commands to mech service
            response = await self.send_to_socket(
                self.mech_socket_path,
                json.dumps(commands)
            )
            
            # Parse response
            try:
                response_data = json.loads(response)
            except json.JSONDecodeError:
                response_data = [response] if isinstance(response, str) else response

            # Process responses
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

            # Return response
            return {
                "status": "ok" if any_successful else "error",
                "total_commands": len(commands),
                "completed_commands": completed_count,
                "commands": command_status,
            }

        except Exception as e:
            logger.error(f"Error processing commands: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connection"""
        await websocket.accept()
        logger.info("WebSocket connection established")
        self.websocket = websocket
        
        # Start monitoring task
        # monitor_task = asyncio.create_task(self.monitor_weight())
        
        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)
                logger.info(f"Received message: {data}")

                # Handle both single commands and lists
                commands = [data] if not isinstance(data, list) else data
                response = await self.process_commands(commands)
                await websocket.send_json(response)
                
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            if not websocket.client_state.DISCONNECTED:
                await websocket.send_json({
                    "status": "error",
                    "message": str(e)
                })
        finally:
            # Cleanup
            self.monitoring = False
            # monitor_task.cancel()
            # try:
            #     # await monitor_task
            # except asyncio.CancelledError:
            #     pass
            self.websocket = None
            logger.info("WebSocket connection closed")
            