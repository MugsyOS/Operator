#  Currently refactoring this to utilize a service -m
# from fastapi import APIRouter, Depends, Body, HTTPException
# from .lib.hx711 import HX711  # import the class HX711
# import pigpio
# import time
# import configparser
# from pydantic import BaseModel
# from statistics import mean

# class CalibrationItem(BaseModel):
#     known_weight_grams: float

# router = APIRouter()

# def get_hx():
#     pi = pigpio.pi()
#     hx = HX711(pi, dout_pin=5, pd_sck_pin=6)
#     return hx

# @router.post("/calibrate")
# def calibrate(item: CalibrationItem, hx: HX711 = Depends(get_hx)):
#     try:
#         err = hx.zero()
#         if err is not None:
#             raise ValueError(err)

#         print(f"Tare weight (offset): {hx.offset}")  # Print the tare weight

#         time.sleep(10)  # Wait for 10 seconds to give the user time to place the known weight on the scale

#         reading = hx.get_weight()
#         if not reading:
#             raise ValueError('Cannot calculate mean value. Try debug mode. Variable reading:', reading)

#         known_weight_grams = item.known_weight_grams
#         ratio = reading / known_weight_grams
#         hx.set_scale_ratio(ratio)

#         # Write the calibration value and tare weight to the config_hardware.ini file
#         config = configparser.ConfigParser()
#         config.read('config_hardware.ini')
#         config['DEFAULT']['CalibrationValue'] = str(ratio)
#         config['DEFAULT']['TareWeight'] = str(hx.offset)
#         with open('config_hardware.ini', 'w') as configfile:
#             config.write(configfile)

#         print(f"Written tare weight: {config['DEFAULT']['TareWeight']}")  # Print the written tare weight

#         return {"status": "Calibration successful", "ratio": ratio}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/read-weight")
# def get_weight(hx: HX711 = Depends(get_hx)):
#   readings = 5
#   values = [hx.read() for _ in range(readings)]
#   values = [x for x in values if x is not False]  # Filter out invalid readings

#   if not values:
#     raise HTTPException(status_code=500, detail="Cannot get valid readings")

#   # Load the calibration ratio and tare weight from the config file
#   config = configparser.ConfigParser()
#   config.read('config_hardware.ini')
#   ratio = float(config['DEFAULT']['CalibrationValue'])
#   tare_weight = float(config['DEFAULT']['TareWeight'])

#   # Calculate the weight
#   weight = (mean(values) - tare_weight) / ratio

#   return {"weight": weight}