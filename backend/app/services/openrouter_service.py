import httpx
from typing import Any, Dict, List, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenRouterService:
    """Service for interacting with OpenRouter API to access OpenAI models."""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = str(settings.OPENROUTER_BASE_URL)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Full Stack FastAPI Project",
            "Content-Type": "application/json"
        }

    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Create a chat completion using OpenRouter API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: The model to use (default: gpt-3.5-turbo)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response

        Returns:
            The chat completion response from OpenRouter
        """

        if not self.api_key:
            raise ValueError("OpenRouter API key is not configured")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code != 200:
                    logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                    response.raise_for_status()

                return response.json()

        except httpx.TimeoutException:
            logger.error("OpenRouter API request timed out")
            raise Exception("Chat completion request timed out")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise Exception(f"Failed to get chat completion: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in chat completion: {e}")
            raise Exception(f"An error occurred during chat completion: {str(e)}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models from OpenRouter.

        Returns:
            List of available models
        """

        if not self.api_key:
            raise ValueError("OpenRouter API key is not configured")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self.headers,
                    timeout=10.0
                )

                if response.status_code != 200:
                    response.raise_for_status()

                data = response.json()
                return data.get("data", [])

        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise Exception(f"Failed to list available models: {str(e)}")


openrouter_service = OpenRouterService()