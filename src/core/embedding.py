import ollama
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Ollama host from environment, default to localhost if not set
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Initialize Ollama asynchronous client
# Use AsyncClient for methods that will be awaited
client = ollama.AsyncClient(host=OLLAMA_HOST)

async def get_ollama_embedding(text: str, model_name: str = "nomic-embed-text") -> list[float] | None:
    """
    Generates a vector embedding for the given text using an Ollama embedding model.

    Args:
        text (str): The input text to embed.
        model_name (str): The name of the Ollama embedding model to use (e.g., "nomic-embed-text").

    Returns:
        list[float] | None: A list of floats representing the embedding, or None if an error occurs.
    """
    if not text:
        print("Warning: Attempted to get embedding for empty text.")
        return None
    try:
        # Call Ollama's embedding endpoint using the async client
        response = await client.embeddings(model=model_name, prompt=text)
        return response['embedding']
    except Exception as e:
        print(f"Error getting embedding from Ollama ({model_name}): {e}")
        print(f"Ensure Ollama server is running at {OLLAMA_HOST} and model '{model_name}' is pulled.")
        return None

# Example of how to use it (for testing purposes, can be removed later)
if __name__ == "__main__":
    import asyncio

    async def test_embedding():
        test_text = "This is a test sentence for embedding."
        print(f"Attempting to generate embedding for: '{test_text}'")
        embedding = await get_ollama_embedding(test_text)
        if embedding:
            print(f"Embedding generated (first 5 values): {embedding[:5]}...")
            print(f"Embedding dimension: {len(embedding)}")
        else:
            print("Failed to generate embedding.")
            print("Please ensure Ollama is running and 'nomic-embed-text' is pulled.")

    asyncio.run(test_embedding())
