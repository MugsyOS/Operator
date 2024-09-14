import time
import datetime
import binascii
from pn532pi import Pn532, Pn532I2c
from pn532pi.nfc.pn532 import PN532_MIFARE_ISO14443A_106KBPS
import requests
import configparser
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Read the configuration file
config = configparser.ConfigParser()
config.read('src/operator_app/hardware_config.ini')

# Get the URL from the configuration file
decf_url = config.get('DECAF_API', 'DECAF_RFID_API_URL')

def setup_nfc():
    pn532_i2c = Pn532I2c(1)
    nfc = Pn532(pn532_i2c)
    nfc.begin()
    versiondata = nfc.getFirmwareVersion()
    if not versiondata:
        logging.error("Didn't find PN53x board")
        raise RuntimeError("Didn't find PN53x board")
    nfc.SAMConfig()
    logging.info(f"Found chip PN5 {versiondata >> 24 & 0xFF}, Firmware ver. {versiondata >> 16 & 0xFF}.{versiondata >> 8 & 0xFF}")
    return nfc

def loop(nfc):
    last_uid = None
    last_read_time = None

    while True:
        time.sleep(0.1)
        success, uid = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A_106KBPS)
        if success:
            logging.info("Found an ISO14443A card")
            logging.info(f"UID Length: {len(uid)}")
            uid_value = binascii.hexlify(uid).decode('utf-8')
            logging.info(f"UID Value: {uid_value}")
            time.sleep(0.5)

            # Check if the current UID is the same as the last read UID and if less than 10 minutes have passed since it was read
            if last_uid == uid_value and (datetime.datetime.now() - last_read_time).total_seconds() < 600:
                logging.info("UID already read or less than 10 minutes have passed since it was read.")
                continue

            # Make a POST request with a JSON payload containing the UID
            headers = {"Content-Type": "application/json"}
            data = {"uid": uid_value}
            response = requests.post(decf_url, headers=headers, json=data)

            if response.status_code == 200:
                logging.info("Successfully sent UID to API.")
                logging.info(f"API Response: {response.json()}")
            else:
                logging.error(f"Failed to send UID to API. Status code: {response.status_code}")

            # Update the last read UID and the time it was read
            last_uid = uid_value
            last_read_time = datetime.datetime.now()

        time.sleep(1)

if __name__ == "__main__":
    logging.info("Starting RFID service")
    try:
        nfc_module = setup_nfc()
        loop(nfc_module)
    except Exception as e:
        logging.exception(f"An error occurred: {str(e)}")