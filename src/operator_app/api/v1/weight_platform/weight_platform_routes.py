from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import socket
import json
import os

class CalibrationItem(BaseModel):
    known_weight_grams: float

router = APIRouter()

# Unix Socket Path
socket_path = "/tmp/pour_weight_service.sock"

def handle_pour_weight_service(request_data):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(json.dumps(request_data).encode())
        response = client.recv(1024).decode()
        return json.loads(response)

@router.post("/calibrate")
def calibrate(item: CalibrationItem):
    try:
        response = handle_pour_weight_service({
            "action": "calibrate",
            "known_weight_grams": item.known_weight_grams
        })
        if "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/read-weight")
def get_weight():
    try:
        response = handle_pour_weight_service({
            "action": "read_weight"
        })
        if "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
