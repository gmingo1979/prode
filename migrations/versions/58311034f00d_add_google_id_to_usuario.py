"""add google_id to usuario

Revision ID: 58311034f00d
Revises: 597932a6672d
Create Date: 2026-04-09 23:02:56.336456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '58311034f00d'
down_revision = '597932a6672d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_id', sa.String(length=120), nullable=True))
        batch_op.create_unique_constraint('uq_usuarios_google_id', ['google_id'])


def downgrade():
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_constraint('uq_usuarios_google_id', type_='unique')
        batch_op.drop_column('google_id')
