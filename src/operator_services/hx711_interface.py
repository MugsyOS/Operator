import pigpio
from libs.hx711 import HX711
import time
import statistics as stat

class HX711Interface:
    def __init__(self, dout_pin, pd_sck_pin):
        self.pi = pigpio.pi()
        self.hx = HX711(self.pi, dout_pin=dout_pin, pd_sck_pin=pd_sck_pin)
        self.calibration_factor = 1
        self.offset = 0

    def tare(self, readings=30):
        values = [self.hx.read() for _ in range(readings)]
        values = [x for x in values if x is not False]
        if values:
            self.offset = stat.mean(values)
            return True
        return False

    def calibrate(self, known_weight_grams, delay_seconds=10):
        print(f"Please wait {delay_seconds} seconds to place the known weight...")
        time.sleep(delay_seconds)
        print("Taking readings for calibration...")
        readings = [self.hx.read() for _ in range(30)]
        readings = [r for r in readings if r is not False]
        if not readings:
            return False
        average_reading = stat.mean(readings) - self.offset
        self.calibration_factor = known_weight_grams / average_reading
        return True

    def get_weight(self, readings=10):
        values = [self.hx.read() for _ in range(readings)]
        values = [x for x in values if x is not False]
        if not values:
            return None
        average = stat.mean(values)
        return (average - self.offset) * self.calibration_factor

    def cleanup(self):
        self.pi.stop()