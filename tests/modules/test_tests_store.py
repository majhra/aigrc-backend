import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from app.modules.tests_store import MyTestStore
from app.modules.store_interface import LocalStore
from app.schemas import TestSchema, MyTestCreate, User, ConnectionConfig, ValidationConfig, ValidationCriterion


class TestMyTestStore(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_store = MagicMock(spec=LocalStore)
        self.test_store = MyTestStore(self.mock_store)
        
        # Create test user
        self.test_user = User(
            id=str(uuid4()),
            email="test@example.com",
            full_name="Test User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        
        # Create test data
        self.test_data = MyTestCreate(
            name="Test Test",
            description="A test test",
            prompt_template="Hello {name}",
            interface_type="DIRECT_LLM",
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com",
                auth_type="API_KEY"
            ),
            validation_config=ValidationConfig(
                validator_type="HUMAN",
                validation_criteria=[
                    ValidationCriterion(
                        id="criterion1",
                        name="Test Criterion",
                        description="A test criterion",
                        type="exact_match"
                    )
                ]
            ),
            tags=["test"],
            risk_level="LOW",
            status="ACTIVE"
        )
        
        # Create test timestamp
        self.test_timestamp = datetime.now(timezone.utc)

    def test_get_success(self):
        """Test successful test retrieval by ID."""
        # Mock the underlying store to return test data
        test_schema = TestSchema(
            id=str(uuid4()),
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        self.mock_store.get.return_value = test_schema.model_dump()
        
        result = self.test_store.get(str(test_schema.id))
        
        # Verify the store was called with the correct key
        self.mock_store.get.assert_called_once_with(str(test_schema.id))
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.name, test_schema.name)
        self.assertEqual(result.id, test_schema.id)
        self.assertEqual(result.group_id, test_schema.group_id)

    def test_get_not_found(self):
        """Test test retrieval when test doesn't exist."""
        self.mock_store.get.return_value = None
        
        result = self.test_store.get("non-existent-id")
        
        self.assertIsNone(result)

    def test_list_success(self):
        """Test successful test listing."""
        # Mock the store to return keys and test data
        test_id = str(uuid4())
        test_keys = [test_id]
        
        test_schema = TestSchema(
            id=test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = test_schema.model_dump()
        
        tests, total = self.test_store.list(page=1, limit=10)
        
        # Verify the result
        self.assertEqual(len(tests), 1)
        self.assertEqual(total, 1)
        self.assertEqual(tests[0].name, test_schema.name)

    def test_list_with_group_filter(self):
        """Test test listing with group filter."""
        # Mock the store to return keys and test data
        test_id = str(uuid4())
        test_keys = [test_id]
        
        test_schema = TestSchema(
            id=test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = test_schema.model_dump()
        
        tests, total = self.test_store.list(group_id=self.test_user.group, page=1, limit=10)
        
        # Should return tests for the specified group
        self.assertEqual(len(tests), 1)
        self.assertEqual(total, 1)
        self.assertEqual(tests[0].group_id, self.test_user.group)

    def test_list_with_status_filter(self):
        """Test test listing with status filter."""
        # Mock the store to return keys and test data
        test_id = str(uuid4())
        test_keys = [test_id]
        
        test_schema = TestSchema(
            id=test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = test_schema.model_dump()
        
        tests, total = self.test_store.list(status="ACTIVE", page=1, limit=10)
        
        # Should return tests with the specified status
        self.assertEqual(len(tests), 1)
        self.assertEqual(total, 1)

    def test_list_with_risk_level_filter(self):
        """Test test listing with risk level filter."""
        # Mock the store to return keys and test data
        test_id = str(uuid4())
        test_keys = [test_id]
        
        test_schema = TestSchema(
            id=test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = test_schema.model_dump()
        
        tests, total = self.test_store.list(risk_level="LOW", page=1, limit=10)
        
        # Should return tests with the specified risk level
        self.assertEqual(len(tests), 1)
        self.assertEqual(total, 1)

    def test_list_with_search(self):
        """Test test listing with search filter."""
        # Mock the store to return keys and test data
        test_id = str(uuid4())
        test_keys = [test_id]
        
        test_schema = TestSchema(
            id=test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = test_schema.model_dump()
        
        tests, total = self.test_store.list(search="test", page=1, limit=10)
        
        # Should return tests matching the search
        self.assertEqual(len(tests), 1)
        self.assertEqual(total, 1)

    def test_list_empty(self):
        """Test test listing when no tests exist."""
        self.mock_store.keys.return_value = []
        
        tests, total = self.test_store.list(page=1, limit=10)
        
        self.assertEqual(len(tests), 0)
        self.assertEqual(total, 0)

    def test_list_pagination(self):
        """Test test listing with pagination."""
        # Mock the store to return multiple keys
        test_keys = [f"test{i}" for i in range(5)]
        test_schema = TestSchema(
            id=str(uuid4()),
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = test_schema.model_dump()
        
        tests, total = self.test_store.list(page=1, limit=3)
        
        # Should return paginated results
        self.assertEqual(len(tests), 3)
        self.assertEqual(total, 5)

    def test_create_success(self):
        """Test successful test creation."""
        # Mock the store
        self.mock_store.put.return_value = None
        
        result = self.test_store.create(self.test_data, self.test_user)
        
        # Verify the store was called
        self.mock_store.put.assert_called_once()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.test_data.name)
        self.assertEqual(result.description, self.test_data.description)
        self.assertEqual(result.group_id, self.test_user.group)
        self.assertEqual(result.created_by, self.test_user.id)
        self.assertIsNotNone(result.id)

    def test_update_success(self):
        """Test successful test update."""
        # Mock the store to return existing test
        existing_test = TestSchema(
            id=str(uuid4()),
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        self.mock_store.get.return_value = existing_test.model_dump()
        self.mock_store.put.return_value = None
        
        update_data = self.test_data.model_dump()
        update_data["name"] = "Updated Test"
        result = self.test_store.update(str(existing_test.id), MyTestCreate(**update_data))
        
        # Verify the store was called correctly
        self.mock_store.get.assert_called_once_with(str(existing_test.id))
        self.mock_store.put.assert_called_once()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Updated Test")
        self.assertEqual(result.group_id, existing_test.group_id)  # Should preserve group_id
        # updated_at should be updated
        self.assertGreaterEqual(result.updated_at, existing_test.updated_at)

    def test_update_test_not_found(self):
        """Test test update when test doesn't exist."""
        self.mock_store.get.return_value = None
        
        update_data = self.test_data.model_dump()
        update_data["name"] = "Updated Test"
        result = self.test_store.update("non-existent-id", MyTestCreate(**update_data))
        
        self.assertIsNone(result)

    def test_delete_success(self):
        """Test successful test deletion."""
        # Mock the store to return existing test
        existing_test = TestSchema(
            id=str(uuid4()),
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        self.mock_store.get.return_value = existing_test.model_dump()
        self.mock_store.pop.return_value = existing_test.model_dump()
        
        result = self.test_store.delete(str(existing_test.id))
        
        # Verify the store was called correctly
        #self.mock_store.get.assert_called_once_with(str(existing_test.id))
        self.mock_store.pop.assert_called_once_with(str(existing_test.id))
        
        # Verify the result
        self.assertTrue(result)

    def test_delete_test_not_found(self):
        """Test test deletion when test doesn't exist."""
        self.mock_store.get.return_value = None
        self.mock_store.pop.return_value = None
        
        result = self.test_store.delete("non-existent-id")
        
        self.assertFalse(result)

    def test_belongs_to_group_true(self):
        """Test belongs_to_group when test belongs to group."""
        test_schema = TestSchema(
            id=str(uuid4()),
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        self.mock_store.get.return_value = test_schema.model_dump()
        
        result = self.test_store.belongs_to_group(str(test_schema.id), self.test_user.group)
        
        self.assertTrue(result)

    def test_belongs_to_group_false(self):
        """Test belongs_to_group when test doesn't belong to group."""
        test_schema = TestSchema(
            id=str(uuid4()),
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        self.mock_store.get.return_value = test_schema.model_dump()
        
        result = self.test_store.belongs_to_group(str(test_schema.id), "different_group")
        
        self.assertFalse(result)

    def test_belongs_to_group_test_not_found(self):
        """Test belongs_to_group when test doesn't exist."""
        self.mock_store.get.return_value = None
        
        result = self.test_store.belongs_to_group("non-existent-id", self.test_user.group)
        
        self.assertFalse(result)

    def test_get_tests_by_group(self):
        """Test getting tests by group."""
        # Mock the store to return keys and test data
        test_id = str(uuid4())
        test_keys = [test_id]
        
        test_schema = TestSchema(
            id=test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = test_schema.model_dump()
        
        tests = self.test_store.get_tests_by_group(self.test_user.group)
        
        # Should return tests for the specified group
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0].group_id, self.test_user.group)

    def test_list_with_exception_handling(self):
        """Test test listing with exception handling."""
        # Mock the store to raise an exception
        self.mock_store.keys.return_value = ["test1"]
        self.mock_store.get.side_effect = Exception("Store error")
        
        tests, total = self.test_store.list(page=1, limit=10)
        
        # Should handle the exception gracefully
        self.assertEqual(len(tests), 0)
        self.assertEqual(total, 0) 