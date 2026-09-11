"""
Modelos de Zentra+.

Todo lo que sea una tabla se reexporta aqui: es lo que lee `alembic/env.py` para
detectar el esquema y lo que leen los tests para crear las tablas. Un modelo que
no aparezca en este archivo no existe para las migraciones.
"""

from app.models.auth import RefreshToken
from app.models.base import ConSucursal, IdUUID, Timestamps, ahora_utc
from app.models.branch import (
    Branch,
    BranchCounter,
    BranchCreate,
    BranchPublic,
    BranchUpdate,
)
from app.models.role import (
    Permission,
    PermissionPublic,
    Role,
    RolePermission,
    RolePublic,
)
from app.models.user import (
    LoginPorCorreo,
    LoginPorPin,
    User,
    UserBranch,
    UserOperativo,
    UserPublic,
)

__all__ = [
    "Branch",
    "BranchCounter",
    "BranchCreate",
    "BranchPublic",
    "BranchUpdate",
    "ConSucursal",
    "IdUUID",
    "LoginPorCorreo",
    "LoginPorPin",
    "Permission",
    "PermissionPublic",
    "RefreshToken",
    "Role",
    "RolePermission",
    "RolePublic",
    "Timestamps",
    "User",
    "UserBranch",
    "UserOperativo",
    "UserPublic",
    "ahora_utc",
]
