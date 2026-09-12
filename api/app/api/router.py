from fastapi import APIRouter, Depends

from app.api.routes import (
    auth,
    business_config,
    catalog,
    floor,
    health,
    orders,
    roles,
    users,
)
from app.core.deps import sesion_requerida

api_router = APIRouter()

# PUBLICOS, uno a uno y con nombre. Anadir algo aqui es una decision visible en
# un diff, no un descuido.
api_router.include_router(health.router)
api_router.include_router(auth.router)
# La rejilla del teclado de PIN: hay que verla ANTES de tener sesion.
api_router.include_router(users.router_publico)

# Todo lo demas nace autenticado: la sesion se exige en el router padre, asi que
# un modulo nuevo no puede quedar abierto por olvidar una dependencia.
protegido = APIRouter(dependencies=[Depends(sesion_requerida)])
protegido.include_router(users.router)
protegido.include_router(roles.router)
protegido.include_router(business_config.router)
protegido.include_router(catalog.router)
protegido.include_router(floor.router)
protegido.include_router(orders.router)

api_router.include_router(protegido)
