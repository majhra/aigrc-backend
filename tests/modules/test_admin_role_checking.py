import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas import User


class TestAdminRoleChecking:
    """Test suite to prevent admin role checking bugs."""
    
    def test_user_schema_attributes(self):
        """Test that User schema has the correct attributes for admin checking."""
        
        # Create test users
        regular_user = User(
            id=str(uuid4()),
            email="regular@example.com",
            full_name="Regular User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="user",
            group="test_group"
        )
        
        admin_user = User(
            id=str(uuid4()),
            email="admin@example.com",
            full_name="Admin User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="admin",
            group="test_group"
        )
        
        # Test that role attribute exists
        assert hasattr(regular_user, 'role')
        assert hasattr(admin_user, 'role')
        
        # Test that is_admin attribute does NOT exist (this would cause the bug)
        assert not hasattr(regular_user, 'is_admin')
        assert not hasattr(admin_user, 'is_admin')
        
        # Test accessing is_admin raises AttributeError
        with pytest.raises(AttributeError, match="'User' object has no attribute 'is_admin'"):
            _ = regular_user.is_admin
            
        with pytest.raises(AttributeError, match="'User' object has no attribute 'is_admin'"):
            _ = admin_user.is_admin

    def test_correct_admin_checking_pattern(self):
        """Test the correct pattern for checking admin access."""
        
        # Create test users with different roles
        test_cases = [
            ("admin", True),
            ("user", False),
            ("moderator", False),
            ("", False),
            (None, False),
            ("ADMIN", False),  # Case sensitive
            ("Admin", False),  # Case sensitive
        ]
        
        for role, expected_is_admin in test_cases:
            user = User(
                id=str(uuid4()),
                email=f"test_{role}@example.com",
                full_name=f"Test {role} User",
                disabled=False,
                created_at=datetime.now(timezone.utc),
                is_verified=True,
                role=role,
                group="test_group"
            )
            
            # Test the correct admin checking pattern
            is_admin = (user.role == "admin")
            assert is_admin == expected_is_admin, f"Failed for role '{role}': expected {expected_is_admin}, got {is_admin}"
            
            # Test the incorrect pattern would fail (this is what we're preventing)
            # Note: We can't actually test user.is_admin because it would raise AttributeError
            # But we document that this is the pattern that causes the bug
            
    def test_admin_check_in_conditional_logic(self):
        """Test admin checking in conditional logic like used in the API."""
        
        admin_user = User(
            id=str(uuid4()),
            email="admin@example.com",
            full_name="Admin User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="admin",
            group="group1"
        )
        
        regular_user = User(
            id=str(uuid4()),
            email="user@example.com",
            full_name="Regular User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="user",
            group="group1"
        )
        
        # Simulate the API logic for group access checking
        test_group_id = "group1"
        other_group_id = "group2"
        
        # Test admin can access any group (correct pattern)
        def can_access_test(current_user, test_group_id):
            # This is the CORRECT pattern used in the fixed code
            return current_user.role == "admin" or current_user.group == test_group_id
        
        # Admin should be able to access tests from any group
        assert can_access_test(admin_user, test_group_id) is True
        assert can_access_test(admin_user, other_group_id) is True
        
        # Regular user should only access their own group
        assert can_access_test(regular_user, test_group_id) is True
        assert can_access_test(regular_user, other_group_id) is False
        
        # Test the old INCORRECT pattern would fail
        def incorrect_can_access_test(current_user, test_group_id):
            # This is the INCORRECT pattern that caused the bug
            try:
                return current_user.is_admin or current_user.group == test_group_id
            except AttributeError as e:
                # This is the error we're preventing
                assert "'User' object has no attribute 'is_admin'" in str(e)
                return False
        
        # The incorrect pattern should fail for all users
        assert incorrect_can_access_test(admin_user, test_group_id) is False
        assert incorrect_can_access_test(regular_user, test_group_id) is False

    def test_edge_cases_in_admin_role_checking(self):
        """Test edge cases that might cause issues with admin role checking."""
        
        edge_cases = [
            # (role_value, description)
            (None, "None role"),
            ("", "Empty string role"),
            ("admin", "Correct admin role"),
            ("ADMIN", "Uppercase admin role"),
            ("Admin", "Capitalized admin role"),
            ("administrator", "Full administrator role"),
            ("user", "Regular user role"),
            ("moderator", "Moderator role"),
            ("guest", "Guest role"),
            ("admin ", "Admin with trailing space"),
            (" admin", "Admin with leading space"),
        ]
        
        for role_value, description in edge_cases:
            user = User(
                id=str(uuid4()),
                email=f"test@example.com",
                full_name="Test User",
                disabled=False,
                created_at=datetime.now(timezone.utc),
                is_verified=True,
                role=role_value,
                group="test_group"
            )
            
            # Test correct admin checking (only "admin" exactly should be True)
            is_admin_correct = (user.role == "admin")
            expected = (role_value == "admin")
            
            assert is_admin_correct == expected, f"Admin check failed for {description}: role='{role_value}'"
            
            # Verify that the user object doesn't have is_admin attribute
            assert not hasattr(user, 'is_admin'), f"User with {description} should not have is_admin attribute"

    def test_group_access_authorization_logic(self):
        """Test the complete authorization logic used in the API endpoints."""
        
        # Create users for testing
        group1_admin = User(id=str(uuid4()), email="admin1@example.com", role="admin", group="group1")
        group1_user = User(id=str(uuid4()), email="user1@example.com", role="user", group="group1")
        group2_user = User(id=str(uuid4()), email="user2@example.com", role="user", group="group2")
        no_role_user = User(id=str(uuid4()), email="norole@example.com", role=None, group="group1")
        
        # Test scenarios: (current_user, test_group, should_have_access, description)
        test_scenarios = [
            (group1_admin, "group1", True, "Admin accessing own group"),
            (group1_admin, "group2", True, "Admin accessing other group"),
            (group1_user, "group1", True, "User accessing own group"),
            (group1_user, "group2", False, "User accessing other group"),
            (group2_user, "group1", False, "User from group2 accessing group1"),
            (group2_user, "group2", True, "User accessing own group"),
            (no_role_user, "group1", True, "User with no role accessing own group"),
            (no_role_user, "group2", False, "User with no role accessing other group"),
        ]
        
        for current_user, test_group, expected_access, description in test_scenarios:
            # This is the CORRECT authorization logic from the fixed endpoint
            has_access = (current_user.role == "admin") or (current_user.group == test_group)
            
            assert has_access == expected_access, f"{description}: expected {expected_access}, got {has_access}"
            
            # Verify the INCORRECT logic would fail with AttributeError
            try:
                # This would be the buggy code
                incorrect_access = current_user.is_admin or (current_user.group == test_group)
                # If we get here, the test failed because the attribute should not exist
                assert False, f"is_admin attribute should not exist on User object"
            except AttributeError as e:
                # This is expected - the attribute should not exist
                assert "'User' object has no attribute 'is_admin'" in str(e)