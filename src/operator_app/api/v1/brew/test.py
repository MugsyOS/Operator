from fastapi import APIRouter, WebSocket
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws-test")
async def test_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Test WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()
            logger.info(f"Received message: {message}")
            
            # Echo the message back with a prefix
            response = f"Server received: {message}"
            await websocket.send_text(response)
            
    except Exception as e:
        logger.error(f"Error in test websocket: {e}")
        try:
            await websocket.close()
        except:
            pass