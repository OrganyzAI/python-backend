from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.middlewares.auth import CurrentUserDep
from app.schemas.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatError,
    ModelsListResponse,
    ModelInfo
)
from app.services.openrouter_service import openrouter_service
from app.services.ollama_service import ollama_service
from app.schemas.response import ResponseSchema
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    summary="Create chat completion",
    description="Create a chat completion using OpenAI models via OpenRouter. Requires authentication.",
    responses={
        200: {
            "description": "Successful response",
            "model": ChatCompletionResponse,
        },
        401: {
            "description": "Unauthorized - Invalid or missing authentication",
            "model": ChatError,
        },
        403: {
            "description": "Forbidden - User is not active",
            "model": ChatError,
        },
        500: {
            "description": "Internal server error",
            "model": ChatError,
        },
    }
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    current_user: CurrentUserDep
) -> ChatCompletionResponse:
    """
    Create a chat completion with OpenAI models via OpenRouter with Ollama as fallback.

    This endpoint requires authentication. Only authenticated users can access this endpoint.

    The service will first try to use OpenRouter/OpenAI. If that fails, it will fall back
    to the local Ollama instance.

    **Request Body:**
    - messages: List of messages in the conversation
    - model: The model to use (default: openai/gpt-3.5-turbo)
    - temperature: Sampling temperature (0-2, default: 0.7)
    - max_tokens: Maximum tokens in response (optional)
    - stream: Whether to stream the response (default: false)

    **Returns:**
    - Chat completion response with the assistant's message
    """
    try:
        logger.info(f"User {current_user.email} requesting chat completion")

        # Convert Pydantic models to dict for the service
        messages = [msg.model_dump() for msg in request.messages]

        # Try OpenRouter first
        try:
            logger.info("Attempting to use OpenRouter for chat completion")
            response = await openrouter_service.create_chat_completion(
                messages=messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=request.stream
            )
            logger.info("Successfully used OpenRouter for chat completion")

            # Return the response directly as it matches our schema
            return ChatCompletionResponse(**response)

        except Exception as openrouter_error:
            logger.warning(f"OpenRouter failed: {openrouter_error}. Attempting Ollama fallback...")

            # Check if Ollama is available
            if not await ollama_service.is_available():
                logger.error("Ollama service is not available")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Both OpenRouter and Ollama services are unavailable"
                )

            # Use Ollama as fallback
            try:
                # Extract model name for Ollama (remove provider prefix if present)
                ollama_model = None
                if request.model and "/" in request.model:
                    # If it's an OpenAI model, map to an appropriate Ollama model
                    if "gpt-4" in request.model.lower():
                        ollama_model = "llama3.2:3b"  # Use a better model for GPT-4 requests
                    elif "gpt-3.5" in request.model.lower():
                        ollama_model = "llama3.2:1b"  # Use lightweight model for GPT-3.5
                else:
                    ollama_model = request.model

                logger.info(f"Using Ollama with model: {ollama_model}")
                response = await ollama_service.create_chat_completion(
                    messages=messages,
                    model=ollama_model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stream=request.stream
                )

                logger.info("Successfully used Ollama for chat completion")
                return ChatCompletionResponse(**response)

            except Exception as ollama_error:
                logger.error(f"Ollama fallback also failed: {ollama_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Both services failed. OpenRouter: {str(openrouter_error)}, Ollama: {str(ollama_error)}"
                )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service configuration error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate chat completion: {str(e)}"
        )


@router.get(
    "/models",
    response_model=ModelsListResponse,
    summary="List available models",
    description="Get a list of available AI models from OpenRouter. Requires authentication.",
    responses={
        200: {
            "description": "Successful response",
            "model": ModelsListResponse,
        },
        401: {
            "description": "Unauthorized - Invalid or missing authentication",
            "model": ChatError,
        },
        500: {
            "description": "Internal server error",
            "model": ChatError,
        },
    }
)
async def list_models(
    current_user: CurrentUserDep
) -> ModelsListResponse:
    """
    List available AI models from OpenRouter.

    This endpoint requires authentication. Only authenticated users can access this endpoint.

    **Returns:**
    - List of available models with their details
    """
    try:
        logger.info(f"User {current_user.email} requesting models list")

        # Get models from OpenRouter service
        models = await openrouter_service.list_models()

        # Transform the response to match our schema
        model_list = []
        for model in models:
            model_info = ModelInfo(
                id=model.get("id", ""),
                name=model.get("name", model.get("id", "")),
                description=model.get("description"),
                pricing=model.get("pricing"),
                context_length=model.get("context_length")
            )
            model_list.append(model_info)

        return ModelsListResponse(
            models=model_list,
            total=len(model_list)
        )

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service configuration error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )