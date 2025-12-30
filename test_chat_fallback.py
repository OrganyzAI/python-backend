#!/usr/bin/env python3
"""
Test script to demonstrate fallback from OpenRouter to Ollama.

This script will test the chat completion endpoint and show how it falls back
to Ollama when OpenRouter is unavailable.
"""

import asyncio
import httpx
import json
import sys


async def login(base_url: str, email: str, password: str) -> str:
    """Login and get access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return data["data"]["access_token"]
        else:
            print(f"Login failed: {response.text}")
            return None


async def test_chat_completion(base_url: str, token: str, force_ollama: bool = False):
    """Test chat completion with fallback."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # If force_ollama is True, use an invalid OpenRouter model to trigger fallback
    model = "invalid/model" if force_ollama else "openai/gpt-3.5-turbo"

    payload = {
        "messages": [
            {"role": "user", "content": "Say 'Hello from AI!' in exactly 5 words"}
        ],
        "model": model,
        "temperature": 0.7,
        "max_tokens": 50
    }

    print(f"\n{'='*50}")
    print(f"Testing with model: {model}")
    print(f"Force Ollama: {force_ollama}")
    print(f"{'='*50}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{base_url}/api/v1/chat/completions",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                print("\n✅ Success! Response:")
                print(f"Model used: {data.get('model', 'unknown')}")
                print(f"Response: {data['choices'][0]['message']['content']}")
                print(f"Tokens used: {data.get('usage', {}).get('total_tokens', 'N/A')}")
            else:
                print(f"\n❌ Error {response.status_code}: {response.text}")

        except Exception as e:
            print(f"\n❌ Exception: {e}")


async def check_ollama_status(base_url: str = "http://localhost:11434"):
    """Check if Ollama is running."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print(f"\n✅ Ollama is running")
                if models:
                    print(f"Available models: {', '.join([m.get('name', '') for m in models])}")
                else:
                    print("No models installed yet")
                return True
            else:
                print(f"\n❌ Ollama responded with status {response.status_code}")
                return False
    except Exception as e:
        print(f"\n❌ Ollama is not available: {e}")
        return False


async def main():
    base_url = "http://localhost:8000"
    email = "test@example.com"
    password = "Test@12345"

    print("Chat Completion Fallback Test")
    print("=" * 50)

    # Check Ollama status
    print("\nChecking Ollama status...")
    ollama_available = await check_ollama_status()

    # Login
    print("\nLogging in...")
    token = await login(base_url, email, password)
    if not token:
        print("Failed to login. Make sure the user exists and is active.")
        sys.exit(1)

    print("✅ Login successful!")

    # Test 1: Normal OpenRouter call
    print("\n\nTest 1: Normal OpenRouter/OpenAI call")
    await test_chat_completion(base_url, token, force_ollama=False)

    if ollama_available:
        # Test 2: Force Ollama fallback by using invalid model
        print("\n\nTest 2: Force Ollama fallback (simulated OpenRouter failure)")
        await test_chat_completion(base_url, token, force_ollama=True)
    else:
        print("\n\n⚠️  Skipping Ollama fallback test - Ollama is not available")
        print("To test fallback, ensure Ollama is running:")
        print("  docker run -d -p 11434:11434 --name ollama ollama/ollama")
        print("  docker exec ollama ollama pull llama3.2:1b")


if __name__ == "__main__":
    asyncio.run(main())