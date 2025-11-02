import time
from rpi_ws281x import PixelStrip, Color

# LED strip configuration:
LED_COUNT = 1        # Number of LED pixels.
LED_PIN = 18         # GPIO pin connected to the pixels (18 uses PWM).
LED_FREQ_HZ = 800000 # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10         # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 50  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0      # set to '1' for GPIOs 13, 19, 41, 45 or 53

# Create PixelStrip object with our configuration
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
# Initialize the library (must be called once before other functions)
strip.begin()

def color_wipe(color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms/1000.0)

print('Press Ctrl-C to quit.')

try:
    while True:
        print('Color wipe: Red')
        color_wipe(Color(255, 0, 0))  # Red
        time.sleep(1)
        
        print('Color wipe: Green')
        color_wipe(Color(0, 255, 0))  # Green
        time.sleep(1)
        
        print('Color wipe: Blue')
        color_wipe(Color(0, 0, 255))  # Blue
        time.sleep(1)
        
        print('LEDs off')
        color_wipe(Color(0, 0, 0))    # Turn off
        time.sleep(0.5)

except KeyboardInterrupt:
    color_wipe(Color(0, 0, 0))  # Turn off all LEDs
    print('Test finished.')