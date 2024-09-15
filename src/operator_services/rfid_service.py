import time
import datetime
import binascii
import signal
import sys
from typing import Tuple
from pn532pi import Pn532, Pn532I2c
from pn532pi.nfc.pn532 import PN532_MIFARE_ISO14443A_106KBPS
import requests
import configparser
import logging

# Constants
CONFIG_FILE = 'src/operator_app/hardware_config.ini'
UID_COOLDOWN = 600  # seconds
SCAN_INTERVAL = 0.1  # seconds
CARD_READ_DELAY = 0.5  # seconds
MAIN_LOOP_DELAY = 1  # seconds

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def read_config() -> Tuple[str, int]:
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return (
        config.get('DECAF_API', 'DECAF_RFID_API_URL'),
        config.getint('NFC', 'I2C_BUS', fallback=1)
    )

def setup_nfc(i2c_bus: int) -> Pn532:
    pn532_i2c = Pn532I2c(i2c_bus)
    nfc = Pn532(pn532_i2c)
    nfc.begin()
    versiondata = nfc.getFirmwareVersion()
    if not versiondata:
        logger.error("Didn't find PN53x board")
        raise RuntimeError("Didn't find PN53x board")
    nfc.SAMConfig()
    logger.info(f"Found chip PN5 {versiondata >> 24 & 0xFF}, Firmware ver. {versiondata >> 16 & 0xFF}.{versiondata >> 8 & 0xFF}")
    return nfc

def send_uid_to_api(url: str, uid: str) -> bool:
    headers = {"Content-Type": "application/json"}
    data = {"uid": uid}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        logger.info("Successfully sent UID to API.")
        logger.info(f"API Response: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send UID to API: {str(e)}")
        return False

def loop(nfc: Pn532, api_url: str):
    last_uid = None
    last_read_time = None

    while True:
        time.sleep(SCAN_INTERVAL)
        success, uid = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A_106KBPS)
        if success:
            logger.info("Found an ISO14443A card")
            logger.info(f"UID Length: {len(uid)}")
            uid_value = binascii.hexlify(uid).decode('utf-8')
            logger.info(f"UID Value: {uid_value}")
            time.sleep(CARD_READ_DELAY)

            current_time = datetime.datetime.now()
            if last_uid == uid_value and (current_time - last_read_time).total_seconds() < UID_COOLDOWN:
                logger.info("UID already read or cooldown period not elapsed.")
                continue

            if send_uid_to_api(api_url, uid_value):
                last_uid = uid_value
                last_read_time = current_time

        time.sleep(MAIN_LOOP_DELAY)

def signal_handler(signum, frame):
    logger.info("Received shutdown signal. Exiting gracefully...")
    sys.exit(0)

def main():
    logger.info("Starting RFID service")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        api_url, i2c_bus = read_config()
        nfc_module = setup_nfc(i2c_bus)
        loop(nfc_module, api_url)
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()