"""Select entities for FreeLLM Chat."""

from __future__ import annotations

from typing import override

from homeassistant.components.select import SelectEntity
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import LLM7Error
from .const import (
    AUTO_FALLBACK_MODEL,
    CONF_CHAT_MODEL,
    CONF_ENABLE_DEVICE_CONTROL,
    CONF_FALLBACK_MODEL,
    DEFAULT_ENABLE_DEVICE_CONTROL,
)
from .entity import service_device_info
from .model_manager import choose_default_model, model_supports_tools
from .runtime import FreeLLMConfigEntry

_AUTO_OPTION = "automatic"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FreeLLMConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up model selectors."""
    async_add_entities([ChatModelSelect(entry), FallbackModelSelect(entry)])


class _ModelSelectBase(SelectEntity):
    """Shared behavior for model selectors."""

    _attr_has_entity_name = True

    def __init__(self, entry: FreeLLMConfigEntry, key: str) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = service_device_info(entry)

    @property
    def manager(self):
        """Return the shared model manager."""
        return self.entry.runtime_data.model_manager

    @property
    def _require_tools(self) -> bool:
        return bool(
            self.entry.options.get(
                CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
            )
            and self.entry.options.get(CONF_LLM_HASS_API)
        )

    def _eligible_model_ids(self) -> list[str]:
        return [
            model["id"]
            for model in self.manager.models
            if not self._require_tools or model_supports_tools(model)
        ]

    @override
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class ChatModelSelect(_ModelSelectBase):
    """Select the active provider chat model without opening integration options."""

    _attr_translation_key = "chat_model"
    _attr_icon = "mdi:brain"

    def __init__(self, entry: FreeLLMConfigEntry) -> None:
        super().__init__(entry, "chat_model")

    @property
    @override
    def options(self) -> list[str]:
        return self._eligible_model_ids()

    @property
    @override
    def current_option(self) -> str | None:
        selected = self.entry.options.get(CONF_CHAT_MODEL)
        return selected if selected in self.options else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, object]:
        model = self.manager.get_model(self.current_option or "")
        return _model_attributes(model, self.manager.status)

    @override
    async def async_select_option(self, option: str) -> None:
        try:
            await self.manager.async_select_model(option)
        except LLM7Error as err:
            raise HomeAssistantError(str(err)) from err


class FallbackModelSelect(_ModelSelectBase):
    """Choose the preferred model used when the active model is unavailable."""

    _attr_translation_key = "fallback_model"
    _attr_icon = "mdi:backup-restore"

    def __init__(self, entry: FreeLLMConfigEntry) -> None:
        super().__init__(entry, "fallback_model")

    @property
    @override
    def options(self) -> list[str]:
        return [_AUTO_OPTION, *self._eligible_model_ids()]

    @property
    @override
    def current_option(self) -> str | None:
        configured = self.entry.options.get(
            CONF_FALLBACK_MODEL, AUTO_FALLBACK_MODEL
        )
        if configured == AUTO_FALLBACK_MODEL:
            return _AUTO_OPTION
        return str(configured) if configured in self.options else _AUTO_OPTION

    @property
    @override
    def extra_state_attributes(self) -> dict[str, object]:
        configured = self.entry.options.get(
            CONF_FALLBACK_MODEL, AUTO_FALLBACK_MODEL
        )
        resolved = choose_default_model(
            self.manager.models,
            require_tools=self._require_tools,
            preferred=configured,
        )
        model = self.manager.get_model(resolved)
        return {
            "mode": "automatic" if configured == AUTO_FALLBACK_MODEL else "preferred",
            "resolved_model": resolved,
            **_model_attributes(model, self.manager.status),
        }

    @override
    async def async_select_option(self, option: str) -> None:
        model_id = AUTO_FALLBACK_MODEL if option == _AUTO_OPTION else option
        try:
            await self.manager.async_select_fallback_model(model_id)
        except LLM7Error as err:
            raise HomeAssistantError(str(err)) from err


def _model_attributes(
    model: dict[str, object] | None, catalog_status: str
) -> dict[str, object]:
    """Return compact capability metadata for one model."""
    return {
        "catalog_source": catalog_status,
        "token_free": not bool(model.get("usage_based_only")) if model else None,
        "supports_tools": model.get("tools_calling") if model else None,
        "supports_streaming": model.get("stream") if model else None,
        "supports_reasoning": model.get("reasoning") if model else None,
        "supports_json_mode": model.get("json_mode") if model else None,
        "tier": model.get("tier") if model else None,
        "provider": model.get("owned_by") if model else None,
        "modalities": model.get("modalities") if model else None,
        "context_window": model.get("context_window") if model else None,
    }
