"""add resolution_description to complaints

Revision ID: f9f3f74b0677
Revises: 620e9158d592
Create Date: 2026-08-13 13:58:38.485842

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9f3f74b0677'
down_revision = '620e9158d592'
branch_labels = None
depends_on = None


def upgrade():
    # autogenerate also wanted to drop and the 'borough' CHECK constraint here -
    # a false positive (see CLAUDE.md, "Migrations"), not part of this change.
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resolution_description', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.drop_column('resolution_description')
