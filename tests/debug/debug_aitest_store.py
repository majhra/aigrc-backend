import sys
sys.path.insert(0, '/workspace')

from app.modules.sql_store import SQLStore
from app.models.test import AITest as AITestModel
from app.core.database import get_db
from app.modules.tlogger import TLogger
from app.modules.tests_store import AITestStore
import logging

# Setup
logging.basicConfig(level=logging.INFO)
logger = TLogger('debug')

# Get database session
db_gen = get_db()
db = next(db_gen)

try:
    # Create AITestStore with SQL store
    sql_store = SQLStore(db, AITestModel.__table__, logger)
    test_store = AITestStore(sql_store)
    
    # Test the exact call that the endpoint makes
    user_group = '29f46b82-293d-4074-bc99-2e6d1e8acbcc'
    
    print(f"Testing AITestStore.list() with group_id='{user_group}'")
    
    # This is the exact call from the endpoint
    tests, total = test_store.list(
        page=1,
        limit=10,
        status=None,
        risk_level=None,
        search=None,
        group_id=user_group
    )
    
    print(f"Results: {len(tests)} tests, total={total}")
    for test in tests:
        print(f"  Test: {test.name}, group_id: {test.group_id}")
        
    # Also test without group filter (admin view)
    print(f"\nTesting without group filter (admin view):")
    tests_admin, total_admin = test_store.list(
        page=1,
        limit=10,
        status=None,
        risk_level=None,
        search=None,
        group_id=None
    )
    
    print(f"Admin results: {len(tests_admin)} tests, total={total_admin}")
    for test in tests_admin:
        print(f"  Test: {test.name}, group_id: {test.group_id}")
        
finally:
    db.close()