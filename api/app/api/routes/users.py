from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import col, select

from app.core import permissions as P
from app.core.deps import SessionDep, SucursalActiva, publico, requiere
from app.models import Role, User, UserBranch, UserOperativo, UserPublic

router = APIRouter(prefix="/users", tags=["personas"])

# Router aparte para lo que de verdad es publico. No basta con marcar el
# endpoint: si colgara del router protegido, la dependencia del padre exigiria
# sesion igual y la pantalla de PIN no podria pintarse.
router_publico = APIRouter(prefix="/users", tags=["personas"])


@router_publico.get(
    "/operational",
    dependencies=[Depends(publico)],
    summary="Quien puede entrar por PIN en una sucursal",
)
def operativos(session: SessionDep, branch: UUID | None = None) -> list[UserOperativo]:
    """
    La rejilla del teclado de PIN. PUBLICA, y a proposito.

    Hay que ver la lista ANTES de tener sesion: es como se elige quien eres. Que
    sea publica no es seguridad por oscuridad al reves — ocultarla obligaria a
    teclear un identificador que nadie recuerda, y lo que protege la cuenta es el
    PIN, no que el nombre este escondido.

    Lleva lo justo para reconocerse: nombre y puesto. NUNCA el correo, que no
    hace falta para entrar y convierte la pantalla en un listado del personal.
    """
    consulta = (
        select(User, Role)
        .join(Role, isouter=True)
        .where(col(User.is_active).is_(True))
        .where(col(User.pin_hash).is_not(None))
    )
    if branch is not None:
        consulta = consulta.join(UserBranch, col(UserBranch.user_id) == col(User.id)).where(
            col(UserBranch.branch_id) == branch
        )

    filas = session.exec(consulta.order_by(col(User.name))).all()
    return [
        UserOperativo(id=usuario.id, name=usuario.name, role_name=rol.name if rol else None)
        for usuario, rol in filas
    ]


@router.get("", dependencies=[Depends(requiere(P.USERS_READ))], summary="El personal")
def listar(session: SessionDep, alcance: SucursalActiva) -> list[UserPublic]:
    del alcance  # el personal es del negocio; el filtro por sede llega con su pantalla
    filas = session.exec(select(User, Role).join(Role, isouter=True).order_by(col(User.name))).all()
    return [
        UserPublic(
            id=usuario.id,
            name=usuario.name,
            email=usuario.email,
            is_active=usuario.is_active,
            role_id=usuario.role_id,
            role_name=rol.name if rol else None,
        )
        for usuario, rol in filas
    ]
