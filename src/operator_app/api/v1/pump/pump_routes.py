# pragma: no cover
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from enum import Enum
import pigpio
import configparser

# Load configurations
config = configparser.ConfigParser()
config.read('hardware_config.ini')
min_flow_rate = config.getint('PUMP', 'MIN_FLOW_RATE', fallback=40)

class PumpDirection(str, Enum):
  forward = "forward"
  reverse = "reverse"
  stop = "stop"

class PumpControl(BaseModel):
  direction: PumpDirection

class PumpSpeedControl(BaseModel):
  direction: PumpDirection
  speed: int = Field(..., ge=40, le=100, description="minimum flow rate setting to 100")

router = APIRouter()
pi = pigpio.pi()

# Define the pin numbers for forward and reverse
FORWARD_PIN = 13
REVERSE_PIN = 19

@router.post("/")
async def control_pump(pump: PumpControl):
  # Initialize the GPIO pins
  pi.set_mode(FORWARD_PIN, pigpio.OUTPUT)
  pi.set_mode(REVERSE_PIN, pigpio.OUTPUT)

  # Ensure both pins are initially low
  pi.write(FORWARD_PIN, 0)
  pi.write(REVERSE_PIN, 0)

  if pump.direction == PumpDirection.forward:
    pi.write(FORWARD_PIN, 1)  # Activate forward
    pi.write(REVERSE_PIN, 0)  # Ensure reverse is deactivated
  elif pump.direction == PumpDirection.reverse:
    pi.write(FORWARD_PIN, 0)  # Ensure forward is deactivated
    pi.write(REVERSE_PIN, 1)  # Activate reverse
  elif pump.direction == PumpDirection.stop:
    # Both pins low stops the pump
    pi.write(FORWARD_PIN, 0)
    pi.write(REVERSE_PIN, 0)

  return {"status": f"Pump set to {pump.direction}"}

@router.post("/flow-rate")
async def control_pump_speed(pump: PumpSpeedControl):
  # Initialize the GPIO pins
  pi.set_mode(FORWARD_PIN, pigpio.OUTPUT)
  pi.set_mode(REVERSE_PIN, pigpio.OUTPUT)

  duty_cycle = int(pump.speed * 255 / 100)  # Calculate the PWM duty cycle

  # Ensure both pins are initially low
  pi.write(FORWARD_PIN, 0)
  pi.write(REVERSE_PIN, 0)

  if pump.direction == PumpDirection.forward:
    pi.set_PWM_dutycycle(FORWARD_PIN, duty_cycle)  # Set PWM duty cycle for speed
    pi.write(REVERSE_PIN, 0)  # Ensure reverse is deactivated
  elif pump.direction == PumpDirection.reverse:
    pi.set_PWM_dutycycle(REVERSE_PIN, duty_cycle)  # Set PWM duty cycle for speed
    pi.write(FORWARD_PIN, 0)  # Ensure forward is deactivated
  elif pump.direction == PumpDirection.stop:
    pi.set_PWM_dutycycle(FORWARD_PIN, 0)
    pi.set_PWM_dutycycle(REVERSE_PIN, 0)  # Stop the pump by setting duty cycle to 0

  return {"status": f"Pump set to {pump.direction} at {pump.speed}% speed"}