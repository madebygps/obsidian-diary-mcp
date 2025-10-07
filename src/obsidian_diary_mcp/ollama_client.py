"""Ollama API client for text generation."""

import httpx
from .config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_TEMPERATURE, OLLAMA_NUM_PREDICT
from .logger import ollama_logger as logger, log_section


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self):
        self.url = OLLAMA_URL
        self.model = OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT
    
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate text using Ollama API."""
        log_section(logger, "Ollama API Call")
        logger.debug(f"Endpoint: {self.url}/api/generate")
        logger.debug(f"Model: {self.model} | Timeout: {self.timeout}s | Temp: {OLLAMA_TEMPERATURE}")
        logger.debug(f"Prompt size: system={len(system_prompt)} chars, user={len(prompt):,} chars")
        
        async with httpx.AsyncClient() as client:
            try:
                logger.info("Sending request to Ollama...")
                response = await client.post(
                    f"{self.url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"{system_prompt}\n\n{prompt}",
                        "stream": False,
                        "options": {
                            "temperature": OLLAMA_TEMPERATURE,
                            "num_predict": OLLAMA_NUM_PREDICT,
                        }
                    },
                    timeout=self.timeout
                )
                logger.debug(f"Response status: {response.status_code}")
                response.raise_for_status()
                result = response.json()
                response_text = result.get("response", "")
                logger.info(f"✓ Received {len(response_text):,} chars from Ollama")
                return response_text
            except httpx.TimeoutException as e:
                logger.error(f"Timeout after {self.timeout}s: {e}")
                raise
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e}")
                raise
            except Exception as e:
                logger.error(f"Request failed ({type(e).__name__}): {e}")
                raise
    
    def test_connection(self) -> bool:
        """Test if Ollama is available."""
        try:
            httpx.get(f"{self.url}/api/tags", timeout=2)
            return True
        except Exception:
            return False


ollama_client = OllamaClient()


def initialize_ollama():
    """Initialize and test Ollama connection."""
    if ollama_client.test_connection():
        logger.info(f"✓ Ollama connected: {OLLAMA_URL} | Model: {OLLAMA_MODEL}")
    else:
        logger.warning(f"Ollama not available at {OLLAMA_URL}")
        logger.warning("Install Ollama and run: ollama pull llama3.1")