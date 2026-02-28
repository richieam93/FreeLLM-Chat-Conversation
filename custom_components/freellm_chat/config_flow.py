"""Config flow for freellm_chat Conversation integration."""
from __future__ import annotations

import logging
import types
from types import MappingProxyType
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    TemplateSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_CHAT_MODEL,
    CONF_PROMPT,
    CONF_CHAT_TEMPERATURE,
    CONF_CHAT_MAX_TOKENS,
    CONF_ENABLE_DEVICE_CONTROL,
    CONF_CONTROL_PROMPT,
    CONF_CONTROL_TEMPERATURE,
    CONF_CONTROL_MAX_TOKENS,
    CONF_SELECTED_ENTITIES,
    CONF_SELECTED_AREAS,
    CONF_ENABLE_SENSORS,
    CONF_HISTORY_LIMIT,
    CONF_TIMEOUT,
    CONF_RETRY_COUNT,
    DEFAULT_CHAT_MODEL,
    DEFAULT_PROMPT,
    DEFAULT_CHAT_TEMPERATURE,
    DEFAULT_CHAT_MAX_TOKENS,
    DEFAULT_ENABLE_DEVICE_CONTROL,
    DEFAULT_CONTROL_PROMPT,
    DEFAULT_CONTROL_TEMPERATURE,
    DEFAULT_CONTROL_MAX_TOKENS,
    DEFAULT_ENABLE_SENSORS,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DOMAIN,
)
from .entity_selector import EntitySelector

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({})

DEFAULT_OPTIONS = types.MappingProxyType({
    CONF_CHAT_MODEL: DEFAULT_CHAT_MODEL,
    CONF_PROMPT: DEFAULT_PROMPT,
    CONF_CHAT_TEMPERATURE: DEFAULT_CHAT_TEMPERATURE,
    CONF_CHAT_MAX_TOKENS: DEFAULT_CHAT_MAX_TOKENS,
    CONF_ENABLE_DEVICE_CONTROL: DEFAULT_ENABLE_DEVICE_CONTROL,
    CONF_CONTROL_PROMPT: DEFAULT_CONTROL_PROMPT,
    CONF_CONTROL_TEMPERATURE: DEFAULT_CONTROL_TEMPERATURE,
    CONF_CONTROL_MAX_TOKENS: DEFAULT_CONTROL_MAX_TOKENS,
    CONF_SELECTED_ENTITIES: [],
    CONF_SELECTED_AREAS: [],
    CONF_ENABLE_SENSORS: DEFAULT_ENABLE_SENSORS,
    CONF_HISTORY_LIMIT: DEFAULT_HISTORY_LIMIT,
    CONF_TIMEOUT: DEFAULT_TIMEOUT,
    CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
})

# Alle LLM7.io Modelle
ALL_MODELS = [
    {"label": "GPT-4o Mini (2024-07-18)", "value": "gpt-4o-mini-2024-07-18"},
    {"label": "GPT-4o", "value": "gpt-4o"},
    {"label": "GPT-o3 Mini", "value": "gpt-o3-mini"},
    {"label": "DeepSeek V3", "value": "deepseek-v3"},
    {"label": "DeepSeek R1", "value": "deepseek-r1"},
    {"label": "DeepSeek R1 Qwen 32B", "value": "deepseek-r1-qwen:32b"},
    {"label": "Llama 3.1 8B", "value": "llama3.1:8b"},
    {"label": "Llama 3.2 11B", "value": "llama3.2:11b"},
    {"label": "Llama 3.3 70B Instruct", "value": "llama-3.3-70b-instruct-fp8-fast"},
    {"label": "Qwen QWQ 32B", "value": "qwen-qwq-32b"},
    {"label": "Mistral Small 2503", "value": "mistral-small-2503"},
    {"label": "Gemini 2.0 Flash", "value": "gemini-2.0-flash"},
    {"label": "Phi-4", "value": "phi-4"},
]


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for freellm_chat."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA
            )

        return self.async_create_entry(title="FreeLLM Chat", data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """freellm_chat options handler."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Main menu - nur 3 Optionen."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "chat_settings",
                "control_settings",
                "entity_selection",
            ]
        )

    async def async_step_chat_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle chat settings."""
        if user_input is not None:
            new_options = {**self.config_entry.options}
            new_options[CONF_CHAT_MODEL] = user_input.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
            new_options[CONF_PROMPT] = user_input.get(CONF_PROMPT, DEFAULT_PROMPT)
            new_options[CONF_CHAT_TEMPERATURE] = user_input.get(CONF_CHAT_TEMPERATURE, DEFAULT_CHAT_TEMPERATURE)
            new_options[CONF_CHAT_MAX_TOKENS] = user_input.get(CONF_CHAT_MAX_TOKENS, DEFAULT_CHAT_MAX_TOKENS)
            new_options[CONF_HISTORY_LIMIT] = user_input.get(CONF_HISTORY_LIMIT, DEFAULT_HISTORY_LIMIT)
            new_options[CONF_TIMEOUT] = user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            new_options[CONF_RETRY_COUNT] = user_input.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)
            return self.async_create_entry(title="", data=new_options)

        options = {**DEFAULT_OPTIONS, **self.config_entry.options}

        return self.async_show_form(
            step_id="chat_settings",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_CHAT_MODEL,
                    description={"suggested_value": options.get(CONF_CHAT_MODEL)},
                ): SelectSelector(SelectSelectorConfig(
                    options=ALL_MODELS,
                    mode=SelectSelectorMode.DROPDOWN
                )),
                vol.Optional(
                    CONF_CHAT_TEMPERATURE,
                    description={"suggested_value": options.get(CONF_CHAT_TEMPERATURE)},
                ): NumberSelector(NumberSelectorConfig(
                    min=0.0, max=2.0, step=0.1, mode=NumberSelectorMode.SLIDER
                )),
                vol.Optional(
                    CONF_CHAT_MAX_TOKENS,
                    description={"suggested_value": options.get(CONF_CHAT_MAX_TOKENS)},
                ): NumberSelector(NumberSelectorConfig(
                    min=100, max=4000, step=100, mode=NumberSelectorMode.SLIDER
                )),
                vol.Optional(
                    CONF_HISTORY_LIMIT,
                    description={"suggested_value": options.get(CONF_HISTORY_LIMIT)},
                ): NumberSelector(NumberSelectorConfig(
                    min=5, max=50, step=5, mode=NumberSelectorMode.SLIDER
                )),
                vol.Optional(
                    CONF_TIMEOUT,
                    description={"suggested_value": options.get(CONF_TIMEOUT)},
                ): NumberSelector(NumberSelectorConfig(
                    min=10, max=120, step=10, mode=NumberSelectorMode.SLIDER
                )),
                vol.Optional(
                    CONF_RETRY_COUNT,
                    description={"suggested_value": options.get(CONF_RETRY_COUNT)},
                ): NumberSelector(NumberSelectorConfig(
                    min=0, max=5, step=1, mode=NumberSelectorMode.SLIDER
                )),
                vol.Optional(
                    CONF_PROMPT,
                    description={"suggested_value": options.get(CONF_PROMPT)},
                ): TemplateSelector(),
            }),
        )

    async def async_step_control_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle control settings."""
        if user_input is not None:
            new_options = {**self.config_entry.options}
            new_options[CONF_ENABLE_DEVICE_CONTROL] = user_input.get(CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL)
            new_options[CONF_ENABLE_SENSORS] = user_input.get(CONF_ENABLE_SENSORS, DEFAULT_ENABLE_SENSORS)
            new_options[CONF_CONTROL_TEMPERATURE] = user_input.get(CONF_CONTROL_TEMPERATURE, DEFAULT_CONTROL_TEMPERATURE)
            new_options[CONF_CONTROL_MAX_TOKENS] = user_input.get(CONF_CONTROL_MAX_TOKENS, DEFAULT_CONTROL_MAX_TOKENS)
            new_options[CONF_CONTROL_PROMPT] = user_input.get(CONF_CONTROL_PROMPT, DEFAULT_CONTROL_PROMPT)
            return self.async_create_entry(title="", data=new_options)

        options = {**DEFAULT_OPTIONS, **self.config_entry.options}

        return self.async_show_form(
            step_id="control_settings",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_ENABLE_DEVICE_CONTROL,
                    description={"suggested_value": options.get(CONF_ENABLE_DEVICE_CONTROL)},
                ): BooleanSelector(),
                vol.Optional(
                    CONF_ENABLE_SENSORS,
                    description={"suggested_value": options.get(CONF_ENABLE_SENSORS)},
                ): BooleanSelector(),
                vol.Optional(
                    CONF_CONTROL_TEMPERATURE,
                    description={"suggested_value": options.get(CONF_CONTROL_TEMPERATURE)},
                ): NumberSelector(NumberSelectorConfig(
                    min=0.0, max=1.0, step=0.1, mode=NumberSelectorMode.SLIDER
                )),
                vol.Optional(
                    CONF_CONTROL_MAX_TOKENS,
                    description={"suggested_value": options.get(CONF_CONTROL_MAX_TOKENS)},
                ): NumberSelector(NumberSelectorConfig(
                    min=100, max=4000, step=100, mode=NumberSelectorMode.SLIDER
                )),
                vol.Optional(
                    CONF_CONTROL_PROMPT,
                    description={"suggested_value": options.get(CONF_CONTROL_PROMPT)},
                ): TemplateSelector(),
            }),
        )

    async def async_step_entity_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle entity selection."""
        if user_input is not None:
            new_options = {**self.config_entry.options}
            new_options[CONF_SELECTED_AREAS] = user_input.get(CONF_SELECTED_AREAS, [])
            new_options[CONF_SELECTED_ENTITIES] = user_input.get(CONF_SELECTED_ENTITIES, [])
            return self.async_create_entry(title="", data=new_options)

        enable_sensors = self.config_entry.options.get(CONF_ENABLE_SENSORS, DEFAULT_ENABLE_SENSORS)
        areas = EntitySelector.get_available_areas(self.hass)
        entities = EntitySelector.get_available_entities(self.hass, include_sensors=enable_sensors)
        options = {**DEFAULT_OPTIONS, **self.config_entry.options}

        schema_dict = {}

        if areas:
            schema_dict[vol.Optional(
                CONF_SELECTED_AREAS,
                description={"suggested_value": options.get(CONF_SELECTED_AREAS, [])},
            )] = SelectSelector(SelectSelectorConfig(
                options=areas, mode=SelectSelectorMode.DROPDOWN, multiple=True
            ))

        if entities:
            schema_dict[vol.Optional(
                CONF_SELECTED_ENTITIES,
                description={"suggested_value": options.get(CONF_SELECTED_ENTITIES, [])},
            )] = SelectSelector(SelectSelectorConfig(
                options=entities, mode=SelectSelectorMode.DROPDOWN, multiple=True
            ))

        if not schema_dict:
            return self.async_abort(reason="no_entities_available")

        return self.async_show_form(
            step_id="entity_selection",
            data_schema=vol.Schema(schema_dict),
        )