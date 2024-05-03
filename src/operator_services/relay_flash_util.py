import pigpio
import time

def flash_pins(pi, pins, duration, flash_duration=0.5):
    end_time = time.time() + duration
    while time.time() < end_time:
        for pin in pins:
            pi.write(pin, 0)  # Turn all specified pins on
        time.sleep(flash_duration)  # Keep them on for half a second
        for pin in pins:
            pi.write(pin, 1)  # Turn all specified pins off
        time.sleep(flash_duration)  # Off for half a second

pi = pigpio.pi()
if not pi.connected:
    print("Pigpio daemon is not running.")
else:
    try:
        pins = [22, 23, 24, 25]  # List of pins to control
        for pin in pins:
            pi.set_mode(pin, pigpio.OUTPUT)  # Set each pin as an output
        print("Flashing pins...")
        flash_pins(pi, pins, 5)  # Flash all pins for 5 seconds
    finally:
        pi.stop()
        print("Done flashing pins and disconnected from pigpio.")
