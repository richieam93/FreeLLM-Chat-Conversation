"""Diagnostics support for FreeLLM Chat."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import (
    CONF_API_KEY,
    CONF_OVH_API_KEY,
    CONF_PROVIDER,
    CONF_DEVICE_QUERY_MAX_RESULTS,
    CONF_ENABLE_EXTENDED_DEVICE_QUERIES,
    CONF_PROMPT,
    CONF_TOKEN_SAVING_MODE,
    DEFAULT_DEVICE_QUERY_MAX_RESULTS,
    DEFAULT_ENABLE_EXTENDED_DEVICE_QUERIES,
    DEFAULT_TOKEN_SAVING_MODE,
)
from .runtime import FreeLLMConfigEntry
from .model_manager import (
    model_is_token_free,
    model_supports_streaming,
    model_supports_tools,
    model_supports_vision,
)

TO_REDACT = {CONF_API_KEY, CONF_OVH_API_KEY, CONF_PROMPT}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FreeLLMConfigEntry
) -> dict[str, Any]:
    """Return safe diagnostics for a config entry."""
    runtime = entry.runtime_data
    manager = runtime.model_manager
    usage = runtime.usage_manager
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
            "version": entry.version,
            "minor_version": entry.minor_version,
        },
        "provider": {
            "id": runtime.client.provider,
            "name": runtime.client.provider_name,
            "access_mode": usage.access_mode,
            "website": runtime.client.website_url,
            "documentation": runtime.client.docs_url,
        },
        "catalog": {
            "status": manager.status,
            "source": manager.catalog_source,
            "count": len(manager.models),
            "last_update": (
                manager.last_update.isoformat() if manager.last_update else None
            ),
            "last_attempt": (
                manager.last_attempt.isoformat() if manager.last_attempt else None
            ),
            "last_error": manager.last_error,
            "cache_is_stale": manager.cache_is_stale,
            "last_fallback_from": manager.last_fallback_from,
            "last_fallback_at": (
                manager.last_fallback_at.isoformat()
                if manager.last_fallback_at
                else None
            ),
        },
        "usage": {
            "access_mode": usage.access_mode,
            "total_conversations": usage.total_conversations,
            "total_api_requests": usage.total_api_requests,
            "successful_api_requests": usage.successful_api_requests,
            "failed_api_requests": usage.failed_api_requests,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
            "requests_24h": usage.requests_24h,
            "requests_hour": usage.requests_hour,
            "requests_minute": usage.requests_minute,
            "requests_second": usage.requests_second,
            "tokens_24h": usage.tokens_24h,
            "success_rate_24h": usage.success_rate_24h,
            "average_latency_24h": usage.average_latency_24h,
            "p95_latency_24h": usage.p95_latency_24h,
            "quota_status": usage.quota_status,
            "quota_usage_percent": usage.quota_usage_percent,
            "request_hour_usage_percent": usage.request_hour_usage_percent,
            "request_minute_usage_percent": usage.request_minute_usage_percent,
            "request_second_usage_percent": usage.request_second_usage_percent,
            "highest_reference_usage_percent": (
                usage.highest_reference_usage_percent
            ),
            "limiting_metric": usage.limiting_metric,
            "last_request_at": (
                usage.last_request_at.isoformat()
                if usage.last_request_at
                else None
            ),
            "last_model": usage.last_model,
            "last_provider_model": usage.last_provider_model,
            "last_latency_ms": usage.last_latency_ms,
            "last_status": usage.last_status,
            "last_error": usage.last_error,
            "last_input_tokens": usage.last_input_tokens,
            "last_output_tokens": usage.last_output_tokens,
            "last_total_tokens": usage.last_total_tokens,
            "last_payload_chars": usage.last_payload_chars,
            "last_estimated_input_tokens": usage.last_estimated_input_tokens,
            "last_message_count": usage.last_message_count,
            "last_tool_count": usage.last_tool_count,
            "last_context_mode": usage.last_context_mode,
            "local_statistics_only": True,
        },
        "capabilities": {
            "token_saving_mode": entry.options.get(
                CONF_TOKEN_SAVING_MODE, DEFAULT_TOKEN_SAVING_MODE
            ),
            "extended_device_queries": entry.options.get(
                CONF_ENABLE_EXTENDED_DEVICE_QUERIES,
                DEFAULT_ENABLE_EXTENDED_DEVICE_QUERIES,
            ),
            "device_query_max_results": entry.options.get(
                CONF_DEVICE_QUERY_MAX_RESULTS, DEFAULT_DEVICE_QUERY_MAX_RESULTS
            ),
            "token_free_models": sum(
                model_is_token_free(model) for model in manager.models
            ),
            "tool_models": sum(
                model_supports_tools(model) for model in manager.models
            ),
            "vision_models": sum(
                model_supports_vision(model) for model in manager.models
            ),
            "streaming_models": sum(
                model_supports_streaming(model) for model in manager.models
            ),
        },
        "models": [
            {
                "id": model["id"],
                "token_free": model_is_token_free(model),
                "tools": model_supports_tools(model),
                "vision": model_supports_vision(model),
                "streaming": model_supports_streaming(model),
                "reasoning": bool(model.get("reasoning")),
                "json_mode": bool(model.get("json_mode")),
                "tier": model.get("tier"),
                "owned_by": model.get("owned_by"),
                "context_window": model.get("context_window"),
            }
            for model in manager.models
        ],
    }
