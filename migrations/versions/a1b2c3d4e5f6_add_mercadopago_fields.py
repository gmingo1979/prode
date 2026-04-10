"""add mercadopago fields

Revision ID: a1b2c3d4e5f6
Revises: 58311034f00d
Create Date: 2026-04-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '58311034f00d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('prode_torneos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('precio_inscripcion', sa.Numeric(10, 2), nullable=False, server_default='0'))

    with op.batch_alter_table('prode_inscripciones', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mp_preference_id', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('mp_payment_id',    sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('mp_status',        sa.String(length=50),  nullable=True))


def downgrade():
    with op.batch_alter_table('prode_inscripciones', schema=None) as batch_op:
        batch_op.drop_column('mp_status')
        batch_op.drop_column('mp_payment_id')
        batch_op.drop_column('mp_preference_id')

    with op.batch_alter_table('prode_torneos', schema=None) as batch_op:
        batch_op.drop_column('precio_inscripcion')
