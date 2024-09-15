import logging
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from .mug_weight_service import start_weight_stream, get_current_weight, zero_scale, pump_to_weight

router = APIRouter()

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connection opened")
    try:
        await start_weight_stream(websocket)
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
    except Exception as e:
        logging.error(f"Error in WebSocket: {e}", exc_info=True)
    finally:
        logging.info("WebSocket connection closed")

@router.get("/current")
async def get_weight():
    return await get_current_weight()

@router.post("/zero")
async def zero_weight_scale():
    return await zero_scale()

class PumpToWeightRequest(BaseModel):
    target_weight: float
    pump_speed: int
    tolerance: float = 0.5

@router.post("/pump-to-weight")
async def pump_to_weight_endpoint(request: PumpToWeightRequest):
    result = await pump_to_weight(request.target_weight, request.pump_speed, request.tolerance)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result