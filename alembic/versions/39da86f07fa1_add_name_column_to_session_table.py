"""add name column to session table

Revision ID: 39da86f07fa1
Revises: 
Create Date: 2025-03-13 16:11:36.415562

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '39da86f07fa1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('sessions', sa.Column('name', sa.String(), nullable=False, server_default='Untitled Session'))
    op.drop_constraint('sessions_user_id_fkey', 'sessions', type_='foreignkey')
    op.drop_column('sessions', 'user_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('sessions', sa.Column('user_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.create_foreign_key('sessions_user_id_fkey', 'sessions', 'users', ['user_id'], ['id'])
    op.drop_column('sessions', 'name')
    # ### end Alembic commands ### 