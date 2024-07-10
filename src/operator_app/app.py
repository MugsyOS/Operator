from fastapi import FastAPI
from operator_app.api.v1.routes import v1_router
import os

debug = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
app = FastAPI(debug=debug)

app.include_router(v1_router, prefix="/v1")
