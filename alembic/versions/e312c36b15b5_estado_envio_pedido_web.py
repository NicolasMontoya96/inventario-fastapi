"""agregar seguimiento de envio a pedido_web

Revision ID: e312c36b15b5
Revises: f1a92c7bd410
Create Date: 2026-11-18 00:00:00.000000

Agrega transportadora y numero_guia a pedido_web, para el estado "enviado"
nuevo (el campo estado en si es texto libre, no una columna enum, asi que
no requiere migracion aparte para admitir "enviado" y "entregado" como
valores). Ambas columnas nuevas son opcionales: se llenan a mano desde el
panel de admin solo cuando se despacha el pedido.

Idempotente, igual que las migraciones anteriores.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'e312c36b15b5'
down_revision: Union[str, Sequence[str], None] = 'f1a92c7bd410'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUMNAS_NUEVAS = ["transportadora", "numero_guia"]


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