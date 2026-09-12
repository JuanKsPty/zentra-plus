"""comandas

Revision ID: bc0234cea38b
Revises: 6f1e79f76ac9
Create Date: 2026-09-12 06:32:03.758272+00:00

Las comandas, sus lineas y el historial de estados.

`order_items` guarda COPIAS del nombre, el precio y la estacion del producto en
el momento del pedido. Renombrar un producto o cambiarle el precio manana no
puede reescribir un recibo ya impreso.

`order_status_history` entra AHORA y no cuando hagan falta los reportes, porque
es imposible de reconstruir hacia atras: si se anade en la fase 5, las metricas
de tiempo de preparacion solo tendran datos desde ese dia.

El numero de cuenta es unico POR SUCURSAL. El unico compuesto no es redundante
con el contador: es lo que convierte una restauracion mal hecha o un INSERT a
mano en un error inmediato, en vez de en dos cuentas con el mismo numero.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "bc0234cea38b"
down_revision: str | None = "6f1e79f76ac9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.Integer(), nullable=False),
        sa.Column("label", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=True),
        sa.Column("table_id", sa.Uuid(), nullable=True),
        sa.Column("waiter_id", sa.Uuid(), nullable=True),
        sa.Column("shift_id", sa.Uuid(), nullable=True),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("tip_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
        ),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["waiter_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_orders_abiertas", "orders", ["branch_id", "status", "created_at"], unique=False
    )
    op.create_index("idx_orders_mesa", "orders", ["table_id"], unique=False)
    op.create_index(op.f("ix_orders_branch_id"), "orders", ["branch_id"], unique=False)
    op.create_index(op.f("ix_orders_shift_id"), "orders", ["shift_id"], unique=False)
    op.create_index(
        "uq_orders_numero_por_sucursal", "orders", ["branch_id", "order_number"], unique=True
    )
    # Los CHECK no los escribe el autogenerate. Estos cierran estados que no
    # significan nada, y uno que ademas es media funcion de seguridad: `counter`
    # no puede entrar por aqui, solo lo escribe la venta de mostrador.
    op.create_check_constraint(
        "ck_orders_estado",
        "orders",
        "status IN ('pending', 'preparing', 'ready', 'delivered', 'closed', 'cancelled')",
    )
    op.create_check_constraint("ck_orders_origen", "orders", "source IN ('staff', 'counter')")
    op.create_check_constraint("ck_orders_numero_positivo", "orders", "order_number > 0")
    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("station", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    # Una linea de cantidad cero no es nada; una negativa es un descuento
    # disfrazado que ningun reporte sabria contar.
    op.create_check_constraint("ck_order_items_cantidad", "order_items", "quantity > 0")
    op.create_table(
        "order_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column("to_status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_historial_estado", "order_status_history", ["to_status", "changed_at"], unique=False
    )
    op.create_index(
        op.f("ix_order_status_history_order_id"), "order_status_history", ["order_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_order_status_history_order_id"), table_name="order_status_history")
    op.drop_index("idx_historial_estado", table_name="order_status_history")
    op.drop_table("order_status_history")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("uq_orders_numero_por_sucursal", table_name="orders")
    op.drop_index(op.f("ix_orders_shift_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_branch_id"), table_name="orders")
    op.drop_index("idx_orders_mesa", table_name="orders")
    op.drop_index("idx_orders_abiertas", table_name="orders")
    op.drop_table("orders")
