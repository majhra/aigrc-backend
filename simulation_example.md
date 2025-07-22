# OpenAI Simulation Endpoint

This document describes the simulation endpoint that mimics the OpenAI API for testing purposes.

## Base URL
`/api/v1.0/simulation`

## Authentication
All requests require a Bearer token with the hardcoded API key: `12345`

```
Authorization: Bearer 12345
```

## Endpoints

### 1. Chat Completions
**POST** `/api/v1.0/simulation/v1/chat/completions`

Simulates the OpenAI chat completions endpoint.

#### Request Example
```bash
curl -X POST "http://localhost:8000/api/v1.0/simulation/v1/chat/completions" \
  -H "Authorization: Bearer 12345" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "temperature": 0.7
  }'
```

#### Response Example
```json
{
  "id": "chatcmpl-abc123def456ghi789",
  "object": "chat.completion",
  "created": 1703123456,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "This is a simulated response to: 'Hello, how are you?'"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 13,
    "completion_tokens": 12,
    "total_tokens": 25
  },
  "system_fingerprint": "fp_abc12345"
}
```

#### Supported Parameters
- `model`: Any model name (required)
- `messages`: Array of message objects (required)
- `temperature`: Float between 0-2 (optional, default: 1.0)
- `top_p`: Float between 0-1 (optional, default: 1.0)
- `n`: Integer 1-128 (optional, default: 1)
- `stream`: Boolean (optional, default: false)
- `stop`: Array of strings (optional)
- `max_tokens`: Integer >= 1 (optional)
- `presence_penalty`: Float between -2 to 2 (optional, default: 0.0)
- `frequency_penalty`: Float between -2 to 2 (optional, default: 0.0)
- `logit_bias`: Object with string keys and float values (optional)
- `user`: String identifier (optional)

### 2. List Models
**GET** `/api/v1.0/simulation/v1/models`

Returns a list of available models for testing.

#### Request Example
```bash
curl -X GET "http://localhost:8000/api/v1.0/simulation/v1/models" \
  -H "Authorization: Bearer 12345"
```

#### Response Example
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4",
      "object": "model",
      "created": 1703123456,
      "owned_by": "openai-simulation"
    },
    {
      "id": "gpt-4-turbo",
      "object": "model",
      "created": 1703123456,
      "owned_by": "openai-simulation"
    },
    {
      "id": "gpt-3.5-turbo",
      "object": "model",
      "created": 1703123456,
      "owned_by": "openai-simulation"
    },
    {
      "id": "claude-3-sonnet",
      "object": "model",
      "created": 1703123456,
      "owned_by": "openai-simulation"
    }
  ]
}
```

## Configuration for AI Endpoint Testing

When creating an AI endpoint configuration in the system, use these settings:

### Connection Configuration
- **Endpoint**: `http://localhost:8000/api/v1.0/simulation/v1/chat/completions`
- **Auth Type**: `API_KEY`
- **Auth String**: `12345`
- **Model**: Any model name (e.g., `gpt-4`, `gpt-3.5-turbo`, `claude-3-sonnet`)

### Example Python Usage
```python
import requests

def test_simulation_endpoint():
    url = "http://localhost:8000/api/v1.0/simulation/v1/chat/completions"
    headers = {
        "Authorization": "Bearer 12345",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "Test message"}
        ]
    }
    
    response = requests.post(url, json=data, headers=headers)
    return response.json()

# Usage
result = test_simulation_endpoint()
print(result)
```

## Error Responses

### Invalid API Key
```json
{
  "detail": "Invalid API key"
}
```
HTTP Status: 401

### Invalid Authorization Header
```json
{
  "detail": "Invalid authorization header format. Expected 'Bearer <token>'"
}
```
HTTP Status: 401

### Missing Authorization Header
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["header", "authorization"],
      "msg": "Field required"
    }
  ]
}
```
HTTP Status: 422

## Features

- ✅ OpenAI-compatible API format
- ✅ Accepts any model name
- ✅ API key validation (hardcoded: 12345)
- ✅ Simulated token usage calculation
- ✅ Proper error handling
- ✅ Multiple message support
- ✅ All OpenAI parameters accepted
- ✅ Consistent response structure
- ✅ Models listing endpoint
- ✅ Comprehensive test coverage

## Use Cases

1. **Testing AI configurations** without using real API tokens
2. **Development and debugging** of AI integration features
3. **Automated testing** of the AI GRC system
4. **Demo environments** where real API calls aren't needed
5. **Load testing** without incurring API costs