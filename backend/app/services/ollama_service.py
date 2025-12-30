import httpx
from typing import Any, Dict, List, Optional
import logging
import json

logger = logging.getLogger(__name__)


class OllamaService:
    """Service for interacting with local Ollama API for LLM inference."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.default_model = "llama3.2:1b"  # Lightweight 1B parameter model

    async def ensure_model_exists(self, model: str) -> bool:
        """
        Check if a model exists, and pull it if it doesn't.

        Args:
            model: The model name to check/pull

        Returns:
            True if model is available, False otherwise
        """
        try:
            # Check if model exists
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]

                    if model in model_names:
                        return True

                    # Model doesn't exist, try to pull it
                    logger.info(f"Model {model} not found, attempting to pull...")
                    pull_response = await client.post(
                        f"{self.base_url}/api/pull",
                        json={"name": model},
                        timeout=300.0  # 5 minutes timeout for pulling
                    )

                    if pull_response.status_code == 200:
                        logger.info(f"Successfully pulled model {model}")
                        return True
                    else:
                        logger.error(f"Failed to pull model {model}: {pull_response.text}")
                        return False

        except Exception as e:
            logger.error(f"Error checking/pulling model {model}: {e}")
            return False

    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Create a chat completion using Ollama API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: The model to use (default: llama3.2:1b)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response

        Returns:
            The chat completion response formatted like OpenAI's response
        """

        model_to_use = model or self.default_model

        # Ensure the model exists
        model_available = await self.ensure_model_exists(model_to_use)
        if not model_available:
            # Fall back to the default model
            logger.warning(f"Model {model_to_use} not available, falling back to {self.default_model}")
            model_to_use = self.default_model
            model_available = await self.ensure_model_exists(model_to_use)
            if not model_available:
                raise Exception(f"Failed to load fallback model {self.default_model}")

        # Convert messages to Ollama format
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt += f"System: {content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"

        prompt += "Assistant: "

        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "temperature": temperature,
            "stream": stream
        }

        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=60.0
                )

                if response.status_code != 200:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    raise Exception(f"Ollama API error: {response.status_code}")

                ollama_response = response.json()

                # Convert Ollama response to OpenAI format
                return {
                    "id": f"ollama-{model_to_use}-response",
                    "object": "chat.completion",
                    "created": int(httpx.AsyncClient().headers.get("date", "0")),
                    "model": f"ollama/{model_to_use}",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": ollama_response.get("response", "")
                            },
                            "finish_reason": "stop" if ollama_response.get("done", False) else "length"
                        }
                    ],
                    "usage": {
                        "prompt_tokens": ollama_response.get("prompt_eval_count", 0),
                        "completion_tokens": ollama_response.get("eval_count", 0),
                        "total_tokens": ollama_response.get("prompt_eval_count", 0) + ollama_response.get("eval_count", 0)
                    }
                }

        except httpx.TimeoutException:
            logger.error("Ollama API request timed out")
            raise Exception("Ollama chat completion request timed out")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise Exception(f"Failed to get Ollama chat completion: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Ollama chat completion: {e}")
            raise

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models from Ollama.

        Returns:
            List of available models
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=10.0
                )

                if response.status_code != 200:
                    raise Exception(f"Failed to list Ollama models: {response.status_code}")

                data = response.json()
                models = data.get("models", [])

                # Format the response
                formatted_models = []
                for model in models:
                    formatted_models.append({
                        "id": f"ollama/{model.get('name', '')}",
                        "name": model.get("name", ""),
                        "size": model.get("size", 0),
                        "modified": model.get("modified_at", "")
                    })

                return formatted_models

        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            raise Exception(f"Failed to list Ollama models: {str(e)}")

    async def is_available(self) -> bool:
        """
        Check if Ollama service is available.

        Returns:
            True if Ollama is reachable, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=2.0
                )
                return response.status_code == 200
        except:
            return False


ollama_service = OllamaService()