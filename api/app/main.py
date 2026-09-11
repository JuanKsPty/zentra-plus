import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings

# Se configura AL IMPORTAR, antes de instanciar la app: si estuviera dentro del
# arranque, un fallo de configuracion saldria con el formato por defecto de
# uvicorn justo en el momento en que mas falta hace poder leerlo.
logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("zentra")


app = FastAPI(
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


@app.exception_handler(Exception)
async def error_no_previsto(request: Request, exc: Exception) -> JSONResponse:
    """
    Cualquier excepcion sin manejar sale como JSON, no como HTML de error.

    El mensaje de la excepcion NO viaja al cliente: `str()` de un error de
    SQLAlchemy incluye los parametros enlazados de la consulta, y eso puede
    llevar un hash de credencial. Al log va la traza; al cliente, una frase.
    """
    logger.exception("Error no manejado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "error_interno", "message": "Error interno del servidor."}},
    )


app.include_router(api_router, prefix="/api")
