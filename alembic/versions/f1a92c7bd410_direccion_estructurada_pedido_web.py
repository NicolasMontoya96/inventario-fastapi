"""agregar direccion estructurada a pedido_web

Revision ID: f1a92c7bd410
Revises: e8cea2351cd8
Create Date: 2026-11-17 00:00:00.000000

Agrega departamento, ciudad, direccion y referencia_direccion a
pedido_web, para dejar de depender de un solo cuadro de texto libre
(direccion_envio) que mezclaba todo. direccion_envio se deja intacta por
compatibilidad con pedidos ya existentes; los nuevos pedidos llenan además
estas columnas.

Idempotente, igual que las migraciones anteriores.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'f1a92c7bd410'
down_revision: Union[str, Sequence[str], None] = 'e8cea2351cd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUMNAS_NUEVAS = ["departamento", "ciudad", "direccion", "referencia_direccion"]


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if 'pedidoweb' not in insp.get_table_names():
        return

    columnas_existentes = {c['name'] for c in insp.get_columns('pedidoweb')}
    for columna in COLUMNAS_NUEVAS:
        if columna not in columnas_existentes:
            op.add_column('pedidoweb', sa.Column(columna, sa.String(), nullable=True))


def downgrade() -> None:
    # Deliberadamente no implementado: ver la nota de la migración
    # 23b669f8703d sobre por qué downgrade() se deja vacío en este repo.
    pass