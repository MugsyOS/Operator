import PyCmdMessenger
import asyncio
import json
import os
import logging
from typing import Any, List, Dict, Optional
import configparser
import sys
import socket
from enum import Enum
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configurations
config = configparser.ConfigParser()
config.read('hardware_config.ini')
SERIAL_PORT = config.get('MICROCONTROLLER', 'SERIAL_PORT', fallback='/dev/ttyUSB0')
BAUD_RATE = config.getint('MICROCONTROLLER', 'BAUD_RATE', fallback=9600)
WEIGHT_SOCKET_PATH = "/tmp/mug_scale_service.sock"
PUMP_SOCKET_PATH = "/tmp/pump_control.sock"

class PumpDirection(str, Enum):
    forward = "forward"
    reverse = "reverse"
    stop = "stop"

class PumpClient:
    def __init__(self, socket_path: str = PUMP_SOCKET_PATH):
        self.socket_path = socket_path
        self._is_running = False

    def _send_command(self, command: dict) -> Optional[dict]:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(self.socket_path)
                sock.send(json.dumps(command).encode('utf-8'))
                
                # Only wait for response if it's a status request
                if command['action'] == 'status':
                    response = sock.recv(1024).decode('utf-8')
                    return json.loads(response)
                return None
        except Exception as e:
            logger.error(f"Failed to send pump command: {e}")
            return None

    def start_pump(self) -> None:
        if not self._is_running:
            command = {
                'action': 'control_speed',
                'params': {
                    'direction': PumpDirection.forward,
                    'speed': 78
                }
            }
            self._send_command(command)
            self._is_running = True
            logger.info("Pump started")

    def stop_pump(self) -> None:
        if self._is_running:
            command = {
                'action': 'stop',
                'params': {}
            }
            self._send_command(command)
            self._is_running = False
            logger.info("Pump stopped")

    @property
    def is_running(self) -> bool:
        return self._is_running

class WeightService:
    def __init__(self):
        self.socket_path = WEIGHT_SOCKET_PATH

    async def get_weight(self):
        try:
            reader, writer = await asyncio.open_unix_connection(self.socket_path)
            
            # Send single read command
            writer.write(b"single_read\n")
            await writer.drain()
            
            # Read response
            response = await reader.readline()
            weight_data = json.loads(response.decode())
            
            writer.close()
            await writer.wait_closed()
            
            if "error" in weight_data:
                logging.error(f"Error reading weight: {weight_data['error']}")
                return None
                
            return weight_data['weight']
            
        except Exception as e:
            logging.error(f"Failed to get weight: {e}")
            return None

class MechControlService:
    def __init__(self, socket_path: str = "/tmp/mech-control.sock"):
        # Initialize Arduino
        self.arduino = PyCmdMessenger.ArduinoBoard(SERIAL_PORT, BAUD_RATE)
        self.weight_service = WeightService()
        self.pump_client = PumpClient()
        
        # Control state
        self.stop_mech = False
        self.stop_reason = None
        
        # Command definitions for microcontroller
        # (We don't add 'pause' here because it is handled entirely in Python)
        self.commands = [
            ["move_cone", "lii"],       # steps, speed, direction
            ["cone_done", ""],
            ["move_spout", "lii"],      # degrees, speed, direction
            ["spout_done", ""],
            ["move_both", "lilii"],     # cone_steps, cone_speed, spout_degrees, spout_speed, direction
            ["both_done", ""],
            ["zero_spout", ""],         # Zero the spout stepper
            ["zero_done", ""],          # Zero complete acknowledgment
            ["error", "s"]
        ]
        
        self.messenger = PyCmdMessenger.CmdMessenger(self.arduino, self.commands)
        self.socket_path = socket_path

    async def wait_for_response(self, expected_done_cmd: str, timeout: float = 30) -> List[Any]:
        loop = asyncio.get_running_loop()
        try:
            while True:
                if self.stop_mech:
                    logger.info(f"Movement stopped: {self.stop_reason}")
                    return ['completed', self.stop_reason]
                
                response = await loop.run_in_executor(None, self.messenger.receive)
                if response is not None:
                    logger.debug(f"Received response: {response}")
                    if response[0] == "error":
                        raise Exception(f"Arduino error: {response[1]}")
                    if response[0] == expected_done_cmd:
                        return response
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            raise TimeoutError(f"Timeout waiting for {expected_done_cmd}")

    def validate_command_parameters(self, command: Dict[str, Any]) -> None:
        """
        Validate the JSON command parameters before execution.
        """
        cmd_type = command.get('command')
        if cmd_type == 'move_cone':
            required_fields = ['steps', 'speed', 'direction']
        elif cmd_type == 'move_spout':
            required_fields = ['degrees', 'speed', 'direction']
        elif cmd_type == 'move_both':
            required_fields = ['cone_steps', 'cone_speed', 'spout_degrees', 'spout_speed', 'direction']
        elif cmd_type == 'zero_spout':
            required_fields = []
        elif cmd_type == 'stop_mechanism':
            required_fields = ['state', 'reason']
        elif cmd_type == 'pause':
            required_fields = ['duration']
        else:
            raise ValueError(f"Unknown command type: {cmd_type}")

        # Special validation for stop_mechanism
        if cmd_type == 'stop_mechanism':
            if not isinstance(command.get('state'), bool):
                raise ValueError("'state' must be a boolean")
            if not isinstance(command.get('reason'), str):
                raise ValueError("'reason' must be a string")
        # Special validation for pause
        elif cmd_type == 'pause':
            if 'duration' not in command or not isinstance(command['duration'], int):
                raise ValueError("'duration' (int) is required for pause command")
        else:
            # All other commands with numeric parameters
            for field in required_fields:
                if field not in command or not isinstance(command[field], int):
                    raise ValueError(f"Invalid or missing '{field}' in command.")

    async def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single command from the client.
        """
        cmd_type = command.get('command')
        
        # Handle stop mechanism command
        if cmd_type == 'stop_mechanism':
            self.stop_mech = command['state']
            self.stop_reason = command['reason']
            logger.info(f"Stop mechanism set to: {self.stop_mech}, reason: {self.stop_reason}")
            if self.stop_mech:
                self.pump_client.stop_pump()
            return {
                'command': cmd_type,
                'status': 'success',
                'data': {'stop_mech': self.stop_mech, 'reason': self.stop_reason}
            }

        # For mechanical or pause commands, check if we are already in a stop state
        if self.stop_mech:
            self.pump_client.stop_pump()
            return {
                'command': cmd_type,
                'status': 'completed',
                'data': self.stop_reason
            }

        # Read weight prior to executing commands
        weight = await self.weight_service.get_weight()
        if weight is not None:
            logging.info(f"current weight {weight}g")
        
        # If weight is above threshold, stop
        if weight is not None and weight > 600.00:
            self.stop_mech = True
            self.stop_reason = "Pour weight reached for step"
            self.pump_client.stop_pump()
            logger.info(f"Stopping mechanism: {self.stop_reason}")
            return {
                'command': cmd_type,
                'status': 'completed',
                'data': self.stop_reason
            }

        # Validate command params
        self.validate_command_parameters(command)
        
        loop = asyncio.get_running_loop()
        try:
            # ------------------------------------------------------
            # Handle the new 'pause' command (entirely local logic)
            # ------------------------------------------------------
            if cmd_type == 'pause':
                duration = command['duration']
                # Stop the pump during pause
                self.pump_client.stop_pump()
                logger.info(f"Pausing for {duration} seconds...")
                
                await asyncio.sleep(duration)
                
                # Return with completed status
                return {
                    'command': cmd_type,
                    'status': 'success',
                    'data': f"Paused for {duration} seconds"
                }

            # ------------------------------------------------------
            # Existing command types requiring microcontroller calls
            # ------------------------------------------------------
            if cmd_type == 'zero_spout':
                self.pump_client.stop_pump()
                await loop.run_in_executor(None, self.messenger.send, 'zero_spout')
                logger.info(f"Executing command: zero_spout")
                response = await asyncio.wait_for(self.wait_for_response('zero_done'), timeout=30)

            elif cmd_type == 'move_cone':
                steps = command['steps']
                speed = command['speed']
                direction = command['direction']
                # Start pump if not already running
                self.pump_client.start_pump()
                await loop.run_in_executor(None, self.messenger.send, 'move_cone', steps, speed, direction)
                logger.info(f"Executing command: move_cone with steps={steps}, speed={speed}, direction={direction}")
                response = await asyncio.wait_for(self.wait_for_response('cone_done'), timeout=30)

            elif cmd_type == 'move_spout':
                degrees = command['degrees']
                speed = command['speed']
                direction = command['direction']
                # Start pump if not already running
                self.pump_client.start_pump()
                await loop.run_in_executor(None, self.messenger.send, 'move_spout', degrees, speed, direction)
                logger.info(f"Executing command: move_spout with degrees={degrees}, speed={speed}, direction={direction}")
                response = await asyncio.wait_for(self.wait_for_response('spout_done'), timeout=30)

            elif cmd_type == 'move_both':
                cone_steps = command['cone_steps']
                cone_speed = command['cone_speed']
                spout_degrees = command['spout_degrees']
                spout_speed = command['spout_speed']
                direction = command['direction']
                # Start pump if not already running
                self.pump_client.start_pump()
                await loop.run_in_executor(
                    None,
                    self.messenger.send,
                    'move_both',
                    cone_steps,
                    cone_speed,
                    spout_degrees,
                    spout_speed,
                    direction
                )
                logger.info(
                    f"Executing command: move_both with cone_steps={cone_steps}, cone_speed={cone_speed}, "
                    f"spout_degrees={spout_degrees}, spout_speed={spout_speed}, direction={direction}"
                )
                response = await asyncio.wait_for(self.wait_for_response('both_done'), timeout=30)

            # Gather response to send back
            return {
                'command': cmd_type,
                'status': response[0] if response else 'no_response',
                'data': response[1] if response and len(response) > 1 else None
            }

        except Exception as e:
            logger.error(f"Error executing command {cmd_type}: {str(e)}", exc_info=True)
            self.pump_client.stop_pump()  # Stop pump on error
            return {
                'command': cmd_type,
                'status': 'error',
                'data': str(e)
            }

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        Handle incoming client connections and batch commands.
        """
        while True:
            try:
                data = await reader.readline()
                if not data:
                    break

                received_data = json.loads(data.decode())
                responses = []

                if isinstance(received_data, list):
                    # Clear stop_mech when starting new batch
                    self.stop_mech = False
                    self.stop_reason = "Starting new brew batch"
                    logger.info("Cleared stop_mech for new batch")
                    
                    # If already stopped, return single response for whole batch
                    if self.stop_mech:
                        self.pump_client.stop_pump()
                        responses.append({
                            'command': 'batch',
                            'status': 'completed',
                            'data': self.stop_reason
                        })
                    else:
                        # Process commands until stopped or completed
                        for command in received_data:
                            logger.info(f"Processing command {command['command']} from batch")
                            response = await self.execute_command(command)
                            responses.append(response)
                            
                            # If this command triggered a stop or an error, stop processing remaining commands
                            if response['status'] in ['completed', 'error'] or self.stop_mech:
                                if self.stop_mech:
                                    logger.info(f"Stopping batch processing: {self.stop_reason}")
                                self.pump_client.stop_pump()
                                responses.append({
                                    'command': 'remaining_batch',
                                    'status': 'completed',
                                    'data': self.stop_reason
                                })
                                break
                else:
                    # Handle single command
                    response = await self.execute_command(received_data)
                    responses.append(response)

                # Send response back to client
                writer.write((json.dumps(responses) + '\n').encode())
                await writer.drain()

            except Exception as e:
                logger.error(f"Error handling client request: {e}", exc_info=True)
                self.pump_client.stop_pump()  # Stop pump on error
                error_response = json.dumps({'error': str(e)})
                writer.write((error_response + '\n').encode())
                await writer.drain()

    async def start_server(self) -> None:
        """
        Start the UNIX socket server and await connections.
        """
        try:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
        except OSError as e:
            logger.error(f"Error unlinking socket: {e}")

        server = await asyncio.start_unix_server(
            self.handle_client, 
            path=self.socket_path
        )

        logger.info(f"Mech-Control service started on {self.socket_path}")
        
        async with server:
            await server.serve_forever()

    def cleanup(self) -> None:
        """
        Perform cleanup on shutdown: stop pumps, close Arduino connection, remove socket.
        """
        self.pump_client.stop_pump()  # Ensure pump is stopped on cleanup
        self.arduino.close()
        try:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
        except OSError as e:
            logger.error(f"Error cleaning up socket: {e}")

if __name__ == "__main__":
    service = MechControlService()
    
    try:
        asyncio.run(service.start_server())
    except KeyboardInterrupt:
        logger.info("Shutting down Mech-Control service...")
    finally:
        service.cleanup()
