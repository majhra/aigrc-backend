# Foreign Key Constraint Tests

This directory contains unit tests specifically designed to catch database constraint violations that could cause 500 errors in production.

## Background

During production testing, we discovered that deleting AI tests that had associated test executions would cause foreign key constraint violations:

```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.ForeignKeyViolation) 
update or delete on table "ai_tests" violates foreign key constraint 
"test_executions_test_id_fkey" on table "test_executions"
DETAIL: Key (id)=(test-id) is still referenced from table "test_executions".
```

This resulted in 500 Internal Server Error responses and backend crashes.

## The Fix

We implemented cascade deletion logic in `app/modules/tests_store.py` to:
1. List all executions for a test before deletion
2. Delete each execution individually 
3. Then delete the test itself

This prevents foreign key constraint violations.

## Test Coverage

### 1. Core Constraint Fix Validation
**File**: `tests/test_foreign_key_constraint_fix.py`
- ✅ Validates that test deletion properly calls execution cleanup
- ✅ Tests graceful handling when no executions exist
- ✅ Tests error handling when execution cleanup fails
- ✅ Documents the before/after behavior

### 2. Comprehensive Foreign Key Tests  
**File**: `tests/modules/test_foreign_key_constraints.py`
- ✅ Tests cascade deletion with multiple executions
- ✅ Tests foreign key violation simulation
- ✅ Tests edge cases and error handling

### 3. Cascade Deletion Scenarios
**File**: `tests/modules/test_cascade_deletion_scenarios.py`
- ✅ Tests user deletion with created resources
- ✅ Tests bulk execution deletion
- ✅ Tests orphaned execution detection
- ✅ Tests concurrent deletion race conditions

### 4. Database Constraint Validation
**File**: `tests/modules/test_database_constraints.py`
- ✅ Tests foreign key constraint violations
- ✅ Tests NOT NULL constraint violations
- ✅ Tests UNIQUE constraint violations
- ✅ Tests transaction rollback handling
- ✅ Tests connection pool issues
- ✅ Tests deadlock detection

## Running the Tests

### Run All Constraint Tests
```bash
python -m pytest tests/test_foreign_key_constraint_fix.py -v
```

### Run Individual Test Suites
```bash
# Core fix validation
python -m pytest tests/test_foreign_key_constraint_fix.py -v

# Comprehensive constraint tests (requires complex schema setup)
python -m pytest tests/modules/test_foreign_key_constraints.py -v
python -m pytest tests/modules/test_cascade_deletion_scenarios.py -v  
python -m pytest tests/modules/test_database_constraints.py -v
```

### Run with Coverage
```bash
python -m pytest tests/test_foreign_key_constraint_fix.py --cov=app.modules.tests_store --cov-report=html
```

## Integration with CI/CD

Add these tests to your CI/CD pipeline to catch constraint violations before production:

```yaml
# .github/workflows/test.yml
- name: Run Constraint Tests
  run: |
    python -m pytest tests/test_foreign_key_constraint_fix.py -v
    python -m pytest tests/modules/test_*constraint*.py -v --tb=short
```

## Key Test Cases

### ✅ Happy Path: Test with Executions
- Creates test with multiple executions
- Deletes test
- Verifies executions are deleted first
- Verifies test deletion succeeds

### ✅ Edge Case: Test without Executions  
- Creates test with no executions
- Deletes test
- Verifies normal deletion flow

### ✅ Error Case: Execution Cleanup Fails
- Simulates execution cleanup failure
- Verifies test deletion is still attempted
- Verifies graceful error handling

### ✅ Database Constraint Simulation
- Simulates actual PostgreSQL foreign key violation
- Verifies our fix prevents the constraint violation
- Tests transaction rollback scenarios

## Expected Outcomes

With these tests in place:

1. **500 errors prevented**: Foreign key violations caught before production
2. **Data integrity maintained**: Proper cascade deletion ensures referential integrity
3. **Regression prevention**: Future changes that break constraint handling will be caught
4. **Documentation**: Clear understanding of constraint relationships and handling

## Maintenance

When adding new entity relationships:

1. **Add constraint tests** for new foreign key relationships
2. **Update cascade deletion logic** if needed
3. **Test both happy path and constraint violation scenarios**
4. **Document the relationship** in test comments

## Related Files

- `app/modules/tests_store.py` - Contains the constraint fix
- `app/models/test.py` - Database model with foreign key definitions
- `app/modules/sql_store.py` - SQL store implementation
- `tests/integration/production/` - Production integration tests that caught the original issue