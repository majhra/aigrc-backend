from sqlalchemy.orm import Session
from sqlalchemy import Table, select, insert, update, delete, and_, or_, func
from app.modules.store_interface import StoreProtocol
from app.modules.tlogger import TLogger
import json
from typing import Dict, List, Any, Optional, Union, Tuple
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

    def query(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        keys_only: bool = True,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        order_direction: str = "asc"
    ) -> Union[List[str], List[Dict[str, Any]], Tuple[List[str], int], Tuple[List[Dict[str, Any]], int]]:
        """
        Unified query method for efficient data retrieval.
        
        Args:
            filters: Dict of column_name: value filters
            keys_only: If True, return only keys; if False, return full records
            page: Page number for pagination (1-based)
            limit: Records per page
            order_by: Column name to sort by
            order_direction: "asc" or "desc"
        
        Returns:
            - List[str]: Keys only, no pagination
            - List[Dict]: Full records, no pagination  
            - Tuple[List[str], int]: Keys + total count
            - Tuple[List[Dict], int]: Records + total count
        """
        try:
            # Build base query
            if keys_only:
                stmt = select(getattr(self.table.c, self.key_column))
            else:
                stmt = select(self.table)
            
            # Apply filters
            if filters:
                conditions = []
                for column_name, value in filters.items():
                    # Handle special OR conditions
                    if column_name == '_or':
                        or_conditions = []
                        for or_filter in value:
                            for or_column_name, or_value in or_filter.items():
                                if '__' in or_column_name:
                                    field_name, operator = or_column_name.rsplit('__', 1)
                                    if hasattr(self.table.c, field_name):
                                        column = getattr(self.table.c, field_name)
                                        if operator == 'ilike':
                                            # Use LOWER() for case-insensitive search instead of ILIKE
                                            or_conditions.append(func.lower(column).like(func.lower(or_value)))
                                        elif operator == 'like':
                                            or_conditions.append(column.like(or_value))
                                        elif operator == 'in':
                                            or_conditions.append(column.in_(or_value))
                                elif hasattr(self.table.c, or_column_name):
                                    if isinstance(or_value, list):
                                        or_conditions.append(getattr(self.table.c, or_column_name).in_(or_value))
                                    else:
                                        or_conditions.append(getattr(self.table.c, or_column_name) == or_value)
                        if or_conditions:
                            conditions.append(or_(*or_conditions))
                    # Handle special search operators (column__operator format)
                    elif '__' in column_name:
                        field_name, operator = column_name.rsplit('__', 1)
                        if hasattr(self.table.c, field_name):
                            column = getattr(self.table.c, field_name)
                            if operator == 'ilike':
                                # Use LOWER() for case-insensitive search instead of ILIKE
                                conditions.append(func.lower(column).like(func.lower(value)))
                            elif operator == 'like':
                                conditions.append(column.like(value))
                            elif operator == 'in':
                                conditions.append(column.in_(value))
                            # Add more operators as needed
                    elif hasattr(self.table.c, column_name):
                        if isinstance(value, list):
                            conditions.append(getattr(self.table.c, column_name).in_(value))
                        else:
                            conditions.append(getattr(self.table.c, column_name) == value)
                if conditions:
                    stmt = stmt.where(and_(*conditions))
            
            # Apply ordering
            if order_by and hasattr(self.table.c, order_by):
                order_col = getattr(self.table.c, order_by)
                if order_direction.lower() == "desc":
                    stmt = stmt.order_by(order_col.desc())
                else:
                    stmt = stmt.order_by(order_col)
            
            # Handle pagination
            if page is not None and limit is not None:
                # Get total count first
                count_stmt = select(func.count()).select_from(self.table)
                # Apply same filters to count query
                if filters:
                    conditions = []
                    for column_name, value in filters.items():
                        # Handle special OR conditions
                        if column_name == '_or':
                            or_conditions = []
                            for or_filter in value:
                                for or_column_name, or_value in or_filter.items():
                                    if '__' in or_column_name:
                                        field_name, operator = or_column_name.rsplit('__', 1)
                                        if hasattr(self.table.c, field_name):
                                            column = getattr(self.table.c, field_name)
                                            if operator == 'ilike':
                                                # Use LOWER() for case-insensitive search instead of ILIKE
                                                or_conditions.append(func.lower(column).like(func.lower(or_value)))
                                            elif operator == 'like':
                                                or_conditions.append(column.like(or_value))
                                            elif operator == 'in':
                                                or_conditions.append(column.in_(or_value))
                                    elif hasattr(self.table.c, or_column_name):
                                        if isinstance(or_value, list):
                                            or_conditions.append(getattr(self.table.c, or_column_name).in_(or_value))
                                        else:
                                            or_conditions.append(getattr(self.table.c, or_column_name) == or_value)
                            if or_conditions:
                                conditions.append(or_(*or_conditions))
                        # Handle special search operators (column__operator format)
                        elif '__' in column_name:
                            field_name, operator = column_name.rsplit('__', 1)
                            if hasattr(self.table.c, field_name):
                                column = getattr(self.table.c, field_name)
                                if operator == 'ilike':
                                    # Use LOWER() for case-insensitive search instead of ILIKE
                                    conditions.append(func.lower(column).like(func.lower(value)))
                                elif operator == 'like':
                                    conditions.append(column.like(value))
                                elif operator == 'in':
                                    conditions.append(column.in_(value))
                                # Add more operators as needed
                        elif hasattr(self.table.c, column_name):
                            if isinstance(value, list):
                                conditions.append(getattr(self.table.c, column_name).in_(value))
                            else:
                                conditions.append(getattr(self.table.c, column_name) == value)
                    if conditions:
                        count_stmt = count_stmt.where(and_(*conditions))
                
                total_count = self.session.execute(count_stmt).scalar()
                
                # Apply pagination
                offset = (page - 1) * limit
                stmt = stmt.offset(offset).limit(limit)
                
                # Execute query
                results = self.session.execute(stmt).fetchall()
                
                if keys_only:
                    return [str(row[0]) for row in results], total_count
                else:
                    return [self._row_to_dict(row) for row in results], total_count
            else:
                # No pagination
                results = self.session.execute(stmt).fetchall()
                
                if keys_only:
                    return [str(row[0]) for row in results]
                else:
                    return [self._row_to_dict(row) for row in results]
                    
        except Exception as e:
            self.logger.error(f"Error in query: {str(e)}")
            raise
    
    def _prepare_record(self, key: str, value: dict) -> dict:
        """Convert Redis-style dict to SQL record"""
        record = value.copy()
        
        # Set the primary key
        record[self.key_column] = key
        
        # Handle field name mapping for SQL table compatibility
        if 'group' in record and 'group_id' not in record:
            record['group_id'] = record.pop('group')
        if 'lastRun_at' in record and 'last_run_at' not in record:
            record['last_run_at'] = record.pop('lastRun_at')
        
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
            
            # Handle field name mapping for Pydantic schema compatibility
            field_name = column_name
            if column_name == 'group_id':
                # Only map group_id -> group for users table, not for tests table
                if self.table.name == 'users':
                    field_name = 'group'
                # For other tables (like tests), keep group_id as group_id
            elif column_name == 'last_run_at':
                field_name = 'lastRun_at'
            
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
                elif column_name.endswith('_id'):
                    # For UUID fields that are None, skip them so Pydantic gets None instead of empty string
                    continue
                else:
                    # Include None values as empty strings for non-datetime fields
                    result[field_name] = ""
        
        return result