from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(tags=["sistema"])


class Salud(BaseModel):
    status: str
    app: str
    version: str
    environment: str


@router.get("/health", summary="Estado del proceso")
def health() -> Salud:
    """
    Dice que el proceso esta vivo, y nada mas.

    NO toca la base de datos, y es deliberado: esto es lo que mira el
    HEALTHCHECK de la imagen, y un proceso sano no debe reiniciarse porque
    Postgres haya parpadeado. Para saber si la base responde hay un endpoint
    aparte, /api/ready, que llega con la fase de endurecimiento.
    """
    return Salud(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
