from fastapi import APIRouter, BackgroundTasks
from typing import Optional
from pydantic import BaseModel
from .pin_services import turn_on, turn_off

router = APIRouter()

class PinData(BaseModel):
    gpio_pin: int
    time: Optional[int] = None

@router.post("/on")
def turn_on_route(pin_data: PinData, background_tasks: BackgroundTasks):
    return turn_on(pin_data.gpio_pin, pin_data.time, background_tasks)

@router.get("/off/{gpio_pin}")
def turn_off_route(gpio_pin: int):
    return turn_off(gpio_pin)
