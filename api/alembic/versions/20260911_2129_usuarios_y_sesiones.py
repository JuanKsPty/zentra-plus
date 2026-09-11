"""usuarios, sucursales por usuario y refrescos

Revision ID: 30e4b7233f56
Revises: bbef0604e062
Create Date: 2026-09-11 21:29:28.129189+00:00

Las personas que trabajan en el negocio y sus sesiones.

`users` guarda dos credenciales opcionales —contrasena y PIN— porque hay dos
puertas de entrada y no todo el mundo usa las dos: un cocinero no tiene correo
de empresa y no deberia necesitarlo para marcar una comanda como lista.

`refresh_tokens` guarda el JTI, no el token. Asi un volcado de la base no
contiene credenciales reutilizables, la clave son 16 bytes en vez de un texto
largo indexado, y `replaced_by` permite detectar que alguien esta reproduciendo
un token viejo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "30e4b7233f56"
down_revision: str | None = "bbef0604e062"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("password_hash", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("pin_hash", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Un usuario sin ninguna credencial no puede entrar por ningun sitio: es una
    # fila que solo puede confundir a quien mire la tabla de empleados.
    op.create_check_constraint(
        "ck_users_alguna_credencial",
        "users",
        "password_hash IS NOT NULL OR pin_hash IS NOT NULL",
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "refresh_tokens",
        sa.Column("jti", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("login_method", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)
    op.create_table(
        "user_branches",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "branch_id"),
    )


def downgrade() -> None:
    op.drop_table("user_branches")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
