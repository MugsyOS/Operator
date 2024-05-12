import socket
import os
import json
from operator_services.lib.hx711 import HX711  # Adjust the import as per your structure
import pigpio
import configparser
from statistics import mean

# Unix Socket Path
socket_path = "/tmp/pour_weight_service.sock"

# Get the absolute directory of the script
base_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the configuration file
config_path = os.path.join(base_dir, 'config', 'calibration.ini')

# Ensure the socket does not already exist
try:
    os.unlink(socket_path)
except OSError:
    if os.path.exists(socket_path):
        raise

def handle_calibration(hx, data):
    known_weight_grams = data["known_weight_grams"]
    err = hx.zero()
    if err:
        return {"error": str(err)}

    # Placeholder for delay for user action
    import time
    time.sleep(10)

    reading = hx.get_weight()
    if not reading:
        return {"error": "Cannot calculate mean value. Variable reading: " + str(reading)}

    ratio = reading / known_weight_grams
    hx.set_scale_ratio(ratio)

    config = configparser.ConfigParser()
    config.read(config_path)
    config['DEFAULT']['CalibrationValue'] = str(ratio)
    config['DEFAULT']['TareWeight'] = str(hx.offset)
    with open(config_path, 'w') as configfile:
        config.write(configfile)

    return {"status": "Calibration successful", "ratio": ratio}

def handle_read_weight(hx):
    readings = 5
    values = [hx.read() for _ in range(readings)]
    values = [x for x in values if x is not False]

    if not values:
        return {"error": "Cannot get valid readings"}

    config = configparser.ConfigParser()
    config.read(config_path)
    ratio = float(config['DEFAULT']['CalibrationValue'])
    tare_weight = float(config['DEFAULT']['TareWeight'])

    weight = (mean(values) - tare_weight) / ratio
    return {"weight": weight}

def main():
    pi = pigpio.pi()
    hx = HX711(pi, dout_pin=5, pd_sck_pin=6)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(socket_path)
    server.listen()

    while True:
        connection, client_address = server.accept()
        try:
            while True:
                data = connection.recv(1024)
                if data:
                    request = json.loads(data.decode())
                    if request["action"] == "calibrate":
                        response = handle_calibration(hx, request)
                    elif request["action"] == "read_weight":
                        response = handle_read_weight(hx)
                    connection.sendall(json.dumps(response).encode())
                else:
                    break
        finally:
            connection.close()

if __name__ == "__main__":
    main()
