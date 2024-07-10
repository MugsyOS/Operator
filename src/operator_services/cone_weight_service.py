from hx711_interface import HX711Interface
import json
import os
import time

class WeightService:
    def __init__(self, config_path):
        self.config_path = config_path
        self.load_config()
        self.hx = HX711Interface(dout_pin=self.dout_pin, pd_sck_pin=self.pd_sck_pin)
        self.hx.calibration_factor = self.calibration_factor
        self.hx.offset = self.offset

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            self.dout_pin = config.get('dout_pin', 17)
            self.pd_sck_pin = config.get('pd_sck_pin', 27)
            self.calibration_factor = config.get('calibration_factor', 1)
            self.offset = config.get('offset', 0)
        else:
            self.dout_pin = 5
            self.pd_sck_pin = 6
            self.calibration_factor = 1
            self.offset = 0

    def save_config(self):
        config = {
            'dout_pin': self.dout_pin,
            'pd_sck_pin': self.pd_sck_pin,
            'calibration_factor': self.hx.calibration_factor,
            'offset': self.hx.offset
        }
        with open(self.config_path, 'w') as f:
            json.dump(config, f)

    def calibrate(self, known_weight_grams, delay_seconds=10):
        print("Starting calibration process...")
        print("Taring the scale. Please ensure the scale is empty.")
        if self.hx.tare():
            print("Tare successful.")
            print(f"Please place the {known_weight_grams}g weight on the scale.")
            if self.hx.calibrate(known_weight_grams, delay_seconds):
                self.save_config()
                print("Calibration successful and configuration saved.")
                return True
            else:
                print("Calibration failed.")
                return False
        else:
            print("Tare failed. Unable to proceed with calibration.")
            return False

    def get_weight(self):
        return self.hx.get_weight()

    def cleanup(self):
        self.hx.cleanup()