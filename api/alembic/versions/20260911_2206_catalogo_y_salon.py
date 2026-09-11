"""catalogo y salon

Revision ID: 6f1e79f76ac9
Revises: 4900438ad3da
Create Date: 2026-09-11 22:06:26.696291+00:00

El catalogo y el salon.

EL CATALOGO ES DEL NEGOCIO. Categorias, productos y modificadores no llevan
sucursal: la carta se define una vez y se hereda en todas las sedes. Es la mitad
del modelo multisucursal, y lo que evita que comparar el ticket promedio de un
producto entre locales necesite una tabla de equivalencias.

Lo que cambia por sede vive en `product_branch`, y su fila SOLO EXISTE SI HAY
ALGO QUE DECIR: ausencia = herencia. Asi dar de alta una sucursal no siembra
N x M filas, que con cuatro sedes y trescientos productos seria inmanejable.

EL SALON SI ES DE LA SUCURSAL. Y el numero de mesa pasa a ser unico POR
SUCURSAL: global significaba que la segunda sede no podia tener una «mesa 1».

`status_changed_at` va aparte de `updated_at` a proposito: es la marca para
desempatar cuando dos dispositivos cambian la misma mesa, y `updated_at` se
mueve tambien al renombrarla o arrastrarla en el mapa, que no son cambios de
estado.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "6f1e79f76ac9"
down_revision: str | None = "4900438ad3da"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "modifier_groups",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("allow_multiple", sa.Boolean(), nullable=False),
        sa.Column("min_selections", sa.Integer(), nullable=False),
        sa.Column("max_selections", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "modifier_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("price_adjustment", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["modifier_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_modifier_options_group_id"), "modifier_options", ["group_id"], unique=False
    )
    op.create_table(
        "products",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("station", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("image_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Los CHECK no los escribe el autogenerate. Estos tres cierran estados que
    # no significan nada: un producto que se prepara en ningun sitio, un rango
    # de selecciones imposible y una mesa sin sitio para nadie.
    op.create_check_constraint(
        "ck_products_estacion",
        "products",
        "station IN ('kitchen', 'bar', 'immediate')",
    )
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"], unique=False)
    op.create_table(
        "sectors",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sectors_branch_id"), "sectors", ["branch_id"], unique=False)
    op.create_index("uq_sectors_nombre_por_sucursal", "sectors", ["branch_id", "name"], unique=True)
    op.create_table(
        "product_branch",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("is_listed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id", "branch_id"),
    )
    op.create_table(
        "product_modifier_groups",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["modifier_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id", "group_id"),
    )
    op.create_table(
        "tables",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("shape", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("position_x", sa.Integer(), nullable=True),
        sa.Column("position_y", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sector_id", sa.Uuid(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
        ),
        sa.ForeignKeyConstraint(["sector_id"], ["sectors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_tables_branch_status", "tables", ["branch_id", "status"], unique=False)
    op.create_index(op.f("ix_tables_branch_id"), "tables", ["branch_id"], unique=False)
    op.create_index(op.f("ix_tables_sector_id"), "tables", ["sector_id"], unique=False)
    op.create_index("uq_tables_numero_por_sucursal", "tables", ["branch_id", "number"], unique=True)
    op.create_check_constraint(
        "ck_tables_estado",
        "tables",
        "status IN ('available', 'occupied', 'cleaning', 'reserved', 'maintenance')",
    )
    op.create_check_constraint(
        "ck_modifier_groups_rango",
        "modifier_groups",
        "max_selections IS NULL OR max_selections >= min_selections",
    )


def downgrade() -> None:
    op.drop_index("uq_tables_numero_por_sucursal", table_name="tables")
    op.drop_index(op.f("ix_tables_sector_id"), table_name="tables")
    op.drop_index(op.f("ix_tables_branch_id"), table_name="tables")
    op.drop_index("idx_tables_branch_status", table_name="tables")
    op.drop_table("tables")
    op.drop_table("product_modifier_groups")
    op.drop_table("product_branch")
    op.drop_index("uq_sectors_nombre_por_sucursal", table_name="sectors")
    op.drop_index(op.f("ix_sectors_branch_id"), table_name="sectors")
    op.drop_table("sectors")
    op.drop_index(op.f("ix_products_category_id"), table_name="products")
    op.drop_table("products")
    op.drop_index(op.f("ix_modifier_options_group_id"), table_name="modifier_options")
    op.drop_table("modifier_options")
    op.drop_table("modifier_groups")
    op.drop_table("categories")
