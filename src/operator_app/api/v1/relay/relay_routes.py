from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from enum import Enum
import pigpio
import asyncio
import logging
from typing import Optional, Dict
import socket
import json
import configparser

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

config = configparser.ConfigParser()
config.read('src/operator_app/hardware_config.ini')

class RelayMapping(BaseModel):
    mapping: Dict[int, int] = {
        1: int(config['RELAY_CHANNELS']['CHANNEL_1']),
        2: int(config['RELAY_CHANNELS']['CHANNEL_2']),
        3: int(config['RELAY_CHANNELS']['CHANNEL_3']),
        4: int(config['RELAY_CHANNELS']['CHANNEL_4'])
    }

class State(str, Enum):
    on = "on"
    off = "off"

class Relay(BaseModel):
    relay_channel: int
    state: State
    timer: Optional[int] = None


class WeightGrind(BaseModel):
    relay_channel: int
    target_weight: float = Field(..., gt=0)
    timeout: Optional[int] = 30

router = APIRouter()
pi = pigpio.pi()
socket_path = "/tmp/watchtower_socket"
CONE_SCALE_SOCKET_PATH = "/tmp/cone_scale_service.sock"

def send_command_to_watchtower(command):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(json.dumps(command).encode())

async def set_relay_off_after_timer(gpio_pin: int, timer: int):
    await asyncio.sleep(timer)
    pi.write(gpio_pin, 1)  # Turn off relay

async def grind_to_weight(gpio_pin: int, target_weight: float, timeout: int = 30):
    reader = None
    writer = None
    
    try:
        logging.info(f"Zeroing scale before grinding to target weight: {target_weight}")
        zero_reader, zero_writer = await asyncio.open_unix_connection(CONE_SCALE_SOCKET_PATH)
        zero_writer.write(b"zero\n")
        await zero_writer.drain()
        
        zero_response = await asyncio.wait_for(zero_reader.readline(), timeout=3.0)
        zero_writer.close()
        await zero_writer.wait_closed()
        
        if not zero_response:
            logging.error("Failed to zero scale")
            return
        
        logging.info(f"Starting grinder (relay {gpio_pin})")
        pi.write(gpio_pin, 0)  # Turn on the relay
        
        reader, writer = await asyncio.open_unix_connection(CONE_SCALE_SOCKET_PATH)
        writer.write(b"stream_start\n")
        await writer.drain()
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                logging.warning(f"Grinding timeout after {timeout} seconds")
                break
            
            try:
                response = await asyncio.wait_for(reader.readline(), timeout=1.0)
                if not response:
                    logging.warning("Empty response from weight service, continuing...")
                    await asyncio.sleep(0.1)
                    continue
                
                data = json.loads(response.decode().strip())
                if "error" in data:
                    logging.error(f"Scale error: {data['error']}")
                    continue
                
                current_weight = data.get("weight", 0)
                logging.debug(f"Current weight: {current_weight}, target: {target_weight}")
                
                if current_weight >= target_weight:
                    logging.info(f"Target weight reached: {current_weight} >= {target_weight}")
                    pi.write(gpio_pin, 1)  #turn off the relay
                    
                    try:
                        writer.write(b"stream_stop\n")
                        await writer.drain()
                    except Exception as e:
                        logging.error(f"Error sending stream_stop: {e}", exc_info=True)
                    break
                
            except asyncio.TimeoutError:
                logging.warning("Timeout reading from scale, continuing...")
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON: {e}")
            except Exception as e:
                logging.error(f"Error in weight streaming: {e}", exc_info=True)
                break
                        
            await asyncio.sleep(0.1)
            
    except Exception as e:
        logging.error(f"Unexpected error in grind_to_weight: {e}", exc_info=True)
    finally:
        logging.info("Stopping grinder (final cleanup)")
        pi.write(gpio_pin, 1)
        
        if writer is not None:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                logging.error(f"Error cleaning up scale connection: {e}")
        
        logging.info("Grinding completed")

@router.post("/", response_model=Relay)
async def set_relay(relay: Relay, background_tasks: BackgroundTasks):
    relay_mapping = RelayMapping()
    gpio_pin = relay_mapping.mapping.get(relay.relay_channel)
    if gpio_pin is None:
        raise HTTPException(status_code=400, detail="Invalid relay_channel.")
    
    pi.set_mode(gpio_pin, pigpio.OUTPUT)
    
    if relay.state == State.on:
        watchtower_details = {"pin": gpio_pin, "delay": 300}  # Format command for watchtower
        send_command_to_watchtower(watchtower_details)
        pi.write(gpio_pin, 0)  # Turn on the relay
    else:
        pi.write(gpio_pin, 1)  # Turn off the relay
    
    if relay.timer:
        background_tasks.add_task(set_relay_off_after_timer, gpio_pin, relay.timer)
    
    return relay

@router.post("/grind-by-weight", response_model=WeightGrind)
async def grind_by_weight(request: WeightGrind, background_tasks: BackgroundTasks):
    relay_mapping = RelayMapping()
    gpio_pin = relay_mapping.mapping.get(request.relay_channel)
    
    if gpio_pin is None:
        raise HTTPException(status_code=400, detail="Invalid relay_channel.")
    
    pi.set_mode(gpio_pin, pigpio.OUTPUT)
    
    watchtower_details = {"pin": gpio_pin, "delay": request.timeout * 1000}  # delay in ms
    send_command_to_watchtower(watchtower_details)
    
    background_tasks.add_task(
        grind_to_weight, 
        gpio_pin, 
        request.target_weight, 
        request.timeout
    )
    
    return request
