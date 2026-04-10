"""add foto_url to usuario

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('usuarios', sa.Column('foto_url', sa.String(500), nullable=True))


def downgrade():
    op.drop_column('usuarios', 'foto_url')
