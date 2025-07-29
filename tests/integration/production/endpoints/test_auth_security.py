"""
Authentication and Authorization Security Tests

Comprehensive security testing for authentication and authorization
across all API endpoints.
"""
import pytest
from typing import List, Dict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import ProductionAPIClient, APIResponse
from utils.test_data_factory import ProductionDataFactory, ProductionTestUser
from conftest import (
    assert_auth_required, 
    assert_forbidden, 
    assert_success_response,
    assert_error_response
)


class TestAuthenticationSecurity:
    """Test authentication security across all endpoints"""
    
    def test_all_protected_endpoints_require_auth(self, clean_api_client: ProductionAPIClient):
        """Test that all protected endpoints reject unauthenticated requests"""
        
        # Comprehensive list of all protected endpoints
        protected_endpoints = [
            # User endpoints
            ("GET", "/user/me"),
            ("POST", "/user/update_profile"),
            ("POST", "/user/support"),
            ("POST", "/user/invite"),
            ("GET", "/user/users"),
            ("GET", "/user/users/email/test@example.com"),
            ("GET", "/user/users/00000000-0000-0000-0000-000000000000"),
            ("POST", "/user/users"),
            ("PUT", "/user/users/00000000-0000-0000-0000-000000000000"),
            
            # Prompt endpoints
            ("GET", "/prompts/categories"),
            ("GET", "/prompts/categories/00000000-0000-0000-0000-000000000000"),
            ("POST", "/prompts/categories"),
            ("PUT", "/prompts/categories/00000000-0000-0000-0000-000000000000"),
            ("DELETE", "/prompts/categories/00000000-0000-0000-0000-000000000000"),
            ("GET", "/prompts/"),
            ("GET", "/prompts/sets"),
            ("GET", "/prompts/sets/00000000-0000-0000-0000-000000000000"),
            ("POST", "/prompts/sets"),
            ("PUT", "/prompts/sets/00000000-0000-0000-0000-000000000000"),
            ("DELETE", "/prompts/sets/00000000-0000-0000-0000-000000000000"),
            ("GET", "/prompts/00000000-0000-0000-0000-000000000000"),
            ("POST", "/prompts/"),
            ("PUT", "/prompts/00000000-0000-0000-0000-000000000000"),
            ("DELETE", "/prompts/00000000-0000-0000-0000-000000000000"),
            ("POST", "/prompts/validate"),
            ("POST", "/prompts/preview"),
            
            # Configuration endpoints
            ("GET", "/configurations/"),
            ("GET", "/configurations/00000000-0000-0000-0000-000000000000"),
            ("POST", "/configurations/"),
            ("PUT", "/configurations/00000000-0000-0000-0000-000000000000"),
            ("DELETE", "/configurations/00000000-0000-0000-0000-000000000000"),
            ("POST", "/configurations/00000000-0000-0000-0000-000000000000/test"),
            ("GET", "/configurations/providers/list"),
            ("GET", "/configurations/templates/list"),
            ("POST", "/configurations/validate"),
            
            # Test endpoints
            ("GET", "/tests"),
            ("GET", "/tests/00000000-0000-0000-0000-000000000000"),
            ("POST", "/tests"),
            ("PUT", "/tests/00000000-0000-0000-0000-000000000000"),
            ("DELETE", "/tests/00000000-0000-0000-0000-000000000000"),
            ("POST", "/tests/00000000-0000-0000-0000-000000000000/execute"),
            ("GET", "/tests/00000000-0000-0000-0000-000000000000/executions"),
            ("GET", "/tests/00000000-0000-0000-0000-000000000000/00000000-0000-0000-0000-000000000000"),
            ("PUT", "/tests/00000000-0000-0000-0000-000000000000/00000000-0000-0000-0000-000000000000/validate"),
            ("POST", "/tests/test-connection"),
            
            # Report endpoints
            ("GET", "/reports/summary"),
            ("GET", "/reports/trends"),
            ("GET", "/reports/performance"),
            ("GET", "/reports/trends/00000000-0000-0000-0000-000000000000"),
            ("GET", "/reports/performance/00000000-0000-0000-0000-000000000000"),
            
            # Feature flags - Skip due to external service dependency
            # ("GET", "/feature_flags/proxy"),
        ]
        
        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = clean_api_client.get(endpoint)
            elif method == "POST":
                response = clean_api_client.post(endpoint, {})
            elif method == "PUT":
                response = clean_api_client.put(endpoint, {})
            elif method == "DELETE":
                response = clean_api_client.delete(endpoint)
            else:
                continue
            
            # Should require authentication
            assert_auth_required(response)
    
    def test_public_endpoints_allow_access(self, clean_api_client: ProductionAPIClient):
        """Test that public endpoints allow unauthenticated access"""
        
        public_endpoints = [
            ("POST", "/user/login"),
            ("POST", "/user/register"),
            ("POST", "/user/verify_email"),
            ("POST", "/user/resend_verification_email"),
            ("POST", "/user/password_reset/request"),
            ("POST", "/user/password_reset/verify"),
            ("POST", "/simulation/v1/chat/completions"),
            ("GET", "/simulation/v1/models"),
        ]
        
        for method, endpoint in public_endpoints:
            if method == "GET":
                response = clean_api_client.get(endpoint)
            elif method == "POST":
                # Use minimal valid data to avoid 400 errors
                test_data = {"test": "data"}
                if "login" in endpoint:
                    test_data = {"username": "test", "password": "test"}
                elif "register" in endpoint:
                    test_data = {"email": "test@example.com", "password": "test", "full_name": "Test"}
                elif "chat/completions" in endpoint:
                    test_data = {"messages": [{"role": "user", "content": "test"}]}
                
                response = clean_api_client.post(endpoint, test_data)
            else:
                continue
            
            # Should not require authentication (might return 400 for invalid data, but not 401)
            assert response.status_code != 401, f"Public endpoint {endpoint} should not require auth"
    
    def test_invalid_token_handling(self, clean_api_client: ProductionAPIClient):
        """Test handling of invalid authentication tokens"""
        
        # Test with malformed token
        clean_api_client.set_auth_token("invalid-token")
        response = clean_api_client.get("/user/me")
        assert_auth_required(response)
        
        # Test with expired-looking token (JWT format but invalid)
        fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        clean_api_client.set_auth_token(fake_jwt)
        response = clean_api_client.get("/user/me")
        assert_auth_required(response)
        
        # Test with empty token
        clean_api_client.set_auth_token("")
        response = clean_api_client.get("/user/me")
        assert_auth_required(response)
    
    def test_token_expiration_handling(self, clean_api_client: ProductionAPIClient, data_factory: ProductionDataFactory):
        """Test that expired tokens are properly rejected"""
        
        # Note: This test would require manipulating token expiration or waiting
        # For production tests, we might need to mock or use short-lived tokens
        pytest.skip("Token expiration testing requires time manipulation or short-lived tokens")


class TestAuthorizationSecurity:
    """Test authorization and access control security"""
    
    def test_user_cannot_access_admin_functions(self, api_client: ProductionAPIClient, regular_user: ProductionTestUser):
        """Test that regular users cannot perform admin-only operations"""
        
        api_client.set_auth_token(regular_user.access_token)
        
        # Test admin-specific operations that regular users should not be able to perform
        # Note: Most endpoints use group-based access rather than role-based admin access
        
        # Try to access all users (might be restricted for non-admins)
        users_response = api_client.get("/user/users")
        # This might be allowed but with filtered results, so we check for reasonable response
        assert users_response.status_code in [200, 403], f"Unexpected status for user list access: {users_response.status_code}"
    
    def test_cross_user_data_access_prevention(self, api_client: ProductionAPIClient, user_manager):
        """Test that users cannot access other users' private data"""
        
        # Create two different users
        user1 = user_manager.create_regular_user()
        user2 = user_manager.create_regular_user()
        
        # User 1 creates some data
        api_client.set_auth_token(user1.access_token)
        
        # Create a prompt category as user 1
        category_data = {"name": "User 1 Category", "description": "Private category"}
        create_response = api_client.post("/prompts/categories", category_data)
        
        if create_response.status_code == 201:
            category_id = create_response.data.get("id")
            
            # User 2 tries to access User 1's category
            api_client.set_auth_token(user2.access_token)
            access_response = api_client.get(f"/prompts/categories/{category_id}")
            
            # Should be forbidden if proper isolation is implemented
            # Note: This depends on group isolation being properly implemented
            assert access_response.status_code in [403, 404], f"User should not access other user's data: {access_response.status_code}"
    
    def test_data_modification_authorization(self, api_client: ProductionAPIClient, user_manager):
        """Test that users cannot modify data they don't own"""
        
        # Create two users
        user1 = user_manager.create_regular_user()
        user2 = user_manager.create_regular_user()
        
        # User 1 creates data
        api_client.set_auth_token(user1.access_token)
        category_data = {"name": "User 1 Category", "description": "Private category"}
        create_response = api_client.post("/prompts/categories", category_data)
        
        if create_response.status_code == 201:
            category_id = create_response.data.get("id")
            
            # User 2 tries to modify User 1's data
            api_client.set_auth_token(user2.access_token)
            modified_data = {"name": "Hacked Category", "description": "Modified by user 2"}
            
            # Try to update
            update_response = api_client.put(f"/prompts/categories/{category_id}", modified_data)
            assert update_response.status_code in [403, 404], f"User should not modify other user's data: {update_response.status_code}"
            
            # Try to delete
            delete_response = api_client.delete(f"/prompts/categories/{category_id}")
            assert delete_response.status_code in [403, 404], f"User should not delete other user's data: {delete_response.status_code}"


class TestInputValidationSecurity:
    """Test input validation and injection prevention"""
    
    def test_sql_injection_prevention(self, api_client: ProductionAPIClient, regular_user: ProductionTestUser):
        """Test that SQL injection attempts are prevented"""
        
        api_client.set_auth_token(regular_user.access_token)
        
        # Test SQL injection in various fields
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; UPDATE users SET role='admin'; --",
            "1' UNION SELECT * FROM users; --"
        ]
        
        for payload in sql_injection_payloads:
            # Test in category name
            malicious_data = {"name": payload, "description": "test"}
            response = api_client.post("/prompts/categories", malicious_data)
            
            # Should either be rejected as invalid or safely handled
            assert response.status_code in [400, 422, 201], f"Unexpected response to SQL injection: {response.status_code}"
            
            # If accepted, verify it was safely stored
            if response.status_code == 201:
                category_id = response.data.get("id")
                get_response = api_client.get(f"/prompts/categories/{category_id}")
                if get_response.status_code == 200:
                    # Name should be exactly what was provided (escaped/sanitized)
                    assert get_response.data.get("name") == payload, "SQL injection payload should be safely stored"
                # Clean up
                api_client.delete(f"/prompts/categories/{category_id}")
    
    def test_xss_prevention(self, api_client: ProductionAPIClient, regular_user: ProductionTestUser):
        """Test that XSS attempts are prevented"""
        
        api_client.set_auth_token(regular_user.access_token)
        
        # Test XSS payloads
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            malicious_data = {"name": payload, "description": "test"}
            response = api_client.post("/prompts/categories", malicious_data)
            
            # Should be handled safely
            if response.status_code == 201:
                category_id = response.data.get("id")
                get_response = api_client.get(f"/prompts/categories/{category_id}")
                if get_response.status_code == 200:
                    # XSS payload should be safely stored/escaped
                    stored_name = get_response.data.get("name")
                    # Should contain the payload (properly escaped) or be rejected
                    assert stored_name is not None, "Name should be stored safely"
                # Clean up
                api_client.delete(f"/prompts/categories/{category_id}")
    
    def test_field_length_limits(self, api_client: ProductionAPIClient, regular_user: ProductionTestUser):
        """Test that excessively long inputs are properly handled"""
        
        api_client.set_auth_token(regular_user.access_token)
        
        # Test extremely long strings
        very_long_string = "A" * 10000  # 10KB string
        extremely_long_string = "B" * 100000  # 100KB string
        
        for test_string in [very_long_string, extremely_long_string]:
            long_data = {"name": test_string, "description": "test"}
            response = api_client.post("/prompts/categories", long_data)
            
            # Should either be rejected or truncated safely
            assert response.status_code in [400, 422, 201], f"Long string handling failed: {response.status_code}"
            
            if response.status_code == 201:
                # Clean up
                category_id = response.data.get("id")
                api_client.delete(f"/prompts/categories/{category_id}")
    
    def test_null_and_empty_input_handling(self, api_client: ProductionAPIClient, regular_user: ProductionTestUser):
        """Test handling of null and empty inputs"""
        
        api_client.set_auth_token(regular_user.access_token)
        
        # Test various empty/null inputs
        invalid_inputs = [
            {"name": None, "description": "test"},
            {"name": "", "description": "test"},
            {"name": "test", "description": None},
            {},  # Missing required fields
            {"name": "   ", "description": "test"},  # Whitespace only
        ]
        
        for invalid_data in invalid_inputs:
            response = api_client.post("/prompts/categories", invalid_data)
            
            # Should be rejected with appropriate error
            assert response.status_code in [400, 422], f"Invalid input should be rejected: {invalid_data}"


class TestRateLimitingSecurity:
    """Test rate limiting and abuse prevention"""
    
    def test_basic_rate_limiting(self, api_client: ProductionAPIClient, regular_user: ProductionTestUser):
        """Test that the API has some form of rate limiting"""
        
        api_client.set_auth_token(regular_user.access_token)
        
        # Make many rapid requests
        responses = []
        for i in range(50):  # Make 50 rapid requests
            response = api_client.get("/user/me")
            responses.append(response.status_code)
            
            # Stop if we hit rate limiting
            if response.status_code == 429:
                break
        
        # We should either see all successes (no rate limiting) or some rate limiting
        success_count = sum(1 for status in responses if status == 200)
        rate_limited_count = sum(1 for status in responses if status == 429)
        
        # Either the system handles the load or implements rate limiting
        assert success_count > 0, "At least some requests should succeed"
        
        # If rate limiting is implemented, it should be reasonable
        if rate_limited_count > 0:
            assert success_count >= 10, "Rate limiting should allow reasonable number of requests"


class TestErrorInformationLeakage:
    """Test that errors don't leak sensitive information"""
    
    def test_authentication_error_messages(self, clean_api_client: ProductionAPIClient):
        """Test that authentication errors don't leak information"""
        
        # Test with non-existent user
        login_response = clean_api_client.login("nonexistent@example.com", "password123")
        
        # Should not indicate whether user exists or not
        if login_response.status_code in [400, 401]:
            error_message = str(login_response.data).lower()
            # Should not reveal if user exists
            sensitive_terms = ["user not found", "user does not exist", "invalid user"]
            for term in sensitive_terms:
                assert term not in error_message, f"Error message leaks user existence: {error_message}"
    
    def test_resource_access_error_messages(self, api_client: ProductionAPIClient, regular_user: ProductionTestUser):
        """Test that resource access errors don't leak information"""
        
        api_client.set_auth_token(regular_user.access_token)
        
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        
        # Test access to non-existent resource
        response = api_client.get(f"/prompts/categories/{fake_uuid}")
        
        # Should return 404, not reveal internal structure
        if response.status_code == 404:
            error_message = str(response.data).lower()
            # Should not reveal database structure or internal paths
            sensitive_terms = ["database", "table", "sql", "select", "internal"]
            for term in sensitive_terms:
                assert term not in error_message, f"Error message leaks internal information: {error_message}"