"""Añade trazabilidad de origen a servicios existentes.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def add_if_missing(table: str, columns: list[sa.Column]):
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}
    for column in columns:
        if column.name not in existing:
            op.add_column(table, column)

def upgrade():
    for table in ("servicio_nivel1", "servicio_nivel2"):
        add_if_missing(table, [
            sa.Column("origen_hoja", sa.String(120), nullable=True),
            sa.Column("origen_fila", sa.Integer(), nullable=True),
            sa.Column("origen_rango", sa.String(80), nullable=True),
        ])

def downgrade():
    for table in ("servicio_nivel2", "servicio_nivel1"):
        existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}
        for name in ("origen_rango", "origen_fila", "origen_hoja"):
            if name in existing:
                op.drop_column(table, name)
