#!/usr/bin/env python3

import sys
import os
sys.path.append('/workspace')

from app.modules.configurations_store import AIConfigurationStore
from app.modules.sql_store import SQLStore
from app.models.configuration import AIConfiguration
from app.core.database import SessionLocal
from app.modules.tlogger import TLogger
import logging

def debug_configurations():
    """Debug the configuration listing issue"""
    logger = TLogger('debug', logging.INFO)
    db = SessionLocal()
    
    try:
        # Create SQL store
        sql_store = SQLStore(db, AIConfiguration.__table__, logger)
        config_store = AIConfigurationStore(sql_store)
        
        print("=== Debug Configuration Store ===")
        
        # Test keys() method
        print("\n1. Testing keys() method:")
        keys = sql_store.keys()
        print(f"Keys found: {keys}")
        
        # Test list() method
        print("\n2. Testing list() method:")
        configs, total = config_store.list(page=1, limit=10)
        print(f"Configs returned: {len(configs)}")
        print(f"Total count: {total}")
        
        if configs:
            print("First config:")
            print(f"  ID: {configs[0].id}")
            print(f"  Name: {configs[0].name}")
        
        # Test get() method with a specific key if available
        if keys:
            print(f"\n3. Testing get() method with key: {keys[0]}")
            config = config_store.get(keys[0])
            if config:
                print(f"Config retrieved: {config.name}")
            else:
                print("Config is None")
                
                # Debug the raw data
                raw_data = sql_store.get(keys[0])
                print(f"Raw data: {raw_data}")
        
        # Check if there are any configurations in the database directly
        print("\n4. Direct database query:")
        from sqlalchemy import select
        stmt = select(AIConfiguration)
        results = db.execute(stmt).fetchall()
        print(f"Direct DB query found {len(results)} records")
        
        if results:
            first_record = results[0]
            print(f"First record ID: {first_record.id}")
            print(f"First record name: {first_record.name}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_configurations()