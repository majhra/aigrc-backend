from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4
import re

from app.modules.store_interface import LocalStore, StoreProtocol
from app.schemas import (
    PromptCategory, PromptCategoryCreate, PromptCategoryUpdate,
    Prompt, PromptCreate, PromptUpdate,
    PromptSet, PromptSetCreate, PromptSetUpdate,
    PromptVariable, PromptValidationResponse, PromptPreviewResponse,
    User
)

class PromptCategoryStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()

    def get(self, category_id: str) -> Optional[PromptCategory]:
        data = self._store.get(category_id)
        if not data:
            return None
        
        try:
            return PromptCategory(**data)
        except Exception as e:
            return None

    def list(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        category_type: Optional[str] = None,
        search: Optional[str] = None,
        group_id: Optional[str] = None,  # INTERNAL USE ONLY - NOT FROM CLIENT
    ) -> tuple[List[PromptCategory], int]:
        sql_filtered = False  # Track if SQL filtering was used
        
        # For SQL stores, use more efficient filtered queries when possible
        try:
            if hasattr(self._store, 'get_filtered'):
                # Build filters for SQL query
                filters = {}
                if status:
                    filters['status'] = status
                if category_type:
                    filters['category_type'] = category_type
                if group_id:
                    filters['group_id'] = group_id
                
                # Get filtered results from SQL
                if filters:
                    sql_filtered = True
                    category_data = self._store.get_filtered(filters)
                    categories = []
                    for data in category_data:
                        try:
                            category = PromptCategory(**data)
                            categories.append(category)
                        except Exception:
                            continue
                else:
                    # No filters were applied, fall back to keys() approach for SQL stores
                    keys = self._store.keys()
                    if keys:
                        categories = [self.get(key) for key in keys]
                        categories = [c for c in categories if c is not None]
                    else:
                        categories = []
            else:
                raise Exception("Not an SQL store")
        except Exception:
            # Fallback to Redis-style approach
            keys = self._store.keys()
            if not keys:
                return [], 0

            try:
                categories = [self.get(key) for key in keys]
                categories = [c for c in categories if c is not None]
            except Exception as e:
                return [], 0

        # Apply filters only if SQL filtering wasn't used
        if not sql_filtered:
            if status:
                categories = [c for c in categories if c.status == status]
            if category_type:
                categories = [c for c in categories if c.category_type == category_type]
            if group_id:
                categories = [c for c in categories if str(c.group_id) == str(group_id)]
        if search:
            search_lower = search.lower()
            categories = [
                c for c in categories
                if search_lower in c.name.lower()
                or search_lower in c.description.lower()
                or any(search_lower in tag.lower() for tag in c.tags)
            ]

        # Sort by name
        categories.sort(key=lambda x: x.name.lower())

        # Calculate pagination
        total = len(categories)
        start = (page - 1) * limit
        end = start + limit
        paginated_categories = categories[start:end]

        return paginated_categories, total

    def create(self, category: PromptCategoryCreate, user: User) -> PromptCategory:
        now = datetime.now(timezone.utc)
        category_id = str(uuid4())
        
        new_category = PromptCategory(
            id=category_id,
            created_by=user.id,
            group_id=user.group,
            created_at=now,
            updated_at=now,
            **category.model_dump()
        )
        
        self._store.put(category_id, new_category.model_dump())
        return new_category

    def update(self, category_id: str, category: PromptCategoryUpdate) -> Optional[PromptCategory]:
        existing_data = self._store.get(category_id)
        if not existing_data:
            return None
            
        existing_category = PromptCategory(**existing_data)
        now = datetime.now(timezone.utc)
        
        # Update only provided fields
        update_data = category.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing_category, field, value)
        
        existing_category.updated_at = now
        
        self._store.put(category_id, existing_category.model_dump())
        return existing_category

    def delete(self, category_id: str) -> bool:
        existing_data = self._store.get(category_id)
        if not existing_data:
            return False
        
        # Check if category has prompts (in real implementation, we'd check prompts store)
        # For now, we'll allow deletion
        
        self._store.pop(category_id)
        return True

class PromptStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()
    
    def get(self, prompt_id: str) -> Optional[Prompt]:
        data = self._store.get(prompt_id)
        if not data:
            return None
        
        try:
            return Prompt(**data)
        except Exception as e:
            return None

    def list(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        category_id: Optional[str] = None,
        category_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        group_id: Optional[str] = None,  # INTERNAL USE ONLY - NOT FROM CLIENT
        category_store=None,
    ) -> tuple[List[Prompt], int]:
        sql_filtered = False  # Track if SQL filtering was used
        
        # For SQL stores, use more efficient filtered queries when possible
        try:
            if hasattr(self._store, 'get_filtered'):
                # Build filters for SQL query
                filters = {}
                if status:
                    filters['status'] = status
                if category_id:
                    filters['category_id'] = category_id
                if risk_level:
                    filters['risk_level'] = risk_level
                if group_id:
                    filters['group_id'] = group_id
                
                # Get filtered results from SQL
                if filters:
                    sql_filtered = True
                    prompt_data = self._store.get_filtered(filters)
                    prompts = []
                    for data in prompt_data:
                        try:
                            prompt = Prompt(**data)
                            prompts.append(prompt)
                        except Exception:
                            continue
                else:
                    # No filters were applied, fall back to keys() approach for SQL stores
                    keys = self._store.keys()
                    if keys:
                        prompts = [self.get(key) for key in keys]
                        prompts = [p for p in prompts if p is not None]
                    else:
                        prompts = []
            else:
                raise Exception("Not an SQL store")
        except Exception:
            # Fallback to Redis-style approach
            keys = self._store.keys()
            if not keys:
                return [], 0

            try:
                prompts = [self.get(key) for key in keys]
                prompts = [p for p in prompts if p is not None]
            except Exception as e:
                return [], 0

        # Apply filters only if SQL filtering wasn't used
        if not sql_filtered:
            if status:
                prompts = [p for p in prompts if p.status == status]
            if category_id:
                prompts = [p for p in prompts if str(p.category_id) == str(category_id)]
            if risk_level:
                prompts = [p for p in prompts if p.risk_level == risk_level]
            if group_id:
                prompts = [p for p in prompts if str(p.group_id) == str(group_id)]
        if category_type and category_store:
            # Get all categories with the specified type
            matching_categories, _ = category_store.list()
            matching_category_ids = [
                str(cat.id) for cat in matching_categories 
                if cat.category_type == category_type
            ]
            prompts = [p for p in prompts if str(p.category_id) in matching_category_ids]
        if risk_level:
            prompts = [p for p in prompts if p.risk_level == risk_level]
        if search:
            search_lower = search.lower()
            prompts = [
                p for p in prompts
                if search_lower in p.name.lower()
                or search_lower in p.description.lower()
                or search_lower in p.content.lower()
                or any(search_lower in tag.lower() for tag in p.tags)
            ]
        if tags:
            prompts = [
                p for p in prompts
                if any(tag in p.tags for tag in tags)
            ]

        # Sort by updated_at (most recent first)
        prompts.sort(key=lambda x: x.updated_at, reverse=True)

        # Calculate pagination
        total = len(prompts)
        start = (page - 1) * limit
        end = start + limit
        paginated_prompts = prompts[start:end]

        return paginated_prompts, total

    def create(self, prompt: PromptCreate, user: User) -> Prompt:
        now = datetime.now(timezone.utc)
        prompt_id = str(uuid4())
        
        new_prompt = Prompt(
            id=prompt_id,
            created_by=user.id,
            group_id=user.group,
            created_at=now,
            updated_at=now,
            **prompt.model_dump()
        )
        
        self._store.put(prompt_id, new_prompt.model_dump())
        return new_prompt

    def update(self, prompt_id: str, prompt: PromptUpdate) -> Optional[Prompt]:
        existing_data = self._store.get(prompt_id)
        if not existing_data:
            return None
            
        existing_prompt = Prompt(**existing_data)
        now = datetime.now(timezone.utc)
        
        # Update only provided fields
        update_data = prompt.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing_prompt, field, value)
        
        # Increment version if content changed
        if 'content' in update_data:
            existing_prompt.version += 1
        
        existing_prompt.updated_at = now
        
        self._store.put(prompt_id, existing_prompt.model_dump())
        return existing_prompt

    def delete(self, prompt_id: str) -> bool:
        existing_data = self._store.get(prompt_id)
        if not existing_data:
            return False
        
        self._store.pop(prompt_id)
        return True

    def update_usage(self, prompt_id: str) -> Optional[Prompt]:
        """Update prompt usage statistics"""
        existing_data = self._store.get(prompt_id)
        if not existing_data:
            return None
            
        existing_prompt = Prompt(**existing_data)
        existing_prompt.usage_count += 1
        existing_prompt.last_used_at = datetime.now(timezone.utc)
        
        self._store.put(prompt_id, existing_prompt.model_dump())
        return existing_prompt

class PromptSetStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()

    def get(self, set_id: str) -> Optional[PromptSet]:
        data = self._store.get(set_id)
        if not data:
            return None
        
        try:
            return PromptSet(**data)
        except Exception as e:
            return None

    def list(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        group_id: Optional[str] = None,  # INTERNAL USE ONLY - NOT FROM CLIENT
    ) -> tuple[List[PromptSet], int]:
        sql_filtered = False  # Track if SQL filtering was used
        
        # For SQL stores, use more efficient filtered queries when possible
        try:
            if hasattr(self._store, 'get_filtered'):
                # Build filters for SQL query
                filters = {}
                if status:
                    filters['status'] = status
                if category_id:
                    filters['category_id'] = category_id
                if group_id:
                    filters['group_id'] = group_id
                
                # Get filtered results from SQL
                if filters:
                    sql_filtered = True
                    set_data = self._store.get_filtered(filters)
                    sets = []
                    for data in set_data:
                        try:
                            prompt_set = PromptSet(**data)
                            sets.append(prompt_set)
                        except Exception:
                            continue
                else:
                    # No filters were applied, fall back to keys() approach for SQL stores
                    keys = self._store.keys()
                    if keys:
                        sets = [self.get(key) for key in keys]
                        sets = [s for s in sets if s is not None]
                    else:
                        sets = []
            else:
                raise Exception("Not an SQL store")
        except Exception:
            # Fallback to Redis-style approach
            keys = self._store.keys()
            if not keys:
                return [], 0

            try:
                sets = [self.get(key) for key in keys]
                sets = [s for s in sets if s is not None]
            except Exception as e:
                return [], 0

        # Apply filters only if SQL filtering wasn't used
        if not sql_filtered:
            if status:
                sets = [s for s in sets if s.status == status]
            if category_id:
                sets = [s for s in sets if str(s.category_id) == str(category_id)]
            if group_id:
                sets = [s for s in sets if str(s.group_id) == str(group_id)]
        if search:
            search_lower = search.lower()
            sets = [
                s for s in sets
                if search_lower in s.name.lower()
                or search_lower in s.description.lower()
                or any(search_lower in tag.lower() for tag in s.tags)
            ]

        # Sort by name
        sets.sort(key=lambda x: x.name.lower())

        # Calculate pagination
        total = len(sets)
        start = (page - 1) * limit
        end = start + limit
        paginated_sets = sets[start:end]

        return paginated_sets, total

    def create(self, prompt_set: PromptSetCreate, user: User) -> PromptSet:
        now = datetime.now(timezone.utc)
        set_id = str(uuid4())
        
        new_set = PromptSet(
            id=set_id,
            created_by=user.id,
            group_id=user.group,
            created_at=now,
            updated_at=now,
            **prompt_set.model_dump()
        )
        
        self._store.put(set_id, new_set.model_dump())
        return new_set

    def update(self, set_id: str, prompt_set: PromptSetUpdate) -> Optional[PromptSet]:
        existing_data = self._store.get(set_id)
        if not existing_data:
            return None
            
        existing_set = PromptSet(**existing_data)
        now = datetime.now(timezone.utc)
        
        # Update only provided fields
        update_data = prompt_set.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing_set, field, value)
        
        existing_set.updated_at = now
        
        self._store.put(set_id, existing_set.model_dump())
        return existing_set

    def delete(self, set_id: str) -> bool:
        existing_data = self._store.get(set_id)
        if not existing_data:
            return False
        
        self._store.pop(set_id)
        return True

class PromptTemplateEngine:
    """Utility class for prompt template processing"""
    
    @staticmethod
    def validate_prompt(content: str, variables: List[PromptVariable]) -> PromptValidationResponse:
        """Validate a prompt template"""
        errors = []
        warnings = []
        
        # Find all variable placeholders in content
        placeholder_pattern = r'\{\{(\w+)\}\}'
        found_placeholders = re.findall(placeholder_pattern, content)
        
        # Check if all placeholders have corresponding variables
        variable_names = {var.name for var in variables}
        for placeholder in found_placeholders:
            if placeholder not in variable_names:
                errors.append(f"Variable '{placeholder}' used in template but not defined")
        
        # Check if all required variables have placeholders
        for variable in variables:
            if variable.required and variable.name not in found_placeholders:
                warnings.append(f"Required variable '{variable.name}' is not used in template")
        
        return PromptValidationResponse(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            variable_placeholders=found_placeholders
        )
    
    @staticmethod
    def render_prompt(content: str, variable_values: Dict[str, any]) -> PromptPreviewResponse:
        """Render a prompt template with variable values"""
        errors = []
        rendered_content = content
        
        try:
            # Simple variable substitution
            for variable_name, value in variable_values.items():
                placeholder = f"{{{{{variable_name}}}}}"
                if placeholder in rendered_content:
                    rendered_content = rendered_content.replace(placeholder, str(value))
            
            # Check for remaining unsubstituted variables
            placeholder_pattern = r'\{\{(\w+)\}\}'
            remaining_placeholders = re.findall(placeholder_pattern, rendered_content)
            if remaining_placeholders:
                errors.append(f"Unsubstituted variables: {', '.join(remaining_placeholders)}")
            
        except Exception as e:
            errors.append(f"Error rendering template: {str(e)}")
            rendered_content = content
        
        return PromptPreviewResponse(
            rendered_content=rendered_content,
            is_valid=len(errors) == 0,
            errors=errors
        )