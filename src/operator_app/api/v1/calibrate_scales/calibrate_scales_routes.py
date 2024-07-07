from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import asyncio
import configparser
import pigpio
import json
from HX711 import SimpleHX711, GpioException, TimeoutException, Options
import os

# Read configuration
config = configparser.ConfigParser()
config_path = 'src/operator_app/hardware_config.ini'
if not os.path.exists(config_path):
    raise FileNotFoundError(f"Configuration file not found: {config_path}")

config.read(config_path)

router = APIRouter()

class CalibrationStep(BaseModel):
    message: str

@router.websocket("/{scale_type}")
async def websocket_endpoint(websocket: WebSocket, scale_type: str):
    await websocket.accept()
    if scale_type not in ["CONE_SCALE", "MUG_SCALE"]:
        await websocket.send_json({"error": "Invalid scale type. Please use CONE_SCALE or MUG_SCALE."})
        await websocket.close(code=1008)  # Policy violation code
        return

    # Retrieve data and clock pins from configuration
    try:
        if scale_type == "CONE_SCALE":
            data_pin = int(config['SCALES']['CONE_SCALE_DATA_PIN'])
            clock_pin = int(config['SCALES']['CONE_SCALE_CLOCK_PIN'])
        elif scale_type == "MUG_SCALE":
            data_pin = int(config['SCALES']['MUG_SCALE_DATA_PIN'])
            clock_pin = int(config['SCALES']['MUG_SCALE_CLOCK_PIN'])
    except KeyError as e:
        await websocket.send_json({"error": f"Missing configuration for {scale_type}: {e}"})
        await websocket.close(code=1011)  # Internal error code
        return

    # Connect to pigpio daemon
    pi = pigpio.pi()
    if not pi.connected:
        await websocket.send_json({"error": "Failed to connect to pigpio daemon."})
        await websocket.close(code=1011)
        return

    # Initialize HX711
    try:
        hx = SimpleHX711(data_pin, clock_pin, 1, 0)
        await websocket.send_json({"message": "Successfully connected to HX711 chip."})
    except GpioException:
        await websocket.send_json({"error": "Failed to connect to HX711 chip due to GPIO exception."})
        await websocket.close(code=1011)
        return
    except TimeoutException:
        await websocket.send_json({"error": "Failed to connect to HX711 chip due to timeout."})
        await websocket.close(code=1011)
        return

    try:
        # Step 1: Request unit
        await websocket.send_json({"message": "Enter the unit you want to measure the object in (e.g., g, kg, lb, oz):"})
        unit = (await websocket.receive_json())["unit"]

        # Step 2: Request known weight
        await websocket.send_json({"message": f"Enter the weight of the object in {unit}:"})
        known_weight = float((await websocket.receive_json())["known_weight"])

        # Step 3: Request number of samples
        await websocket.send_json({"message": "Enter the number of samples to take from the HX711 chip (e.g., 15):"})
        samples = int((await websocket.receive_json())["samples"])

        # Create Options object for read method
        options = Options(samples)

        # Step 4: Zero the scale
        await websocket.send_json({"message": "Remove all objects from the scale and then press enter."})
        await websocket.receive_json()  # Wait for user to press enter
        zero_value = hx.read(options)
        await websocket.send_json({"message": "Scale zeroed. Value: " + str(zero_value)})

        # Step 5: Measure known weight
        await websocket.send_json({"message": "Place the object on the scale and then press enter."})
        await websocket.receive_json()  # Wait for user to press enter
        raw_value = hx.read(options)
        ref_unit = (raw_value - zero_value) / known_weight
        ref_unit = round(ref_unit, 0) if ref_unit != 0 else 1

        # Send calibration results
        await websocket.send_json({
            "message": "Calibration complete.",
            "known_weight": known_weight,
            "unit": unit,
            "raw_value": raw_value,
            "samples": samples,
            "reference_unit": ref_unit,
            "zero_value": zero_value
        })
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        pi.stop()  # Stop pigpio connection
        await websocket.close()
