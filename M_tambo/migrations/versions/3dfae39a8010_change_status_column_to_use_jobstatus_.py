"""Change status column to use JobStatus enum and set existing values to Pending

Revision ID: 3dfae39a8010
Revises: 
Create Date: 2024-09-17 19:14:54.362507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3dfae39a8010'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
