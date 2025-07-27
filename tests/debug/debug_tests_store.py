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
    
    # Test 1: Check what keys() returns
    keys = sql_store.keys()
    print(f"SQL Store keys(): {keys}")
    
    if keys:
        # Test 2: Get the first test
        first_key = keys[0]
        test_data = sql_store.get(first_key)
        print(f"Test data: {test_data}")
        print(f"Test group_id: '{test_data.get('group')}' (type: {type(test_data.get('group'))})")
        
        # Test 3: Test the filtering logic manually
        user_group = '29f46b82-293d-4074-bc99-2e6d1e8acbcc'
        test_group = test_data.get('group')
        
        print(f"User group: '{user_group}'")
        print(f"Test group: '{test_group}'")
        print(f"Groups equal: {user_group == test_group}")
        print(f"str(user_group) == str(test_group): {str(user_group) == str(test_group)}")
        
        # Test 4: Test the exact filtering condition from tests_store.py line 94
        group_id = user_group  # This is what gets passed as group_id parameter
        t_group_id = test_group  # This is what t.group_id would be
        condition_result = (t_group_id is None and group_id == "default") or str(t_group_id) == str(group_id)
        print(f"Filtering condition result: {condition_result}")
        
    else:
        print("No test keys found!")
        
finally:
    db.close()