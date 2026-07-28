"""Button entities for FreeLLM Chat."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import LLM7Error
from .const import (
    CONF_CHAT_MODEL,
    DATA_MODEL_MANAGER,
    DATA_USAGE_MANAGER,
    DOMAIN,
)
from .entity import service_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up model and usage management buttons."""
    async_add_entities(
        [
            RefreshModelsButton(entry),
            SelectDefaultModelButton(entry),
            ResetUsageStatisticsButton(entry),
        ]
    )


class _ModelManagerButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, key: str) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = service_device_info(entry)

    @property
    def manager(self):
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_MODEL_MANAGER]

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "selected_model": self.entry.options.get(CONF_CHAT_MODEL),
            "available_models": len(self.manager.models),
            "catalog_source": self.manager.status,
            "last_update": self.manager.last_update,
            "last_attempt": self.manager.last_attempt,
            "last_error": self.manager.last_error,
        }

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class RefreshModelsButton(_ModelManagerButton):
    """Refresh the LLM7 model catalog immediately."""

    _attr_translation_key = "refresh_models"
    _attr_icon = "mdi:refresh"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "refresh_models")

    @override
    async def async_press(self) -> None:
        try:
            await self.manager.async_refresh(force=True)
        except LLM7Error as err:
            raise HomeAssistantError(str(err)) from err


class SelectDefaultModelButton(_ModelManagerButton):
    """Select the configured preferred or automatic fallback model."""

    _attr_translation_key = "select_default_model"
    _attr_icon = "mdi:restore"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "select_default_model")

    @override
    async def async_press(self) -> None:
        try:
            await self.manager.async_select_default_model()
        except LLM7Error as err:
            raise HomeAssistantError(str(err)) from err


class ResetUsageStatisticsButton(ButtonEntity):
    """Reset locally stored request and token counters."""

    _attr_has_entity_name = True
    _attr_translation_key = "reset_usage_statistics"
    _attr_icon = "mdi:counter"

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_reset_usage_statistics"
        self._attr_device_info = service_device_info(entry)

    @property
    def usage_manager(self):
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_USAGE_MANAGER]

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "total_conversations": self.usage_manager.total_conversations,
            "total_api_requests": self.usage_manager.total_api_requests,
            "total_tokens": self.usage_manager.total_tokens,
        }

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.usage_manager.async_add_listener(self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @override
    async def async_press(self) -> None:
        await self.usage_manager.async_reset()
