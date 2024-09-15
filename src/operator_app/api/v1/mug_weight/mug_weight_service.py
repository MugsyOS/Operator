import asyncio
import json
import logging
from pydantic_settings import BaseSettings
from starlette.websockets import WebSocketState, WebSocketDisconnect
import pigpio
import configparser
import os

# Read configuration
config = configparser.ConfigParser()
config_path = os.path.join('src', 'operator_app', 'hardware_config.ini')
config.read(config_path)

# Configuration
FORWARD_PIN = config.getint('PUMP', 'forward_pin')
REVERSE_PIN = config.getint('PUMP', 'reverse_pin')
SOCKET_PATH = config.get('SCALES', 'mug_scale_socket_path', fallback="/tmp/mug_scale_service.sock")

pi = pigpio.pi()


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class Settings(BaseSettings):
    WEIGHT_SERVICE_SOCKET: str = "/tmp/mug_scale_service.sock"

settings = Settings()

async def start_weight_stream(websocket):
    try:
        reader, writer = await asyncio.open_unix_connection(settings.WEIGHT_SERVICE_SOCKET)
        writer.write(b"stream_start\n")
        await writer.drain()
        
        while True:
            if websocket.client_state == WebSocketState.DISCONNECTED:
                logging.info("WebSocket disconnected, stopping stream")
                break

            try:
                response = await reader.readline()
                if not response:
                    logging.warning("Empty response from weight service, retrying...")
                    await asyncio.sleep(0.1)
                    continue

                data = json.loads(response.decode().strip())
                
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(data)
                else:
                    logging.info("WebSocket no longer connected, stopping stream")
                    break

            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON: {e}")
                continue
            except WebSocketDisconnect:
                logging.info("WebSocket disconnected, stopping stream")
                break
            except Exception as e:
                logging.error(f"Error in weight streaming: {e}", exc_info=True)
                break

    except asyncio.CancelledError:
        logging.info("Weight stream cancelled")
    except Exception as e:
        logging.error(f"Error in weight streaming: {e}", exc_info=True)
    finally:
        if 'writer' in locals():
            try:
                writer.write(b"stream_stop\n")
                await writer.drain()
            except Exception as e:
                logging.error(f"Error stopping stream: {e}", exc_info=True)
            finally:
                writer.close()
                await writer.wait_closed()
        logging.info("Weight stream stopped")

async def get_current_weight():
    try:
        reader, writer = await asyncio.open_unix_connection(settings.WEIGHT_SERVICE_SOCKET)
        writer.write(b"single_read\n")
        await writer.drain()
        
        response = await asyncio.wait_for(reader.readline(), timeout=5.0)
        
        writer.close()
        await writer.wait_closed()
        
        data = json.loads(response.decode().strip())
        return data
    except asyncio.TimeoutError:
        logging.error("Timeout while waiting for weight service response")
        return {"error": "Weight service timed out"}
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {e}")
        return {"error": "Invalid response from weight service"}
    except Exception as e:
        logging.error(f"Error getting weight: {e}", exc_info=True)
        return {"error": "Failed to get weight"}

async def pump_to_weight(target_weight: float, pump_speed: int, tolerance: float = 0.5):
    reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)
    
    try:
        # Zero the scale before starting
        await zero_scale()

        # Initialize GPIO pins
        pi.set_mode(FORWARD_PIN, pigpio.OUTPUT)
        pi.set_mode(REVERSE_PIN, pigpio.OUTPUT)

        # Ensure both pins are initially low
        pi.write(FORWARD_PIN, 0)
        pi.write(REVERSE_PIN, 0)

        # Start the pump
        duty_cycle = int(pump_speed * 255 / 100)  # Convert speed percentage to duty cycle
        pi.set_PWM_dutycycle(FORWARD_PIN, duty_cycle)
        
        writer.write(b"stream_start\n")
        await writer.drain()
        
        while True:
            response = await reader.readline()
            if not response:
                raise Exception("Empty response from weight service")
            
            data = json.loads(response.decode().strip())
            current_weight = data['weight']
            logging.info(f"Current weight: {current_weight}")
            
            if current_weight >= target_weight - tolerance:
                # Stop the pump
                logging.info(f"Final weight: {current_weight}")
                pi.set_PWM_dutycycle(FORWARD_PIN, 0)
                break
            
            await asyncio.sleep(0.1)  # Small delay to prevent overwhelming the system
        
        return {"status": "success", "final_weight": current_weight}
    
    except Exception as e:
        logging.error(f"Error in pump_to_weight: {e}", exc_info=True)
        # Ensure pump is stopped in case of error
        pi.set_PWM_dutycycle(FORWARD_PIN, 0)
        return {"status": "error", "message": str(e)}
    
    finally:
        # Make sure to stop the pump
        pi.set_PWM_dutycycle(FORWARD_PIN, 0)
        writer.write(b"stream_stop\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

async def zero_scale():
    try:
        reader, writer = await asyncio.open_unix_connection(settings.WEIGHT_SERVICE_SOCKET)
        writer.write(b"zero\n")
        await writer.drain()
        
        response = await asyncio.wait_for(reader.readline(), timeout=5.0)
        
        writer.close()
        await writer.wait_closed()
        
        data = json.loads(response.decode().strip())
        return data
    except asyncio.TimeoutError:
        logging.error("Timeout while waiting for weight service response")
        return {"error": "Weight service timed out"}
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {e}")
        return {"error": "Invalid response from weight service"}
    except Exception as e:
        logging.error(f"Error zeroing scale: {e}", exc_info=True)
        return {"error": "Failed to zero scale"}