from fastapi import APIRouter, Depends
from sqlmodel import col, select

from app.core import permissions as P
from app.core.deps import SessionDep, requiere
from app.models import Permission, PermissionPublic, Role, RolePermission, RolePublic

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "/permissions",
    dependencies=[Depends(requiere(P.ROLES_READ))],
    summary="El catalogo de permisos",
)
def listar_permisos(session: SessionDep) -> list[PermissionPublic]:
    # Ruta literal declarada ANTES de /{role_id}: en Starlette gana la primera
    # que casa, igual que en Nest, y si no «permissions» se intentaria leer
    # como un uuid.
    filas = session.exec(select(Permission).order_by(col(Permission.key))).all()
    return [PermissionPublic.model_validate(f, from_attributes=True) for f in filas]


@router.get("", dependencies=[Depends(requiere(P.ROLES_READ))], summary="Los roles")
def listar(session: SessionDep) -> list[RolePublic]:
    roles = session.exec(select(Role).order_by(col(Role.name))).all()
    asignados = session.exec(select(RolePermission)).all()

    por_rol: dict = {}
    for fila in asignados:
        por_rol.setdefault(fila.role_id, []).append(fila.permission_key)

    return [
        RolePublic(
            id=rol.id,
            name=rol.name,
            description=rol.description,
            is_system=rol.is_system,
            is_active=rol.is_active,
            permissions=sorted(por_rol.get(rol.id, [])),
        )
        for rol in roles
    ]
