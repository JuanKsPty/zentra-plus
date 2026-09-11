from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.db.types import TimestampTZ
from app.models.base import IdUUID, Timestamps, ahora_utc


class User(IdUUID, Timestamps, table=True):
    """
    Una persona que trabaja en el negocio.

    Dos puertas de entrada, y puede tener una, las dos o ninguna: correo con
    contrasena para quien usa el panel, y PIN para quien esta de pie en el
    salon. Un cocinero no tiene correo de empresa y no deberia necesitarlo para
    marcar una comanda como lista.
    """

    __tablename__ = "users"

    name: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=255, unique=True, index=True)

    # Nunca salen en una respuesta. Los esquemas *Public sencillamente no los
    # declaran, que es mas seguro que acordarse de excluirlos.
    password_hash: str | None = Field(default=None, max_length=255)
    pin_hash: str | None = Field(default=None, max_length=255)

    is_active: bool = True

    # El contador de revocacion. Sube al desactivar a alguien, al cambiarle el
    # rol o la contrasena, y al cerrar sesion en todas partes. Viaja en el token
    # como `tv`, asi que invalidar una sesion no necesita tocar la base en cada
    # peticion: basta con que el numero del token no cuadre.
    token_version: int = Field(default=0)

    last_login_at: datetime | None = Field(default=None, sa_type=TimestampTZ)


class UserBranch(SQLModel, table=True):
    """
    En que sucursales trabaja alguien.

    Es una tabla y no una columna en `users` porque un gerente puede cubrir dos
    sedes. La sucursal ACTIVA de una sesion se elige entre estas y viaja en el
    token; cambiarla es reemitirlo.
    """

    __tablename__ = "user_branches"

    user_id: UUID = Field(foreign_key="users.id", primary_key=True, ondelete="CASCADE")
    branch_id: UUID = Field(foreign_key="branches.id", primary_key=True, ondelete="CASCADE")
    # La que se preselecciona al entrar.
    is_primary: bool = False
    created_at: datetime = Field(default_factory=ahora_utc, sa_type=TimestampTZ)


class UserPublic(SQLModel):
    """Lo que la API devuelve de un usuario. Sin hashes: no estan declarados."""

    id: UUID
    name: str
    email: str | None
    is_active: bool


class LoginPorCorreo(SQLModel):
    # `str` y no `EmailStr` a proposito. `EmailStr` rechaza los dominios de uso
    # especial —`.local`, `.test`, `.internal`— asi que ninguna instalacion de
    # desarrollo podria entrar. Y en un formulario de acceso la validacion
    # estricta no compra nada: la direccion o coincide con una cuenta o no, y
    # rechazarla antes solo sirve para dar un mensaje distinto segun el formato,
    # que es la clase de pista que no se quiere dar.
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class LoginPorPin(SQLModel):
    user_id: UUID
    pin: str = Field(min_length=4, max_length=8)
