"""roles y permisos

Revision ID: f9786b5c8fc6
Revises: 30e4b7233f56
Create Date: 2026-09-11 21:35:14.451715+00:00

Los puestos y lo que puede hacer cada uno.

Los roles son del NEGOCIO y no de la sucursal: «Mesero» significa lo mismo en
todas las sedes. Lo que cambia por sede es en cual trabaja cada persona, y eso
vive en `user_branches`.

`permissions` materializa el catalogo que esta en `app/core/permissions.py`. La
fuente de verdad sigue siendo el codigo; la tabla existe para que la pantalla de
roles pueda listarlos y para que la relacion sea una clave foranea de verdad. La
siembra la sincroniza, asi que un permiso nuevo no necesita migracion.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "f9786b5c8fc6"
down_revision: str | None = "30e4b7233f56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(length=60), nullable=False),
        sa.Column("module", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(op.f("ix_permissions_module"), "permissions", ["module"], unique=False)
    op.create_table(
        "roles",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=60), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_key", sqlmodel.sql.sqltypes.AutoString(length=60), nullable=False),
        sa.ForeignKeyConstraint(["permission_key"], ["permissions.key"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_key"),
    )
    op.add_column("users", sa.Column("role_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"], unique=False)
    op.create_foreign_key(None, "users", "roles", ["role_id"], ["id"])


def downgrade() -> None:
    # WARNING: constraint name is None; this directive will fail as
    # rendered.  Add a name, or use a naming convention; see
    # https://alembic.sqlalchemy.org/en/latest/naming.html
    op.drop_constraint(None, "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_role_id"), table_name="users")
    op.drop_column("users", "role_id")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_index(op.f("ix_permissions_module"), table_name="permissions")
    op.drop_table("permissions")
