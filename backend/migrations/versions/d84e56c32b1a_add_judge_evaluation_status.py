"""add judge evaluation status

Revision ID: d84e56c32b1a
Revises: c67f23d106ab
Create Date: 2026-10-12 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd84e56c32b1a'
down_revision: Union[str, Sequence[str], None] = 'c67f23d106ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status column to judge_evaluations table
    with op.batch_alter_table('judge_evaluations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=32), nullable=True, server_default='completed'))


def downgrade() -> None:
    with op.batch_alter_table('judge_evaluations', schema=None) as batch_op:
        batch_op.drop_column('status')
