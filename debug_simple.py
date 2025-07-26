#!/usr/bin/env python3

import sys
import os
sys.path.append('/workspace')

from app.models.configuration import AIConfiguration
from app.core.database import SessionLocal
from sqlalchemy import select

def debug_db():
    """Simple database debug"""
    db = SessionLocal()
    
    try:
        print("=== Direct Database Query ===")
        
        # Check if there are any configurations in the database
        stmt = select(AIConfiguration)
        results = db.execute(stmt).fetchall()
        print(f"Found {len(results)} configuration records in database")
        
        if results:
            for i, record in enumerate(results[:3]):  # Show first 3
                print(f"\nRecord {i+1}:")
                print(f"  ID: {record.id}")
                print(f"  Name: {record.name}")
                print(f"  Provider: {record.provider}")
                print(f"  Status: {record.status}")
                print(f"  Created by: {record.created_by}")
        else:
            print("No configuration records found in database")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_db()