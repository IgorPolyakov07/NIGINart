from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = '20251231_create_oauth_states'
down_revision: Union[str, None] = '20251231_add_oauth_credentials'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    op.create_table(
        'oauth_states',
        sa.Column(
            'state',
            sa.String(length=255),
            nullable=False,
            comment='CSRF protection token (UUID)'
        ),
        sa.Column(
            'platform',
            sa.String(length=50),
            nullable=False,
            comment='Platform name (tiktok, instagram, etc.)'
        ),
        sa.Column(
            'user_identifier',
            sa.String(length=255),
            nullable=True,
            comment='Optional user ID for multi-user scenarios'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
            comment='State creation timestamp'
        ),
        sa.Column(
            'expires_at',
            sa.DateTime(timezone=True),
            nullable=False,
            comment='Expiration timestamp (TTL = 10 minutes)'
        ),
        sa.Column(
            'is_used',
            sa.Boolean(),
            server_default='false',
            nullable=False,
            comment='One-time use protection flag'
        ),
        sa.PrimaryKeyConstraint('state')
    )
    op.create_index(
        op.f('ix_oauth_states_platform'),
        'oauth_states',
        ['platform'],
        unique=False
    )
    op.create_index(
        op.f('ix_oauth_states_expires_at'),
        'oauth_states',
        ['expires_at'],
        unique=False
    )
def downgrade() -> None:
    op.drop_index(op.f('ix_oauth_states_expires_at'), table_name='oauth_states')
    op.drop_index(op.f('ix_oauth_states_platform'), table_name='oauth_states')
    op.drop_table('oauth_states')
