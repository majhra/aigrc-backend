"""
Production API Client for Integration Testing

This client connects to the actual backend service for comprehensive integration testing.
"""
import json
import time
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class APIResponse:
    """Wrapper for API response data"""
    status_code: int
    data: Any
    headers: Dict[str, str]
    response_time: float
    raw_response: requests.Response


class ProductionAPIClient:
    """
    HTTP client for production-level integration testing.
    
    Connects to the actual backend service and provides methods for
    testing all API endpoints with proper authentication and error handling.
    """
    
    def __init__(self, base_url: str = "http://backend-grc_api-1:80"):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1.0"
        self.session = requests.Session()
        self.auth_token: Optional[str] = None
        
        # Configure retry strategy for resilient testing
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set reasonable timeouts
        self.timeout = (5, 30)  # (connect, read)
    
    def set_auth_token(self, token: str) -> None:
        """Set the JWT authentication token"""
        self.auth_token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def clear_auth(self) -> None:
        """Clear authentication token"""
        self.auth_token = None
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        files: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> APIResponse:
        """Make HTTP request and return structured response"""
        url = f"{self.api_base}{endpoint}"
        
        # Merge headers
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        
        # Prepare request data
        request_kwargs = {
            "timeout": self.timeout,
            "params": params,
            "headers": request_headers
        }
        
        if files:
            # For file uploads, don't set Content-Type (requests will set it)
            del request_kwargs["headers"]["Content-Type"]
            request_kwargs["files"] = files
        elif data is not None:
            request_kwargs["data"] = json.dumps(data)
        
        # Make request and measure time
        start_time = time.time()
        try:
            response = self.session.request(method, url, **request_kwargs)
            response_time = time.time() - start_time
            
            # Parse response data
            try:
                response_data = response.json() if response.content else None
            except json.JSONDecodeError:
                response_data = response.text
            
            return APIResponse(
                status_code=response.status_code,
                data=response_data,
                headers=dict(response.headers),
                response_time=response_time,
                raw_response=response
            )
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            # Return error response for connection issues
            return APIResponse(
                status_code=0,
                data={"error": str(e)},
                headers={},
                response_time=response_time,
                raw_response=None
            )
    
    # HTTP method helpers
    def get(self, endpoint: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> APIResponse:
        """Make GET request"""
        return self._make_request("GET", endpoint, params=params, headers=headers)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None, headers: Optional[Dict] = None) -> APIResponse:
        """Make POST request"""
        return self._make_request("POST", endpoint, data=data, files=files, headers=headers)
    
    def put(self, endpoint: str, data: Optional[Dict] = None, headers: Optional[Dict] = None) -> APIResponse:
        """Make PUT request"""
        return self._make_request("PUT", endpoint, data=data, headers=headers)
    
    def delete(self, endpoint: str, headers: Optional[Dict] = None) -> APIResponse:
        """Make DELETE request"""
        return self._make_request("DELETE", endpoint, headers=headers)
    
    # Authentication helpers
    def login(self, email: str, password: str) -> APIResponse:
        """Login and set authentication token"""
        # Use form data for OAuth2 login
        form_data = {
            "username": email,  # FastAPI OAuth2 uses 'username' field
            "password": password
        }
        
        # Make request with form data instead of JSON
        response = self._make_request(
            "POST", 
            "/user/login", 
            data=None,  # No JSON data
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Set form data directly on the session
        url = f"{self.api_base}/user/login"
        start_time = time.time()
        try:
            raw_response = self.session.post(
                url, 
                data=form_data,  # Form data, not JSON
                timeout=self.timeout
            )
            response_time = time.time() - start_time
            
            # Parse response
            try:
                response_data = raw_response.json() if raw_response.content else None
            except json.JSONDecodeError:
                response_data = raw_response.text
            
            response = APIResponse(
                status_code=raw_response.status_code,
                data=response_data,
                headers=dict(raw_response.headers),
                response_time=response_time,
                raw_response=raw_response
            )
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            response = APIResponse(
                status_code=0,
                data={"error": str(e)},
                headers={},
                response_time=response_time,
                raw_response=None
            )
        
        if response.status_code == 200 and response.data:
            token = response.data.get("access_token")
            if token:
                self.set_auth_token(token)
        
        return response
    
    def register_user(self, email: str, password: str, full_name: str, group: Optional[str] = None) -> APIResponse:
        """Register a new user"""
        # Use form data for registration - only email and password are required
        form_data = {
            "email": email,
            "password": password
        }
        # Note: full_name and group are not supported by the UserSignup schema
        
        # Make request with form data
        url = f"{self.api_base}/user/register"
        start_time = time.time()
        try:
            raw_response = self.session.post(
                url, 
                data=form_data,  # Form data, not JSON
                timeout=self.timeout
            )
            response_time = time.time() - start_time
            
            # Parse response
            try:
                response_data = raw_response.json() if raw_response.content else None
            except json.JSONDecodeError:
                response_data = raw_response.text
            
            return APIResponse(
                status_code=raw_response.status_code,
                data=response_data,
                headers=dict(raw_response.headers),
                response_time=response_time,
                raw_response=raw_response
            )
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            return APIResponse(
                status_code=0,
                data={"error": str(e)},
                headers={},
                response_time=response_time,
                raw_response=None
            )
    
    # Health check
    def health_check(self) -> bool:
        """Check if the API is accessible"""
        try:
            response = self.get("/user/me")  # Simple endpoint to test connectivity
            return response.status_code in [200, 401]  # 401 is expected without auth
        except Exception:
            return False
    
    # Context manager for temporary authentication
    def authenticated_as(self, token: str):
        """Context manager for temporary authentication"""
        class AuthContext:
            def __init__(self, client: 'ProductionAPIClient', auth_token: str):
                self.client = client
                self.auth_token = auth_token
                self.previous_token = client.auth_token
            
            def __enter__(self):
                self.client.set_auth_token(self.auth_token)
                return self.client
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.previous_token:
                    self.client.set_auth_token(self.previous_token)
                else:
                    self.client.clear_auth()
        
        return AuthContext(self, token)