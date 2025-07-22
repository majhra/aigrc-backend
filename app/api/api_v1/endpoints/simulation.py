from typing import List, Optional, Dict, Any
from datetime import datetime
import time
import uuid

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field


router = APIRouter()


# OpenAI API Request/Response Models
class ChatCompletionMessage(BaseModel):
    role: str = Field(..., description="The role of the message author")
    content: str = Field(..., description="The content of the message")
    name: Optional[str] = Field(None, description="An optional name for the participant")


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="ID of the model to use")
    messages: List[ChatCompletionMessage] = Field(..., description="List of messages")
    temperature: Optional[float] = Field(1.0, ge=0, le=2, description="Sampling temperature")
    top_p: Optional[float] = Field(1.0, ge=0, le=1, description="Top-p sampling")
    n: Optional[int] = Field(1, ge=1, le=128, description="Number of completions to generate")
    stream: Optional[bool] = Field(False, description="Whether to stream responses")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens to generate")
    presence_penalty: Optional[float] = Field(0.0, ge=-2, le=2, description="Presence penalty")
    frequency_penalty: Optional[float] = Field(0.0, ge=-2, le=2, description="Frequency penalty")
    logit_bias: Optional[Dict[str, float]] = Field(None, description="Logit bias")
    user: Optional[str] = Field(None, description="User identifier")


class ChatCompletionResponseChoice(BaseModel):
    index: int = Field(..., description="Choice index")
    message: ChatCompletionMessage = Field(..., description="The response message")
    finish_reason: str = Field(..., description="The reason the model stopped generating tokens")


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(..., description="Number of tokens in the completion")
    total_tokens: int = Field(..., description="Total number of tokens used")


class ChatCompletionResponse(BaseModel):
    id: str = Field(..., description="Unique identifier for the chat completion")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="The model used for completion")
    choices: List[ChatCompletionResponseChoice] = Field(..., description="List of completion choices")
    usage: ChatCompletionUsage = Field(..., description="Usage statistics")
    system_fingerprint: Optional[str] = Field(None, description="System fingerprint")


# Simulation endpoint
@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def simulate_chat_completion(
    request: ChatCompletionRequest,
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Simulates an OpenAI chat completion endpoint for testing purposes.
    Accepts any model name and requires API key '12345'.
    """
    # Validate API key
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )
    
    api_key = authorization.replace("Bearer ", "").strip()
    if api_key != "12345":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Generate simulated response
    current_time = int(time.time())
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
    
    # Create a simple simulated response based on the last user message
    user_messages = [msg for msg in request.messages if msg.role == "user"]
    last_user_message = user_messages[-1].content if user_messages else "Hello!"
    
    # Generate a simple response
    simulated_response = f"This is a simulated response to: '{last_user_message[:50]}...'"
    
    # Calculate token usage (simulated)
    prompt_tokens = sum(len(msg.content.split()) for msg in request.messages)
    completion_tokens = len(simulated_response.split())
    total_tokens = prompt_tokens + completion_tokens
    
    # Create response
    response = ChatCompletionResponse(
        id=completion_id,
        object="chat.completion",
        created=current_time,
        model=request.model,
        choices=[
            ChatCompletionResponseChoice(
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=simulated_response
                ),
                finish_reason="stop"
            )
        ],
        usage=ChatCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens
        ),
        system_fingerprint=f"fp_{uuid.uuid4().hex[:8]}"
    )
    
    return response


@router.get("/v1/models")
async def list_models(
    authorization: str = Header(..., description="Bearer token for authentication")
):
    """
    Simulates the OpenAI models endpoint.
    Returns a list of available models for testing.
    """
    # Validate API key
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )
    
    api_key = authorization.replace("Bearer ", "").strip()
    if api_key != "12345":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Return simulated models list
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-4",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "openai-simulation"
            },
            {
                "id": "gpt-4-turbo",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "openai-simulation"
            },
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "openai-simulation"
            },
            {
                "id": "claude-3-sonnet",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "openai-simulation"
            }
        ]
    }