from fastapi import APIRouter
from .status_services import turn_on, turn_off, read_state

router = APIRouter()

@router.get("/on/{gpio_pin}")
def turn_on_route(gpio_pin: int):
    return turn_on(gpio_pin)

@router.get("/off/{gpio_pin}")
def turn_off_route(gpio_pin: int):
    return turn_off(gpio_pin)

@router.get("/state/{gpio_pin}")
def read_state_route(gpio_pin: int):
    return read_state(gpio_pin)
