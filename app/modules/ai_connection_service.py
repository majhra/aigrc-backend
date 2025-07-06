import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
import time

from app.schemas.tests import ConnectionConfig
from app.modules.tlogger import TLogger


class AIConnectionError(Exception):
    """Custom exception for AI connection errors."""
    pass


class AIConnectionService:
    """Service for handling AI endpoint connections and requests."""
    
    def __init__(self, logger: TLogger):
        self.logger = logger
    
    async def execute_prompt(
        self, 
        connection_config: ConnectionConfig, 
        prompt: str,
        input_variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a prompt against an AI endpoint using the provided connection configuration.
        
        Args:
            connection_config: Configuration for connecting to the AI endpoint
            prompt: The prompt to send to the AI
            input_variables: Optional variables to substitute in the prompt
            
        Returns:
            Dictionary containing response data and benchmarks
        """
        if not connection_config.endpoint:
            raise AIConnectionError("No endpoint specified in connection configuration")
        
        # Format prompt with input variables if provided
        formatted_prompt = self._format_prompt(prompt, input_variables or {})
        
        # Prepare headers based on auth type
        headers = self._prepare_headers(connection_config)
        
        # Prepare request payload
        payload = self._prepare_payload(formatted_prompt)
        
        # Execute request
        start_time = time.time()
        try:
            response_data = await self._make_request(
                connection_config.endpoint,
                headers,
                payload,
                connection_config.timeout
            )
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Extract response and create benchmarks
            ai_response = self._extract_response(response_data)
            benchmarks = self._create_benchmarks(response_data, response_time, total_time=(time.time() - start_time) * 1000)
            
            return {
                "response": ai_response,
                "benchmarks": benchmarks,
                "raw_response": response_data
            }
            
        except Exception as e:
            self.logger.error(f"Error executing prompt: {str(e)}")
            raise AIConnectionError(f"Failed to execute prompt: {str(e)}")
    
    def _format_prompt(self, prompt: str, input_variables: Dict[str, Any]) -> str:
        """Format prompt with input variables using string substitution."""
        try:
            return prompt.format(**input_variables)
        except KeyError as e:
            raise AIConnectionError(f"Missing required input variable: {e}")
        except Exception as e:
            raise AIConnectionError(f"Error formatting prompt: {str(e)}")
    
    def _prepare_headers(self, connection_config: ConnectionConfig) -> Dict[str, str]:
        """Prepare HTTP headers based on authentication type."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AI-GRC-Test-Suite/1.0"
        }
        
        if connection_config.auth_type == "API_KEY":
            if not connection_config.auth_string:
                raise AIConnectionError("API_KEY auth type requires auth_string")
            headers["Authorization"] = f"Bearer {connection_config.auth_string}"
        elif connection_config.auth_type == "BEARER_TOKEN":
            if not connection_config.auth_string:
                raise AIConnectionError("BEARER_TOKEN auth type requires auth_string")
            headers["Authorization"] = f"Bearer {connection_config.auth_string}"
        elif connection_config.auth_type == "NONE":
            # No additional headers needed
            pass
        else:
            raise AIConnectionError(f"Unsupported auth_type: {connection_config.auth_type}")
        
        return headers
    
    def _prepare_payload(self, prompt: str) -> Dict[str, Any]:
        """Prepare the request payload for the AI endpoint."""
        # This is a generic payload structure that works with most OpenAI-compatible APIs
        # Can be extended to support different API formats
        return {
            "model": "gpt-3.5-turbo",  # Default model, could be made configurable
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
    
    async def _make_request(
        self, 
        endpoint: str, 
        headers: Dict[str, str], 
        payload: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to the AI endpoint."""
        timeout_obj = aiohttp.ClientTimeout(total=timeout or 30)
        
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(endpoint, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise AIConnectionError(
                        f"HTTP {response.status}: {error_text}"
                    )
                
                return await response.json()
    
    def _extract_response(self, response_data: Dict[str, Any]) -> str:
        """Extract the AI response from the API response data."""
        try:
            # Handle OpenAI-compatible response format
            if "choices" in response_data and len(response_data["choices"]) > 0:
                choice = response_data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
                elif "text" in choice:
                    return choice["text"]
            
            # Handle other response formats
            if "response" in response_data:
                return response_data["response"]
            elif "content" in response_data:
                return response_data["content"]
            elif "text" in response_data:
                return response_data["text"]
            
            # If no standard format found, return the whole response as string
            return str(response_data)
            
        except Exception as e:
            self.logger.error(f"Error extracting response: {str(e)}")
            return str(response_data)
    
    def _create_benchmarks(
        self, 
        response_data: Dict[str, Any], 
        response_time: float, 
        total_time: float
    ) -> Dict[str, Any]:
        """Create benchmark data from the response."""
        benchmarks = {
            "response_time": round(response_time, 2),
            "total_time": round(total_time, 2),
            "token_usage": {
                "prompt": 0,
                "completion": 0,
                "total": 0
            }
        }
        
        # Extract token usage if available
        if "usage" in response_data:
            usage = response_data["usage"]
            benchmarks["token_usage"]["prompt"] = usage.get("prompt_tokens", 0)
            benchmarks["token_usage"]["completion"] = usage.get("completion_tokens", 0)
            benchmarks["token_usage"]["total"] = usage.get("total_tokens", 0)
        
        return benchmarks
    
    async def test_connection(self, connection_config: ConnectionConfig) -> bool:
        """
        Test the connection to the AI endpoint.
        
        Args:
            connection_config: Configuration for connecting to the AI endpoint
            
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Send a simple test prompt
            test_prompt = "Hello, this is a connection test. Please respond with 'OK'."
            result = await self.execute_prompt(connection_config, test_prompt)
            
            # Check if we got a valid response
            if result["response"] and len(result["response"]) > 0:
                self.logger.info("Connection test successful")
                return True
            else:
                self.logger.warning("Connection test failed: Empty response")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False 