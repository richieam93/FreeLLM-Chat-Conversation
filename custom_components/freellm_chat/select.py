"""Select entities for FreeLLM Chat."""

from __future__ import annotations

from typing import override

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import LLM7Error
from .const import (
    CONF_CHAT_MODEL,
    CONF_ENABLE_DEVICE_CONTROL,
    DATA_MODEL_MANAGER,
    DEFAULT_ENABLE_DEVICE_CONTROL,
    DOMAIN,
)
from .entity import service_device_info
from .model_manager import model_supports_tools


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the model selector."""
    async_add_entities([ChatModelSelect(entry)])


class ChatModelSelect(SelectEntity):
    """Select the active LLM7 chat model without opening integration options."""

    _attr_has_entity_name = True
    _attr_translation_key = "chat_model"
    _attr_icon = "mdi:brain"

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_chat_model"
        self._attr_device_info = service_device_info(entry)

    @property
    def manager(self):
        """Return the shared model manager."""
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_MODEL_MANAGER]

    @property
    @override
    def options(self) -> list[str]:
        require_tools = bool(
            self.entry.options.get(
                CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
            )
            and self.entry.options.get(CONF_LLM_HASS_API)
        )
        return [
            model["id"]
            for model in self.manager.models
            if not require_tools or model_supports_tools(model)
        ]

    @property
    @override
    def current_option(self) -> str | None:
        selected = self.entry.options.get(CONF_CHAT_MODEL)
        return selected if selected in self.options else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, object]:
        model = self.manager.get_model(self.current_option or "")
        return {
            "catalog_source": self.manager.status,
            "token_free": (
                not bool(model.get("usage_based_only")) if model else None
            ),
            "supports_tools": model.get("tools_calling") if model else None,
            "supports_streaming": model.get("stream") if model else None,
            "modalities": model.get("modalities") if model else None,
            "context_window": model.get("context_window") if model else None,
        }

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @override
    async def async_select_option(self, option: str) -> None:
        try:
            await self.manager.async_select_model(option)
        except LLM7Error as err:
            raise HomeAssistantError(str(err)) from err
