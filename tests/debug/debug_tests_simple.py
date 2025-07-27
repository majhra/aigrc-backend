#!/usr/bin/env python3

import sys
import os
sys.path.append('/workspace')

from app.models.test import AITest
from app.core.database import SessionLocal
from sqlalchemy import select

def debug_db():
    """Simple database debug for tests"""
    db = SessionLocal()
    
    try:
        print("=== Direct Database Query for Tests ===")
        
        # Check if there are any tests in the database
        stmt = select(AITest)
        results = db.execute(stmt).fetchall()
        print(f"Found {len(results)} test records in database")
        
        if results:
            for i, record in enumerate(results[:3]):  # Show first 3
                print(f"\nRecord {i+1}:")
                print(f"  ID: {record.id}")
                print(f"  Name: {record.name}")
                print(f"  Status: {record.status}")
                print(f"  Risk Level: {record.risk_level}")
                print(f"  Group ID: {record.group_id}")
                print(f"  Created by: {record.created_by}")
                print(f"  Last run at: {record.last_run_at}")
                print(f"  Created at: {record.created_at}")
        else:
            print("No test records found in database")
            
        # Also check what columns exist
        print(f"\nTable columns: {list(AITest.__table__.columns.keys())}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_db()