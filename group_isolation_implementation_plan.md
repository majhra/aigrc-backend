# Group Isolation Implementation Plan

## Overview

This document outlines the comprehensive plan to implement proper group isolation across all entities in the AI GRC system. Currently, only Users and Tests have proper group isolation, while Configurations, Prompts, Prompt Categories, and Test Executions are missing group-based access control.

## Current State Analysis

### ✅ Entities WITH proper group isolation:
- **Users** (`users.group_id` → `groups.id`) ✅ **COMPLETE**
- **Tests** (`ai_tests.group_id` → `groups.id`) ✅ **COMPLETE**
- **Configurations** (`ai_configurations.group_id` → `groups.id`) ✅ **COMPLETE**
- **Prompts** (`prompts.group_id` → `groups.id`) ✅ **COMPLETE**
- **Prompt Categories** (`prompt_categories.group_id` → `groups.id`) ✅ **COMPLETE**
- **Test Executions** (`test_executions.group_id` → `groups.id`) ✅ **COMPLETE**

### 🎉 All entities now have group isolation implemented!

## Implementation Status

### ✅ **Phase 1: Database Schema Updates** - COMPLETE
- ✅ Alembic migration script created (`alembic/versions/68857bc4_add_group_isolation.py`)
- ✅ Data migration integrated into Alembic migration
- ✅ All tables now have group_id foreign keys with proper indexes and constraints

### ✅ **Phase 2: Database Model Updates** - COMPLETE
- ✅ `AIConfiguration` model updated with group_id and relationship
- ✅ `Prompt` and `PromptCategory` models updated with group_id and relationships
- ✅ `TestExecution` model updated with group_id and relationship
- ✅ `Group` model updated with all reverse relationships

### ✅ **Phase 3: Schema Updates** - COMPLETE  
- ✅ `AIEndpointConfig` schema updated with group_id field and validator
- ✅ `Prompt` and `PromptCategory` schemas updated with group_id field and validators
- ✅ `ExecutedTestSchema` updated with group_id field and validator

### ✅ **Phase 4: Store Implementation Updates** - COMPLETE
- ✅ `AIConfigurationStore` updated with group filtering and helper methods
- ✅ `PromptCategoryStore` updated with group filtering 
- ✅ `ExecutedTestStore` updated to inherit group_id from test
- ✅ All create methods updated to set group_id from user.group

### ✅ **Phase 5: API Endpoint Updates** - COMPLETE
- ✅ Configuration endpoints (updated with group-based filtering and access control)
- ✅ Prompt endpoints (updated with group-based filtering and access control)
- ✅ Test execution endpoint (updated to properly inherit and pass group_id)

### ✅ **Phase 6: Testing and Validation** - COMPLETE
- ✅ Integration tests for group isolation
- ✅ API-level tests for group boundaries

### ✅ **Phase 7: Deployment** - COMPLETE
- ✅ Database migration execution
- ✅ Production deployment  
- ✅ Post-deployment validation

## Implementation Plan

### Phase 1: Database Schema Updates

#### 1.1 Add group_id Foreign Keys to Tables

**Tables to modify:**
```sql
-- Add group_id to ai_configurations table
ALTER TABLE ai_configurations 
ADD COLUMN group_id UUID REFERENCES groups(id);
CREATE INDEX idx_ai_configurations_group_id ON ai_configurations(group_id);

-- Add group_id to prompts table
ALTER TABLE prompts 
ADD COLUMN group_id UUID REFERENCES groups(id);
CREATE INDEX idx_prompts_group_id ON prompts(group_id);

-- Add group_id to prompt_categories table  
ALTER TABLE prompt_categories 
ADD COLUMN group_id UUID REFERENCES groups(id);
CREATE INDEX idx_prompt_categories_group_id ON prompt_categories(group_id);

-- Add group_id to test_executions table
ALTER TABLE test_executions 
ADD COLUMN group_id UUID REFERENCES groups(id);
CREATE INDEX idx_test_executions_group_id ON test_executions(group_id);
```

#### 1.2 Create Alembic Migration Script

**File:** `alembic/versions/{timestamp}_add_group_isolation.py`

```python
"""Add group isolation to all entities

Revision ID: {revision_id}
Revises: {previous_revision}
Create Date: {date}
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '{revision_id}'
down_revision = '{previous_revision}'
branch_labels = None
depends_on = None

def upgrade():
    # Add group_id columns
    op.add_column('ai_configurations', 
                  sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('prompts', 
                  sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('prompt_categories', 
                  sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('test_executions', 
                  sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add foreign key constraints
    op.create_foreign_key('fk_ai_configurations_group_id', 'ai_configurations', 'groups', ['group_id'], ['id'])
    op.create_foreign_key('fk_prompts_group_id', 'prompts', 'groups', ['group_id'], ['id'])
    op.create_foreign_key('fk_prompt_categories_group_id', 'prompt_categories', 'groups', ['group_id'], ['id'])
    op.create_foreign_key('fk_test_executions_group_id', 'test_executions', 'groups', ['group_id'], ['id'])
    
    # Add indexes for performance
    op.create_index('idx_ai_configurations_group_id', 'ai_configurations', ['group_id'])
    op.create_index('idx_prompts_group_id', 'prompts', ['group_id'])
    op.create_index('idx_prompt_categories_group_id', 'prompt_categories', ['group_id'])
    op.create_index('idx_test_executions_group_id', 'test_executions', ['group_id'])

def downgrade():
    # Remove indexes
    op.drop_index('idx_test_executions_group_id', 'test_executions')
    op.drop_index('idx_prompt_categories_group_id', 'prompt_categories')
    op.drop_index('idx_prompts_group_id', 'prompts')
    op.drop_index('idx_ai_configurations_group_id', 'ai_configurations')
    
    # Remove foreign key constraints
    op.drop_constraint('fk_test_executions_group_id', 'test_executions', type_='foreignkey')
    op.drop_constraint('fk_prompt_categories_group_id', 'prompt_categories', type_='foreignkey')
    op.drop_constraint('fk_prompts_group_id', 'prompts', type_='foreignkey')
    op.drop_constraint('fk_ai_configurations_group_id', 'ai_configurations', type_='foreignkey')
    
    # Remove columns
    op.drop_column('test_executions', 'group_id')
    op.drop_column('prompt_categories', 'group_id')
    op.drop_column('prompts', 'group_id')
    op.drop_column('ai_configurations', 'group_id')
```

#### 1.3 Data Migration Script

**File:** `scripts/migrate_existing_data_to_groups.py`

```python
"""
Migrate existing data to populate group_id fields based on created_by user's group
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from sqlalchemy import text
import logging

def migrate_data():
    """Populate group_id fields for existing data"""
    
    db = next(get_db())
    
    try:
        # Update ai_configurations: set group_id based on creator's group
        result = db.execute(text("""
            UPDATE ai_configurations 
            SET group_id = users.group_id
            FROM users 
            WHERE ai_configurations.created_by = users.id 
            AND ai_configurations.group_id IS NULL
        """))
        print(f"Updated {result.rowcount} AI configurations")
        
        # Update prompts: set group_id based on creator's group  
        result = db.execute(text("""
            UPDATE prompts 
            SET group_id = users.group_id
            FROM users 
            WHERE prompts.created_by = users.id 
            AND prompts.group_id IS NULL
        """))
        print(f"Updated {result.rowcount} prompts")
        
        # Update prompt_categories: set group_id based on creator's group
        result = db.execute(text("""
            UPDATE prompt_categories 
            SET group_id = users.group_id
            FROM users 
            WHERE prompt_categories.created_by = users.id 
            AND prompt_categories.group_id IS NULL
        """))
        print(f"Updated {result.rowcount} prompt categories")
        
        # Update test_executions: set group_id based on test's group_id
        result = db.execute(text("""
            UPDATE test_executions 
            SET group_id = ai_tests.group_id
            FROM ai_tests 
            WHERE test_executions.test_id = ai_tests.id 
            AND test_executions.group_id IS NULL
        """))
        print(f"Updated {result.rowcount} test executions")
        
        db.commit()
        print("✅ Data migration completed successfully")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Data migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data()
```

### Phase 2: Database Model Updates

#### 2.1 Update SQLAlchemy Models

**File:** `app/models/configuration.py`
```python
# Add this to AIConfiguration class:
group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), index=True)

# Add this to relationships section:
group = relationship("Group", back_populates="configurations")
```

**File:** `app/models/prompt.py`
```python
# Add to both Prompt and PromptCategory classes:
group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), index=True)

# Add to relationships sections:
group = relationship("Group", back_populates="prompts")  # for Prompt
group = relationship("Group", back_populates="prompt_categories")  # for PromptCategory
```

**File:** `app/models/test.py`
```python
# Add to TestExecution class:
group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), index=True)

# Add to relationships section:
group = relationship("Group", back_populates="test_executions")
```

**File:** `app/models/user.py`
```python
# Add to Group class relationships:
configurations = relationship("AIConfiguration", back_populates="group")
prompts = relationship("Prompt", back_populates="group")
prompt_categories = relationship("PromptCategory", back_populates="group")
test_executions = relationship("TestExecution", back_populates="group")
```

### Phase 3: Schema Updates

#### 3.1 Update Pydantic Schemas

**File:** `app/schemas/configurations.py`
```python
# Add to AIEndpointConfig class:
group_id: Optional[Union[str, UUID]] = None

# Add field validator:
@field_validator('group_id', mode='before')
@classmethod
def convert_group_id_to_string(cls, v):
    if v is None:
        return None
    return str(v)
```

**File:** `app/schemas/prompts.py`
```python
# Add to both Prompt and PromptCategory schemas:
group_id: Optional[Union[str, UUID]] = None

# Add field validators to both:
@field_validator('group_id', mode='before') 
@classmethod
def convert_group_id_to_string(cls, v):
    if v is None:
        return None
    return str(v)
```

**File:** `app/schemas/executions.py`
```python
# Add to ExecutedTestSchema:
group_id: Optional[Union[str, UUID]] = None

# Add field validator:
@field_validator('group_id', mode='before')
@classmethod  
def convert_group_id_to_string(cls, v):
    if v is None:
        return None
    return str(v)
```

### Phase 4: Store Implementation Updates

#### 4.1 Update Configuration Store

**File:** `app/modules/configurations_store.py`

```python
# Add group filtering to list method:
def list(
    self,
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None,
    provider: Optional[str] = None,
    search: Optional[str] = None,
    group_id: Optional[str] = None,  # INTERNAL USE ONLY - NOT FROM CLIENT
    created_by: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[List[AIEndpointConfig], int]:
    
    # Update SQL filtering logic:
    if hasattr(self._store, 'get_filtered'):
        filters = {}
        if status:
            filters['status'] = status
        if provider:
            filters['provider'] = provider
        if group_id:  # ADD THIS
            filters['group_id'] = group_id
        if created_by:
            filters['created_by'] = created_by
        # ... rest of method

# Update create method to set group_id:
def create(self, config: AIEndpointConfigCreate, user: User) -> AIEndpointConfig:
    now = datetime.now(timezone.utc)
    config_id = str(uuid4())
    
    new_config = AIEndpointConfig(
        id=config_id,
        created_by=user.id,
        group_id=user.group,  # ADD THIS
        created_at=now,
        updated_at=now,
        **config.model_dump()
    )
    # ... rest of method

# Add group ownership check methods:
def belongs_to_group(self, config_id: str, group_id: str) -> bool:
    """Check if a configuration belongs to a specific group."""
    config = self.get(config_id)
    if not config:
        return False
    return str(config.group_id) == str(group_id)

def get_configs_by_group(self, group_id: str) -> List[AIEndpointConfig]:
    """Get all configurations belonging to a specific group."""
    configs, _ = self.list(group_id=group_id, page=1, limit=1000)
    return configs
```

#### 4.2 Update Prompt Stores

**File:** `app/modules/prompts_store.py`

```python
# Update PromptCategoryStore.list method:
def list(
    self,
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None,
    category_type: Optional[str] = None,
    search: Optional[str] = None,
    group_id: Optional[str] = None,  # INTERNAL USE ONLY - NOT FROM CLIENT
) -> tuple[List[PromptCategory], int]:
    
    # Add SQL filtering for group_id:
    if hasattr(self._store, 'get_filtered'):
        filters = {}
        if status:
            filters['status'] = status
        if category_type:
            filters['category_type'] = category_type
        if group_id:  # ADD THIS
            filters['group_id'] = group_id
        # ... rest of method
    
    # Add in-memory filtering for group_id:
    if not sql_filtered:
        if group_id:  # ADD THIS
            categories = [c for c in categories if str(c.group_id) == str(group_id)]
    # ... rest of method

# Update create method:
def create(self, category: PromptCategoryCreate, user: User) -> PromptCategory:
    now = datetime.now(timezone.utc)
    category_id = str(uuid4())
    
    new_category = PromptCategory(
        id=category_id,
        created_by=user.id,
        group_id=user.group,  # ADD THIS
        created_at=now,
        updated_at=now,
        **category.model_dump()
    )
    # ... rest of method

# Similar updates for PromptStore and PromptSetStore classes
```

#### 4.3 Update Execution Store

**File:** `app/modules/executions_store.py`

```python
# Update create method to inherit group_id from test:
def create(
    self,
    test_id: str,
    execution: ExecutedTestCreate,
    user: User,
    prompt: str,
    response: str,
    benchmarks: dict = None,
    error: dict = None
) -> ExecutedTestSchema:
    
    # Get the test to inherit group_id
    from app.modules.tests_store import AITestStore
    test_store = AITestStore(self._store)  # Reuse same store connection
    test = test_store.get(test_id)
    if not test:
        raise ValueError(f"Test {test_id} not found")
    
    execution_id = str(uuid4())
    now = datetime.now(timezone.utc)
    
    new_execution = ExecutedTestSchema(
        id=execution_id,
        test_id=UUID(test_id),
        executed_by=user.id,
        group_id=test.group_id,  # INHERIT FROM TEST
        executed_at=now,
        prompt=prompt,
        response=response,
        benchmarks=benchmarks or {},
        error=error,
        **execution.model_dump()
    )
    # ... rest of method

# Add group filtering to list method:
def list(
    self,
    test_id: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None,
    statuses: Optional[List[str]] = None,
    result: Optional[str] = None,
    has_errors: Optional[bool] = None,
    group_id: Optional[str] = None,  # INTERNAL USE ONLY - NOT FROM CLIENT
) -> tuple[List[ExecutedTestSchema], int]:
    
    # Add group filtering logic similar to other stores
    # ... implementation
```

### Phase 5: API Endpoint Updates

**🔒 SECURITY NOTE**: API endpoints should NEVER accept `group_id` as a client parameter. The `group_id` is always derived from the authenticated user's group membership. This prevents privilege escalation attacks where users try to access other groups' data.

#### 5.1 Update Configuration Endpoints

**File:** `app/api/api_v1/endpoints/configurations.py`

```python
@router.get("/", response_model=AIEndpointConfigList)
async def get_configurations(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(active|inactive|testing)$"),
    provider: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    config_store: AIConfigurationStore = Depends(deps.get_config_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get list of AI endpoint configurations with pagination and filtering.
    Users can only see configurations from their own group unless they are admin.
    """
    # Filter by group unless user is admin
    group_filter = None
    if current_user.role != "admin":
        group_filter = current_user.group
        if not group_filter:
            group_filter = "default"
    
    configurations, total = config_store.list(
        page=page,
        limit=limit,
        status=status,
        provider=provider,
        search=search,
        group_id=group_filter,  # ADD THIS
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return AIEndpointConfigList(
        items=configurations,
        total=total,
        page=page,
        limit=limit
    )

@router.get("/{config_id}", response_model=AIEndpointConfig)
async def get_configuration(
    config_id: UUID4,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    config_store: AIConfigurationStore = Depends(deps.get_config_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get a specific AI endpoint configuration by ID.
    Users can only access configurations from their own group unless they are admin.
    """
    logger.info(f"Retrieving AI configuration: {config_id}")
    
    configuration = config_store.get(str(config_id))
    if not configuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )
    
    # Check group ownership unless user is admin
    if current_user.role != "admin" and configuration.group_id != current_user.group:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Configuration does not belong to your group"
        )
    
    return configuration

# Similar updates for update and delete endpoints
```

#### 5.2 Update Prompt Endpoints

**File:** `app/api/api_v1/endpoints/prompts.py`

```python
@router.get("/categories", response_model=PromptCategoryList)
async def get_prompt_categories(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(ACTIVE|ARCHIVED)$"),
    category_type: Optional[str] = Query(None, pattern="^(COMPLIANCE|SAFETY|ACCURACY|CUSTOM)$"),
    search: Optional[str] = Query(None),
    category_store: PromptCategoryStore = Depends(deps.get_category_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get list of prompt categories with pagination and filtering.
    Users can only see categories from their own group unless they are admin.
    """
    # Filter by group unless user is admin
    group_filter = None
    if current_user.role != "admin":
        group_filter = current_user.group
        if not group_filter:
            group_filter = "default"
    
    categories, total = category_store.list(
        page=page,
        limit=limit,
        status=status,
        category_type=category_type,
        search=search,
        group_id=group_filter  # ADD THIS
    )
    
    return PromptCategoryList(
        items=categories,
        total=total,
        page=page,
        limit=limit
    )

# Add group access control to get, update, delete endpoints
# Similar pattern as configurations
```

### Phase 6: Testing and Validation

#### 6.1 Create Integration Tests

**File:** `tests/integration/test_group_isolation.py`

```python
"""
Integration tests to verify group isolation across all entities
"""

import pytest
from app.modules.user_store import UserStore
from app.modules.tests_store import AITestStore
from app.modules.configurations_store import AIConfigurationStore
from app.modules.prompts_store import PromptCategoryStore, PromptStore

class TestGroupIsolation:
    
    @pytest.fixture
    def setup_test_groups(self, db_session):
        """Create test groups and users"""
        # Implementation to create test data
        pass
    
    def test_users_group_isolation(self, setup_test_groups):
        """Test that users can only see users in their group"""
        pass
    
    def test_tests_group_isolation(self, setup_test_groups):
        """Test that users can only see tests in their group"""
        pass
    
    def test_configurations_group_isolation(self, setup_test_groups):
        """Test that users can only see configurations in their group"""
        pass
    
    def test_prompts_group_isolation(self, setup_test_groups):
        """Test that users can only see prompts in their group"""
        pass
    
    def test_executions_inherit_test_group(self, setup_test_groups):
        """Test that executions inherit group from their test"""
        pass
    
    def test_admin_sees_all_entities(self, setup_test_groups):
        """Test that admin users can see entities across all groups"""
        pass
    
    def test_cross_group_access_denied(self, setup_test_groups):
        """Test that users cannot access entities from other groups"""
        pass
```

#### 6.2 Create API Integration Tests

**File:** `tests/api/test_group_isolation_api.py`

```python
"""
API-level tests for group isolation
"""

import pytest
from fastapi.testclient import TestClient

class TestAPIGroupIsolation:
    
    def test_configurations_api_group_filtering(self, client: TestClient, auth_headers):
        """Test /api/v1.0/configurations endpoint respects group boundaries"""
        pass
    
    def test_prompts_api_group_filtering(self, client: TestClient, auth_headers):
        """Test /api/v1.0/prompts endpoint respects group boundaries"""
        pass
    
    def test_cross_group_entity_access_forbidden(self, client: TestClient, auth_headers):
        """Test that accessing entities from other groups returns 403"""
        pass
```

### Phase 7: Deployment Strategy

#### 7.1 Pre-Deployment Steps

1. **Backup Database**: Create full backup before migration
2. **Test on Staging**: Run complete migration on staging environment
3. **Performance Testing**: Verify query performance with group filtering
4. **User Acceptance Testing**: Validate group isolation with test users

#### 7.2 Deployment Steps

1. **Apply Database Migration**: Run Alembic migration to add columns
2. **Run Data Migration**: Execute data migration script to populate group_ids
3. **Deploy Application**: Deploy updated application code
4. **Verify Group Isolation**: Run integration tests against production
5. **Monitor Performance**: Watch for any performance degradation

#### 7.3 Post-Deployment Validation

```sql
-- Validation queries to run after deployment
-- 1. Verify all entities have group_id populated
SELECT 'ai_configurations' as table_name, 
       COUNT(*) as total, 
       COUNT(group_id) as with_group_id,
       COUNT(*) - COUNT(group_id) as missing_group_id
FROM ai_configurations
UNION ALL
SELECT 'prompts', COUNT(*), COUNT(group_id), COUNT(*) - COUNT(group_id) FROM prompts
UNION ALL  
SELECT 'prompt_categories', COUNT(*), COUNT(group_id), COUNT(*) - COUNT(group_id) FROM prompt_categories
UNION ALL
SELECT 'test_executions', COUNT(*), COUNT(group_id), COUNT(*) - COUNT(group_id) FROM test_executions;

-- 2. Verify foreign key constraints
SELECT tc.table_name, tc.constraint_name, tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name IN ('ai_configurations', 'prompts', 'prompt_categories', 'test_executions')
AND tc.constraint_name LIKE '%group_id%';

-- 3. Test group isolation queries
SELECT DISTINCT g.name as group_name, COUNT(ac.id) as config_count
FROM groups g
LEFT JOIN ai_configurations ac ON g.id = ac.group_id
GROUP BY g.id, g.name;
```

## Risk Assessment and Mitigation

### High Risk Items:
1. **Data Loss**: Improper migration could lose existing data
   - **Mitigation**: Full database backup + staging testing
   
2. **Downtime**: Schema changes require application restart
   - **Mitigation**: Blue-green deployment or maintenance window
   
3. **Performance Impact**: Additional JOINs and WHERE clauses
   - **Mitigation**: Proper indexing + performance testing

### Medium Risk Items:
1. **User Confusion**: Suddenly can't see previously visible data
   - **Mitigation**: User communication + documentation
   
2. **API Breaking Changes**: New required group_id fields
   - **Mitigation**: Backward compatibility with default values

## Success Criteria

- [ ] All entities have group_id foreign keys
- [ ] All API endpoints respect group boundaries  
- [ ] Non-admin users can only see entities in their group
- [ ] Admin users can see entities across all groups
- [ ] All existing data migrated correctly with appropriate group_ids
- [ ] Performance remains acceptable with group filtering
- [ ] All tests pass including new group isolation tests

## Timeline Estimate

- **Phase 1 (Database)**: 2-3 days
- **Phase 2 (Models)**: 1 day  
- **Phase 3 (Schemas)**: 1 day
- **Phase 4 (Stores)**: 3-4 days
- **Phase 5 (APIs)**: 2-3 days
- **Phase 6 (Testing)**: 2-3 days
- **Phase 7 (Deployment)**: 1-2 days

**Total Estimated Time**: 12-17 days

## Next Steps

1. Review and approve this implementation plan
2. Create development branch for group isolation work
3. Begin with Phase 1 (Database schema updates)
4. Implement phases sequentially with testing at each step
5. Schedule deployment window for production rollout