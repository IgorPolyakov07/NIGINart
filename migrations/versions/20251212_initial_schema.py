from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False, comment='Platform name (instagram, telegram, youtube, etc.)'),
        sa.Column('account_id', sa.String(length=255), nullable=False, comment='Platform-specific account identifier'),
        sa.Column('account_url', sa.String(length=500), nullable=False, comment='Full URL to the account'),
        sa.Column('display_name', sa.String(length=255), nullable=False, comment='Human-readable account name'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Whether data collection is enabled'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accounts_platform'), 'accounts', ['platform'], unique=False)
    op.create_table(
        'metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False, comment='Timestamp when data was collected'),
        sa.Column('followers', sa.Integer(), nullable=True, comment='Number of followers/subscribers'),
        sa.Column('posts_count', sa.Integer(), nullable=True, comment='Total number of posts/videos'),
        sa.Column('total_likes', sa.Integer(), nullable=True, comment='Total likes across recent posts'),
        sa.Column('total_comments', sa.Integer(), nullable=True, comment='Total comments across recent posts'),
        sa.Column('total_views', sa.Integer(), nullable=True, comment='Total views (for video platforms)'),
        sa.Column('total_shares', sa.Integer(), nullable=True, comment='Total shares/reposts'),
        sa.Column('engagement_rate', sa.Float(), nullable=True, comment='Engagement rate percentage'),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Additional platform-specific metrics'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_metrics_account_id'), 'metrics', ['account_id'], unique=False)
    op.create_index(op.f('ix_metrics_collected_at'), 'metrics', ['collected_at'], unique=False)
    op.create_table(
        'collection_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, comment='Collection start time'),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True, comment='Collection end time'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='Status: success, partial, failed'),
        sa.Column('accounts_processed', sa.Integer(), nullable=False, server_default='0', comment='Number of accounts successfully processed'),
        sa.Column('accounts_failed', sa.Integer(), nullable=False, server_default='0', comment='Number of accounts that failed'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Error details if collection failed'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_collection_logs_started_at'), 'collection_logs', ['started_at'], unique=False)
def downgrade() -> None:
    op.drop_index(op.f('ix_collection_logs_started_at'), table_name='collection_logs')
    op.drop_table('collection_logs')
    op.drop_index(op.f('ix_metrics_collected_at'), table_name='metrics')
    op.drop_index(op.f('ix_metrics_account_id'), table_name='metrics')
    op.drop_table('metrics')
    op.drop_index(op.f('ix_accounts_platform'), table_name='accounts')
    op.drop_table('accounts')
