from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision: str = 'd2t99os4qe7j'
down_revision: Union[str, None] = '20251231_create_oauth_states'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    op.create_table(
        'instagram_story_snapshots',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Primary key UUID'
        ),
        sa.Column(
            'account_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Reference to Instagram account'
        ),
        sa.Column(
            'story_id',
            sa.String(length=255),
            nullable=False,
            comment='Instagram story media ID (from Graph API)'
        ),
        sa.Column(
            'collected_at',
            sa.DateTime(timezone=True),
            nullable=False,
            comment='Timestamp of this snapshot collection'
        ),
        sa.Column(
            'posted_at',
            sa.DateTime(timezone=True),
            nullable=False,
            comment='When the story was originally posted'
        ),
        sa.Column(
            'retention_expires_at',
            sa.DateTime(timezone=True),
            nullable=False,
            comment='When story will expire (posted_at + 24 hours)'
        ),
        sa.Column(
            'media_type',
            sa.String(length=50),
            nullable=False,
            comment='Story media type (IMAGE or VIDEO)'
        ),
        sa.Column(
            'media_url',
            sa.String(length=1000),
            nullable=True,
            comment='Media URL (if available, may expire with story)'
        ),
        sa.Column(
            'reach',
            sa.Integer(),
            nullable=True,
            comment='Unique accounts that saw this story'
        ),
        sa.Column(
            'impressions',
            sa.Integer(),
            nullable=True,
            comment='Total views of this story (includes multiple views by same user)'
        ),
        sa.Column(
            'exits',
            sa.Integer(),
            nullable=True,
            comment='Number of times users exited this story'
        ),
        sa.Column(
            'replies',
            sa.Integer(),
            nullable=True,
            comment='Number of direct message replies'
        ),
        sa.Column(
            'taps_forward',
            sa.Integer(),
            nullable=True,
            comment='Number of taps to next story'
        ),
        sa.Column(
            'taps_back',
            sa.Integer(),
            nullable=True,
            comment='Number of taps to previous story'
        ),
        sa.Column(
            'completion_rate',
            sa.Float(),
            nullable=True,
            comment='Percentage of viewers who watched to completion (calculated)'
        ),
        sa.Column(
            'extra_data',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Additional story metadata and insights'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
            comment='Record creation timestamp'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
            comment='Record last update timestamp'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_instagram_story_snapshots_account_id', 'instagram_story_snapshots', ['account_id'])
    op.create_index('idx_instagram_story_snapshots_story_id', 'instagram_story_snapshots', ['story_id'])
    op.create_index('idx_instagram_story_snapshots_collected_at', 'instagram_story_snapshots', ['collected_at'])
    op.create_index('idx_instagram_story_snapshots_retention_expires_at', 'instagram_story_snapshots', ['retention_expires_at'])
    op.create_index(
        'idx_story_snapshots_story_id_collected',
        'instagram_story_snapshots',
        ['story_id', 'collected_at'],
        unique=False
    )
    op.create_index(
        'idx_story_snapshots_account_retention',
        'instagram_story_snapshots',
        ['account_id', 'retention_expires_at'],
        unique=False
    )
def downgrade() -> None:
    op.drop_index('idx_story_snapshots_account_retention', table_name='instagram_story_snapshots')
    op.drop_index('idx_story_snapshots_story_id_collected', table_name='instagram_story_snapshots')
    op.drop_index('idx_instagram_story_snapshots_retention_expires_at', table_name='instagram_story_snapshots')
    op.drop_index('idx_instagram_story_snapshots_collected_at', table_name='instagram_story_snapshots')
    op.drop_index('idx_instagram_story_snapshots_story_id', table_name='instagram_story_snapshots')
    op.drop_index('idx_instagram_story_snapshots_account_id', table_name='instagram_story_snapshots')
    op.drop_table('instagram_story_snapshots')
