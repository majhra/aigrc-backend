import sys
sys.path.insert(0, '/workspace')

from app.modules.sql_store import SQLStore
from app.models.test import AITest as AITestModel
from app.core.database import get_db
from app.modules.tlogger import TLogger
import logging

# Setup
logging.basicConfig(level=logging.INFO)
logger = TLogger('debug')

# Get database session
db_gen = get_db()
db = next(db_gen)

try:
    # Create SQL store directly
    sql_store = SQLStore(db, AITestModel.__table__, logger)
    
    # Test 1: Test get_filtered with group_id
    user_group = '29f46b82-293d-4074-bc99-2e6d1e8acbcc'
    filters = {'group_id': user_group}
    
    print(f"Testing sql_store.get_filtered with filters: {filters}")
    
    try:
        filtered_results = sql_store.get_filtered(filters)
        print(f"get_filtered returned {len(filtered_results)} results:")
        for result in filtered_results:
            print(f"  Test: {result.get('name')}, group: {result.get('group')}")
    except Exception as e:
        print(f"get_filtered failed with error: {e}")
        
    # Test 2: Test with no filters (should return all)
    print(f"\nTesting get_filtered with no filters:")
    try:
        all_results = sql_store.get_filtered({})
        print(f"get_filtered({{}}) returned {len(all_results)} results:")
        for result in all_results:
            print(f"  Test: {result.get('name')}, group: {result.get('group')}")
    except Exception as e:
        print(f"get_filtered({{}}) failed with error: {e}")
        
    # Test 3: Check if get_filtered exists
    print(f"\nHas get_filtered method: {hasattr(sql_store, 'get_filtered')}")
    
finally:
    db.close()