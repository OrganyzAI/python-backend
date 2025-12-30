from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal


class ChatMessage(BaseModel):
    """Schema for a single chat message."""
    role: Literal["system", "user", "assistant"] = Field(
        ..., description="The role of the message sender"
    )
    content: str = Field(
        ..., description="The content of the message"
    )


class ChatCompletionRequest(BaseModel):
    """Schema for chat completion request."""
    messages: List[ChatMessage] = Field(
        ..., description="List of messages in the conversation"
    )
    model: str = Field(
        default="openai/gpt-3.5-turbo",
        description="The model to use for completion"
    )
    temperature: float = Field(
        default=0.7,
        ge=0,
        le=2,
        description="Sampling temperature (0-2)"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=4000,
        description="Maximum tokens in response"
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, how are you?"
                    }
                ],
                "model": "openai/gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 150
            }
        }


class ChatCompletionChoice(BaseModel):
    """Schema for a single completion choice."""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionUsage(BaseModel):
    """Schema for token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Schema for chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[ChatCompletionUsage] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "chatcmpl-abc123",
                "object": "chat.completion",
                "created": 1677649420,
                "model": "gpt-3.5-turbo",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Hello! I'm doing well, thank you for asking. How can I help you today?"
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        }


class ChatError(BaseModel):
    """Schema for error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")


class ModelInfo(BaseModel):
    """Schema for model information."""
    id: str
    name: str
    description: Optional[str] = None
    pricing: Optional[Dict[str, Any]] = None
    context_length: Optional[int] = None


class ModelsListResponse(BaseModel):
    """Schema for models list response."""
    models: List[ModelInfo]
    total: int