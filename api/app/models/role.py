from uuid import UUID

from sqlmodel import Field, SQLModel

from app.models.base import IdUUID, Timestamps


class Role(IdUUID, Timestamps, table=True):
    """
    Un puesto, con lo que puede hacer.

    Los roles son del NEGOCIO, no de la sucursal: «Mesero» significa lo mismo en
    todas las sedes. Lo que cambia por sede es en cual trabaja cada persona, y
    eso vive en `user_branches`.
    """

    __tablename__ = "roles"

    name: str = Field(min_length=2, max_length=60, unique=True)
    description: str = Field(default="", max_length=255)
    # Los de sistema no se borran ni se renombran: si alguien borra «Cajero»,
    # quien lo tenia se queda sin poder cobrar y no hay forma obvia de deshacerlo.
    is_system: bool = False
    is_active: bool = True


class Permission(SQLModel, table=True):
    """
    Un permiso del catalogo, materializado.

    La fuente de verdad es `app/core/permissions.py`; esta tabla existe para que
    la pantalla de roles pueda listarlos y para que la relacion con los roles sea
    una clave foranea de verdad. La siembra la sincroniza con las constantes.
    """

    __tablename__ = "permissions"

    key: str = Field(primary_key=True, max_length=60)
    module: str = Field(max_length=30, index=True)
    action: str = Field(max_length=30)


class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"

    role_id: UUID = Field(foreign_key="roles.id", primary_key=True, ondelete="CASCADE")
    permission_key: str = Field(
        foreign_key="permissions.key", primary_key=True, ondelete="CASCADE", max_length=60
    )


class RolePublic(SQLModel):
    id: UUID
    name: str
    description: str
    is_system: bool
    is_active: bool
    permissions: list[str] = []


class PermissionPublic(SQLModel):
    key: str
    module: str
    action: str
