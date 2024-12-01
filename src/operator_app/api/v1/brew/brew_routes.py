from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from operator_app.auth import auth_handler
import logging
from .brew_services import BrewService

logger = logging.getLogger(__name__)
router = APIRouter()
brew_service = BrewService()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("hithithit")
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            message = await websocket.receive_text()
            await brew_service.process_message(websocket, message)
    except WebSocketDisconnect:
        logger.info("ferterteil")
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.info("fi32423423424l")
        logger.error(f"Unexpected error in WebSocket handler: {e}", exc_info=True)