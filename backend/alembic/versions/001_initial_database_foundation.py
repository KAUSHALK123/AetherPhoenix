"""initial_database_foundation

Revision ID: 001_initial_db
Revises: 
Create Date: 2026-08-07 18:48:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "001_initial_db"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Database foundation baseline - no application tables created yet
    pass


def downgrade() -> None:
    # Database foundation rollback - no application tables to drop
    pass
