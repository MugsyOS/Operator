import pigpio

# Define the pins used by the HX711
pins_to_release = [17, 27, 5, 6]  # Add all pins that might be used

# Connect to pigpio daemon
pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon.")
    exit(1)

# Reset each pin
for pin in pins_to_release:
    pi.set_mode(pin, pigpio.INPUT)  # Set pin mode to INPUT to release it
    pi.set_pull_up_down(pin, pigpio.PUD_OFF)  # Disable any pull up/down resistors
    pi.write(pin, 0)  # Write a low value to reset the state

pi.stop()
print("Pins released successfully.")
