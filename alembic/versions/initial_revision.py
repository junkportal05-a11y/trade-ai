"""initial revision

Revision ID: initial_revision
Revises:
Create Date: $(date +"%Y-%m-%d %H:%M:%S.%f") ->

"""

from alembic import op
from datetime import datetime
from app.core.database import Base

def upgrade():
    # Create all tables defined in Base metadata
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    # Drop all tables created in upgrade
    Base.metadata.drop_all(bind=op.get_bind())