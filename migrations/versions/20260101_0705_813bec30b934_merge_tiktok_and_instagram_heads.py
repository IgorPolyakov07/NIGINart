from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = '813bec30b934'
down_revision: Union[str, None] = ('c4baf51763b0', 'd2t99os4qe7j')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    pass
def downgrade() -> None:
    pass
