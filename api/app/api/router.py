from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()

# Publicos, uno a uno y con nombre: no hay forma de anadir un router abierto
# por descuido. Cuando llegue la autenticacion, todo lo demas colgara de un
# router padre que ya exige sesion.
api_router.include_router(health.router)
