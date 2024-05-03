import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import pigpio  # Import pigpio for usage in your test

from operator_app.api.v1.status.status_routes import router  # replace with the actual location of your status routes

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@patch('operator_app.api.v1.status.status_services.pi')
def test_turn_on_route(mocked_pi):
  mocked_pi.connected = True
  response = client.get("/on/22")
  assert response.status_code == 200
  mocked_pi.set_mode.assert_called_once_with(22, pigpio.OUTPUT)
  mocked_pi.write.assert_called_once_with(22, 1)

@patch('operator_app.api.v1.status.status_services.pi')
def test_turn_off_route(mocked_pi):
  mocked_pi.connected = True
  response = client.get("/off/22")
  assert response.status_code == 200
  mocked_pi.set_mode.assert_called_once_with(22, pigpio.OUTPUT)
  mocked_pi.write.assert_called_once_with(22, 0)

@patch('operator_app.api.v1.status.status_services.pi')
def test_read_state_route(mocked_pi):
  mocked_pi.connected = True
  mocked_pi.read.return_value = 1
  response = client.get("/state/22")
  assert response.status_code == 200
  assert response.json() == {"gpio_pin": 22, "state": 1}
  mocked_pi.read.assert_called_once_with(22)