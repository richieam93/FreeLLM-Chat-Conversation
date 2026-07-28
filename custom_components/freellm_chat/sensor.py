"""Status and local usage sensors for FreeLLM Chat."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DATA_MODEL_MANAGER,
    DATA_USAGE_MANAGER,
    DOMAIN,
    LLM7_DASHBOARD_URL,
    LLM7_DOCS_URL,
    LLM7_STATUS_URL,
    LLM7_WEB_URL,
)
from .entity import service_device_info
from .model_manager import (
    model_is_token_free,
    model_supports_streaming,
    model_supports_tools,
    model_supports_vision,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up catalog and usage sensors."""
    async_add_entities(
        [
            CatalogStatusSensor(entry),
            AvailableModelsSensor(entry),
            ConversationRequestsSensor(entry),
            ApiRequestsSensor(entry),
            TokenUsageSensor(entry),
            QuotaStatusSensor(entry),
            LastApiRequestSensor(entry),
        ]
    )


class _ManagerSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, key: str) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = service_device_info(entry)


class _ModelManagerSensor(_ManagerSensor):
    @property
    def manager(self):
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_MODEL_MANAGER]

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class _UsageManagerSensor(_ManagerSensor):
    @property
    def usage(self):
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_USAGE_MANAGER]

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.usage.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class CatalogStatusSensor(_ModelManagerSensor):
    """Expose where the active model catalog came from."""

    _attr_translation_key = "catalog_status"
    _attr_icon = "mdi:database-sync"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["live", "cache", "stale_cache", "bundled"]

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "catalog_status")

    @property
    @override
    def native_value(self) -> str:
        return self.manager.status

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "last_update": self.manager.last_update,
            "last_attempt": self.manager.last_attempt,
            "last_error": self.manager.last_error,
            "cache_is_stale": self.manager.cache_is_stale,
            "last_fallback_from": self.manager.last_fallback_from,
            "last_fallback_at": self.manager.last_fallback_at,
            "provider_website": LLM7_WEB_URL,
            "api_key_dashboard": LLM7_DASHBOARD_URL,
            "documentation": LLM7_DOCS_URL,
            "service_status": LLM7_STATUS_URL,
        }


class AvailableModelsSensor(_ModelManagerSensor):
    """Expose the number and capability mix of available models."""

    _attr_translation_key = "available_models"
    _attr_icon = "mdi:format-list-numbered"
    _attr_native_unit_of_measurement = "models"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "available_models")

    @property
    @override
    def native_value(self) -> int:
        return len(self.manager.models)

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        models = self.manager.models
        return {
            "token_free": sum(model_is_token_free(model) for model in models),
            "with_tools": sum(model_supports_tools(model) for model in models),
            "with_vision": sum(model_supports_vision(model) for model in models),
            "with_streaming": sum(
                model_supports_streaming(model) for model in models
            ),
            "model_ids": [model["id"] for model in models],
            "provider_website": LLM7_WEB_URL,
            "api_key_dashboard": LLM7_DASHBOARD_URL,
        }


class ConversationRequestsSensor(_UsageManagerSensor):
    """Expose user conversation requests handled by this integration."""

    _attr_translation_key = "conversation_requests"
    _attr_icon = "mdi:message-text-outline"
    _attr_native_unit_of_measurement = "requests"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "conversation_requests")

    @property
    @override
    def native_value(self) -> int:
        return self.usage.total_conversations


class ApiRequestsSensor(_UsageManagerSensor):
    """Expose locally counted API requests, including retries and tool rounds."""

    _attr_translation_key = "api_requests"
    _attr_icon = "mdi:api"
    _attr_native_unit_of_measurement = "requests"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "api_requests")

    @property
    @override
    def native_value(self) -> int:
        return self.usage.total_api_requests

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "requests_24h": self.usage.requests_24h,
            "requests_hour": self.usage.requests_hour,
            "requests_minute": self.usage.requests_minute,
            "requests_second": self.usage.requests_second,
            "successful_total": self.usage.successful_api_requests,
            "failed_total": self.usage.failed_api_requests,
            "successful_24h": self.usage.successful_requests_24h,
            "failed_24h": self.usage.failed_requests_24h,
            "reference_limit_hour": self.usage.reference_request_limit_hour,
            "reference_limit_minute": self.usage.reference_request_limit_minute,
            "reference_limit_second": self.usage.reference_request_limit_second,
            "estimated_remaining_hour": (
                self.usage.estimated_requests_remaining_hour
            ),
            "estimated_remaining_minute": (
                self.usage.estimated_requests_remaining_minute
            ),
            "estimated_remaining_second": (
                self.usage.estimated_requests_remaining_second
            ),
            "hour_usage_percent": self.usage.request_hour_usage_percent,
            "minute_usage_percent": self.usage.request_minute_usage_percent,
            "second_usage_percent": self.usage.request_second_usage_percent,
            "access_mode": self.usage.access_mode,
            "local_statistics_only": True,
        }


class TokenUsageSensor(_UsageManagerSensor):
    """Expose token usage returned by successful API responses."""

    _attr_translation_key = "token_usage"
    _attr_icon = "mdi:counter"
    _attr_native_unit_of_measurement = "tokens"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "token_usage")

    @property
    @override
    def native_value(self) -> int:
        return self.usage.total_tokens

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "input_tokens_total": self.usage.input_tokens,
            "output_tokens_total": self.usage.output_tokens,
            "tokens_24h": self.usage.tokens_24h,
            "estimated_tokens_remaining_24h": (
                self.usage.estimated_tokens_remaining_24h
            ),
            "reference_token_limit_24h": self.usage.reference_token_limit_24h,
            "access_mode": self.usage.access_mode,
            "estimate_only": True,
            "limits_source": LLM7_WEB_URL,
            "note": (
                "Local count only. The provider may count other clients, cached "
                "tokens, or requests differently. Token plans can have other limits."
            ),
        }


class QuotaStatusSensor(_UsageManagerSensor):
    """Expose a warning based on locally observed reference-limit usage."""

    _attr_translation_key = "quota_status"
    _attr_icon = "mdi:gauge"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["ok", "warning", "limit_reached"]

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "quota_status")

    @property
    @override
    def native_value(self) -> str:
        return self.usage.quota_status

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "highest_reference_usage": (
                self.usage.highest_reference_usage_percent
            ),
            "reference_usage_unit": PERCENTAGE,
            "limiting_metric": self.usage.limiting_metric,
            "token_quota_usage": self.usage.quota_usage_percent,
            "hour_request_usage": self.usage.request_hour_usage_percent,
            "minute_request_usage": self.usage.request_minute_usage_percent,
            "second_request_usage": self.usage.request_second_usage_percent,
            "tokens_24h": self.usage.tokens_24h,
            "requests_hour": self.usage.requests_hour,
            "requests_minute": self.usage.requests_minute,
            "requests_second": self.usage.requests_second,
            "access_mode": self.usage.access_mode,
            "estimate_only": True,
            "limits_source": LLM7_WEB_URL,
        }


class LastApiRequestSensor(_UsageManagerSensor):
    """Expose the timestamp and result of the last local API attempt."""

    _attr_translation_key = "last_api_request"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "last_api_request")

    @property
    @override
    def native_value(self):
        return self.usage.last_request_at

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "last_success_at": self.usage.last_success_at,
            "last_failure_at": self.usage.last_failure_at,
            "selected_model": self.usage.last_model,
            "provider_model": self.usage.last_provider_model,
            "latency_ms": self.usage.last_latency_ms,
            "http_status": self.usage.last_status,
            "last_error": self.usage.last_error,
        }
