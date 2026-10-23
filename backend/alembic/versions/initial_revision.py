"""initial revision

Revision ID: initial_revision
Revises:
Create Date: 2026-10-15 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from app.core.database import Base

# revision identifiers, used by Alembic.
revision = 'initial_revision'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create all tables defined in Base metadata
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    # Drop all tables created in upgrade
    Base.metadata.drop_all(bind=op.get_bind())