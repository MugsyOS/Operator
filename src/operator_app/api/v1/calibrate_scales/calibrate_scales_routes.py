from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from pydantic import BaseModel
import asyncio
import configparser

config = configparser.ConfigParser()
config.read('src/operator_app/hardware_config.ini')

router = APIRouter()

class CalibrationStep(BaseModel):
    message: str

@router.websocket("/ws/calibrate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    steps = [
        "Please place the calibration weight on the scale.",
        "Please remove the calibration weight.",
        "Calibration complete. Thank you!"
    ]
    
    try:
        for step in steps:
            await websocket.send_json({"message": step})
            response = await websocket.receive_json()
            # Here, you can handle the response from the user if needed
            print(response)
        await websocket.send_json({"message": "Calibration process finished. Closing connection."})
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        await websocket.close()
