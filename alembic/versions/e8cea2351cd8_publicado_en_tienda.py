"""agregar producto.publicado_en_tienda

Revision ID: e8cea2351cd8
Revises: 23b669f8703d
Create Date: 2026-11-16 00:00:00.000000

Separa "existe en el inventario" de "se muestra en la tienda online": nueva
columna booleana en producto, con default false tanto a nivel de columna
(para filas nuevas) como explícito para las filas existentes (para que
ningún producto ya cargado aparezca publicado en la tienda sin que el admin
lo decida a propósito).

Idempotente, igual que la migración anterior: revisa qué existe antes de
actuar, así que corre igual contra una base nueva o contra producción.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'e8cea2351cd8'
down_revision: Union[str, Sequence[str], None] = '23b669f8703d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if 'producto' not in insp.get_table_names():
        return

    columnas_producto = {c['name'] for c in insp.get_columns('producto')}
    if 'publicado_en_tienda' not in columnas_producto:
        op.add_column(
            'producto',
            sa.Column(
                'publicado_en_tienda',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
        # server_default solo hace falta para que el ALTER TABLE no falle
        # contra filas existentes; no lo dejamos pegado a la columna a largo
        # plazo porque create_all() (la fuente de verdad para una base
        # nueva) no define uno — así evitamos que las dos vías de creación
        # de la tabla queden en silencio con comportamientos distintos.
        op.alter_column('producto', 'publicado_en_tienda', server_default=None)


def downgrade() -> None:
    # Deliberadamente no implementado: ver la nota de la migración anterior
    # (23b669f8703d) sobre por qué downgrade() se deja vacío en este repo.
    pass