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
    CONF_ENABLE_CACHE,
    CONF_CACHE_DURATION,
    CONF_OPTIMIZE_PROMPTS,
    CONF_COMPRESSION_LEVEL,
    CONF_ENABLE_STATISTICS,
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
    DEFAULT_ENABLE_CACHE,
    DEFAULT_CACHE_DURATION,
    DEFAULT_OPTIMIZE_PROMPTS,
    DEFAULT_COMPRESSION_LEVEL,
    DEFAULT_ENABLE_STATISTICS,
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
    CONF_ENABLE_CACHE: DEFAULT_ENABLE_CACHE,
    CONF_CACHE_DURATION: DEFAULT_CACHE_DURATION,
    CONF_OPTIMIZE_PROMPTS: DEFAULT_OPTIMIZE_PROMPTS,
    CONF_COMPRESSION_LEVEL: DEFAULT_COMPRESSION_LEVEL,
    CONF_ENABLE_STATISTICS: DEFAULT_ENABLE_STATISTICS,
    CONF_HISTORY_LIMIT: DEFAULT_HISTORY_LIMIT,
    CONF_TIMEOUT: DEFAULT_TIMEOUT,
    CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
})

# Alle LLM7.io Modelle
ALL_MODELS = [
    # GPT Modelle
    {"label": "GPT-4o Mini (2024-07-18)", "value": "gpt-4o-mini-2024-07-18"},
    {"label": "GPT-4o", "value": "gpt-4o"},
    {"label": "GPT-o3 Mini", "value": "gpt-o3-mini"},
    
    # DeepSeek Modelle
    {"label": "DeepSeek V3", "value": "deepseek-v3"},
    {"label": "DeepSeek R1", "value": "deepseek-r1"},
    {"label": "DeepSeek R1 Qwen 32B", "value": "deepseek-r1-qwen:32b"},
    {"label": "DeepSeek R1 Distill Llama 70B FP8", "value": "deepseek-r1-distill-llama-70b:fp8"},
    
    # Llama Modelle
    {"label": "Llama 3.1 8B", "value": "llama3.1:8b"},
    {"label": "Llama 3.2 11B", "value": "llama3.2:11b"},
    {"label": "Llama 3.3 70B Instruct FP8 Fast", "value": "llama-3.3-70b-instruct-fp8-fast"},
    {"label": "Llama 4 Scout 17B 16E Instruct", "value": "llama-4-scout-17b-16e-instruct"},
    {"label": "Llama Scaleway", "value": "llama-scaleway"},
    
    # Qwen Modelle
    {"label": "Qwen 2.5 Coder 32B Instruct INT8", "value": "qwen2.5-coder-32b-instruct:int8"},
    {"label": "Qwen QWQ 32B", "value": "qwen-qwq-32b"},
    
    # Mistral Modelle
    {"label": "Mistral Small 2503", "value": "mistral-small-2503"},
    {"label": "Unity Mistral Large", "value": "unity-mistral-large"},
    {"label": "Mistral Roblox", "value": "mistral-roblox"},
    
    # Gemini Modelle
    {"label": "Gemini 2.0 Flash", "value": "gemini-2.0-flash"},
    {"label": "Gemini 2.0 Flash Thinking", "value": "gemini-2.0-flash-thinking"},
    
    # Andere Modelle
    {"label": "Phi-4", "value": "phi-4"},
    {"label": "Pixtral 12B", "value": "pixtral:12b"},
    {"label": "Hormoz 8B", "value": "hormoz:8b"},
    {"label": "Hypnosis Tracy 7B", "value": "hypnosis-tracy:7b"},
    
    # Spezial-Modelle
    {"label": "SearchGPT", "value": "searchgpt"},
    {"label": "Midijourney", "value": "midijourney"},
    {"label": "Rtist", "value": "rtist"},
    {"label": "Evil", "value": "evil"},
    {"label": "Sur", "value": "sur"},
    {"label": "Roblox RP", "value": "roblox-rp"},
    {"label": "OpenAI Audio", "value": "openai-audio"},
]

COMPRESSION_LEVELS = [
    {"label": "🔄 Automatisch (empfohlen)", "value": "auto"},
    {"label": "📄 Keine Komprimierung", "value": "none"},
    {"label": "📊 Mittel", "value": "medium"},
    {"label": "⚡ Hoch (schnellste)", "value": "high"},
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
        """Main menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "chat_settings",
                "control_settings",
                "entity_selection",
                "performance_settings",
                "advanced_settings"
            ]
        )

    # ===== CHAT EINSTELLUNGEN =====
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
                    CONF_PROMPT,
                    description={"suggested_value": options.get(CONF_PROMPT)},
                ): TemplateSelector(),
            }),
        )

    # ===== STEUERUNGS EINSTELLUNGEN =====
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
                    min=100, max=2000, step=50, mode=NumberSelectorMode.SLIDER
                )),
                vol.Optional(
                    CONF_CONTROL_PROMPT,
                    description={"suggested_value": options.get(CONF_CONTROL_PROMPT)},
                ): TemplateSelector(),
            }),
        )

    # ===== ENTITY AUSWAHL =====
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

    # ===== PERFORMANCE EINSTELLUNGEN =====
    async def async_step_performance_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle performance settings."""
        if user_input is not None:
            new_options = {**self.config_entry.options}
            new_options[CONF_ENABLE_CACHE] = user_input.get(CONF_ENABLE_CACHE, DEFAULT_ENABLE_CACHE)
            new_options[CONF_CACHE_DURATION] = user_input.get(CONF_CACHE_DURATION, DEFAULT_CACHE_DURATION)
            new_options[CONF_OPTIMIZE_PROMPTS] = user_input.get(CONF_OPTIMIZE_PROMPTS, DEFAULT_OPTIMIZE_PROMPTS)
            new_options[CONF_COMPRESSION_LEVEL] = user_input.get(CONF_COMPRESSION_LEVEL, DEFAULT_COMPRESSION_LEVEL)
            return self.async_create_entry(title="", data=new_options)

        options = {**DEFAULT_OPTIONS, **self.config_entry.options}

        return self.async_show_form(
            step_id="performance_settings",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_ENABLE_CACHE,
                    description={"suggested_value": options.get(CONF_ENABLE_CACHE)},
                ): BooleanSelector(),
                vol.Optional(
                    CONF_CACHE_DURATION,
                    description={"suggested_value": options.get(CONF_CACHE_DURATION)},
                ): NumberSelector(NumberSelectorConfig(
                    min=60, max=3600, step=60, mode=NumberSelectorMode.SLIDER,
                    unit_of_measurement="Sekunden"
                )),
                vol.Optional(
                    CONF_OPTIMIZE_PROMPTS,
                    description={"suggested_value": options.get(CONF_OPTIMIZE_PROMPTS)},
                ): BooleanSelector(),
                vol.Optional(
                    CONF_COMPRESSION_LEVEL,
                    description={"suggested_value": options.get(CONF_COMPRESSION_LEVEL)},
                ): SelectSelector(SelectSelectorConfig(
                    options=COMPRESSION_LEVELS, mode=SelectSelectorMode.DROPDOWN
                )),
            }),
        )

    # ===== ERWEITERTE EINSTELLUNGEN =====
    async def async_step_advanced_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced settings."""
        if user_input is not None:
            new_options = {**self.config_entry.options}
            new_options[CONF_ENABLE_STATISTICS] = user_input.get(CONF_ENABLE_STATISTICS, DEFAULT_ENABLE_STATISTICS)
            new_options[CONF_TIMEOUT] = user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            new_options[CONF_RETRY_COUNT] = user_input.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)
            return self.async_create_entry(title="", data=new_options)

        options = {**DEFAULT_OPTIONS, **self.config_entry.options}

        return self.async_show_form(
            step_id="advanced_settings",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_ENABLE_STATISTICS,
                    description={"suggested_value": options.get(CONF_ENABLE_STATISTICS)},
                ): BooleanSelector(),
                vol.Optional(
                    CONF_TIMEOUT,
                    description={"suggested_value": options.get(CONF_TIMEOUT)},
                ): NumberSelector(NumberSelectorConfig(
                    min=10, max=120, step=5, mode=NumberSelectorMode.SLIDER,
                    unit_of_measurement="Sekunden"
                )),
                vol.Optional(
                    CONF_RETRY_COUNT,
                    description={"suggested_value": options.get(CONF_RETRY_COUNT)},
                ): NumberSelector(NumberSelectorConfig(
                    min=0, max=5, step=1, mode=NumberSelectorMode.SLIDER
                )),
            }),
        )