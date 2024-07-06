from fastapi import FastAPI
from operator_app.api.v1.relay.relay_routes import router as relay_router
from operator_app.api.v1.status.status_routes import router as status_router
from operator_app.api.v1.pump.pump_routes import router as pump_router
from operator_app.api.v1.pins.pin_routes import router as pin_router
from operator_app.api.v1.calibrate_scales.calibrate_scales_routes import router as calibrate_scales_router
from operator_app.api.v1.weight_platform.weight_platform_routes import router as weight_platform_router


app = FastAPI()

app.include_router(relay_router, prefix="/v1/relay")
app.include_router(status_router, prefix="/v1/status")
app.include_router(pump_router, prefix="/v1/pump")
app.include_router(pin_router, prefix="/v1/pin")
app.include_router(weight_platform_router, prefix="/v1/weight-platform")
app.include_router(calibrate_scales_router, prefix="/v1/calibrate-scales")
