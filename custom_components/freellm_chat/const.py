"""Constants for the freellm_chat Conversation integration."""

DOMAIN = "freellm_chat"
CONF_CHAT_MODEL = "chat_model"
DEFAULT_CHAT_MODEL = "gpt-4o-mini-2024-07-18"  # Standardmodell für LLM7.io
CONF_PROMPT = "prompt"
DEFAULT_PROMPT = """You are a helpful and smart assistant. 
You accurately provide answers to the provided user query.
You must speak in the user's language unless they ask you to speak in another one."""
LLM7_BASE_URL = "https://api.llm7.io/v1"  # LLM7.io Basis-URL