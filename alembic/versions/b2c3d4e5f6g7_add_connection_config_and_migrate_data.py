"""Add connection_config and migrate data

Revision ID: b2c3d4e5f6g7
Revises: 913dc56ea8ea
Create Date: 2025-07-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = '913dc56ea8ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new fields and migrate existing data."""
    
    # Add new columns
    op.add_column('ai_configurations', sa.Column('failed_requests', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ai_configurations', sa.Column('avg_response_time_ms', sa.Float(), nullable=True))
    op.add_column('ai_configurations', sa.Column('connection_config', sa.JSON(), nullable=True))
    op.add_column('ai_configurations', sa.Column('bearer_token_encrypted', sa.Text(), nullable=True))
    op.add_column('ai_configurations', sa.Column('azure_client_secret_encrypted', sa.Text(), nullable=True))
    
    # Migrate existing azure_api_version data to connection_config
    # This will move azure_api_version from individual column to the JSON connection_config
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE ai_configurations 
        SET connection_config = 
            CASE 
                WHEN azure_api_version IS NOT NULL 
                THEN jsonb_build_object('azure_api_version', azure_api_version)
                ELSE '{}'::jsonb
            END
        WHERE connection_config IS NULL
    """))
    
    # Set default empty JSON for null connection_config fields
    op.alter_column('ai_configurations', 'connection_config', 
                   nullable=False, server_default='{}')
    
    # Remove the old azure_api_version column since it's now in connection_config
    op.drop_column('ai_configurations', 'azure_api_version')


def downgrade() -> None:
    """Reverse the migration."""
    
    # Add back the azure_api_version column
    op.add_column('ai_configurations', sa.Column('azure_api_version', sa.String(length=50), nullable=True))
    
    # Migrate data back from connection_config to azure_api_version
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE ai_configurations 
        SET azure_api_version = connection_config->>'azure_api_version'
        WHERE connection_config->>'azure_api_version' IS NOT NULL
    """))
    
    # Drop the new columns
    op.drop_column('ai_configurations', 'azure_client_secret_encrypted')
    op.drop_column('ai_configurations', 'bearer_token_encrypted')
    op.drop_column('ai_configurations', 'connection_config')
    op.drop_column('ai_configurations', 'avg_response_time_ms')
    op.drop_column('ai_configurations', 'failed_requests')