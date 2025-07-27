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
    
    # Test get_filtered with group_id
    user_group = '29f46b82-293d-4074-bc99-2e6d1e8acbcc'
    filters = {'group_id': user_group}
    
    print(f"Testing sql_store.get_filtered with filters: {filters}")
    
    filtered_results = sql_store.get_filtered(filters)
    print(f"get_filtered returned {len(filtered_results)} results:")
    for result in filtered_results:
        print(f"  Result keys: {list(result.keys())}")
        print(f"  Test name: {result.get('name')}")
        print(f"  group field: {result.get('group')} (type: {type(result.get('group'))})")
        print(f"  group_id field: {result.get('group_id')} (type: {type(result.get('group_id'))})")
        print(f"  Full result: {result}")
        
finally:
    db.close()