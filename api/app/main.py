import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exception_handlers import registrar_manejadores
from app.realtime.hub import hub

# Se configura AL IMPORTAR, antes de instanciar la app: si estuviera dentro del
# arranque, un fallo de configuracion saldria con el formato por defecto de
# uvicorn justo en el momento en que mas falta hace poder leerlo.
logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("zentra")


@asynccontextmanager
async def arranque(app: FastAPI):
    # Se guarda el bucle para poder publicar avisos desde codigo SINCRONO: los
    # servicios corren en el threadpool y desde ahi no se puede hacer `await`.
    hub.registrar_bucle(asyncio.get_running_loop())
    yield


app = FastAPI(
    lifespan=arranque,
    title=f"{settings.app_name} API",
    version=settings.app_version,
    summary="Gestion operativa multisucursal. Todo cuelga de /api.",
    # Bajo /api para que el proxy de Next y el de nginx las sirvan sin reglas
    # extra, y para que el origen unico funcione sin excepciones.
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Todo error sale con la misma forma, venga de donde venga. Ver core/errors.py.
registrar_manejadores(app)

app.include_router(api_router, prefix="/api")
