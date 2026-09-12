"""turnos de caja y cobros

Revision ID: 870d0b359d79
Revises: bc0234cea38b
Create Date: 2026-09-12 07:00:11.468792+00:00

Los turnos de caja y los cobros.

DOS INDICES PARCIALES QUE LLEVAN REGLAS DE NEGOCIO, y van a mano porque el
autogenerate los excluye a proposito (ver `alembic/env.py`):

1. UN TURNO ABIERTO POR CAJERO Y SUCURSAL. Parcial —solo los abiertos— porque
   los cerrados se acumulan sin limite y un unico normal impediria abrir caja
   dos dias seguidos. Sin el, un doble clic abre dos turnos, los cobros se
   reparten entre los dos y NINGUNO cuadra: peor que no cuadrar uno, porque
   nadie sabe cual mirar.

2. UNA CLAVE DE REENVIO SE USA UNA VEZ. Tambien parcial: solo indexa las filas
   que la traen, que son las menos. Sin el, un pago parcial reenviado se cobra
   dos veces — el completo se rechaza de rebote porque la cuenta ya esta
   cerrada, pero 30 + 30 sobre una cuenta de 100 pasa entero.

`payments.branch_id` va denormalizado desde la comanda: el arqueo agrega por
sucursal y unir con `orders` fila a fila es trabajo que se puede ahorrar.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "870d0b359d79"
down_revision: str | None = "bc0234cea38b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shifts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("opened_by", sa.Uuid(), nullable=False),
        sa.Column("closed_by", sa.Uuid(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_cash", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("closing_cash", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
        ),
        sa.ForeignKeyConstraint(
            ["closed_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["opened_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_shifts_branch_opened", "shifts", ["branch_id", "opened_at"], unique=False)
    op.create_index(op.f("ix_shifts_branch_id"), "shifts", ["branch_id"], unique=False)
    op.create_index(op.f("ix_shifts_opened_by"), "shifts", ["opened_by"], unique=False)
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=True),
        sa.Column("method", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("reference", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("client_request_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column("processed_by", sa.Uuid(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["processed_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"],
            ["shifts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_payments_branch_processed", "payments", ["branch_id", "processed_at"], unique=False
    )
    op.create_index(op.f("ix_payments_branch_id"), "payments", ["branch_id"], unique=False)
    op.create_index(op.f("ix_payments_order_id"), "payments", ["order_id"], unique=False)
    op.create_index(op.f("ix_payments_shift_id"), "payments", ["shift_id"], unique=False)

    # --- lo que el autogenerate no escribe -----------------------------------
    op.create_index(
        "idx_shifts_un_abierto_por_cajero_y_sucursal",
        "shifts",
        ["opened_by", "branch_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )
    op.create_index(
        "idx_payments_client_request_id",
        "payments",
        ["client_request_id"],
        unique=True,
        postgresql_where=sa.text("client_request_id IS NOT NULL"),
    )
    op.create_check_constraint("ck_shifts_estado", "shifts", "status IN ('open', 'closed')")
    op.create_check_constraint("ck_shifts_fondo_no_negativo", "shifts", "opening_cash >= 0")
    # Un cobro de cero no es un cobro; uno negativo es una devolucion, y una
    # devolucion es un movimiento con su propio nombre, no un cobro al reves.
    op.create_check_constraint("ck_payments_importe_positivo", "payments", "amount > 0")
    op.create_check_constraint(
        "ck_payments_metodo",
        "payments",
        "method IN ('cash', 'card', 'transfer', 'wallet')",
    )


def downgrade() -> None:
    op.drop_index("idx_payments_client_request_id", table_name="payments")
    op.drop_index("idx_shifts_un_abierto_por_cajero_y_sucursal", table_name="shifts")
    op.drop_index(op.f("ix_payments_shift_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_order_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_branch_id"), table_name="payments")
    op.drop_index("idx_payments_branch_processed", table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_shifts_opened_by"), table_name="shifts")
    op.drop_index(op.f("ix_shifts_branch_id"), table_name="shifts")
    op.drop_index("idx_shifts_branch_opened", table_name="shifts")
    op.drop_table("shifts")
