"""configuracion del negocio

Revision ID: 4900438ad3da
Revises: f9786b5c8fc6
Create Date: 2026-09-11 21:42:27.198843+00:00

Los datos del negocio: nombre, nombre fiscal, moneda, impuesto y pie de recibo.

UNA fila, y lo garantiza la base con un indice unico sobre una expresion
constante. Una comprobacion en el servicio seria un read-then-write, y por esa
ventana dos peticiones simultaneas crean dos filas: a partir de ahi «la
configuracion» depende de cual lea cada consulta, que es un fallo que no da la
cara hasta que alguien cambia el impuesto y no pasa nada.

El indice va a mano porque el autogenerate no escribe expresiones.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "4900438ad3da"
down_revision: str | None = "f9786b5c8fc6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_config",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column("legal_name", sqlmodel.sql.sqltypes.AutoString(length=180), nullable=True),
        sa.Column("tax_id", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=True),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(length=3), nullable=False),
        sa.Column("tax_rate", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("receipt_footer", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("logo_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # UNA sola fila. `((true))` indexa una constante, asi que la segunda
    # insercion choca. El autogenerate no escribe indices sobre expresiones.
    op.execute("CREATE UNIQUE INDEX uq_business_config_fila_unica ON business_config ((true))")


def downgrade() -> None:
    op.drop_table("business_config")
