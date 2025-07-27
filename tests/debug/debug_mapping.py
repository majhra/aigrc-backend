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
    
    # Get the test directly to see raw database values
    test_id = '299a92b5-7ba7-442a-95ce-2846143277c4'
    print(f"Testing sql_store.get('{test_id}')")
    
    # Get raw SQL data
    from sqlalchemy import select
    stmt = select(AITestModel.__table__).where(AITestModel.__table__.c.id == test_id)
    result = sql_store.session.execute(stmt).first()
    
    if result:
        print(f"Raw SQL result:")
        for column_name in AITestModel.__table__.columns.keys():
            raw_value = getattr(result, column_name, 'MISSING')
            print(f"  {column_name}: {raw_value} (type: {type(raw_value)})")
        
        print(f"\nSQL Store _row_to_dict result:")
        converted = sql_store._row_to_dict(result)
        for key, value in converted.items():
            print(f"  {key}: {value} (type: {type(value)})")
            
    else:
        print("No raw SQL result found!")
        
finally:
    db.close()