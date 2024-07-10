from fastapi import APIRouter
from operator_app.api.v1.relay.relay_routes import router as relay_router
from operator_app.api.v1.status.status_routes import router as status_router
from operator_app.api.v1.pump.pump_routes import router as pump_router
from operator_app.api.v1.pins.pin_routes import router as pin_router
from operator_app.api.v1.calibrate_scales.calibrate_scales_routes import router as calibrate_scales_router

v1_router = APIRouter()
router.include_router(relay_router, prefix="/relay")
router.include_router(status_router, prefix="/status")
router.include_router(pump_router, prefix="/pump")
router.include_router(pin_router, prefix="/pin")
router.include_router(calibrate_scales_router, prefix="/calibrate-scales")