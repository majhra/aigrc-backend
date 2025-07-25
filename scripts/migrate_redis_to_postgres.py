#!/usr/bin/env python3
"""
Migration script to transfer data from Redis to PostgreSQL.
Run this from the project root directory.
"""

import sys
import os
import redis
import json
import msgpack
from datetime import datetime
from typing import Dict, Any

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models import User as UserModel, Group as GroupModel, AITest as AITestModel, TestExecution as TestExecutionModel, Prompt as PromptModel, PromptCategory as PromptCategoryModel, AIConfiguration as AIConfigModel
from app.core.config import settings
import uuid


def connect_redis():
    """Connect to Redis without decode_responses to handle binary data"""
    return redis.Redis(
        host=settings.REDIS_ADDRESS, 
        port=settings.REDIS_PORT, 
        decode_responses=False  # Keep binary data as-is
    )


def parse_redis_value(value) -> Any:
    """Parse Redis values handling both string and binary data"""
    if value is None:
        return None
    
    # Handle binary data
    if isinstance(value, bytes):
        # Check if it's msgpack encoded
        if value == b'\xc0':  # msgpack null
            return None
        try:
            # Try to decode as msgpack first
            decoded = msgpack.unpackb(value, raw=False)
            return decoded
        except (msgpack.exceptions.ExtraData, msgpack.exceptions.UnpackException, ValueError):
            # If msgpack fails, try to decode as UTF-8 string
            try:
                value = value.decode('utf-8')
            except UnicodeDecodeError:
                # If UTF-8 fails, return None for undecodable binary data
                return None
    
    # Handle string values
    if isinstance(value, str):
        if value == "True":
            return True
        elif value == "False":
            return False
        elif value == "\\xc0" or value == "":
            return None
        elif value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
    
    return value


def parse_datetime(dt_value) -> datetime:
    """Parse datetime from Redis (could be string or other format)"""
    if dt_value is None:
        return None
    
    # First parse with parse_redis_value to handle encoding
    dt_str = parse_redis_value(dt_value)
    
    if not dt_str or dt_str == "\\xc0":
        return None
        
    if not isinstance(dt_str, str):
        return None
        
    try:
        # Handle both with and without timezone
        if dt_str.endswith('+00:00'):
            return datetime.fromisoformat(dt_str)
        else:
            return datetime.fromisoformat(dt_str + '+00:00')
    except (ValueError, TypeError):
        return None


def migrate_groups(r: redis.Redis, db: Session):
    """Migrate groups from Redis to PostgreSQL"""
    print("Migrating groups...")
    
    group_keys = r.keys(b"group:*")
    migrated_count = 0
    
    for key in group_keys:
        try:
            group_data = r.hgetall(key)
            if not group_data:
                continue
                
            # Decode key and extract group ID
            key_str = key.decode('utf-8')
            group_id = key_str.split(":")[-1]
            
            # Check if group already exists
            existing = db.query(GroupModel).filter(GroupModel.id == group_id).first()
            if existing:
                print(f"Group {group_id} already exists, skipping...")
                continue
            
            # Create group record
            group = GroupModel(
                id=group_id,
                name=parse_redis_value(group_data.get(b'name', b'')),
                description=parse_redis_value(group_data.get(b'description')),
                status=parse_redis_value(group_data.get(b'status', b'ACTIVE')),
                settings=parse_redis_value(group_data.get(b'settings')),
                created_at=parse_datetime(group_data.get(b'created_at')) or datetime.utcnow(),
                updated_at=parse_datetime(group_data.get(b'updated_at')) or datetime.utcnow()
            )
            
            db.add(group)
            migrated_count += 1
            print(f"Migrated group: {group.name} ({group_id})")
            
        except Exception as e:
            print(f"Error migrating group {key}: {str(e)}")
            continue
    
    print(f"Migrated {migrated_count} groups")
    return migrated_count


def migrate_users(r: redis.Redis, db: Session):
    """Migrate users from Redis to PostgreSQL"""
    print("Migrating users...")
    
    user_keys = r.keys(b"user:*")
    migrated_count = 0
    
    for key in user_keys:
        try:
            user_data = r.hgetall(key)
            if not user_data:
                continue
            
            # Decode key
            key_str = key.decode('utf-8')
            
            # Extract user ID from the data (not the key, since key has group:user format)
            user_id_raw = user_data.get(b'id')
            user_id = parse_redis_value(user_id_raw)
            if not user_id:
                print(f"No user ID found in {key_str}, skipping...")
                continue
            
            # Check if user already exists
            existing = db.query(UserModel).filter(UserModel.id == user_id).first()
            if existing:
                print(f"User {user_id} already exists, skipping...")
                continue
            
            # Get group ID from the key (format: user:group_id:user_id)
            key_parts = key_str.split(":")
            group_id = key_parts[1] if len(key_parts) >= 3 else parse_redis_value(user_data.get(b'group'))
            
            # Create user record
            user = UserModel(
                id=user_id,
                email=parse_redis_value(user_data.get(b'email', b'')),
                full_name=parse_redis_value(user_data.get(b'full_name')),
                password=parse_redis_value(user_data.get(b'password', b'')),
                disabled=parse_redis_value(user_data.get(b'disabled', b'False')),
                is_verified=parse_redis_value(user_data.get(b'is_verified', b'False')),
                role=parse_redis_value(user_data.get(b'role')),
                group_id=group_id,
                created_at=parse_datetime(user_data.get(b'created_at')) or datetime.utcnow(),
                last_login=parse_datetime(user_data.get(b'last_login')),
                verification_code=parse_redis_value(user_data.get(b'verification_code')),
                verification_code_expires_at=parse_datetime(user_data.get(b'verification_code_expires_at')),
                password_reset_code=parse_redis_value(user_data.get(b'password_reset_code')),
                password_reset_code_expires_at=parse_datetime(user_data.get(b'password_reset_code_expires_at'))
            )
            
            db.add(user)
            migrated_count += 1
            print(f"Migrated user: {user.email} ({user_id})")
            
        except Exception as e:
            print(f"Error migrating user {key}: {str(e)}")
            continue
    
    print(f"Migrated {migrated_count} users")
    return migrated_count


def migrate_tests(r: redis.Redis, db: Session):
    """Migrate AI tests from Redis to PostgreSQL"""
    print("Migrating AI tests...")
    
    test_keys = r.keys("tests:*")
    migrated_count = 0
    
    for key in test_keys:
        try:
            test_data = r.hgetall(key)
            if not test_data:
                continue
            
            # Extract test ID from key
            test_id = key.split(":")[-1]
            
            # Check if test already exists
            existing = db.query(AITestModel).filter(AITestModel.id == test_id).first()
            if existing:
                print(f"Test {test_id} already exists, skipping...")
                continue
            
            # Create test record
            test = AITestModel(
                id=test_id,
                name=parse_redis_value(test_data.get('name', '')),
                description=parse_redis_value(test_data.get('description')),
                prompt_template=parse_redis_value(test_data.get('prompt_template')),
                interface_type=parse_redis_value(test_data.get('interface_type', 'DIRECT_LLM')),
                connection_config=parse_redis_value(test_data.get('connection_config')),
                validation_config=parse_redis_value(test_data.get('validation_config')),
                tags=parse_redis_value(test_data.get('tags')),
                risk_level=parse_redis_value(test_data.get('risk_level', 'LOW')),
                status=parse_redis_value(test_data.get('status', 'DRAFT')),
                created_by=parse_redis_value(test_data.get('created_by')),
                group_id=parse_redis_value(test_data.get('group_id')),
                created_at=parse_datetime(test_data.get('created_at')) or datetime.utcnow(),
                updated_at=parse_datetime(test_data.get('updated_at')) or datetime.utcnow(),
                last_run_at=parse_datetime(test_data.get('last_run_at')),
                latest_execution_id=parse_redis_value(test_data.get('latest_execution_id'))
            )
            
            db.add(test)
            migrated_count += 1
            print(f"Migrated test: {test.name} ({test_id})")
            
        except Exception as e:
            print(f"Error migrating test {key}: {str(e)}")
            continue
    
    print(f"Migrated {migrated_count} tests")
    return migrated_count


def migrate_executions(r: redis.Redis, db: Session):
    """Migrate test executions from Redis to PostgreSQL"""
    print("Migrating test executions...")
    
    execution_keys = r.keys("execution:*")
    migrated_count = 0
    
    for key in execution_keys:
        try:
            execution_data = r.hgetall(key)
            if not execution_data:
                continue
            
            # Extract execution ID from key
            execution_id = key.split(":")[-1]
            
            # Check if execution already exists
            existing = db.query(TestExecutionModel).filter(TestExecutionModel.id == execution_id).first()
            if existing:
                print(f"Execution {execution_id} already exists, skipping...")
                continue
            
            # Create execution record
            execution = TestExecutionModel(
                id=execution_id,
                test_id=parse_redis_value(execution_data.get('test_id')),
                executed_at=parse_datetime(execution_data.get('executed_at')) or datetime.utcnow(),
                executed_by=parse_redis_value(execution_data.get('executed_by')),
                execution_environment=parse_redis_value(execution_data.get('execution_environment')),
                input_variables=parse_redis_value(execution_data.get('input_variables')),
                prompt=parse_redis_value(execution_data.get('prompt')),
                response=parse_redis_value(execution_data.get('response')),
                benchmarks=parse_redis_value(execution_data.get('benchmarks')),
                validation_status=parse_redis_value(execution_data.get('validation_status', 'PENDING')),
                validations=parse_redis_value(execution_data.get('validations')),
                error=parse_redis_value(execution_data.get('error'))
            )
            
            db.add(execution)
            migrated_count += 1
            print(f"Migrated execution: {execution_id}")
            
        except Exception as e:
            print(f"Error migrating execution {key}: {str(e)}")
            continue
    
    print(f"Migrated {migrated_count} executions")
    return migrated_count


def migrate_other_data(r: redis.Redis, db: Session):
    """Migrate other data types (prompts, configurations, etc.)"""
    print("Migrating other data types...")
    
    # Add migrations for prompt_category, prompt, ai_config, etc.
    # This is a placeholder for now
    print("Other data migration not implemented yet...")
    return 0


def main():
    """Main migration function"""
    print("Starting Redis to PostgreSQL migration...")
    
    # Connect to Redis
    try:
        r = connect_redis()
        r.ping()
        print("✓ Connected to Redis")
    except Exception as e:
        print(f"✗ Failed to connect to Redis: {e}")
        return
    
    # Connect to PostgreSQL
    try:
        db = SessionLocal()
        # Test connection
        db.execute(text("SELECT 1"))
        print("✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"✗ Failed to connect to PostgreSQL: {e}")
        return
    
    try:
        # Migrate data in order (respecting foreign key constraints)
        total_migrated = 0
        
        # 1. Migrate groups first (referenced by users)
        total_migrated += migrate_groups(r, db)
        db.commit()
        
        # 2. Migrate users (referenced by tests and executions)
        total_migrated += migrate_users(r, db)
        db.commit()
        
        # 3. Migrate tests
        total_migrated += migrate_tests(r, db)
        db.commit()
        
        # 4. Migrate executions
        total_migrated += migrate_executions(r, db)
        db.commit()
        
        # 5. Migrate other data
        total_migrated += migrate_other_data(r, db)
        db.commit()
        
        print(f"\n✓ Migration completed successfully!")
        print(f"Total records migrated: {total_migrated}")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()