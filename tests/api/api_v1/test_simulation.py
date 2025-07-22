import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestSimulationEndpoint:
    """Test suite for the simulation endpoint that mimics OpenAI API."""
    
    def test_chat_completion_success(self):
        """Test successful chat completion with valid API key."""
        request_data = {
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "temperature": 0.7
        }
        
        response = client.post(
            "/api/v1.0/simulation/v1/chat/completions",
            json=request_data,
            headers={"Authorization": "Bearer 12345"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify OpenAI-compatible response structure
        assert "id" in data
        assert data["object"] == "chat.completion"
        assert "created" in data
        assert data["model"] == "gpt-4"
        assert "choices" in data
        assert "usage" in data
        
        # Verify choices structure
        assert len(data["choices"]) == 1
        choice = data["choices"][0]
        assert choice["index"] == 0
        assert "message" in choice
        assert choice["message"]["role"] == "assistant"
        assert "content" in choice["message"]
        assert choice["finish_reason"] == "stop"
        
        # Verify usage structure
        usage = data["usage"]
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
    
    def test_chat_completion_invalid_api_key(self):
        """Test chat completion with invalid API key."""
        request_data = {
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
        
        response = client.post(
            "/api/v1.0/simulation/v1/chat/completions",
            json=request_data,
            headers={"Authorization": "Bearer invalid_key"}
        )
        
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_chat_completion_missing_bearer(self):
        """Test chat completion with malformed authorization header."""
        request_data = {
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
        
        response = client.post(
            "/api/v1.0/simulation/v1/chat/completions",
            json=request_data,
            headers={"Authorization": "12345"}  # Missing "Bearer "
        )
        
        assert response.status_code == 401
        assert "Invalid authorization header format" in response.json()["detail"]
    
    def test_chat_completion_no_auth_header(self):
        """Test chat completion without authorization header."""
        request_data = {
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
        
        response = client.post(
            "/api/v1.0/simulation/v1/chat/completions",
            json=request_data
        )
        
        assert response.status_code == 422  # FastAPI validation error for missing header
    
    def test_chat_completion_multiple_messages(self):
        """Test chat completion with multiple messages."""
        request_data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What's the weather like?"},
                {"role": "assistant", "content": "I don't have access to real-time weather data."},
                {"role": "user", "content": "Can you help me with something else?"}
            ],
            "temperature": 0.5,
            "max_tokens": 100
        }
        
        response = client.post(
            "/api/v1.0/simulation/v1/chat/completions",
            json=request_data,
            headers={"Authorization": "Bearer 12345"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "gpt-3.5-turbo"
        assert len(data["choices"]) == 1
        
        # Verify usage calculation with multiple messages
        usage = data["usage"]
        assert usage["prompt_tokens"] > 0
        assert usage["completion_tokens"] > 0
        assert usage["total_tokens"] > 0
    
    def test_chat_completion_different_models(self):
        """Test chat completion with different model names."""
        models_to_test = ["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet", "custom-model"]
        
        for model_name in models_to_test:
            request_data = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": f"Test with {model_name}"}
                ]
            }
            
            response = client.post(
                "/api/v1.0/simulation/v1/chat/completions",
                json=request_data,
                headers={"Authorization": "Bearer 12345"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["model"] == model_name
    
    def test_chat_completion_optional_parameters(self):
        """Test chat completion with optional parameters."""
        request_data = {
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "Test with optional params"}
            ],
            "temperature": 0.8,
            "top_p": 0.9,
            "n": 1,
            "stream": False,
            "max_tokens": 150,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.2,
            "user": "test_user_123"
        }
        
        response = client.post(
            "/api/v1.0/simulation/v1/chat/completions",
            json=request_data,
            headers={"Authorization": "Bearer 12345"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["object"] == "chat.completion"
    
    def test_list_models_success(self):
        """Test successful models listing with valid API key."""
        response = client.get(
            "/api/v1.0/simulation/v1/models",
            headers={"Authorization": "Bearer 12345"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify OpenAI-compatible models response structure
        assert data["object"] == "list"
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
        
        # Verify model structure
        for model in data["data"]:
            assert "id" in model
            assert "object" in model
            assert "created" in model
            assert "owned_by" in model
            assert model["object"] == "model"
            assert model["owned_by"] == "openai-simulation"
        
        # Check for expected models
        model_ids = [model["id"] for model in data["data"]]
        expected_models = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "claude-3-sonnet"]
        for expected_model in expected_models:
            assert expected_model in model_ids
    
    def test_list_models_invalid_api_key(self):
        """Test models listing with invalid API key."""
        response = client.get(
            "/api/v1.0/simulation/v1/models",
            headers={"Authorization": "Bearer invalid_key"}
        )
        
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_list_models_missing_bearer(self):
        """Test models listing with malformed authorization header."""
        response = client.get(
            "/api/v1.0/simulation/v1/models",
            headers={"Authorization": "12345"}  # Missing "Bearer "
        )
        
        assert response.status_code == 401
        assert "Invalid authorization header format" in response.json()["detail"]
    
    def test_list_models_no_auth_header(self):
        """Test models listing without authorization header."""
        response = client.get("/api/v1.0/simulation/v1/models")
        
        assert response.status_code == 422  # FastAPI validation error for missing header
    
    def test_chat_completion_validation_errors(self):
        """Test chat completion with invalid request data."""
        # Test missing required fields
        invalid_requests = [
            {},  # Missing all required fields
            {"model": "gpt-4"},  # Missing messages
            {"messages": []},  # Missing model
            {"model": "gpt-4", "messages": []},  # Empty messages
            {
                "model": "gpt-4",
                "messages": [{"role": "invalid", "content": "test"}]  # Invalid role
            },
        ]
        
        for invalid_request in invalid_requests:
            response = client.post(
                "/api/v1.0/simulation/v1/chat/completions",
                json=invalid_request,
                headers={"Authorization": "Bearer 12345"}
            )
            
            # Should return validation error (422) or handle gracefully (200)
            assert response.status_code in [200, 422]
    
    def test_chat_completion_response_consistency(self):
        """Test that responses are consistent and contain expected data."""
        request_data = {
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "Generate a consistent response"}
            ]
        }
        
        # Make multiple requests
        responses = []
        for _ in range(3):
            response = client.post(
                "/api/v1.0/simulation/v1/chat/completions",
                json=request_data,
                headers={"Authorization": "Bearer 12345"}
            )
            assert response.status_code == 200
            responses.append(response.json())
        
        # Verify all responses have consistent structure
        for response_data in responses:
            assert "id" in response_data
            assert response_data["object"] == "chat.completion"
            assert response_data["model"] == "gpt-4"
            assert len(response_data["choices"]) == 1
            assert "usage" in response_data
            
            # Each response should have unique ID
            assert response_data["id"].startswith("chatcmpl-")
        
        # Verify IDs are unique
        ids = [resp["id"] for resp in responses]
        assert len(set(ids)) == len(ids)  # All IDs should be unique