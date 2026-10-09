"""Config flow for FreeLLM Chat."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import llm
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    LLM7AuthenticationError,
    LLM7Client,
    LLM7ConnectionError,
    LLM7Error,
)
from .const import (
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
    MODEL_REFRESH_MAX_HOURS,
    MODEL_REFRESH_MIN_HOURS,
)
from .provider import (
    DEFAULT_PROVIDER,
    PROVIDER_LLM7,
    PROVIDER_OVHCLOUD,
    normalize_provider,
    provider_dashboard_url,
    provider_docs_url,
    provider_name,
    provider_status_url,
    provider_web_url,
)
from .model_manager import (
    choose_default_model,
    load_bundled_models,
    model_label,
    model_supports_tools,
    normalize_models,
)


def _access_schema(
    *,
    provider: str = DEFAULT_PROVIDER,
    llm7_key: str = "",
    ovh_key: str = "",
    require_disclaimer: bool = False,
) -> vol.Schema:
    fields: dict[Any, Any] = {
        vol.Required(CONF_PROVIDER, default=normalize_provider(provider)): SelectSelector(
            SelectSelectorConfig(
                options=[
                    {"label": "LLM7.io", "value": PROVIDER_LLM7},
                    {"label": "OVHcloud AI Endpoints", "value": PROVIDER_OVHCLOUD},
                ],
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(
            CONF_API_KEY, description={"suggested_value": llm7_key}
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        vol.Optional(
            CONF_OVH_API_KEY, description={"suggested_value": ovh_key}
        ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
    }
    if require_disclaimer:
        fields[vol.Required(CONF_ACCEPT_DISCLAIMER, default=False)] = BooleanSelector()
    return vol.Schema(fields)


def _link_placeholders(provider: str = DEFAULT_PROVIDER) -> dict[str, str]:
    provider = normalize_provider(provider)
    return {
        "provider_name": provider_name(provider),
        "website_url": provider_web_url(provider),
        "api_key_url": provider_dashboard_url(provider),
        "docs_url": provider_docs_url(provider),
        "status_url": provider_status_url(provider),
        "llm7_url": provider_web_url(PROVIDER_LLM7),
        "llm7_key_url": provider_dashboard_url(PROVIDER_LLM7),
        "ovh_url": provider_web_url(PROVIDER_OVHCLOUD),
        "ovh_key_url": provider_dashboard_url(PROVIDER_OVHCLOUD),
        "ovh_docs_url": provider_docs_url(PROVIDER_OVHCLOUD),
    }


def _api_key_for_provider(provider: str, data: dict[str, Any]) -> str:
    key_name = CONF_OVH_API_KEY if provider == PROVIDER_OVHCLOUD else CONF_API_KEY
    return str(data.get(key_name) or "").strip()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the FreeLLM Chat config flow."""

    VERSION = 7

    def __init__(self) -> None:
        self._provider = DEFAULT_PROVIDER
        self._llm7_api_key = ""
        self._ovh_api_key = ""
        self._models: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure provider and optional access keys."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._provider = normalize_provider(user_input.get(CONF_PROVIDER))
            self._llm7_api_key = str(user_input.get(CONF_API_KEY) or "").strip()
            self._ovh_api_key = str(user_input.get(CONF_OVH_API_KEY) or "").strip()
            if user_input.get(CONF_ACCEPT_DISCLAIMER) is not True:
                errors[CONF_ACCEPT_DISCLAIMER] = "disclaimer_required"

            selected_key = (
                self._ovh_api_key
                if self._provider == PROVIDER_OVHCLOUD
                else self._llm7_api_key
            )
            if not errors:
                try:
                    self._models = await _fetch_models(
                        self.hass,
                        self._provider,
                        selected_key,
                        only_free=False,
                    )
                except LLM7AuthenticationError:
                    errors[
                        CONF_OVH_API_KEY
                        if self._provider == PROVIDER_OVHCLOUD
                        else CONF_API_KEY
                    ] = "invalid_auth"
                except LLM7ConnectionError:
                    self._models = load_bundled_models(
                        allow_paid=bool(selected_key),
                        provider=self._provider,
                    )
                    if self._models:
                        return await self.async_step_model()
                    errors["base"] = "cannot_connect"
                except LLM7Error:
                    errors["base"] = "unknown"
                else:
                    return await self.async_step_model()

        current = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=_access_schema(
                provider=current.get(CONF_PROVIDER, self._provider),
                llm7_key=current.get(CONF_API_KEY, self._llm7_api_key),
                ovh_key=current.get(CONF_OVH_API_KEY, self._ovh_api_key),
                require_disclaimer=True,
            ),
            errors=errors,
            description_placeholders=_link_placeholders(
                current.get(CONF_PROVIDER, self._provider)
            ),
        )

    async def async_step_model(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the initial model from the active provider catalog."""
        default_api = _default_llm_api(self.hass)
        default_model = choose_default_model(self._models, require_tools=False)
        options = [
            {"label": model_label(model), "value": model["id"]}
            for model in self._models
        ]

        if user_input is not None:
            selected = user_input[CONF_CHAT_MODEL]
            selected_meta = next(
                (model for model in self._models if model.get("id") == selected), {}
            )
            device_control = bool(default_api and model_supports_tools(selected_meta))
            entry_options: dict[str, Any] = {
                CONF_CHAT_MODEL: selected,
                CONF_FALLBACK_MODEL: AUTO_FALLBACK_MODEL,
                CONF_PROMPT: DEFAULT_PROMPT,
                CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
                CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
                CONF_HISTORY_LIMIT: DEFAULT_HISTORY_LIMIT,
                CONF_MAX_TOOL_ITERATIONS: DEFAULT_MAX_TOOL_ITERATIONS,
                CONF_ENABLE_STREAMING: DEFAULT_ENABLE_STREAMING,
                CONF_ENABLE_VISION: DEFAULT_ENABLE_VISION,
                CONF_ENABLE_DEVICE_CONTROL: device_control,
                CONF_TOKEN_SAVING_MODE: DEFAULT_TOKEN_SAVING_MODE,
                CONF_ENABLE_EXTENDED_DEVICE_QUERIES: (
                    DEFAULT_ENABLE_EXTENDED_DEVICE_QUERIES
                ),
                CONF_DEVICE_QUERY_MAX_RESULTS: DEFAULT_DEVICE_QUERY_MAX_RESULTS,
                CONF_AUTO_UPDATE_MODELS: DEFAULT_AUTO_UPDATE_MODELS,
                CONF_MODEL_REFRESH_INTERVAL: DEFAULT_MODEL_REFRESH_INTERVAL,
                CONF_ONLY_FREE_MODELS: DEFAULT_ONLY_FREE_MODELS,
                CONF_REFERENCE_TOKEN_LIMIT_24H: DEFAULT_REFERENCE_LIMIT,
                CONF_REFERENCE_REQUEST_LIMIT_HOUR: DEFAULT_REFERENCE_LIMIT,
                CONF_REFERENCE_REQUEST_LIMIT_MINUTE: DEFAULT_REFERENCE_LIMIT,
                CONF_REFERENCE_REQUEST_LIMIT_SECOND: DEFAULT_REFERENCE_LIMIT,
            }
            if device_control and default_api:
                entry_options[CONF_LLM_HASS_API] = [default_api]
            existing_entries = len(self._async_current_entries())
            title = (
                "FreeLLM Chat"
                if existing_entries == 0
                else f"FreeLLM Chat {existing_entries + 1}"
            )
            return self.async_create_entry(
                title=title,
                data={
                    CONF_PROVIDER: self._provider,
                    CONF_API_KEY: self._llm7_api_key,
                    CONF_OVH_API_KEY: self._ovh_api_key,
                    CONF_ACCEPT_DISCLAIMER: True,
                },
                options=entry_options,
            )

        selected_key = (
            self._ovh_api_key
            if self._provider == PROVIDER_OVHCLOUD
            else self._llm7_api_key
        )
        return self.async_show_form(
            step_id="model",
            description_placeholders={
                **_link_placeholders(self._provider),
                "free_model_count": str(
                    sum(not model.get("usage_based_only", False) for model in self._models)
                ),
                "access_mode": (
                    f"{provider_name(self._provider)} / "
                    + ("mit API-Key" if selected_key else "anonym")
                ),
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CHAT_MODEL, default=default_model
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change provider or optional access keys."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        current_provider = normalize_provider(entry.data.get(CONF_PROVIDER))
        if user_input is not None:
            provider = normalize_provider(user_input.get(CONF_PROVIDER))
            llm7_key = str(user_input.get(CONF_API_KEY) or "").strip()
            ovh_key = str(user_input.get(CONF_OVH_API_KEY) or "").strip()
            api_key = ovh_key if provider == PROVIDER_OVHCLOUD else llm7_key
            only_free = bool(
                entry.options.get(CONF_ONLY_FREE_MODELS, DEFAULT_ONLY_FREE_MODELS)
            )
            try:
                models = await _fetch_models(
                    self.hass, provider, api_key, only_free=only_free
                )
            except LLM7AuthenticationError:
                errors[
                    CONF_OVH_API_KEY if provider == PROVIDER_OVHCLOUD else CONF_API_KEY
                ] = "invalid_auth"
            except LLM7ConnectionError:
                errors["base"] = "cannot_connect"
            except LLM7Error:
                errors["base"] = "unknown"
            else:
                options = dict(entry.options)
                available = {model["id"] for model in models}
                require_tools = bool(
                    options.get(CONF_ENABLE_DEVICE_CONTROL)
                    and options.get(CONF_LLM_HASS_API)
                )
                if options.get(CONF_CHAT_MODEL) not in available:
                    options[CONF_CHAT_MODEL] = choose_default_model(
                        models,
                        require_tools=require_tools,
                        preferred=options.get(
                            CONF_FALLBACK_MODEL, AUTO_FALLBACK_MODEL
                        ),
                    )
                if options.get(CONF_FALLBACK_MODEL) not in (
                    AUTO_FALLBACK_MODEL,
                    *available,
                ):
                    options[CONF_FALLBACK_MODEL] = AUTO_FALLBACK_MODEL
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_PROVIDER: provider,
                        CONF_API_KEY: llm7_key,
                        CONF_OVH_API_KEY: ovh_key,
                        CONF_ACCEPT_DISCLAIMER: True,
                    },
                    options=options,
                    reason="reconfigure_successful",
                    reload_even_if_entry_is_unchanged=False,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_access_schema(
                provider=current_provider,
                llm7_key=entry.data.get(CONF_API_KEY, ""),
                ovh_key=entry.data.get(CONF_OVH_API_KEY, ""),
            ),
            errors=errors,
            description_placeholders=_link_placeholders(current_provider),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlowWithReload):
    """Manage FreeLLM Chat options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "provider_settings",
                "chat_settings",
                "model_settings",
                "control_settings",
                "usage_settings",
            ],
        )

    async def async_step_provider_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change provider and stored access keys from the options menu."""
        errors: dict[str, str] = {}
        current_provider = normalize_provider(self.config_entry.data.get(CONF_PROVIDER))
        if user_input is not None:
            provider = normalize_provider(user_input.get(CONF_PROVIDER))
            llm7_key = str(user_input.get(CONF_API_KEY) or "").strip()
            ovh_key = str(user_input.get(CONF_OVH_API_KEY) or "").strip()
            api_key = ovh_key if provider == PROVIDER_OVHCLOUD else llm7_key
            only_free = bool(
                self.config_entry.options.get(
                    CONF_ONLY_FREE_MODELS, DEFAULT_ONLY_FREE_MODELS
                )
            )
            try:
                models = await _fetch_models(
                    self.hass, provider, api_key, only_free=only_free
                )
            except LLM7AuthenticationError:
                errors[
                    CONF_OVH_API_KEY if provider == PROVIDER_OVHCLOUD else CONF_API_KEY
                ] = "invalid_auth"
            except LLM7ConnectionError:
                errors["base"] = "cannot_connect"
            except LLM7Error:
                errors["base"] = "unknown"
            else:
                options = dict(self.config_entry.options)
                available = {model["id"] for model in models}
                require_tools = bool(
                    options.get(CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL)
                    and options.get(CONF_LLM_HASS_API)
                )
                if options.get(CONF_CHAT_MODEL) not in available:
                    options[CONF_CHAT_MODEL] = choose_default_model(
                        models,
                        require_tools=require_tools,
                        preferred=options.get(
                            CONF_FALLBACK_MODEL, AUTO_FALLBACK_MODEL
                        ),
                    )
                if options.get(CONF_FALLBACK_MODEL) not in (
                    AUTO_FALLBACK_MODEL,
                    *available,
                ):
                    options[CONF_FALLBACK_MODEL] = AUTO_FALLBACK_MODEL
                data = dict(self.config_entry.data)
                data.update(
                    {
                        CONF_PROVIDER: provider,
                        CONF_API_KEY: llm7_key,
                        CONF_OVH_API_KEY: ovh_key,
                        CONF_ACCEPT_DISCLAIMER: True,
                    }
                )
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=data
                )
                return self.async_create_entry(data=options)

        return self.async_show_form(
            step_id="provider_settings",
            data_schema=_access_schema(
                provider=current_provider,
                llm7_key=self.config_entry.data.get(CONF_API_KEY, ""),
                ovh_key=self.config_entry.data.get(CONF_OVH_API_KEY, ""),
            ),
            errors=errors,
            description_placeholders=_link_placeholders(current_provider),
        )

    async def async_step_chat_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure model, response, context, streaming, and vision."""
        errors: dict[str, str] = {}
        models = await self._async_get_models()
        current = dict(self.config_entry.options)
        require_tools = bool(
            current.get(CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL)
            and current.get(CONF_LLM_HASS_API)
        )
        compatible_models = [
            model
            for model in models
            if not require_tools or model_supports_tools(model)
        ] or models
        available = {model["id"] for model in compatible_models}
        current_model = current.get(CONF_CHAT_MODEL)
        if current_model not in available:
            current_model = choose_default_model(
                compatible_models,
                require_tools=require_tools,
                preferred=current.get(CONF_FALLBACK_MODEL, AUTO_FALLBACK_MODEL),
            )

        if user_input is not None:
            if user_input[CONF_CHAT_MODEL] not in available:
                errors[CONF_CHAT_MODEL] = "model_unavailable"
            else:
                new_options = dict(self.config_entry.options)
                new_options.update(user_input)
                return self.async_create_entry(data=new_options)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CHAT_MODEL,
                    description={"suggested_value": current_model},
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"label": model_label(model), "value": model["id"]}
                            for model in compatible_models
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_TEMPERATURE,
                    description={
                        "suggested_value": current.get(
                            CONF_TEMPERATURE, DEFAULT_TEMPERATURE
                        )
                    },
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0,
                        max=2.0,
                        step=0.1,
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Optional(
                    CONF_MAX_TOKENS,
                    description={
                        "suggested_value": current.get(
                            CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS
                        )
                    },
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=100,
                        max=32000,
                        step=100,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_HISTORY_LIMIT,
                    description={
                        "suggested_value": current.get(
                            CONF_HISTORY_LIMIT, DEFAULT_HISTORY_LIMIT
                        )
                    },
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=4,
                        max=200,
                        step=2,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_MAX_TOOL_ITERATIONS,
                    description={
                        "suggested_value": current.get(
                            CONF_MAX_TOOL_ITERATIONS,
                            DEFAULT_MAX_TOOL_ITERATIONS,
                        )
                    },
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=20,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_ENABLE_STREAMING,
                    description={
                        "suggested_value": current.get(
                            CONF_ENABLE_STREAMING, DEFAULT_ENABLE_STREAMING
                        )
                    },
                ): BooleanSelector(),
                vol.Optional(
                    CONF_ENABLE_VISION,
                    description={
                        "suggested_value": current.get(
                            CONF_ENABLE_VISION, DEFAULT_ENABLE_VISION
                        )
                    },
                ): BooleanSelector(),
                vol.Optional(
                    CONF_TIMEOUT,
                    description={
                        "suggested_value": current.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
                    },
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=10,
                        max=300,
                        step=5,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_RETRY_COUNT,
                    description={
                        "suggested_value": current.get(
                            CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT
                        )
                    },
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=5,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PROMPT,
                    description={
                        "suggested_value": current.get(CONF_PROMPT, DEFAULT_PROMPT)
                    },
                ): TemplateSelector(),
            }
        )
        return self.async_show_form(
            step_id="chat_settings", data_schema=schema, errors=errors
        )

    async def async_step_model_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure filtering, fallback, and automatic model updates."""
        current = dict(self.config_entry.options)
        only_free = bool(
            current.get(CONF_ONLY_FREE_MODELS, DEFAULT_ONLY_FREE_MODELS)
        )
        models = await self._async_get_models(only_free=only_free)
        available = {model["id"] for model in models}
        fallback = current.get(CONF_FALLBACK_MODEL, AUTO_FALLBACK_MODEL)
        if fallback != AUTO_FALLBACK_MODEL and fallback not in available:
            fallback = AUTO_FALLBACK_MODEL

        if user_input is not None:
            new_only_free = bool(
                user_input.get(CONF_ONLY_FREE_MODELS, DEFAULT_ONLY_FREE_MODELS)
            )
            new_models = await self._async_get_models(only_free=new_only_free)
            new_available = {model["id"] for model in new_models}
            new_options = dict(current)
            new_options.update(user_input)
            require_tools = bool(
                new_options.get(
                    CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
                )
                and new_options.get(CONF_LLM_HASS_API)
            )
            if new_options.get(CONF_CHAT_MODEL) not in new_available:
                new_options[CONF_CHAT_MODEL] = choose_default_model(
                    new_models,
                    require_tools=require_tools,
                    preferred=new_options.get(
                        CONF_FALLBACK_MODEL, AUTO_FALLBACK_MODEL
                    ),
                )
            if new_options.get(CONF_FALLBACK_MODEL) not in (
                AUTO_FALLBACK_MODEL,
                *new_available,
            ):
                new_options[CONF_FALLBACK_MODEL] = AUTO_FALLBACK_MODEL
            return self.async_create_entry(data=new_options)

        fallback_options = [
            {
                "label": "Automatisch / Automatic (empfohlen)",
                "value": AUTO_FALLBACK_MODEL,
            },
            *[
                {"label": model_label(model), "value": model["id"]}
                for model in models
            ],
        ]
        return self.async_show_form(
            step_id="model_settings",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ONLY_FREE_MODELS,
                        description={"suggested_value": only_free},
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_FALLBACK_MODEL,
                        description={"suggested_value": fallback},
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=fallback_options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_AUTO_UPDATE_MODELS,
                        description={
                            "suggested_value": current.get(
                                CONF_AUTO_UPDATE_MODELS,
                                DEFAULT_AUTO_UPDATE_MODELS,
                            )
                        },
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_MODEL_REFRESH_INTERVAL,
                        description={
                            "suggested_value": current.get(
                                CONF_MODEL_REFRESH_INTERVAL,
                                DEFAULT_MODEL_REFRESH_INTERVAL,
                            )
                        },
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MODEL_REFRESH_MIN_HOURS,
                            max=MODEL_REFRESH_MAX_HOURS,
                            step=1,
                            unit_of_measurement="h",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )

    async def async_step_control_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure Home Assistant's built-in LLM tools."""
        current = dict(self.config_entry.options)
        api_options = [
            {"label": api.name, "value": api.id}
            for api in llm.async_get_apis(self.hass)
        ]
        valid_api_ids = {option["value"] for option in api_options}
        selected = current.get(CONF_LLM_HASS_API, [])
        if isinstance(selected, str):
            selected = [selected]
        selected = [api for api in selected if api in valid_api_ids]

        if user_input is not None:
            new_options = dict(current)
            enabled = bool(
                user_input.get(
                    CONF_ENABLE_DEVICE_CONTROL,
                    DEFAULT_ENABLE_DEVICE_CONTROL,
                )
            )
            new_options[CONF_ENABLE_DEVICE_CONTROL] = enabled
            new_options[CONF_TOKEN_SAVING_MODE] = bool(
                user_input.get(CONF_TOKEN_SAVING_MODE, DEFAULT_TOKEN_SAVING_MODE)
            )
            new_options[CONF_ENABLE_EXTENDED_DEVICE_QUERIES] = bool(
                user_input.get(
                    CONF_ENABLE_EXTENDED_DEVICE_QUERIES,
                    DEFAULT_ENABLE_EXTENDED_DEVICE_QUERIES,
                )
            )
            new_options[CONF_DEVICE_QUERY_MAX_RESULTS] = int(
                user_input.get(
                    CONF_DEVICE_QUERY_MAX_RESULTS,
                    DEFAULT_DEVICE_QUERY_MAX_RESULTS,
                )
            )
            chosen_apis = user_input.get(CONF_LLM_HASS_API, [])
            if enabled and not chosen_apis:
                default_api = _default_llm_api(self.hass)
                chosen_apis = [default_api] if default_api else []
            chosen_apis = [api for api in chosen_apis if api in valid_api_ids]
            if chosen_apis:
                new_options[CONF_LLM_HASS_API] = chosen_apis
            else:
                new_options.pop(CONF_LLM_HASS_API, None)
                new_options[CONF_ENABLE_DEVICE_CONTROL] = False
            return self.async_create_entry(data=new_options)

        return self.async_show_form(
            step_id="control_settings",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_DEVICE_CONTROL,
                        description={
                            "suggested_value": current.get(
                                CONF_ENABLE_DEVICE_CONTROL,
                                DEFAULT_ENABLE_DEVICE_CONTROL,
                            )
                        },
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_TOKEN_SAVING_MODE,
                        description={
                            "suggested_value": current.get(
                                CONF_TOKEN_SAVING_MODE, DEFAULT_TOKEN_SAVING_MODE
                            )
                        },
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_ENABLE_EXTENDED_DEVICE_QUERIES,
                        description={
                            "suggested_value": current.get(
                                CONF_ENABLE_EXTENDED_DEVICE_QUERIES,
                                DEFAULT_ENABLE_EXTENDED_DEVICE_QUERIES,
                            )
                        },
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_DEVICE_QUERY_MAX_RESULTS,
                        description={
                            "suggested_value": current.get(
                                CONF_DEVICE_QUERY_MAX_RESULTS,
                                DEFAULT_DEVICE_QUERY_MAX_RESULTS,
                            )
                        },
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=5,
                            max=100,
                            step=5,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_LLM_HASS_API,
                        description={"suggested_value": selected},
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=api_options,
                            multiple=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_usage_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure local reference limits used for warnings."""
        current = dict(self.config_entry.options)
        if user_input is not None:
            new_options = dict(current)
            new_options.update(user_input)
            return self.async_create_entry(data=new_options)

        fields = (
            (CONF_REFERENCE_TOKEN_LIMIT_24H, 100_000_000, 10_000),
            (CONF_REFERENCE_REQUEST_LIMIT_HOUR, 100_000, 1),
            (CONF_REFERENCE_REQUEST_LIMIT_MINUTE, 10_000, 1),
            (CONF_REFERENCE_REQUEST_LIMIT_SECOND, 1_000, 1),
        )
        schema: dict[Any, Any] = {}
        for key, maximum, step in fields:
            schema[
                vol.Optional(
                    key,
                    description={
                        "suggested_value": current.get(
                            key, DEFAULT_REFERENCE_LIMIT
                        )
                    },
                )
            ] = NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=maximum,
                    step=step,
                    mode=NumberSelectorMode.BOX,
                )
            )
        return self.async_show_form(
            step_id="usage_settings", data_schema=vol.Schema(schema)
        )

    async def _async_get_models(
        self, only_free: bool | None = None
    ) -> list[dict[str, Any]]:
        current_only_free = bool(
            self.config_entry.options.get(
                CONF_ONLY_FREE_MODELS, DEFAULT_ONLY_FREE_MODELS
            )
        )
        if only_free is None:
            only_free = current_only_free
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime and only_free == current_only_free:
            manager = runtime.model_manager
            if manager.models:
                try:
                    return await manager.async_refresh(force=False)
                except LLM7Error:
                    return manager.models

        provider = normalize_provider(self.config_entry.data.get(CONF_PROVIDER))
        api_key = _api_key_for_provider(provider, dict(self.config_entry.data))
        try:
            return await _fetch_models(
                self.hass, provider, api_key, only_free=bool(only_free)
            )
        except LLM7Error:
            return load_bundled_models(
                allow_paid=bool(api_key) and not bool(only_free),
                provider=provider,
            )


async def _fetch_models(
    hass: HomeAssistant,
    provider: str,
    api_key: str,
    *,
    only_free: bool,
) -> list[dict[str, Any]]:
    client = LLM7Client(hass, api_key, provider=provider)
    raw_models = await client.async_get_models()
    models = normalize_models(
        raw_models,
        allow_paid=client.has_api_key and not only_free,
    )
    if not models:
        raise LLM7Error(
            f"Keine nutzbaren Chat-Modelle bei {client.provider_name} gefunden."
        )
    return models


def _default_llm_api(hass: HomeAssistant) -> str | None:
    apis = llm.async_get_apis(hass)
    for api in apis:
        if "assist" in f"{api.id} {api.name}".casefold():
            return api.id
    return apis[0].id if apis else None
