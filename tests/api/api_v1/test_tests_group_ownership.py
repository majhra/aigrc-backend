import pytest
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import status
from fastapi.testclient import TestClient

from app.schemas import User, MyTestCreate, ConnectionConfig, ValidationConfig, ValidationCriterion
from app.modules.tests_store import MyTestStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.core.config import settings


class TestTestsGroupOwnership:
    """Test group ownership validation for tests."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_store = UserStore(LocalStore())
        self.group_store = GroupStore(LocalStore())
        self.test_store = MyTestStore(LocalStore())
        
        # Create test groups
        from app.schemas import GroupCreate
        group1_data = GroupCreate(name="Group 1", description="Test group 1")
        group2_data = GroupCreate(name="Group 2", description="Test group 2")
        
        self.group1 = self.group_store.create(group1_data, "system")
        self.group2 = self.group_store.create(group2_data, "system")
        
        # Create test users
        self.user1 = User(
            id=uuid4(),
            email="user1@example.com",
            full_name="User 1",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group=str(self.group1.id)
        )
        
        self.user2 = User(
            id=uuid4(),
            email="user2@example.com",
            full_name="User 2",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group=str(self.group2.id)
        )
        
        self.admin_user = User(
            id=uuid4(),
            email="admin@example.com",
            full_name="Admin User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="admin",
            group=str(self.group1.id)
        )
        
        # Store users
        self.user_store.create(self.user1, str(self.group1.id))
        self.user_store.create(self.user2, str(self.group2.id))
        self.user_store.create(self.admin_user, str(self.group1.id))
        
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

    def test_create_test_sets_group_id(self):
        """Test that creating a test sets the group_id from the user's group."""
        test = self.test_store.create(self.test_data, self.user1)
        
        assert test.group_id == str(self.group1.id)
        assert test.created_by == self.user1.id

    def test_list_tests_filters_by_group(self):
        """Test that listing tests filters by user's group."""
        # Create tests for different groups
        test1 = self.test_store.create(self.test_data, self.user1)
        
        test_data2 = self.test_data.model_dump()
        test_data2["name"] = "Test 2"
        test2 = self.test_store.create(MyTestCreate(**test_data2), self.user2)
        
        # List tests for user1 (should only see group1 tests)
        tests, total = self.test_store.list(group_id=str(self.group1.id))
        assert len(tests) == 1
        assert tests[0].id == test1.id
        
        # List tests for user2 (should only see group2 tests)
        tests, total = self.test_store.list(group_id=str(self.group2.id))
        assert len(tests) == 1
        assert tests[0].id == test2.id

    def test_belongs_to_group_validation(self):
        """Test the belongs_to_group method."""
        test = self.test_store.create(self.test_data, self.user1)
        
        # Should belong to group1
        assert self.test_store.belongs_to_group(str(test.id), str(self.group1.id)) is True
        
        # Should not belong to group2
        assert self.test_store.belongs_to_group(str(test.id), str(self.group2.id)) is False
        
        # Should return False for non-existent test
        assert self.test_store.belongs_to_group("non-existent", str(self.group1.id)) is False

    def test_get_tests_by_group(self):
        """Test getting tests by group."""
        # Create tests for different groups
        test1 = self.test_store.create(self.test_data, self.user1)
        
        test_data2 = self.test_data.model_dump()
        test_data2["name"] = "Test 2"
        test2 = self.test_store.create(MyTestCreate(**test_data2), self.user2)
        
        # Get tests for group1
        group1_tests = self.test_store.get_tests_by_group(str(self.group1.id))
        assert len(group1_tests) == 1
        assert group1_tests[0].id == test1.id
        
        # Get tests for group2
        group2_tests = self.test_store.get_tests_by_group(str(self.group2.id))
        assert len(group2_tests) == 1
        assert group2_tests[0].id == test2.id

    def test_update_preserves_group_id(self):
        """Test that updating a test preserves the group_id."""
        test = self.test_store.create(self.test_data, self.user1)
        
        # Update the test
        update_data = self.test_data.model_dump()
        update_data["name"] = "Updated Test"
        updated_test = self.test_store.update(str(test.id), MyTestCreate(**update_data))
        
        assert updated_test.group_id == str(self.group1.id)
        assert updated_test.name == "Updated Test"

    def test_group_ownership_integration(self):
        """Test group ownership validation in a complete workflow."""
        # Create a test
        test = self.test_store.create(self.test_data, self.user1)
        
        # Verify user1 can access the test
        assert self.test_store.belongs_to_group(str(test.id), str(self.group1.id)) is True
        
        # Verify user2 cannot access the test
        assert self.test_store.belongs_to_group(str(test.id), str(self.group2.id)) is False
        
        # Verify admin can access any test (this would be tested in API endpoints)
        # The admin role check happens in the API layer, not in the store layer

    def test_multiple_tests_per_group(self):
        """Test that multiple tests can belong to the same group."""
        # Create multiple tests for group1
        test1 = self.test_store.create(self.test_data, self.user1)
        
        test_data2 = self.test_data.model_dump()
        test_data2["name"] = "Test 2"
        test2 = self.test_store.create(MyTestCreate(**test_data2), self.user1)
        
        test_data3 = self.test_data.model_dump()
        test_data3["name"] = "Test 3"
        test3 = self.test_store.create(MyTestCreate(**test_data3), self.user1)
        
        # All tests should belong to group1
        assert test1.group_id == str(self.group1.id)
        assert test2.group_id == str(self.group1.id)
        assert test3.group_id == str(self.group1.id)
        
        # List should return all tests for group1
        tests, total = self.test_store.list(group_id=str(self.group1.id))
        assert len(tests) == 3
        assert total == 3

    def test_group_filter_with_other_filters(self):
        """Test that group filter works with other filters."""
        # Create tests with different statuses in group1
        test1 = self.test_store.create(self.test_data, self.user1)
        
        test_data2 = self.test_data.model_dump()
        test_data2["name"] = "Draft Test"
        test_data2["status"] = "DRAFT"
        test2 = self.test_store.create(MyTestCreate(**test_data2), self.user1)
        
        # Filter by group and status
        tests, total = self.test_store.list(
            group_id=str(self.group1.id),
            status="ACTIVE"
        )
        assert len(tests) == 1
        assert tests[0].id == test1.id
        
        # Filter by group and status (DRAFT)
        tests, total = self.test_store.list(
            group_id=str(self.group1.id),
            status="DRAFT"
        )
        assert len(tests) == 1
        assert tests[0].id == test2.id 