"""Atajos para montar datos en las pruebas sin repetir veinte lineas."""

from uuid import UUID, uuid4

from sqlmodel import Session

from app.core.security import COOKIE_ACCESO, MetodoDeAcceso, firmar_acceso, hashear
from app.models import Branch, BranchCounter, User, UserBranch


def crear_sucursal(session: Session, *, code: str = "PRIN", name: str = "Principal") -> Branch:
    sucursal = Branch(name=name, code=code, is_default=code == "PRIN")
    session.add(sucursal)
    session.commit()
    session.refresh(sucursal)
    session.add(BranchCounter(branch_id=sucursal.id))
    session.commit()
    return sucursal


def crear_usuario(
    session: Session,
    *,
    name: str = "Ana",
    email: str | None = "ana@zentra.local",
    password: str | None = "Contrasena123",
    pin: str | None = None,
    is_active: bool = True,
    sucursales: list[Branch] | None = None,
) -> User:
    usuario = User(
        name=name,
        email=email,
        password_hash=hashear(password) if password else None,
        pin_hash=hashear(pin) if pin else None,
        is_active=is_active,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    for indice, sucursal in enumerate(sucursales or []):
        session.add(UserBranch(user_id=usuario.id, branch_id=sucursal.id, is_primary=indice == 0))
    session.commit()
    return usuario


def uuid_cualquiera() -> UUID:
    return uuid4()


def cookie_con(
    permisos: list[str],
    *,
    branch_id: UUID | None = None,
    branch_ids: list[UUID] | None = None,
    metodo: MetodoDeAcceso = "email",
    user_id: UUID | None = None,
) -> dict[str, str]:
    """
    Una sesion firmada con EXACTAMENTE los permisos que el caso necesita, sin
    tocar la base.

    Se puede porque `requiere()` lee los permisos DEL TOKEN, no de la base: la
    misma propiedad que hace barato el guard hace trivial la prueba. Es lo que
    permite comprobar «403 con orders:write sobre un endpoint que exige
    orders:read» sin montar roles ni usuarios.

    Cuando la regla que se prueba SI consulta la base —el turno es por usuario y
    sucursal, el umbral de descuento sale del rol— hace falta un usuario de
    verdad, y para eso esta `crear_usuario`.
    """
    identificador = user_id or uuid4()
    sucursal = branch_id or uuid4()
    token = firmar_acceso(
        {
            "sub": str(identificador),
            "tv": 0,
            "name": "Tester",
            "email": "tester@zentra.local",
            "branch_id": str(sucursal),
            "branch_ids": [str(b) for b in (branch_ids or [sucursal])],
            "role_name": "Prueba",
            "permissions": permisos,
        },
        metodo,
    )
    return {COOKIE_ACCESO: token}
