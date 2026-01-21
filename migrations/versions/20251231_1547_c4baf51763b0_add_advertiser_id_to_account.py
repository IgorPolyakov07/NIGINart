from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = 'c4baf51763b0'
down_revision: Union[str, None] = '20251231_create_oauth_states'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    op.add_column('accounts',
        sa.Column('advertiser_id', sa.String(length=255), nullable=True,
                  comment='TikTok advertiser ID for Marketing API')
    )
def downgrade() -> None:
    op.drop_column('accounts', 'advertiser_id')
