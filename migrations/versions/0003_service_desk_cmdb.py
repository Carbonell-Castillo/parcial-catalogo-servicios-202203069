"""Service Desk, flujos, auditoría y CMDB.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
from app.models import Base

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    names = [
        "articulo_conocimiento", "notificacion", "ticket_relacion", "ticket_ci",
        "ticket_adjunto", "ticket_comentario", "ticket_historial", "ticket",
        "servicio_ci", "relacion_ci", "dispositivo_ci", "clasificacion_ci",
        "cola_rol", "cola_miembro", "cola", "usuario_rol",
    ]
    bind = op.get_bind()
    for name in names:
        table = Base.metadata.tables.get(name)
        if table is not None:
            table.drop(bind=bind, checkfirst=True)
