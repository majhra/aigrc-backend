from sqlalchemy.orm import Session
from sqlalchemy import Table, select, insert, update, delete, and_
from app.modules.store_interface import StoreProtocol
from app.modules.tlogger import TLogger
import json
from typing import Dict, List
import uuid
from datetime import datetime


class SQLStore(StoreProtocol):
    """
    SQL implementation of the StoreProtocol interface.
    Provides drop-in replacement for RedisStore with PostgreSQL backend.
    """
    
    def __init__(self, session: Session, table: Table, logger: TLogger, key_column: str = "id", email_column: str = None):
        self.session = session
        self.table = table
        self.logger = logger
        self.key_column = key_column
        self.email_column = email_column or "email"  # Default email column name
    
    def put(self, key: str, value: dict) -> None:
        """Insert or update record"""
        try:
            # Convert dict to match table schema
            record_data = self._prepare_record(key, value)
            
            # Check if record exists
            stmt = select(self.table).where(getattr(self.table.c, self.key_column) == key)
            existing = self.session.execute(stmt).first()
            
            if existing:
                # Update existing record
                update_stmt = update(self.table).where(
                    getattr(self.table.c, self.key_column) == key
                ).values(**record_data)
                self.session.execute(update_stmt)
            else:
                # Insert new record
                insert_stmt = insert(self.table).values(**record_data)
                self.session.execute(insert_stmt)
            
            self.session.commit()
            self.logger.info(f"Successfully stored record with key: {key}")
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error storing record {key}: {str(e)}")
            raise
    
    def get(self, key: str) -> Dict[str, str] | None:
        """Get record by key"""
        try:
            stmt = select(self.table).where(getattr(self.table.c, self.key_column) == key)
            result = self.session.execute(stmt).first()
            
            if result:
                return self._row_to_dict(result)
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving record {key}: {str(e)}")
            raise
    
    def get_by_email(self, email: str) -> Dict[str, str] | None:
        """Get record by email (for user store)"""
        try:
            if not hasattr(self.table.c, self.email_column):
                self.logger.warning(f"Email column '{self.email_column}' not found in table")
                return None
                
            stmt = select(self.table).where(getattr(self.table.c, self.email_column) == email)
            result = self.session.execute(stmt).first()
            
            if result:
                return self._row_to_dict(result)
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving record by email {email}: {str(e)}")
            raise
    
    def keys(self) -> List[str] | None:
        """Get all keys"""
        try:
            stmt = select(getattr(self.table.c, self.key_column))
            results = self.session.execute(stmt).fetchall()
            
            return [str(row[0]) for row in results]
            
        except Exception as e:
            self.logger.error(f"Error retrieving keys: {str(e)}")
            raise
    
    def pop(self, key: str) -> dict | None:
        """Get and delete record"""
        try:
            # Get the record first
            record = self.get(key)
            
            if record:
                # Delete the record
                delete_stmt = delete(self.table).where(getattr(self.table.c, self.key_column) == key)
                self.session.execute(delete_stmt)
                self.session.commit()
                
            return record
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error popping record {key}: {str(e)}")
            raise
    
    def get_filtered(self, filters: dict) -> List[Dict[str, str]]:
        """
        Get records with filters (extension beyond StoreProtocol for SQL-specific queries)
        Usage: store.get_filtered({'group_id': 'some-uuid', 'status': 'ACTIVE'})
        """
        try:
            stmt = select(self.table)
            
            # Apply filters
            conditions = []
            for column_name, value in filters.items():
                if hasattr(self.table.c, column_name):
                    conditions.append(getattr(self.table.c, column_name) == value)
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            results = self.session.execute(stmt).fetchall()
            return [self._row_to_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"Error retrieving filtered records {filters}: {str(e)}")
            raise
    
    def _prepare_record(self, key: str, value: dict) -> dict:
        """Convert Redis-style dict to SQL record"""
        record = value.copy()
        
        # Set the primary key
        record[self.key_column] = key
        
        # Handle field name mapping: group -> group_id for SQL table compatibility
        if 'group' in record and 'group_id' not in record:
            record['group_id'] = record.pop('group')
        
        # Handle special field conversions
        for column_name, column in self.table.columns.items():
            if column_name in record:
                value = record[column_name]
                
                # Handle UUID conversion
                if column_name == self.key_column or column_name.endswith('_id'):
                    if isinstance(value, str) and value:
                        try:
                            # Validate and convert UUID
                            record[column_name] = str(uuid.UUID(value))
                        except ValueError:
                            # If not a valid UUID, generate one for primary key
                            if column_name == self.key_column:
                                record[column_name] = str(uuid.uuid4())
                            else:
                                record[column_name] = value
                
                # Handle datetime fields
                elif column_name.endswith('_at'):
                    if isinstance(value, str):
                        try:
                            # Try to parse ISO format datetime
                            record[column_name] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except ValueError:
                            # Keep as string if parsing fails
                            pass
                
                # Handle JSON fields
                elif hasattr(column.type, '__class__') and 'JSON' in str(column.type.__class__):
                    # Keep as dict/list for JSON columns
                    if isinstance(value, str):
                        try:
                            record[column_name] = json.loads(value)
                        except json.JSONDecodeError:
                            record[column_name] = value
                
                # Handle boolean fields
                elif column.type.python_type == bool:
                    if isinstance(value, str):
                        record[column_name] = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        record[column_name] = bool(value)
                
                # Handle integer fields
                elif column.type.python_type == int:
                    if isinstance(value, str) and value.isdigit():
                        record[column_name] = int(value)
                    elif isinstance(value, (int, float)):
                        record[column_name] = int(value)
            
            # Set default values for missing required fields
            elif not column.nullable and column.default is None and column.server_default is None:
                if column.type.python_type == str:
                    record[column_name] = ""
                elif column.type.python_type == bool:
                    record[column_name] = False
                elif column.type.python_type == int:
                    record[column_name] = 0
        
        return record
    
    def _row_to_dict(self, row) -> dict:
        """Convert SQL row to Redis-style dict"""
        result = {}
        
        for column_name in self.table.columns.keys():
            value = getattr(row, column_name, None)
            
            # Handle field name mapping: group_id -> group for User schema compatibility
            field_name = column_name
            if column_name == 'group_id':
                field_name = 'group'
            
            if value is not None:
                # Convert UUIDs to strings for compatibility
                if isinstance(value, uuid.UUID):
                    result[field_name] = str(value)
                # Convert datetime to ISO string
                elif isinstance(value, datetime):
                    result[field_name] = value.isoformat()
                # Keep JSON fields as-is (dict/list)
                elif isinstance(value, (dict, list)):
                    result[field_name] = value
                # Convert everything else to string for Redis compatibility
                else:
                    result[field_name] = str(value)
            else:
                # For datetime fields, don't include empty values that would break Pydantic validation
                if column_name.endswith('_at') or column_name.endswith('_expires_at'):
                    # Skip datetime fields that are None - let Pydantic handle the absence
                    continue
                else:
                    # Include None values as empty strings for non-datetime fields
                    result[field_name] = ""
        
        return result