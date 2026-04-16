import yaml
import litellm
from config import settings


def _load_model_config():
    """Load model configuration from config.yaml."""
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f) or {}

    model_config = config.get("model_provider", {})
    model = model_config.get("active", "gemini-pro")
    ollama_endpoint = model_config.get("ollama_endpoint", "http://localhost:11434")

    if "ollama" in model or "gemma" in model:
        # Local Ollama/Gemma model endpoint
        litellm.api_base = ollama_endpoint
        litellm.api_key = None
    else:
        # Use Google API key for Gemini or other cloud providers
        litellm.api_key = settings.google_api_key

    return model


def _build_agent_prompt(recommendations, nudges, playlist_context=None):
    """Construct a reasoning prompt for the agent."""
    prompt_lines = [
        "You are FIGMENT, a personal agent assistant for Disney park navigation and Spotify playlist curation.",
        "Analyze the current park recommendations, nudges, and playlist context, then suggest the next best action.",
        "Provide the response in short, actionable steps, with a strong recommendation for the highest-priority ride.",
        "",
        "Current Recommendations:"
    ]

    if recommendations:
        for idx, rec in enumerate(recommendations, 1):
            prompt_lines.append(
                f"{idx}. {rec['name']} - wait {rec['wait_time']} min, score {rec['score']:.1f}, status {rec.get('status', 'Unknown')}"
            )
    else:
        prompt_lines.append("No current recommendations available.")

    prompt_lines.append("")
    prompt_lines.append("Nudges:")
    if nudges:
        for nudge in nudges:
            prompt_lines.append(f"- {nudge['type']}: {nudge['ride']} ({nudge.get('wait_time', 'N/A')} min)")
    else:
        prompt_lines.append("- No active nudges at this time.")

    if playlist_context:
        prompt_lines.append("")
        prompt_lines.append("Spotify Playlist Context:")
        prompt_lines.append(playlist_context)

    prompt_lines.append("")
    prompt_lines.append(
        "Use the recommendation score and current nudges to decide whether the user should ride something now, take a Lightning Lane if available, or wait for a better opportunity."
    )
    prompt_lines.append(
        "If a must-do ride has a strong nudge, prioritize that ride over lower scoring attractions."
    )

    return "\n".join(prompt_lines)


def get_llm_response(prompt: str) -> str:
    """Send a prompt to the configured LLM and return the response."""
    try:
        model = _load_model_config()

        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
        )

        return getattr(response.choices[0].message, "content", str(response))
    except Exception as e:
        # Fallback if LLM isn't available
        print(f"LLM call failed ({e}), returning heuristic guidance")
        return "LLM orchestration unavailable - prioritize the highest-scored recommendation based on current wait times vs. distance."


def get_agent_insight(recommendations, nudges, playlist_context=None):
    """Get an orchestrated agent response from the LLM."""
    prompt = _build_agent_prompt(recommendations, nudges, playlist_context)
    return get_llm_response(prompt)
