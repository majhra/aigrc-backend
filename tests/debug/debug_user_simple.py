import sys
sys.path.insert(0, '/workspace')

from app.modules.sql_store import SQLStore
from app.models.user import User as UserModel
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
    sql_store = SQLStore(db, UserModel.__table__, logger)
    
    # Get raw user data by looking up the ID we know
    user_id = '4bcf6001-e0c3-42c2-b673-76af4193d962'
    user_data = sql_store.get(user_id)
    
    print(f"Raw user data: {user_data}")
    if user_data:
        print(f"User 'group' field: '{user_data.get('group')}' (type: {type(user_data.get('group'))})")
        print(f"User 'role' field: '{user_data.get('role')}' (type: {type(user_data.get('role'))})")
        print(f"User group is None: {user_data.get('group') is None}")
        print(f"User group == 'default': {user_data.get('group') == 'default'}")
        
        # Compare with test group_id
        test_group_id = '29f46b82-293d-4074-bc99-2e6d1e8acbcc'
        print(f"Test group_id: '{test_group_id}'")
        print(f"Groups match: {str(user_data.get('group')) == str(test_group_id)}")
    else:
        print("User not found!")
        
finally:
    db.close()