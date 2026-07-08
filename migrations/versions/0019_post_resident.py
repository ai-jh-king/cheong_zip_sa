"""posts.resident — 단지 주민 표시(우리집 대조, 자가 등록 기반)."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0019_post_resident"
down_revision = "0018_landmarks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    cols = [c["name"] for c in insp.get_columns("posts")]
    if "resident" not in cols:
        op.add_column("posts", sa.Column("resident", sa.Boolean(),
                                         nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("posts", "resident")
