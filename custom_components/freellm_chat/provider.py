"""Provider metadata for FreeLLM Chat."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

PROVIDER_LLM7 = "llm7"
PROVIDER_OVHCLOUD = "ovhcloud"
DEFAULT_PROVIDER = PROVIDER_LLM7

LLM7_BASE_URL = "https://api.llm7.io/v1"
LLM7_MODELS_URL = f"{LLM7_BASE_URL}/models"
LLM7_CHAT_URL = f"{LLM7_BASE_URL}/chat/completions"
LLM7_WEB_URL = "https://llm7.io"
LLM7_DASHBOARD_URL = "https://dash.llm7.io/"
LLM7_DOCS_URL = "https://llm7.io/"
LLM7_STATUS_URL = "https://status.llm7.io/"

OVHCLOUD_BASE_URL = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
OVHCLOUD_CHAT_URL = f"{OVHCLOUD_BASE_URL}/chat/completions"
OVHCLOUD_WEB_URL = "https://www.ovhcloud.com/en/public-cloud/ai-endpoints/"
OVHCLOUD_DASHBOARD_URL = "https://www.ovh.com/manager/"
OVHCLOUD_DOCS_URL = (
    "https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/"
    "ai-endpoints-getting-started"
)
OVHCLOUD_STATUS_URL = "https://www.status-ovhcloud.com/"

# OVHcloud does not currently document a stable OpenAI /v1/models discovery
# endpoint for AI Endpoints. Keep the built-in catalog deliberately small and
# limited to models whose current public catalog explicitly advertises function
# calling + streaming. The user can therefore rely on deterministic behavior.
_OVHCLOUD_MODELS: list[dict[str, Any]] = [
    {
        "id": "gpt-oss-20b",
        "owned_by": "OVHcloud",
        "tier": "anonymous-or-authenticated",
        "usage_based_only": False,
        "model_type": "chat",
        "schema_endpoints": ["openai"],
        "stream": True,
        "json_mode": True,
        "reasoning": True,
        "tools_calling": True,
        "modalities": {"input": ["text"], "output": ["text"]},
        "context_window": {"tokens": 131000},
        "capabilities": {
            "stream": True,
            "json_mode": True,
            "reasoning": True,
            "tools": True,
        },
    },
    {
        "id": "gpt-oss-120b",
        "owned_by": "OVHcloud",
        "tier": "anonymous-or-authenticated",
        "usage_based_only": False,
        "model_type": "chat",
        "schema_endpoints": ["openai"],
        "stream": True,
        "json_mode": True,
        "reasoning": True,
        "tools_calling": True,
        "modalities": {"input": ["text"], "output": ["text"]},
        "context_window": {"tokens": 131000},
        "capabilities": {
            "stream": True,
            "json_mode": True,
            "reasoning": True,
            "tools": True,
        },
    },
]


def normalize_provider(value: object) -> str:
    """Return a supported provider identifier."""
    return value if value in {PROVIDER_LLM7, PROVIDER_OVHCLOUD} else DEFAULT_PROVIDER


def provider_name(provider: str) -> str:
    """Return a human-friendly provider name."""
    return "OVHcloud AI Endpoints" if provider == PROVIDER_OVHCLOUD else "LLM7.io"


def provider_web_url(provider: str) -> str:
    return OVHCLOUD_WEB_URL if provider == PROVIDER_OVHCLOUD else LLM7_WEB_URL


def provider_dashboard_url(provider: str) -> str:
    return (
        OVHCLOUD_DASHBOARD_URL
        if provider == PROVIDER_OVHCLOUD
        else LLM7_DASHBOARD_URL
    )


def provider_docs_url(provider: str) -> str:
    return OVHCLOUD_DOCS_URL if provider == PROVIDER_OVHCLOUD else LLM7_DOCS_URL


def provider_status_url(provider: str) -> str:
    return OVHCLOUD_STATUS_URL if provider == PROVIDER_OVHCLOUD else LLM7_STATUS_URL


def provider_chat_url(provider: str) -> str:
    return OVHCLOUD_CHAT_URL if provider == PROVIDER_OVHCLOUD else LLM7_CHAT_URL


def provider_models_url(provider: str) -> str | None:
    return None if provider == PROVIDER_OVHCLOUD else LLM7_MODELS_URL


def bundled_provider_models(provider: str) -> list[dict[str, Any]]:
    """Return provider-specific built-in models, if any."""
    return deepcopy(_OVHCLOUD_MODELS) if provider == PROVIDER_OVHCLOUD else []


def provider_reference_limits(provider: str, has_api_key: bool) -> dict[str, int]:
    """Return documented reference limits used only for local warning sensors.

    A value of 0 means that the provider does not publish that dimension as a
    generally applicable limit. These values never represent an account balance.
    """
    if provider == PROVIDER_OVHCLOUD:
        return {
            "tokens_24h": 0,
            "requests_hour": 0,
            "requests_minute": 400 if has_api_key else 2,
            "requests_second": 0,
        }
    return {
        "tokens_24h": 1_000_000 if has_api_key else 500_000,
        "requests_hour": 250 if has_api_key else 60,
        "requests_minute": 60 if has_api_key else 10,
        "requests_second": 2 if has_api_key else 1,
    }


def provider_min_chat_interval(provider: str, has_api_key: bool) -> float:
    """Return a conservative request spacing based on published provider limits."""
    if provider == PROVIDER_OVHCLOUD:
        # 2 req/min anonymously, 400 req/min authenticated, per model.
        return 0.17 if has_api_key else 30.5
    return 0.55 if has_api_key else 1.05
