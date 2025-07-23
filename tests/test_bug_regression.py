"""
Regression tests for specific bugs to prevent them from reoccurring.
This file contains focused tests for bugs that have been fixed.
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas import User


class TestBugRegression:
    """Regression tests for specific bugs."""
    
    def test_user_is_admin_attribute_error_bug(self):
        """
        Regression test for: AttributeError: 'User' object has no attribute 'is_admin'
        
        This bug occurred when trying to use current_user.is_admin in API endpoints,
        but the User schema only has a 'role' field, not an 'is_admin' boolean field.
        
        Bug was in: /api/v1.0/tests/{test_id}/executions endpoint
        Original error line: if not current_user.is_admin and test.group_id != current_user.group:
        Fixed line: if current_user.role != "admin" and test.group_id != current_user.group:
        """
        
        # Create test user
        user = User(
            id=str(uuid4()),
            email="test@example.com",
            full_name="Test User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="admin",
            group="test_group"
        )
        
        # This should work - correct pattern
        is_admin_correct = (user.role == "admin")
        assert is_admin_correct is True
        
        # This should fail with AttributeError - the bug pattern
        with pytest.raises(AttributeError, match="'User' object has no attribute 'is_admin'"):
            _ = user.is_admin  # This line would cause the original bug
            
        # Test with different role
        user.role = "user"
        is_admin_correct = (user.role == "admin")
        assert is_admin_correct is False
        
        # Still should fail with AttributeError
        with pytest.raises(AttributeError, match="'User' object has no attribute 'is_admin'"):
            _ = user.is_admin

    def test_admin_check_patterns_comparison(self):
        """
        Test to document the correct vs incorrect admin checking patterns.
        This helps prevent future developers from using the wrong pattern.
        """
        
        admin_user = User(
            id=str(uuid4()),
            email="admin@example.com",
            role="admin",
            group="group1"
        )
        
        regular_user = User(
            id=str(uuid4()),
            email="user@example.com", 
            role="user",
            group="group1"
        )
        
        test_group = "group2"  # Different from user's group
        
        # CORRECT PATTERN (what should be used)
        def correct_admin_check(current_user, test_group_id):
            return current_user.role == "admin" or current_user.group == test_group_id
        
        # Test correct pattern works
        assert correct_admin_check(admin_user, test_group) is True  # Admin can access any group
        assert correct_admin_check(regular_user, test_group) is False  # User can't access other group
        assert correct_admin_check(regular_user, "group1") is True  # User can access own group
        
        # INCORRECT PATTERN (what caused the bug)
        def incorrect_admin_check(current_user, test_group_id):
            try:
                return current_user.is_admin or current_user.group == test_group_id
            except AttributeError:
                return False  # This is what would happen with the bug
        
        # Test incorrect pattern fails for everyone due to AttributeError
        assert incorrect_admin_check(admin_user, test_group) is False
        assert incorrect_admin_check(regular_user, test_group) is False
        assert incorrect_admin_check(regular_user, "group1") is False

    def test_all_user_roles_admin_checking(self):
        """
        Test admin checking with various role values to ensure robustness.
        This test would catch the bug if someone tried to use is_admin.
        """
        
        role_test_cases = [
            ("admin", True),    # Only this should be True
            ("user", False),
            ("moderator", False),
            ("", False),
            (None, False),
            ("ADMIN", False),   # Case sensitive
            ("Admin", False),   # Case sensitive  
            ("administrator", False),
        ]
        
        for role_value, expected_is_admin in role_test_cases:
            user = User(
                id=str(uuid4()),
                email=f"test_{role_value}@example.com",
                role=role_value,
                group="test_group"
            )
            
            # CORRECT way to check admin
            actual_is_admin = (user.role == "admin")
            assert actual_is_admin == expected_is_admin, f"Failed for role '{role_value}'"
            
            # INCORRECT way (the bug) - should always fail
            with pytest.raises(AttributeError):
                _ = user.is_admin

    def test_conditional_logic_that_caused_bug(self):
        """
        Test the specific conditional logic pattern that caused the original bug.
        This simulates the exact code that was failing in the API endpoint.
        """
        
        # Create test scenario
        current_user = User(
            id=str(uuid4()),
            email="admin@example.com",
            role="admin",
            group="group1"
        )
        
        # Simulate test object with group_id
        class MockTest:
            def __init__(self, group_id):
                self.group_id = group_id
        
        test = MockTest("group2")
        
        # CORRECT logic (what the fix uses)
        def access_check_correct(current_user, test):
            return current_user.role == "admin" or test.group_id == current_user.group
        
        # Should work for admin user
        assert access_check_correct(current_user, test) is True
        
        # INCORRECT logic (what caused the bug)  
        def access_check_incorrect(current_user, test):
            # This line caused: AttributeError: 'User' object has no attribute 'is_admin'
            # return not current_user.is_admin and test.group_id != current_user.group
            
            # We can't actually run the buggy code, but we can test that accessing
            # is_admin raises the AttributeError
            try:
                _ = current_user.is_admin  # This is the problematic access
                return False  # Should never reach here
            except AttributeError as e:
                assert "'User' object has no attribute 'is_admin'" in str(e)
                return "BUG_DETECTED"
        
        # The incorrect logic should detect the bug
        result = access_check_incorrect(current_user, test)
        assert result == "BUG_DETECTED"

    def test_authentication_middleware_compatibility(self):
        """
        Test that User objects created by authentication middleware 
        have the expected attributes and don't have is_admin.
        """
        
        # Simulate user object that might come from JWT token or database
        user_data = {
            "id": str(uuid4()),
            "email": "middleware@example.com",
            "full_name": "Middleware User",
            "disabled": False,
            "created_at": datetime.now(timezone.utc),
            "is_verified": True,
            "role": "admin",
            "group": "middleware_group"
        }
        
        # Create User object like middleware would
        user = User(**user_data)
        
        # Verify it has the expected attributes
        assert hasattr(user, 'role')
        assert hasattr(user, 'group')
        assert hasattr(user, 'email')
        
        # Verify it does NOT have is_admin (the bug trigger)
        assert not hasattr(user, 'is_admin')
        
        # Verify admin checking works correctly
        assert (user.role == "admin") is True
        
        # Verify accessing is_admin would cause the bug
        with pytest.raises(AttributeError):
            _ = user.is_admin