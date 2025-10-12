"""Config flow for freellm_chat Conversation integration."""
from __future__ import annotations

import logging
import types
from types import MappingProxyType
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    SelectSelector,
    SelectSelectorConfig
)

from .const import (
    CONF_CHAT_MODEL,
    CONF_PROMPT,
    DEFAULT_CHAT_MODEL,
    DEFAULT_PROMPT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({})

DEFAULT_OPTIONS = types.MappingProxyType(
    {
        CONF_CHAT_MODEL: DEFAULT_CHAT_MODEL,
        CONF_PROMPT: DEFAULT_PROMPT,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    # Da LLM7.io keine Authentifizierung erfordert, ist keine Validierung erforderlich
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
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "invalid_auth"
        else:
            return self.async_create_entry(
                title="FreeLLM Chat", data=user_input
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    """freellm_chat config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                title="FreeLLM Chat", data=user_input
            )
        schema = await freellm_chat_config_option_schema(self, self.config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )

async def freellm_chat_config_option_schema(
    self, options: MappingProxyType[str, Any]
) -> dict:
    """Return a schema for freellm_chat completion options."""

    # Hier kannst du eine Liste der verfügbaren Modelle von LLM7.io einfügen
    # oder die manuelle Eingabe beibehalten
    models = [
        {"label": "gpt-4o-mini-2024-07-18", "value": "gpt-4o-mini-2024-07-18"},
        {"label": "gpt-4o", "value": "gpt-4o"},
        {"label": "gpt-o3-mini", "value": "gpt-o3-mini"},
        {"label": "qwen2.5-coder-32b-instruct:int8", "value": "qwen2.5-coder-32b-instruct:int8"},
        {"label": "llama-3.3-70b-instruct-fp8-fast", "value": "llama-3.3-70b-instruct-fp8-fast"},
        {"label": "llama-4-scout-17b-16e-instruct", "value": "llama-4-scout-17b-16e-instruct"},
        {"label": "mistral-small-2503", "value": "mistral-small-2503"},
        {"label": "unity-mistral-large", "value": "unity-mistral-large"},
        {"label": "midijourney", "value": "midijourney"},
        {"label": "rtist", "value": "rtist"},
        {"label": "searchgpt", "value": "searchgpt"},
        {"label": "evil", "value": "evil"},
        {"label": "deepseek-r1-qwen:32b", "value": "deepseek-r1-qwen:32b"},
        {"label": "deepseek-r1-distill-llama-70b:fp8", "value": "deepseek-r1-distill-llama-70b:fp8"},
        {"label": "llama3.1:8b", "value": "llama3.1:8b"},
        {"label": "phi-4", "value": "phi-4"},
        {"label": "llama3.2:11b", "value": "llama3.2:11b"},
        {"label": "pixtral:12b", "value": "pixtral:12b"},
        {"label": "gemini-2.0-flash", "value": "gemini-2.0-flash"},
        {"label": "gemini-2.0-flash-thinking", "value": "gemini-2.0-flash-thinking"},
        {"label": "hormoz:8b", "value": "hormoz:8b"},
        {"label": "hypnosis-tracy:7b", "value": "hypnosis-tracy:7b"},
        {"label": "mistral-roblox", "value": "mistral-roblox"},
        {"label": "roblox-rp", "value": "roblox-rp"},
        {"label": "deepseek-v3", "value": "deepseek-v3"},
         {"label": "deepseek-r1", "value": "deepseek-r1"},
         {"label": "qwen-qwq-32b", "value": "qwen-qwq-32b"},
         {"label": "sur", "value": "sur"},
         {"label": "llama-scaleway", "value": "llama-scaleway"},
         {"label": "openai-audio", "value": "openai-audio"}
         ]

    options = {**DEFAULT_OPTIONS, **options}

    return {
        vol.Optional(
            CONF_CHAT_MODEL,
            description={"suggested_value": options[CONF_CHAT_MODEL]},
        ): SelectSelector(SelectSelectorConfig(options=models, mode="dropdown")),
        vol.Optional(
            CONF_PROMPT,
            description={"suggested_value": options[CONF_PROMPT]},
            default=DEFAULT_PROMPT,
        ): TemplateSelector(),
    }