"""Add group isolation to all entities

Revision ID: 68857bc4
Revises: b2c3d4e5f6g7
Create Date: 2025-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '68857bc4'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add group_id columns to entities missing group isolation and migrate existing data."""
    
    # Add group_id columns with nullable=True initially for existing data
    op.add_column('ai_configurations', 
                  sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('prompts', 
                  sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('prompt_categories', 
                  sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('test_executions', 
                  sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Populate group_id fields for existing data
    connection = op.get_bind()
    
    # Update ai_configurations: set group_id based on creator's group
    connection.execute(sa.text("""
        UPDATE ai_configurations 
        SET group_id = users.group_id
        FROM users 
        WHERE ai_configurations.created_by = users.id 
        AND ai_configurations.group_id IS NULL
        AND users.group_id IS NOT NULL
    """))
    
    # Update prompts: set group_id based on creator's group  
    connection.execute(sa.text("""
        UPDATE prompts 
        SET group_id = users.group_id
        FROM users 
        WHERE prompts.created_by = users.id 
        AND prompts.group_id IS NULL
        AND users.group_id IS NOT NULL
    """))
    
    # Update prompt_categories: set group_id based on creator's group
    connection.execute(sa.text("""
        UPDATE prompt_categories 
        SET group_id = users.group_id
        FROM users 
        WHERE prompt_categories.created_by = users.id 
        AND prompt_categories.group_id IS NULL
        AND users.group_id IS NOT NULL
    """))
    
    # Update test_executions: set group_id based on test's group_id
    connection.execute(sa.text("""
        UPDATE test_executions 
        SET group_id = ai_tests.group_id
        FROM ai_tests 
        WHERE test_executions.test_id = ai_tests.id 
        AND test_executions.group_id IS NULL
        AND ai_tests.group_id IS NOT NULL
    """))
    
    # Add indexes for performance (before foreign keys for better performance)
    op.create_index('idx_ai_configurations_group_id', 'ai_configurations', ['group_id'])
    op.create_index('idx_prompts_group_id', 'prompts', ['group_id'])
    op.create_index('idx_prompt_categories_group_id', 'prompt_categories', ['group_id'])
    op.create_index('idx_test_executions_group_id', 'test_executions', ['group_id'])
    
    # Add foreign key constraints
    op.create_foreign_key('fk_ai_configurations_group_id', 'ai_configurations', 'groups', ['group_id'], ['id'])
    op.create_foreign_key('fk_prompts_group_id', 'prompts', 'groups', ['group_id'], ['id'])
    op.create_foreign_key('fk_prompt_categories_group_id', 'prompt_categories', 'groups', ['group_id'], ['id'])
    op.create_foreign_key('fk_test_executions_group_id', 'test_executions', 'groups', ['group_id'], ['id'])


def downgrade() -> None:
    """Remove group isolation columns and constraints."""
    
    # Remove foreign key constraints first
    op.drop_constraint('fk_test_executions_group_id', 'test_executions', type_='foreignkey')
    op.drop_constraint('fk_prompt_categories_group_id', 'prompt_categories', type_='foreignkey')
    op.drop_constraint('fk_prompts_group_id', 'prompts', type_='foreignkey')
    op.drop_constraint('fk_ai_configurations_group_id', 'ai_configurations', type_='foreignkey')
    
    # Remove indexes
    op.drop_index('idx_test_executions_group_id', 'test_executions')
    op.drop_index('idx_prompt_categories_group_id', 'prompt_categories')
    op.drop_index('idx_prompts_group_id', 'prompts')
    op.drop_index('idx_ai_configurations_group_id', 'ai_configurations')
    
    # Remove columns (no need to migrate data back since group_id is derived)
    op.drop_column('test_executions', 'group_id')
    op.drop_column('prompt_categories', 'group_id')
    op.drop_column('prompts', 'group_id')
    op.drop_column('ai_configurations', 'group_id')