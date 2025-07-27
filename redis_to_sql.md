# Redis to SQL Migration Issues and Fixes

## Overview

During the migration from Redis to PostgreSQL, several field mapping and schema compatibility issues were discovered that prevented the API from returning data correctly. This document captures the investigation process, issues found, and fixes applied.

## Problem Description

The `GET /api/v1.0/tests` endpoint was returning empty results (`{"items":[],"total":0,"page":1,"limit":10}`) despite having test data in the PostgreSQL database. The issue was traced to field mapping inconsistencies between different Pydantic schemas during the Redis-to-SQL migration.

## Root Cause Analysis

### Issue 1: Inconsistent Field Mapping Between Schemas

**Problem**: The SQL store was applying the same field mapping (`group_id` → `group`) to all tables, but different schemas expected different field names:

- **User schema** (`app/schemas/user.py`): expects `group` field
- **AITest schema** (`app/schemas/tests.py`): expects `group_id` field

**Database Structure**:
- Both `users` and `ai_tests` tables store the group reference as `group_id` (UUID)

**Mapping Conflict**:
- SQL store mapped `group_id` → `group` for all tables
- This worked for users but broke AITest schema validation
- AITestSchema validation failed silently, causing tests to be filtered out

### Issue 2: UUID Field Handling for Null Values

**Problem**: The SQL store converted `None` UUID values to empty strings `""`, but Pydantic schemas expected `None` for optional UUID fields.

**Specific Field**: `latest_execution_id` field was being set to `""` instead of `None`, causing schema validation to fail when trying to convert an empty string to a UUID.

## Investigation Process and Debug Scripts

### Debug Scripts Created

All debug scripts are located in `tests/debug/` directory:

#### 1. `debug_user_group.py`
**Purpose**: Test user store and check user group field mapping
**What it does**: 
- Creates a UserStore with SQL backend
- Retrieves user by email
- Shows the user's group field value and type
- **Issue**: Circular import prevented execution

#### 2. `debug_user_simple.py`
**Purpose**: Direct SQL store testing for user data
**What it does**:
- Creates SQL store directly for users table
- Gets raw user data by ID
- Shows field mappings from `group_id` → `group`
- **Key Finding**: User group mapping was working correctly

#### 3. `debug_tests_store.py`
**Purpose**: Test SQL store behavior for tests table
**What it does**:
- Tests `sql_store.keys()` method
- Gets test data and examines field mappings
- Tests filtering logic manually
- **Key Finding**: Confirmed data was correct and filtering logic should work

#### 4. `debug_aitest_store.py`
**Purpose**: Test the complete AITestStore.list() method
**What it does**:
- Creates AITestStore with SQL backend
- Calls the exact method used by the API endpoint
- **Issue**: Circular import prevented execution

#### 5. `debug_sql_filtered.py`
**Purpose**: Test SQL store's get_filtered method directly
**What it does**:
- Tests `sql_store.get_filtered()` with group filters
- Shows what data is returned by the filtering method
- **Key Finding**: Method worked but returned wrong field names initially

#### 6. `debug_mapping.py`
**Purpose**: Examine raw SQL data vs converted data
**What it does**:
- Gets raw SQL query results
- Shows the `_row_to_dict` conversion process
- Compares raw database values with converted values
- **Key Finding**: Revealed the field mapping was working after fix

#### 7. `debug_filtered_updated.py`
**Purpose**: Verify fixes to the SQL store field mapping
**What it does**:
- Tests get_filtered after applying fixes
- Shows all field names in results
- Confirms group_id field is present and correct
- **Key Finding**: Confirmed the field mapping fix worked

#### 8. `debug_schema.py`
**Purpose**: Test AITestSchema validation directly
**What it does**:
- Takes actual SQL store output data
- Attempts to validate it against AITestSchema
- **Issue**: Circular import prevented execution, but revealed UUID field issue

## Fixes Applied

### Fix 1: Conditional Field Mapping

**File**: `/workspace/app/modules/sql_store.py` (lines 224-228)

**Before**:
```python
if column_name == 'group_id':
    field_name = 'group'
```

**After**:
```python
if column_name == 'group_id':
    # Only map group_id -> group for users table, not for tests table
    if self.table.name == 'users':
        field_name = 'group'
    # For other tables (like tests), keep group_id as group_id
```

**Impact**: Ensures that:
- Users table: `group_id` → `group` (for User schema compatibility)
- Tests table: `group_id` stays as `group_id` (for AITestSchema compatibility)

### Fix 2: UUID Field Null Handling

**File**: `/workspace/app/modules/sql_store.py` (lines 250-252)

**Before**:
```python
else:
    # Include None values as empty strings for non-datetime fields
    result[field_name] = ""
```

**After**:
```python
elif column_name.endswith('_id'):
    # For UUID fields that are None, skip them so Pydantic gets None instead of empty string
    continue
else:
    # Include None values as empty strings for non-datetime fields
    result[field_name] = ""
```

**Impact**: Optional UUID fields like `latest_execution_id` are now properly handled as `None` instead of empty strings, preventing Pydantic validation errors.

## Testing Results

### Before Fixes
```json
{
    "items": [],
    "total": 0,
    "page": 1,
    "limit": 10
}
```

### After Fixes
```json
{
    "items": [
        {
            "name": "test1",
            "description": "Test1",
            "id": "299a92b5-7ba7-442a-95ce-2846143277c4",
            "group_id": "29f46b82-293d-4074-bc99-2e6d1e8acbcc",
            "latest_execution_id": null,
            ...
        }
    ],
    "total": 1,
    "page": 1,
    "limit": 10
}
```

## Database State During Investigation

### User Data
```sql
SELECT id, email, group_id::text FROM users WHERE email = 'goricoaico@gmail.com';
```
Result: User had group_id `29f46b82-293d-4074-bc99-2e6d1e8acbcc`

### Test Data
```sql
SELECT id, name, status, group_id FROM ai_tests LIMIT 5;
```
Result: Test had matching group_id `29f46b82-293d-4074-bc99-2e6d1e8acbcc`

### Groups Data
```sql
SELECT id, name FROM groups LIMIT 5;
```
Result: Group existed and was properly linked

## Remaining Work

### Potential Issues to Investigate

1. **Other Endpoint Consistency**: Check if other endpoints using similar patterns have the same field mapping issues
2. **Schema Validation**: Audit all Pydantic schemas to ensure they match the SQL store field mappings
3. **Migration Script Review**: Review the Redis-to-SQL migration scripts to ensure all data was properly migrated
4. **User Role Handling**: User role field was empty - investigate if this is expected or if there's a migration issue
5. **Circular Import Issues**: The circular imports between schemas and stores should be resolved to enable better testing

### Additional Testing Needed

1. Test all CRUD operations for tests to ensure they work consistently
2. Test user operations to ensure the group field mapping still works correctly
3. Test admin users vs regular users to ensure group filtering works as expected
4. Test other endpoints that use group-based filtering

### Monitoring

Watch for similar issues in other endpoints that may have been affected by the Redis-to-SQL migration, particularly those involving:
- Group-based access control
- UUID field handling
- Schema validation with SQL store data

## Lessons Learned

1. **Field Mapping Consistency**: When migrating between storage systems, ensure field mappings are consistent with the expected schemas
2. **Schema Validation**: Silent schema validation failures can mask underlying data issues
3. **Type Handling**: Pay special attention to how None/null values are handled for different data types (UUID, datetime, etc.)
4. **Testing Strategy**: Direct SQL store testing was more effective than trying to test through the full application stack due to circular imports
5. **Incremental Fixes**: Applying fixes incrementally and testing each change helped isolate the root causes