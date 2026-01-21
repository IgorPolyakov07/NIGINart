from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
revision: str = '98b36e533eb9'
down_revision: Union[str, None] = '813bec30b934'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    op.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_accounts_tiktok_platform
            ON accounts(platform, is_active, display_name)
            WHERE platform = 'tiktok'
        """)
    )
    op.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_metrics_extra_data_gin
            ON metrics USING gin(extra_data)
        """)
    )
    op.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_metrics_account_collected_desc
            ON metrics(account_id, collected_at DESC)
        """)
    )
def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS ix_accounts_tiktok_platform"))
    op.execute(text("DROP INDEX IF EXISTS ix_metrics_extra_data_gin"))
    op.execute(text("DROP INDEX IF EXISTS ix_metrics_account_collected_desc"))
