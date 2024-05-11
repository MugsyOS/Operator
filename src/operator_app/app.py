from fastapi import FastAPI
from operator_app.api.v1.relay.relay_routes import router as relay_router
from operator_app.api.v1.status.status_routes import router as status_router
from operator_app.api.v1.pump.pump_routes import router as pump_router
from operator_app.api.v1.pins.pin_routes import router as pin_router

app = FastAPI()

app.include_router(relay_router, prefix="/v1/relay")
app.include_router(status_router, prefix="/v1/status")
app.include_router(pump_router, prefix="/v1/pump")
app.include_router(pin_router, prefix="/v1/pin")
