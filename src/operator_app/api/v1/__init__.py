from fastapi import APIRouter
from .relay.relay_routes import router as relay_router
from .status.status_routes import router as status_router
from .pump.pump_routes import router as pump_router
from .pins.pin_routes import router as pin_router
from .calibrate_scales.calibrate_scales_routes import router as calibrate_scales_router


v1_router = APIRouter()
v1_router.include_router(relay_router, prefix="/relay")
v1_router.include_router(status_router, prefix="/status")
v1_router.include_router(pump_router, prefix="/pump")
v1_router.include_router(pin_router, prefix="/pin")