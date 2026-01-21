from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = '20251231_add_oauth_credentials'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    op.add_column('accounts', sa.Column(
        'encrypted_access_token',
        sa.Text(),
        nullable=True,
        comment='Encrypted OAuth access token (Fernet AES-128)'
    ))
    op.add_column('accounts', sa.Column(
        'encrypted_refresh_token',
        sa.Text(),
        nullable=True,
        comment='Encrypted OAuth refresh token (Fernet AES-128)'
    ))
    op.add_column('accounts', sa.Column(
        'token_expires_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='OAuth token expiration timestamp (for auto-refresh)'
    ))
    op.add_column('accounts', sa.Column(
        'token_scope',
        sa.String(length=255),
        nullable=True,
        comment='OAuth token scopes (comma-separated)'
    ))
def downgrade() -> None:
    op.drop_column('accounts', 'token_scope')
    op.drop_column('accounts', 'token_expires_at')
    op.drop_column('accounts', 'encrypted_refresh_token')
    op.drop_column('accounts', 'encrypted_access_token')
