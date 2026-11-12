"""baseline - esquema actual

Revision ID: 23b669f8703d
Revises:
Create Date: 2026-11-11 10:53:46.436462

Nota de corrección (2026-11-12): la versión original de esta migración
asumía que las tablas `pedidoweb`/`detallepedidoweb` ya existían (porque en
el entorno donde se autogeneró, `create_db_and_tables()` ya las había
creado antes). Contra una base de producción real -que todavía no las
tiene, y tampoco tiene `producto.imagen_url`- esa versión fallaba de
inmediato con `UndefinedTable: relation "pedidoweb" does not exist`, y aun
si no fallara, nunca agregaba la columna nueva a `producto`.

Esta versión es idempotente: revisa qué existe en la base antes de actuar,
así que funciona igual si se corre contra producción (nada de esto existe
todavía) o contra un entorno de desarrollo donde `create_all()` ya generó
las tablas nuevas por su cuenta.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '23b669f8703d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tablas = insp.get_table_names()

    # --- producto.imagen_url ---
    # Columna nueva para la tienda pública (foto del producto). create_all()
    # nunca altera tablas existentes, así que sin esto la columna jamás
    # aparece en una base que ya tenía `producto` antes de esta rama.
    if 'producto' in tablas:
        columnas_producto = {c['name'] for c in insp.get_columns('producto')}
        if 'imagen_url' not in columnas_producto:
            op.add_column('producto', sa.Column('imagen_url', sa.String(), nullable=True))

    # --- pedidoweb ---
    if 'pedidoweb' not in tablas:
        op.create_table(
            'pedidoweb',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('fecha', sa.DateTime(), nullable=False),
            sa.Column('nombre_cliente', sa.String(), nullable=False),
            sa.Column('telefono_cliente', sa.String(), nullable=False),
            sa.Column('email_cliente', sa.String(), nullable=True),
            sa.Column('direccion_envio', sa.String(), nullable=False),
            sa.Column('acepta_tratamiento_datos', sa.Boolean(), nullable=False),
            sa.Column('total_pedido', sa.Numeric(), nullable=False),
            sa.Column('estado', sa.String(), nullable=False),
            sa.Column('referencia_pago', sa.String(), nullable=False),
            sa.Column('transaccion_wompi_id', sa.String(), nullable=True),
            sa.Column('expira_en', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_pedidoweb_referencia_pago', 'pedidoweb', ['referencia_pago'], unique=True)
        op.create_index('ix_pedidoweb_transaccion_wompi_id', 'pedidoweb', ['transaccion_wompi_id'])
    else:
        # Ya existe (entorno de desarrollo donde create_all() se adelantó).
        # Solo nos asegura que la columna quede NOT NULL, como exige el
        # modelo actual (el endpoint ya valida esto en la aplicación, pero
        # conviene que la base lo exija también).
        columnas_pedidoweb = {c['name'] for c in insp.get_columns('pedidoweb')}
        if 'acepta_tratamiento_datos' in columnas_pedidoweb:
            op.alter_column(
                'pedidoweb', 'acepta_tratamiento_datos',
                existing_type=sa.Boolean(),
                nullable=False,
            )

    # --- detallepedidoweb ---
    if 'detallepedidoweb' not in tablas:
        op.create_table(
            'detallepedidoweb',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('pedido_id', sa.Integer(), sa.ForeignKey('pedidoweb.id'), nullable=False),
            sa.Column('producto_id', sa.Integer(), sa.ForeignKey('producto.id'), nullable=False),
            sa.Column('cantidad', sa.Integer(), nullable=False),
            sa.Column('precio_unitario', sa.Numeric(), nullable=False),
            sa.Column('nombre_producto', sa.String(), nullable=False),
        )


def downgrade() -> None:
    # Downgrade deliberadamente no implementado: esta migración agrega
    # infraestructura nueva (pedidos web). Revertirla significaría borrar
    # pedidos reales de clientes si ya se usó en producción — si alguna vez
    # hace falta deshacerla, es más seguro hacerlo a mano revisando primero
    # si hay datos.
    pass