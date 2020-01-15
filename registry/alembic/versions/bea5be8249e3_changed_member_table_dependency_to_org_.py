"""changed member table dependency to org_uuid

Revision ID: bea5be8249e3
Revises: ff01af45872f
Create Date: 2020-01-14 20:07:52.133578

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'bea5be8249e3'
down_revision = 'ff01af45872f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('org_member', sa.Column('transaction_hash', sa.VARCHAR(length=128), nullable=True))
    op.drop_constraint('org_member_ibfk_1', 'org_member', type_='foreignkey')
    op.drop_column('org_member', 'org_row_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('org_member', sa.Column('org_row_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False))
    op.create_foreign_key('org_member_ibfk_1', 'org_member', 'organization', ['org_row_id'], ['row_id'], onupdate='CASCADE', ondelete='CASCADE')
    op.drop_column('org_member', 'transaction_hash')
    # ### end Alembic commands ###
