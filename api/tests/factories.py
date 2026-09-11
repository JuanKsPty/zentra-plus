"""Atajos para montar datos en las pruebas sin repetir veinte lineas."""

from uuid import UUID, uuid4

from sqlmodel import Session

from app.core.security import hashear
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
