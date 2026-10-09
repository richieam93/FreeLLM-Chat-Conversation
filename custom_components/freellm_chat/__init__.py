"""FreeLLM Chat integration setup."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_LLM_HASS_API, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm

from .api import LLM7Client, LLM7Error
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    AUTO_FALLBACK_MODEL,
    CONF_ACCEPT_DISCLAIMER,
    CONF_API_KEY,
    CONF_OVH_API_KEY,
    CONF_PROVIDER,
    CONF_AUTO_UPDATE_MODELS,
    CONF_CHAT_MODEL,
    CONF_DEVICE_QUERY_MAX_RESULTS,
    CONF_ENABLE_DEVICE_CONTROL,
    CONF_ENABLE_EXTENDED_DEVICE_QUERIES,
    CONF_ENABLE_STREAMING,
    CONF_ENABLE_VISION,
    CONF_FALLBACK_MODEL,
    CONF_HISTORY_LIMIT,
    CONF_MAX_TOKENS,
    CONF_MAX_TOOL_ITERATIONS,
    CONF_MODEL_REFRESH_INTERVAL,
    CONF_ONLY_FREE_MODELS,
    CONF_PROMPT,
    CONF_REFERENCE_REQUEST_LIMIT_HOUR,
    CONF_REFERENCE_REQUEST_LIMIT_MINUTE,
    CONF_REFERENCE_REQUEST_LIMIT_SECOND,
    CONF_REFERENCE_TOKEN_LIMIT_24H,
    CONF_RETRY_COUNT,
    CONF_TEMPERATURE,
    CONF_TIMEOUT,
    CONF_TOKEN_SAVING_MODE,
    DEFAULT_AUTO_UPDATE_MODELS,
    DEFAULT_DEVICE_QUERY_MAX_RESULTS,
    DEFAULT_CHAT_MODEL,
    DEFAULT_ENABLE_DEVICE_CONTROL,
    DEFAULT_ENABLE_EXTENDED_DEVICE_QUERIES,
    DEFAULT_ENABLE_STREAMING,
    DEFAULT_ENABLE_VISION,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_TOOL_ITERATIONS,
    DEFAULT_MODEL_REFRESH_INTERVAL,
    DEFAULT_ONLY_FREE_MODELS,
    DEFAULT_PROMPT,
    DEFAULT_REFERENCE_LIMIT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT,
    DEFAULT_TOKEN_SAVING_MODE,
    DOMAIN,
    SERVICE_REFRESH_MODELS,
    SERVICE_RESET_USAGE_STATISTICS,
    SERVICE_SELECT_DEFAULT_MODEL,
)
from .model_manager import ModelManager
from .provider import DEFAULT_PROVIDER, PROVIDER_OVHCLOUD, normalize_provider
from .runtime import FreeLLMConfigEntry, FreeLLMRuntimeData
from .usage_manager import UsageManager

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [
    Platform.CONVERSATION,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SENSOR,
]
CONFIG_VERSION = 7


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration domain and automation services."""
    async def refresh_models(call: ServiceCall) -> None:
        manager = _get_model_manager_for_service(hass, call)
        try:
            await manager.async_refresh(force=True)
        except LLM7Error as err:
            raise HomeAssistantError(str(err)) from err

    async def select_default_model(call: ServiceCall) -> None:
        manager = _get_model_manager_for_service(hass, call)
        try:
            await manager.async_select_default_model()
        except LLM7Error as err:
            raise HomeAssistantError(str(err)) from err

    async def reset_usage_statistics(call: ServiceCall) -> None:
        usage_manager = _get_usage_manager_for_service(hass, call)
        await usage_manager.async_reset()

    service_schema = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): str})
    services = (
        (SERVICE_REFRESH_MODELS, refresh_models),
        (SERVICE_SELECT_DEFAULT_MODEL, select_default_model),
        (SERVICE_RESET_USAGE_STATISTICS, reset_usage_statistics),
    )
    for service_name, handler in services:
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name,
                handler,
                schema=service_schema,
            )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FreeLLMConfigEntry) -> bool:
    """Set up FreeLLM Chat from a config entry."""
    _ensure_default_control_api(hass, entry)

    provider = normalize_provider(entry.data.get(CONF_PROVIDER))
    api_key = (
        entry.data.get(CONF_OVH_API_KEY)
        if provider == PROVIDER_OVHCLOUD
        else entry.data.get(CONF_API_KEY)
    )
    client = LLM7Client(hass, api_key, provider=provider)
    model_manager = ModelManager(hass, entry, client)
    usage_manager = UsageManager(hass, entry, client)
    await model_manager.async_initialize()
    await usage_manager.async_initialize()

    entry.runtime_data = FreeLLMRuntimeData(
        client=client,
        model_manager=model_manager,
        usage_manager=usage_manager,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FreeLLMConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unloaded:
        return False

    await entry.runtime_data.model_manager.async_shutdown()
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: FreeLLMConfigEntry) -> bool:
    """Migrate legacy configuration to the current streamlined version."""
    if entry.version > CONFIG_VERSION:
        _LOGGER.error(
            "Cannot migrate FreeLLM Chat entry from unsupported version %s",
            entry.version,
        )
        return False
    if entry.version == CONFIG_VERSION:
        return True

    old_version = entry.version
    old = dict(entry.options)
    new_options: dict[str, Any] = {
        CONF_CHAT_MODEL: old.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL),
        CONF_FALLBACK_MODEL: old.get(
            CONF_FALLBACK_MODEL, AUTO_FALLBACK_MODEL
        ),
        CONF_PROMPT: old.get(CONF_PROMPT, DEFAULT_PROMPT),
        CONF_TEMPERATURE: old.get(
            CONF_TEMPERATURE,
            old.get("chat_temperature", DEFAULT_TEMPERATURE),
        ),
        CONF_MAX_TOKENS: old.get(
            CONF_MAX_TOKENS,
            old.get("chat_max_tokens", DEFAULT_MAX_TOKENS),
        ),
        CONF_TIMEOUT: old.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        CONF_RETRY_COUNT: old.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT),
        CONF_HISTORY_LIMIT: old.get(CONF_HISTORY_LIMIT, DEFAULT_HISTORY_LIMIT),
        CONF_MAX_TOOL_ITERATIONS: old.get(
            CONF_MAX_TOOL_ITERATIONS, DEFAULT_MAX_TOOL_ITERATIONS
        ),
        CONF_ENABLE_STREAMING: old.get(
            CONF_ENABLE_STREAMING, DEFAULT_ENABLE_STREAMING
        ),
        CONF_ENABLE_VISION: old.get(CONF_ENABLE_VISION, DEFAULT_ENABLE_VISION),
        CONF_ENABLE_DEVICE_CONTROL: old.get(
            CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
        ),
        CONF_TOKEN_SAVING_MODE: old.get(
            CONF_TOKEN_SAVING_MODE, DEFAULT_TOKEN_SAVING_MODE
        ),
        CONF_ENABLE_EXTENDED_DEVICE_QUERIES: old.get(
            CONF_ENABLE_EXTENDED_DEVICE_QUERIES,
            DEFAULT_ENABLE_EXTENDED_DEVICE_QUERIES,
        ),
        CONF_DEVICE_QUERY_MAX_RESULTS: old.get(
            CONF_DEVICE_QUERY_MAX_RESULTS, DEFAULT_DEVICE_QUERY_MAX_RESULTS
        ),
        CONF_AUTO_UPDATE_MODELS: old.get(
            CONF_AUTO_UPDATE_MODELS, DEFAULT_AUTO_UPDATE_MODELS
        ),
        CONF_MODEL_REFRESH_INTERVAL: old.get(
            CONF_MODEL_REFRESH_INTERVAL, DEFAULT_MODEL_REFRESH_INTERVAL
        ),
        CONF_ONLY_FREE_MODELS: old.get(
            CONF_ONLY_FREE_MODELS, DEFAULT_ONLY_FREE_MODELS
        ),
        CONF_REFERENCE_TOKEN_LIMIT_24H: old.get(
            CONF_REFERENCE_TOKEN_LIMIT_24H, DEFAULT_REFERENCE_LIMIT
        ),
        CONF_REFERENCE_REQUEST_LIMIT_HOUR: old.get(
            CONF_REFERENCE_REQUEST_LIMIT_HOUR, DEFAULT_REFERENCE_LIMIT
        ),
        CONF_REFERENCE_REQUEST_LIMIT_MINUTE: old.get(
            CONF_REFERENCE_REQUEST_LIMIT_MINUTE, DEFAULT_REFERENCE_LIMIT
        ),
        CONF_REFERENCE_REQUEST_LIMIT_SECOND: old.get(
            CONF_REFERENCE_REQUEST_LIMIT_SECOND, DEFAULT_REFERENCE_LIMIT
        ),
    }

    selected_api = old.get(CONF_LLM_HASS_API)
    if selected_api:
        new_options[CONF_LLM_HASS_API] = selected_api
    elif new_options[CONF_ENABLE_DEVICE_CONTROL] and (
        default_api := _default_llm_api(hass)
    ):
        new_options[CONF_LLM_HASS_API] = [default_api]

    new_data = {
        CONF_PROVIDER: normalize_provider(entry.data.get(CONF_PROVIDER, DEFAULT_PROVIDER)),
        CONF_API_KEY: entry.data.get(CONF_API_KEY, ""),
        CONF_OVH_API_KEY: entry.data.get(CONF_OVH_API_KEY, ""),
    }
    if entry.data.get(CONF_ACCEPT_DISCLAIMER) is True:
        new_data[CONF_ACCEPT_DISCLAIMER] = True

    hass.config_entries.async_update_entry(
        entry,
        data=new_data,
        options=new_options,
        version=CONFIG_VERSION,
    )
    _LOGGER.info(
        "Migrated FreeLLM Chat config entry from version %s to %s",
        old_version,
        CONFIG_VERSION,
    )
    return True


def _ensure_default_control_api(hass: HomeAssistant, entry: FreeLLMConfigEntry) -> None:
    """Keep device control working for migrated entries."""
    if not entry.options.get(
        CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
    ) or entry.options.get(CONF_LLM_HASS_API):
        return
    if not (default_api := _default_llm_api(hass)):
        return

    options = dict(entry.options)
    options[CONF_LLM_HASS_API] = [default_api]
    hass.config_entries.async_update_entry(entry, options=options)


def _default_llm_api(hass: HomeAssistant) -> str | None:
    """Return Assist, or the first registered Home Assistant LLM API."""
    apis = llm.async_get_apis(hass)
    for api in apis:
        if "assist" in f"{api.id} {api.name}".casefold():
            return api.id
    return apis[0].id if apis else None


def _get_model_manager_for_service(
    hass: HomeAssistant, call: ServiceCall
) -> ModelManager:
    """Resolve a model manager for a domain service call."""
    return _get_runtime_manager(hass, call, "model_manager")


def _get_usage_manager_for_service(
    hass: HomeAssistant, call: ServiceCall
) -> UsageManager:
    """Resolve a usage manager for a domain service call."""
    return _get_runtime_manager(hass, call, "usage_manager")


def _get_runtime_manager(
    hass: HomeAssistant, call: ServiceCall, attribute: str
) -> Any:
    """Resolve one runtime manager and require an entry id when ambiguous."""
    loaded_entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
        and getattr(entry, "runtime_data", None) is not None
    ]
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id:
        entry = next(
            (candidate for candidate in loaded_entries if candidate.entry_id == entry_id),
            None,
        )
        if entry is not None:
            return getattr(entry.runtime_data, attribute)
        raise HomeAssistantError(
            f"Keine geladene FreeLLM-Konfiguration mit ID {entry_id} gefunden."
        )

    if len(loaded_entries) == 1:
        return getattr(loaded_entries[0].runtime_data, attribute)
    if len(loaded_entries) > 1:
        raise HomeAssistantError(
            "Mehrere FreeLLM-Konfigurationen sind geladen. "
            "Bitte config_entry_id angeben."
        )
    raise HomeAssistantError("FreeLLM Chat ist nicht geladen.")
