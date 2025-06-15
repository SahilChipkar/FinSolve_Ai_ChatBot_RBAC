# src/core/llm.py

import os
import json # Import json for handling payload and response
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# We are no longer using Ollama_HOST or the ollama client for text generation
# For Gemini API, the API key will be implicitly provided by the Canvas environment if empty.

async def generate_llm_response(
    prompt: str,
    # The model_name parameter will still be accepted, but internally we'll use gemini-2.0-flash
    # You can keep it as a parameter if you intend to switch between Gemini models later.
    # For now, we hardcode gemini-2.0-flash as per request.
    model_name: str = "gemini-2.5-flash-preview-05-20", # Placeholder, internal API call will use this
    temperature: float = 0.7,
    max_tokens: int = 500
) -> str | None:
    """
    Generates a response from the Gemini API (gemini-2.0-flash).

    Args:
        prompt (str): The input prompt for the LLM.
        model_name (str): The specific Gemini model to use (e.g., "gemini-2.0-flash").
                          Note: For this implementation, it's fixed to "gemini-2.0-flash".
        temperature (float): Controls the randomness of the output (0.0 for deterministic).
        max_tokens (int): The maximum number of tokens to generate in the response.

    Returns:
        str | None: The generated text response, or None if an error occurs.
    """
    if not prompt:
        print("Warning: Attempted to generate response with empty prompt.")
        return None

    try:
        chatHistory = []
        chatHistory.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": chatHistory,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        # The API key should be an empty string. Canvas will inject it at runtime.
        apiKey = "AIzaSyD3iZpeLQo5cAxxC7UA59qNPpcdibaCePI" 
        apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={apiKey}"

        # Using a direct fetch call. In Python, this translates to requests or httpx.
        # Since this is an async function in a FastAPI context, we'll use httpx if available,
        # or simulate with requests for demonstration if httpx isn't preferred.
        # Given the Canvas environment, let's assume a direct `fetch` like behavior
        # is expected, but in a real Python app, you'd use `httpx`.
        # For demonstration purposes, I'll simulate the fetch structure with `requests` or `httpx`
        # as if it were making an HTTP call. Let's use `httpx` as it's async-native.

        import httpx # Import httpx for async http requests

        async with httpx.AsyncClient() as client:
            response = await client.post(
                apiUrl,
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=60.0 # Add a timeout for robustness
            )
            response.raise_for_status() # Raise an HTTPStatusError for bad responses (4xx or 5xx)
            result = response.json()

        if result.get("candidates") and len(result["candidates"]) > 0 and \
           result["candidates"][0].get("content") and \
           result["candidates"][0]["content"].get("parts") and \
           len(result["candidates"][0]["content"]["parts"]) > 0:
            return result["candidates"][0]["content"]["parts"][0].get("text")
        else:
            print("Gemini API response structure unexpected or content missing.")
            return None

    except httpx.HTTPStatusError as e:
        print(f"HTTP error generating response from Gemini API ({model_name}): {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e:
        print(f"Request error generating response from Gemini API ({model_name}): {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while generating response from Gemini API ({model_name}): {e}")
        return None

# Example of how to use it (for testing purposes)
if __name__ == "__main__":
    import asyncio

    async def test_generation():
        test_prompt = "What is the capital of France?"
        print(f"Attempting to generate response for: '{test_prompt}' using Gemini API")
        response_text = await generate_llm_response(test_prompt, model_name="gemini-2.0-flash")
        if response_text:
            print(f"Generated Response:\n{response_text}")
        else:
            print("Failed to generate response from Gemini API.")
            print("Please ensure your API key is correctly configured (though Canvas should inject it), and try again.")

    asyncio.run(test_generation())
