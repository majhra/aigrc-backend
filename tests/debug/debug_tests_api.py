#!/usr/bin/env python3

import sys
import os
sys.path.append('/workspace')

def debug_tests_endpoint():
    """Debug why tests aren't showing in the API endpoint"""
    try:
        from app.modules.tests_store import AITestStore
        from app.modules.sql_store import SQLStore
        from app.models.test import AITest
        from app.core.database import SessionLocal
        from app.modules.tlogger import TLogger
        import logging
        
        print("=== Debug Tests API Issue ===")
        
        logger = TLogger('debug', logging.INFO)
        db = SessionLocal()
        
        # Test direct database query
        print("\n1. Direct database query:")
        from sqlalchemy import select
        stmt = select(AITest)
        results = db.execute(stmt).fetchall()
        print(f"Found {len(results)} test records in database")
        
        if results:
            for i, record in enumerate(results[:3]):  # Show first 3
                print(f"\nRecord {i+1}:")
                print(f"  ID: {record.id}")
                print(f"  Name: {record.name}")
                print(f"  Status: {record.status}")
                print(f"  Group ID: {record.group_id}")
                print(f"  Created by: {record.created_by}")
                print(f"  Last run at: {record.last_run_at}")
        
        # Test SQL store directly
        print("\n2. Testing SQL Store:")
        sql_store = SQLStore(db, AITest.__table__, logger)
        
        # Test keys() method
        keys = sql_store.keys()
        print(f"SQL store keys() returned: {len(keys) if keys else 0} keys")
        if keys:
            print(f"First few keys: {keys[:3]}")
        
        # Test get() method with first key
        if keys:
            print(f"\n3. Testing get() with key: {keys[0]}")
            data = sql_store.get(keys[0])
            if data:
                print(f"Raw data returned: {list(data.keys())}")
                print(f"Sample fields:")
                for key, value in list(data.items())[:5]:
                    print(f"  {key}: {value} ({type(value)})")
            else:
                print("get() returned None")
        
        # Test AITestStore
        print("\n4. Testing AITestStore:")
        test_store = AITestStore(sql_store)
        
        # Test list with no filters
        print("Testing list() with no filters:")
        tests, total = test_store.list(page=1, limit=10)
        print(f"list() returned: {len(tests)} tests, total: {total}")
        
        if tests:
            print(f"First test: ID={tests[0].id}, Name={tests[0].name}")
        
        # Test list with group filter (this might be the issue)
        print("\nTesting list() with different group filters:")
        for group_filter in [None, "default", str(results[0].group_id) if results and results[0].group_id else None]:
            tests, total = test_store.list(page=1, limit=10, group_id=group_filter)
            print(f"  group_id={group_filter}: {len(tests)} tests returned")
        
        db.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_tests_endpoint()