import pigpio

pi = pigpio.pi()

def turn_on(gpio_pin):
    if not pi.connected:
        return {"error": "GPIO daemon not connected"} # pragma: no cover
    pi.set_mode(gpio_pin, pigpio.OUTPUT) # pragma: no cover
    pi.write(gpio_pin, 1) # pragma: no cover
    return {"gpio_pin": gpio_pin, "status": "on"}

def turn_off(gpio_pin):
    if not pi.connected:
        return {"error": "GPIO daemon not connected"} # pragma: no cover
    pi.set_mode(gpio_pin, pigpio.OUTPUT) # pragma: no cover
    pi.write(gpio_pin, 0) # pragma: no cover
    return {"gpio_pin": gpio_pin, "status": "off"}