"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-25

Baseline migration: creates all tables from the ORM metadata.
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app import models  # noqa: F401
    from app.db import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app import models  # noqa: F401
    from app.db import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
