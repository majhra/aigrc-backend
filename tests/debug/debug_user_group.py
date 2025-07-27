import sys
sys.path.insert(0, '/workspace')

from app.modules.user_store import UserStore
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
    # Create user store
    sql_store = SQLStore(db, UserModel.__table__, logger)
    user_store = UserStore(sql_store)
    
    # Get user
    user = user_store.get_by_email('goricoaico@gmail.com')
    print(f"User found: {user}")
    if user:
        print(f"User group: '{user.group}' (type: {type(user.group)})")
        print(f"User role: '{user.role}' (type: {type(user.role)})")
        print(f"User group is None: {user.group is None}")
        print(f"User group == 'default': {user.group == 'default'}")
    else:
        print("User not found!")
        
finally:
    db.close()