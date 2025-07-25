# PostgreSQL Migration Plan

## Overview
Migration from Redis to PostgreSQL/MySQL using synchronous SQLAlchemy implementation. This approach maintains all current interfaces while providing better data integrity, query capabilities, and standard SQL tooling.

Built into branch dev-s4.

## Current Architecture Analysis

### Store Interface (StoreProtocol)
- **Interface**: `put()`, `get()`, `get_by_email()`, `keys()`, `pop()`
- **Implementations**: RedisStore (production), LocalStore (testing)
- **Pattern**: Clean abstraction with dependency injection

### Existing Store Implementations
1. **UserStore** - Multi-tenant user management with email indexing
2. **AITestStore** - Test definitions and metadata
3. **ExecutedTestStore** - Test execution results with complex indexing
4. **AIConfigurationStore** - AI endpoint configurations with sensitive data separation
5. **PromptCategoryStore/PromptStore/PromptSetStore** - Prompt library management
6. **GroupStore** - Organization/group management
7. **ReportsStore** - Analytics aggregation

### Data Patterns
- **UUID-based keys** throughout the system
- **Group-based multi-tenancy** (`group_id:user_id` patterns)
- **Email indexing** for user lookups
- **JSON serialization** with msgpack
- **Timestamp tracking** via sorted sets

## Database Design

### Recommended Database: PostgreSQL
**Advantages:**
- Native UUID support
- Excellent JSON/JSONB support for complex fields
- Advanced indexing (GIN indexes for JSON arrays)
- Strong ACID compliance for compliance use case
- Mature ecosystem and tooling

### Core Tables Schema

```sql
-- Groups table
CREATE TABLE groups (
    id UUID PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),
    settings JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    password VARCHAR(255) NOT NULL,
    disabled BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    role VARCHAR(50),
    group_id UUID REFERENCES groups(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    verification_code VARCHAR(255),
    verification_code_expires_at TIMESTAMP WITH TIME ZONE,
    password_reset_code VARCHAR(255),
    password_reset_code_expires_at TIMESTAMP WITH TIME ZONE
);

-- Prompt categories table
CREATE TABLE prompt_categories (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category_type VARCHAR(20) NOT NULL CHECK (category_type IN ('COMPLIANCE', 'SAFETY', 'ACCURACY', 'CUSTOM')),
    priority VARCHAR(10) NOT NULL CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW')),
    tags JSONB,
    status VARCHAR(20) NOT NULL CHECK (status IN ('ACTIVE', 'ARCHIVED')),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    prompt_count INTEGER DEFAULT 0
);

-- Prompts table
CREATE TABLE prompts (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    category_id UUID REFERENCES prompt_categories(id),
    variables JSONB,
    tags JSONB,
    risk_level VARCHAR(10) NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    compliance_frameworks JSONB,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL CHECK (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0
);

-- AI configurations table
CREATE TABLE ai_configurations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    provider VARCHAR(50) NOT NULL CHECK (provider IN ('openai', 'anthropic', 'azure_openai', 'google', 'huggingface', 'custom')),
    endpoint_url VARCHAR(512),
    auth_type VARCHAR(30) NOT NULL CHECK (auth_type IN ('api_key', 'bearer_token', 'oauth', 'azure_ad')),
    model_name VARCHAR(255),
    tags JSONB,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'inactive', 'testing')),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_tested_at TIMESTAMP WITH TIME ZONE,
    last_test_status VARCHAR(20) CHECK (last_test_status IN ('success', 'failed', 'pending')),
    last_test_error TEXT,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    -- Sensitive data stored separately
    api_key_encrypted TEXT,
    azure_api_version VARCHAR(50),
    custom_headers JSONB
);

-- AI tests table
CREATE TABLE ai_tests (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    prompt_template TEXT,
    interface_type VARCHAR(30) NOT NULL CHECK (interface_type IN ('DIRECT_LLM', 'CHATBOT', 'PLUGIN_ENABLED', 'CUSTOM_APP')),
    connection_config JSONB,
    validation_config JSONB,
    tags JSONB,
    risk_level VARCHAR(10) NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
    created_by UUID REFERENCES users(id),
    group_id UUID REFERENCES groups(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_run_at TIMESTAMP WITH TIME ZONE,
    latest_execution_id UUID
);

-- Test executions table
CREATE TABLE test_executions (
    id UUID PRIMARY KEY,
    test_id UUID REFERENCES ai_tests(id),
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    executed_by UUID REFERENCES users(id),
    execution_environment JSONB,
    input_variables JSONB,
    prompt TEXT,
    response TEXT,
    benchmarks JSONB,
    validation_status VARCHAR(20) NOT NULL CHECK (validation_status IN ('PENDING', 'IN_PROGRESS', 'VALIDATED', 'ERROR')),
    validations JSONB,
    error JSONB
);

-- Add foreign key constraint after table creation
ALTER TABLE ai_tests ADD CONSTRAINT fk_latest_execution 
    FOREIGN KEY (latest_execution_id) REFERENCES test_executions(id);
```

### Indexes for Performance

```sql
-- User lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_group_id ON users(group_id);

-- Group lookups
CREATE INDEX idx_groups_name ON groups(name);

-- Test queries
CREATE INDEX idx_ai_tests_group_id ON ai_tests(group_id);
CREATE INDEX idx_ai_tests_created_by ON ai_tests(created_by);
CREATE INDEX idx_ai_tests_status ON ai_tests(status);
CREATE INDEX idx_ai_tests_risk_level ON ai_tests(risk_level);

-- Execution queries (time-series)
CREATE INDEX idx_test_executions_test_id ON test_executions(test_id);
CREATE INDEX idx_test_executions_executed_by ON test_executions(executed_by);
CREATE INDEX idx_test_executions_executed_at ON test_executions(executed_at);
CREATE INDEX idx_test_executions_validation_status ON test_executions(validation_status);

-- Prompt queries
CREATE INDEX idx_prompts_category_id ON prompts(category_id);
CREATE INDEX idx_prompts_created_by ON prompts(created_by);
CREATE INDEX idx_prompts_status ON prompts(status);

-- Configuration queries
CREATE INDEX idx_ai_configurations_created_by ON ai_configurations(created_by);
CREATE INDEX idx_ai_configurations_provider ON ai_configurations(provider);
CREATE INDEX idx_ai_configurations_status ON ai_configurations(status);

-- JSON field indexes for tag searches
CREATE INDEX idx_prompts_tags ON prompts USING GIN(tags);
CREATE INDEX idx_ai_tests_tags ON ai_tests USING GIN(tags);
CREATE INDEX idx_ai_configurations_tags ON ai_configurations USING GIN(tags);
```

## Implementation Plan

### Phase 1: Setup and Dependencies (1-2 days)

#### 1. Add Dependencies
```python
# requirements/base.txt
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
alembic>=1.12.0
```

#### 2. Database Configuration
```python
# app/core/config.py - Add new settings
DATABASE_URL: str = "postgresql://user:pass@db:5432/aigrc"  # Using existing db host
DATABASE_POOL_SIZE: int = 10
DATABASE_MAX_OVERFLOW: int = 20
DATABASE_ECHO: bool = False  # Set to True for SQL debugging
```

#### 3. Docker Setup
No changes needed to local Docker setup since PostgreSQL is already running independently on the `db` host.

#### 4. Database Connection Setup
```python
# app/core/database.py (new file)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Phase 2: SQLAlchemy Models (2-3 days)

#### 1. Create SQLAlchemy Models
```python
# app/models/__init__.py (new file)
from app.models.user import User, Group
from app.models.prompt import Prompt, PromptCategory
from app.models.test import AITest, TestExecution
from app.models.configuration import AIConfiguration

__all__ = [
    "User", "Group", "Prompt", "PromptCategory", 
    "AITest", "TestExecution", "AIConfiguration"
]
```

#### 2. Alembic Setup
```bash
# Initialize Alembic
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

### Phase 3: SQL Store Implementation (2-3 days)

#### 1. Create SQL Store Class
```python
# app/modules/sql_store.py (new file)
from sqlalchemy.orm import Session
from sqlalchemy import Table, select, insert, update, delete
from app.modules.store_interface import StoreProtocol
from app.core.logger import TLogger
import json
from typing import Dict, List
import uuid

class SQLStore(StoreProtocol):
    def __init__(self, session: Session, table: Table, logger: TLogger, key_column: str = "id"):
        self.session = session
        self.table = table
        self.logger = logger
        self.key_column = key_column
    
    def put(self, key: str, value: dict) -> None:
        """Insert or update record"""
        try:
            # Convert dict to match table schema
            record_data = self._prepare_record(key, value)
            
            # Check if record exists
            existing = self.session.execute(
                select(self.table).where(getattr(self.table.c, self.key_column) == key)
            ).first()
            
            if existing:
                # Update existing record
                self.session.execute(
                    update(self.table).where(
                        getattr(self.table.c, self.key_column) == key
                    ).values(**record_data)
                )
            else:
                # Insert new record
                self.session.execute(insert(self.table).values(**record_data))
            
            self.session.commit()
            self.logger.info(f"Successfully stored record with key: {key}")
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error storing record {key}: {str(e)}")
            raise
    
    def get(self, key: str) -> Dict[str, str] | None:
        """Get record by key"""
        try:
            result = self.session.execute(
                select(self.table).where(getattr(self.table.c, self.key_column) == key)
            ).first()
            
            if result:
                return self._row_to_dict(result)
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving record {key}: {str(e)}")
            raise
    
    def get_by_email(self, email: str) -> Dict[str, str] | None:
        """Get record by email (for user store)"""
        try:
            if not hasattr(self.table.c, 'email'):
                self.logger.warning("Email column not found in table")
                return None
                
            result = self.session.execute(
                select(self.table).where(self.table.c.email == email)
            ).first()
            
            if result:
                return self._row_to_dict(result)
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving record by email {email}: {str(e)}")
            raise
    
    def keys(self) -> List[str] | None:
        """Get all keys"""
        try:
            results = self.session.execute(
                select(getattr(self.table.c, self.key_column))
            ).fetchall()
            
            return [str(row[0]) for row in results]
            
        except Exception as e:
            self.logger.error(f"Error retrieving keys: {str(e)}")
            raise
    
    def pop(self, key: str) -> dict | None:
        """Get and delete record"""
        try:
            # Get the record first
            record = self.get(key)
            
            if record:
                # Delete the record
                self.session.execute(
                    delete(self.table).where(getattr(self.table.c, self.key_column) == key)
                )
                self.session.commit()
                
            return record
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error popping record {key}: {str(e)}")
            raise
    
    def _prepare_record(self, key: str, value: dict) -> dict:
        """Convert Redis-style dict to SQL record"""
        record = value.copy()
        record[self.key_column] = key
        
        # Handle JSON fields - convert lists/dicts to JSON strings
        for column_name, column in self.table.columns.items():
            if column_name in record:
                if hasattr(column.type, 'python_type') and column.type.python_type == dict:
                    # JSONB column - keep as dict
                    continue
                elif isinstance(record[column_name], (list, dict)):
                    # Convert to JSON string for TEXT columns
                    record[column_name] = json.dumps(record[column_name])
        
        return record
    
    def _row_to_dict(self, row) -> dict:
        """Convert SQL row to Redis-style dict"""
        result = {}
        for column_name in self.table.columns.keys():
            value = getattr(row, column_name)
            
            if value is not None:
                # Convert UUIDs to strings for compatibility
                if isinstance(value, uuid.UUID):
                    result[column_name] = str(value)
                # Handle JSON fields
                elif isinstance(value, (dict, list)):
                    result[column_name] = value
                # Try to parse JSON strings back to objects
                elif isinstance(value, str) and column_name in ['tags', 'settings', 'variables']:
                    try:
                        result[column_name] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[column_name] = value
                else:
                    result[column_name] = str(value)
        
        return result
```

#### 2. Update Store Implementations
No changes needed to existing store classes (`UserStore`, `AITestStore`, etc.) - they will work unchanged with the new `SQLStore`.

### Phase 4: Dependency Injection Updates (1 day)

#### 1. Update Dependencies
```python
# app/api/deps.py - Replace Redis with SQL
from app.core.database import get_db
from app.modules.sql_store import SQLStore
from app.models import User, Group, AITest, TestExecution, Prompt, PromptCategory, AIConfiguration

def get_user_store(
    logger: TLogger = Depends(get_logger),
    db: Session = Depends(get_db)
) -> UserStore:
    sql_store = SQLStore(db, User.__table__, logger)
    return UserStore(sql_store)

def get_ai_test_store(
    logger: TLogger = Depends(get_logger),
    db: Session = Depends(get_db)
) -> AITestStore:
    sql_store = SQLStore(db, AITest.__table__, logger)
    return AITestStore(sql_store)

# Similar updates for other stores...
```

### Phase 5: Data Migration (1-2 days)

#### 1. Export Redis Data
```python
# scripts/export_redis_data.py (new file)
import redis
import json
import uuid
from datetime import datetime

def export_redis_to_json():
    """Export all Redis data to JSON files for migration"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    # Export users
    user_keys = r.keys("user:*")
    users = []
    for key in user_keys:
        user_data = r.hgetall(key)
        users.append(user_data)
    
    with open('users_export.json', 'w') as f:
        json.dump(users, f, indent=2, default=str)
    
    # Export other entities similarly...
    print(f"Exported {len(users)} users")

if __name__ == "__main__":
    export_redis_to_json()
```

#### 2. Import to PostgreSQL
```python
# scripts/import_to_postgres.py (new file)
import json
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models import User, Group, AITest, TestExecution, Prompt, PromptCategory, AIConfiguration

def import_users():
    """Import users from JSON export"""
    db = SessionLocal()
    
    with open('users_export.json', 'r') as f:
        users_data = json.load(f)
    
    for user_data in users_data:
        # Convert Redis format to SQLAlchemy model
        user = User(
            id=user_data['id'],
            email=user_data['email'],
            full_name=user_data.get('full_name'),
            password=user_data['password'],
            disabled=user_data.get('disabled', False),
            is_verified=user_data.get('is_verified', False),
            # ... other fields
        )
        db.add(user)
    
    db.commit()
    db.close()
    print(f"Imported {len(users_data)} users")

if __name__ == "__main__":
    import_users()
    # Import other entities...
```

### Phase 6: Testing and Validation (1-2 days)

#### 1. Update Test Configuration
```python
# tests/conftest.py - Update for PostgreSQL testing
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.main import app

# Test database URL
TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/aigrc_test"

@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_db(test_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(test_db):
    def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

#### 2. Run Existing Tests
All existing tests should work unchanged since the store interface remains the same.

### Phase 7: Environment Configuration (1 day)

#### 1. Update Environment Variables
```bash
# .env updates
# Remove Redis settings
# REDIS_ADDRESS=localhost
# REDIS_PORT=6379

# Add PostgreSQL settings
DATABASE_URL=postgresql://aigrc:aigrc_password@db:5432/aigrc
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=false
```

#### 2. Docker Environment
No changes needed to local Docker setup since PostgreSQL is already running on the independent `db` host.

## Migration Benefits

### Immediate Benefits
- **Data Integrity**: ACID transactions prevent data corruption
- **Query Power**: Complex SQL queries for analytics and reporting
- **Backup/Restore**: Standard PostgreSQL tools (pg_dump, pg_restore)
- **Monitoring**: Standard database monitoring tools
- **Scaling**: Read replicas, connection pooling, query optimization

### Long-term Benefits
- **Analytics**: Direct SQL access for business intelligence tools
- **Compliance**: Better audit trails and data governance
- **Performance**: Proper indexing strategies for specific query patterns
- **Integration**: Easy integration with other systems expecting SQL databases

## Performance Considerations

### For Low Load (<50 concurrent users)
- **Synchronous SQLAlchemy**: 1-5ms per operation
- **Connection Pool**: 10 connections sufficient
- **No Async Complexity**: Simpler debugging and development

### Optimization Opportunities
- **Prepared Statements**: SQLAlchemy handles automatically
- **Query Optimization**: Use EXPLAIN ANALYZE for slow queries
- **Index Tuning**: Monitor query performance and add indexes as needed
- **Connection Pooling**: Tune pool size based on actual load

## Rollback Plan

### If Migration Issues Occur
1. **Keep Redis Running**: Don't shut down Redis until migration is proven successful
2. **Dual Write Period**: Write to both Redis and PostgreSQL during testing
3. **Quick Rollback**: Simple dependency injection change to switch back to Redis
4. **Data Validation**: Compare Redis vs PostgreSQL data before cutover

## Post-Migration Tasks

### Cleanup
1. Remove Redis dependencies from requirements.txt
2. Remove Redis configuration from docker-compose.yml
3. Remove Redis-specific code from stores
4. Update documentation and deployment scripts

### Optimization
1. Monitor query performance
2. Add missing indexes based on slow query log
3. Tune PostgreSQL configuration for workload
4. Set up automated backups

## Timeline Summary

- **Week 1**: Database setup, SQLAlchemy models, basic SQL store implementation
- **Week 2**: Complete SQL store, update dependency injection, initial testing
- **Week 3**: Data migration, validation, production deployment
- **Week 4**: Monitoring, optimization, cleanup

**Total Effort**: 3-4 weeks for complete migration with thorough testing.

## Success Criteria

- [ ] All existing API endpoints work unchanged
- [ ] All existing tests pass
- [ ] Data migration completes successfully with validation
- [ ] Performance is acceptable for current user load
- [ ] No data loss during migration
- [ ] Rollback plan tested and verified