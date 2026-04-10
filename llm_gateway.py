import yaml
import litellm
from config import settings

# Set the API key for Gemini
litellm.api_key = settings.google_api_key

def get_llm_response(prompt: str) -> str:
    """
    Sends a prompt to the configured LLM and returns the response.

    Reads the active model from config.yaml and uses litellm to handle
    the API call, supporting both cloud and local models.
    """
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    model_config = config.get("model_provider", {})
    model = model_config.get("active", "gemini-pro")

    # Special configuration for local Ollama models
    if "ollama" in model:
        litellm.api_base = model_config.get("ollama_endpoint")

    response = litellm.completion(
        model=model, messages=[{"content": prompt, "role": "user"}]
    )
    return response.choices[0].message.content