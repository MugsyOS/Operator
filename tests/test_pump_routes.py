import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import pigpio  # Import pigpio for usage in your test
from operator_app.api.v1 import v1_router

app = FastAPI()
app.include_router(v1_router, prefix="/v1")

client = TestClient(app)

@patch('operator_app.api.v1.pump.pump_routes.pi')
def test_control_pump(mocked_pi):
  response = client.post("/v1/pump/", json={"direction": "forward"})
  assert response.status_code == 200
  mocked_pi.set_mode.assert_any_call(13, pigpio.OUTPUT)
  mocked_pi.set_mode.assert_any_call(19, pigpio.OUTPUT)
  mocked_pi.write.assert_any_call(13, 1)
  mocked_pi.write.assert_any_call(19, 0)

@patch('operator_app.api.v1.pump.pump_routes.pi')
def test_control_pump_speed(mocked_pi):
  response = client.post("/v1/pump/flow-rate", json={"direction": "forward", "speed": 50})
  assert response.status_code == 200
  mocked_pi.set_mode.assert_any_call(13, pigpio.OUTPUT)
  mocked_pi.set_mode.assert_any_call(19, pigpio.OUTPUT)
  mocked_pi.set_PWM_dutycycle.assert_called_with(13, 127)
  mocked_pi.write.assert_called_with(19, 0)