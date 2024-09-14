#!/usr/bin/env python3

import asyncio
import json
import logging
import signal
import socket
import sys
from enum import Enum
from typing import Optional

import pigpio
from HX711 import SimpleHX711, GpioException, TimeoutException, Mass

# Configuration
DATA_PIN = 5
CLOCK_PIN = 6
REF_UNIT = 473
OFFSET = 97870
SOCKET_PATH = "/tmp/scale_service.sock"
SAMPLE_SIZE = 35

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Command(Enum):
    STREAM_START = "stream_start"
    STREAM_STOP = "stream_stop"
    SINGLE_READ = "single_read"

class ScaleService:
    def __init__(self):
        self.hx: Optional[SimpleHX711] = None
        self.pi: Optional[pigpio.pi] = None
        self.streaming = False

    async def initialize(self):
        try:
            self.pi = pigpio.pi()
            if not self.pi.connected:
                raise ConnectionError("Failed to connect to pigpio daemon.")

            self.hx = SimpleHX711(DATA_PIN, CLOCK_PIN, REF_UNIT, OFFSET)
            self.hx.setUnit(Mass.Unit.G)
            self.hx.zero()
            logging.info("Successfully connected to HX711 chip.")
        except (GpioException, TimeoutException, ConnectionError) as e:
            logging.error(f"Failed to initialize: {e}")
            self.cleanup()
            sys.exit(1)

    def cleanup(self):
        logging.info("Cleaning up resources...")
        if self.hx:
            self.hx.cleanup()
        if self.pi:
            self.pi.stop()

    async def handle_client(self, reader, writer):
        while True:
            try:
                data = await reader.read(100)
                if not data:
                    break

                message = data.decode().strip()
                command = Command(message)

                if command == Command.STREAM_START:
                    self.streaming = True
                    self.hx.zero()
                    asyncio.create_task(self.stream_weight(writer))
                elif command == Command.STREAM_STOP:
                    self.streaming = False
                elif command == Command.SINGLE_READ:
                    weight = self.hx.weight(SAMPLE_SIZE)
                    response = json.dumps({"weight": weight}) + "\n"
                    writer.write(response.encode())
                    await writer.drain()

            except ValueError:
                logging.warning(f"Invalid command received: {message}")
            except Exception as e:
                logging.error(f"Error handling client: {e}")
                break

        writer.close()
        await writer.wait_closed()

    async def stream_weight(self, writer):
        while self.streaming:
            try:
                weight = self.hx.weight(SAMPLE_SIZE)
                response = json.dumps({"weight": weight}) + "\n"
                writer.write(response.encode())
                await writer.drain()
                await asyncio.sleep(0.1)  # Adjust the delay as needed
            except Exception as e:
                logging.error(f"Error in weight streaming: {e}")
                self.streaming = False

    async def run_server(self):
        server = await asyncio.start_unix_server(self.handle_client, SOCKET_PATH)
        logging.info(f"Server listening on {SOCKET_PATH}")

        async with server:
            await server.serve_forever()

async def main():
    service = ScaleService()
    await service.initialize()

    def signal_handler(sig, frame):
        logging.info("Received signal to terminate.")
        service.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await service.run_server()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        service.cleanup()

if __name__ == "__main__":
    asyncio.run(main())