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
)

from .const import (
    CONF_CHAT_MODEL,
    CONF_PROMPT,
    CONF_ENABLE_DEVICE_CONTROL,
    CONF_CONTROL_PROMPT,
    CONF_SELECTED_ENTITIES,
    CONF_SELECTED_AREAS,
    DEFAULT_CHAT_MODEL,
    DEFAULT_PROMPT,
    DEFAULT_ENABLE_DEVICE_CONTROL,
    DEFAULT_CONTROL_PROMPT,
    DOMAIN,
)
from .entity_selector import EntitySelector

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({})

DEFAULT_OPTIONS = types.MappingProxyType({
    CONF_CHAT_MODEL: DEFAULT_CHAT_MODEL,
    CONF_PROMPT: DEFAULT_PROMPT,
    CONF_ENABLE_DEVICE_CONTROL: DEFAULT_ENABLE_DEVICE_CONTROL,
    CONF_CONTROL_PROMPT: DEFAULT_CONTROL_PROMPT,
    CONF_SELECTED_ENTITIES: [],
    CONF_SELECTED_AREAS: [],
})

# Vollständige Liste aller LLM7.io Modelle
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


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    pass


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for freellm_chat Conversation."""

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

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "invalid_auth"
        else:
            return self.async_create_entry(
                title="FreeLLM Chat",
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """freellm_chat config flow options handler."""

    # KEIN __init__ mehr nötig! config_entry wird automatisch von der Basisklasse bereitgestellt

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options - Main menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["chat_settings", "control_settings", "entity_selection"]
        )

    async def async_step_chat_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle chat settings."""
        if user_input is not None:
            # Update nur die Chat-Einstellungen, behalte andere Einstellungen
            new_options = {**self.config_entry.options}
            new_options[CONF_CHAT_MODEL] = user_input.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
            new_options[CONF_PROMPT] = user_input.get(CONF_PROMPT, DEFAULT_PROMPT)
            
            return self.async_create_entry(title="", data=new_options)

        options = {**DEFAULT_OPTIONS, **self.config_entry.options}

        schema = vol.Schema({
            vol.Optional(
                CONF_CHAT_MODEL,
                description={"suggested_value": options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)},
            ): SelectSelector(SelectSelectorConfig(
                options=ALL_MODELS,
                mode=SelectSelectorMode.DROPDOWN
            )),
            vol.Optional(
                CONF_PROMPT,
                description={"suggested_value": options.get(CONF_PROMPT, DEFAULT_PROMPT)},
            ): TemplateSelector(),
        })

        return self.async_show_form(
            step_id="chat_settings",
            data_schema=schema,
        )

    async def async_step_control_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device control settings."""
        if user_input is not None:
            # Update nur die Steuerungs-Einstellungen, behalte andere Einstellungen
            new_options = {**self.config_entry.options}
            new_options[CONF_ENABLE_DEVICE_CONTROL] = user_input.get(
                CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
            )
            new_options[CONF_CONTROL_PROMPT] = user_input.get(
                CONF_CONTROL_PROMPT, DEFAULT_CONTROL_PROMPT
            )
            
            return self.async_create_entry(title="", data=new_options)

        options = {**DEFAULT_OPTIONS, **self.config_entry.options}

        schema = vol.Schema({
            vol.Optional(
                CONF_ENABLE_DEVICE_CONTROL,
                description={"suggested_value": options.get(
                    CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
                )},
            ): BooleanSelector(),
            vol.Optional(
                CONF_CONTROL_PROMPT,
                description={"suggested_value": options.get(
                    CONF_CONTROL_PROMPT, DEFAULT_CONTROL_PROMPT
                )},
            ): TemplateSelector(),
        })

        return self.async_show_form(
            step_id="control_settings",
            data_schema=schema,
        )

    async def async_step_entity_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle entity and area selection."""
        if user_input is not None:
            # Update nur die Entity-Auswahl, behalte andere Einstellungen
            new_options = {**self.config_entry.options}
            new_options[CONF_SELECTED_AREAS] = user_input.get(CONF_SELECTED_AREAS, [])
            new_options[CONF_SELECTED_ENTITIES] = user_input.get(CONF_SELECTED_ENTITIES, [])
            
            return self.async_create_entry(title="", data=new_options)

        # Hole verfügbare Bereiche und Entities
        areas = EntitySelector.get_available_areas(self.hass)
        entities = EntitySelector.get_available_entities(self.hass)
        options = {**DEFAULT_OPTIONS, **self.config_entry.options}

        # Erstelle Schema basierend auf verfügbaren Optionen
        schema_dict = {}

        # Bereiche Auswahl (nur wenn Bereiche vorhanden)
        if areas:
            schema_dict[vol.Optional(
                CONF_SELECTED_AREAS,
                description={"suggested_value": options.get(CONF_SELECTED_AREAS, [])},
            )] = SelectSelector(SelectSelectorConfig(
                options=areas,
                mode=SelectSelectorMode.DROPDOWN,
                multiple=True
            ))

        # Entities Auswahl (nur wenn Entities vorhanden)
        if entities:
            schema_dict[vol.Optional(
                CONF_SELECTED_ENTITIES,
                description={"suggested_value": options.get(CONF_SELECTED_ENTITIES, [])},
            )] = SelectSelector(SelectSelectorConfig(
                options=entities,
                mode=SelectSelectorMode.DROPDOWN,
                multiple=True
            ))

        # Fallback wenn keine Entities/Bereiche vorhanden
        if not schema_dict:
            return self.async_abort(reason="no_entities_available")

        schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="entity_selection",
            data_schema=schema,
        )