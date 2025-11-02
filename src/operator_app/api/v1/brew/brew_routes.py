import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from .brew_services import BrewOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter()
orchestrator = BrewOrchestrator()

@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    try:
        # Let the orchestrator handle the websocket
        await orchestrator.handle_websocket(websocket)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass