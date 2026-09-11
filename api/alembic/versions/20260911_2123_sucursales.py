"""sucursales y su contador

Revision ID: bbef0604e062
Revises:
Create Date: 2026-09-11 21:23:08.830680+00:00

La primera revision. Crea las sucursales y la fila contador del numero de cuenta
de cada una.

`branch_counters` es una tabla y no una secuencia a proposito: una secuencia por
sucursal obligaria a ejecutar DDL desde codigo de aplicacion cada vez que se da
de alta un local, y eso rompe la propiedad de que el esquema sale de aqui. La
explicacion larga esta en `app/models/branch.py`.

NO siembra ninguna sucursal. Los datos de negocio van en `app/seed.py`: una
migracion que inserta filas de negocio se vuelve imposible de mantener y rompe
el `downgrade`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "bbef0604e062"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("address", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("phone", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True),
        sa.Column("timezone", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    # El autogenerate no escribe los CHECK: hay que ponerlos a mano.
    op.create_check_constraint("ck_branches_codigo_no_vacio", "branches", "length(trim(code)) > 0")
    op.create_table(
        "branch_counters",
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("last_order_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("branch_id"),
    )
    # Un contador que retrocede significa que alguien escribio a mano; mejor que
    # falle la escritura que descubrirlo por dos cuentas con el mismo numero.
    op.create_check_constraint(
        "ck_branch_counters_no_retrocede", "branch_counters", "last_order_number >= 0"
    )


def downgrade() -> None:
    op.drop_table("branch_counters")
    op.drop_table("branches")
