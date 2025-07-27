# Debug Scripts for Redis-to-SQL Migration

This directory contains debug scripts created during the investigation of Redis-to-SQL migration issues. These scripts helped identify and fix field mapping problems that were preventing the API from returning data correctly.

## Scripts Overview

### User-Related Debug Scripts

- **`debug_user_group.py`**: Tests user store and group field mapping (has circular import issues)
- **`debug_user_simple.py`**: Direct SQL store testing for user data, bypasses circular imports

### Test-Related Debug Scripts

- **`debug_tests_store.py`**: Tests SQL store behavior for tests table
- **`debug_aitest_store.py`**: Tests complete AITestStore.list() method (has circular import issues)
- **`debug_sql_filtered.py`**: Tests SQL store's get_filtered method directly
- **`debug_filtered_updated.py`**: Verifies fixes to SQL store field mapping

### Schema and Mapping Debug Scripts

- **`debug_mapping.py`**: Examines raw SQL data vs converted data through _row_to_dict
- **`debug_schema.py`**: Tests AITestSchema validation directly (has circular import issues)

## Usage

All scripts should be run from the workspace root with the virtual environment activated:

```bash
source /tmp/aigrc_venv/bin/activate && python tests/debug/[script_name].py
```

## Known Issues

Several scripts have circular import issues due to the application's import structure. The scripts that work reliably are:
- `debug_user_simple.py`
- `debug_tests_store.py`
- `debug_sql_filtered.py`
- `debug_filtered_updated.py`
- `debug_mapping.py`

## Key Findings

These scripts helped identify:
1. Field mapping inconsistencies between User and AITest schemas
2. UUID field handling issues for null values
3. The exact point where schema validation was failing
4. Verification that the fixes resolved the issues

See `/workspace/redis_to_sql.md` for complete details on the investigation and fixes.