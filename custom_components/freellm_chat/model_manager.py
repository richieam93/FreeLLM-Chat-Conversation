"""Dynamic LLM7 model discovery, caching, and fallback selection."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import LLM7Client, LLM7Error
from .const import (
    AUTO_FALLBACK_MODEL,
    CONF_AUTO_UPDATE_MODELS,
    CONF_CHAT_MODEL,
    CONF_ENABLE_DEVICE_CONTROL,
    CONF_FALLBACK_MODEL,
    CONF_MODEL_REFRESH_INTERVAL,
    CONF_ONLY_FREE_MODELS,
    DEFAULT_AUTO_UPDATE_MODELS,
    DEFAULT_CHAT_MODEL,
    DEFAULT_ENABLE_DEVICE_CONTROL,
    DEFAULT_MODEL_REFRESH_INTERVAL,
    DEFAULT_ONLY_FREE_MODELS,
    MODEL_CACHE_MAX_AGE,
    MODEL_REFRESH_MAX_HOURS,
    MODEL_REFRESH_MIN_HOURS,
    MODEL_REFRESH_THROTTLE,
    PREFERRED_FREE_MODELS,
)

_LOGGER = logging.getLogger(__name__)
_CACHE_VERSION = 3


class ModelManager:
    """Keep an up-to-date list of usable chat models."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: LLM7Client,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.models: list[dict[str, Any]] = []
        self.last_update: datetime | None = None
        self.last_attempt: datetime | None = None
        self.last_error: str | None = None
        self.catalog_source = "bundled"
        self.last_fallback_from: str | None = None
        self.last_fallback_at: datetime | None = None
        self._listeners: set[Callable[[], None]] = set()
        self._unsub_interval: Callable[[], None] | None = None
        self._refresh_lock = asyncio.Lock()
        self._initial_refresh_task: asyncio.Task[None] | None = None
        self._store: Store[dict[str, Any]] = Store(
            hass, _CACHE_VERSION, f"{entry.domain}.models.{entry.entry_id}"
        )

    @property
    def allow_paid(self) -> bool:
        """Return whether token-only/usage-based models should be shown."""
        return self.client.has_api_key and not self.entry.options.get(
            CONF_ONLY_FREE_MODELS, DEFAULT_ONLY_FREE_MODELS
        )

    @property
    def requires_tools(self) -> bool:
        """Return whether the active configuration requires tool calling."""
        return bool(
            self.entry.options.get(
                CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
            )
            and self.entry.options.get(CONF_LLM_HASS_API)
        )

    @property
    def cache_is_stale(self) -> bool:
        """Return whether the last successful catalog is older than the target age."""
        return bool(
            self.last_update
            and dt_util.utcnow() - self.last_update > MODEL_CACHE_MAX_AGE
        )

    @property
    def status(self) -> str:
        """Return a compact catalog state for entities and diagnostics."""
        if self.catalog_source == "live":
            return "live"
        if self.catalog_source == "cache":
            return "stale_cache" if self.cache_is_stale else "cache"
        return "bundled"

    async def async_initialize(self) -> None:
        """Load immediately available models and refresh in the background."""
        await self._async_load_cache()
        if not self.models or not _has_compatible_model(
            self.models, require_tools=self.requires_tools
        ):
            self.models = load_bundled_models(allow_paid=self.allow_paid)
            self.catalog_source = "bundled"
        await self.async_ensure_valid_model(require_tools=self.requires_tools)
        self._schedule_updates()
        self._initial_refresh_task = self.hass.async_create_task(
            self._async_initial_refresh(),
            name=f"{self.entry.domain}_model_refresh_{self.entry.entry_id}",
        )

    async def _async_initial_refresh(self) -> None:
        try:
            await self.async_refresh(force=True)
        except LLM7Error as err:
            _LOGGER.warning("Could not refresh LLM7 models at startup: %s", err)

    async def async_shutdown(self) -> None:
        """Stop automatic updates."""
        if self._unsub_interval:
            self._unsub_interval()
            self._unsub_interval = None
        if self._initial_refresh_task and not self._initial_refresh_task.done():
            self._initial_refresh_task.cancel()
        self._initial_refresh_task = None

    async def async_refresh(self, force: bool = False) -> list[dict[str, Any]]:
        """Refresh model metadata from LLM7 without discarding a working cache."""
        async with self._refresh_lock:
            now = dt_util.utcnow()
            if (
                not force
                and self.last_attempt
                and now - self.last_attempt < MODEL_REFRESH_THROTTLE
            ):
                return self.models

            self.last_attempt = now
            try:
                raw_models = await self.client.async_get_models()
                models = normalize_models(raw_models, allow_paid=self.allow_paid)
                if not models:
                    raise LLM7Error(
                        "LLM7.io lieferte keine nutzbaren Chat-Modelle für "
                        "diese Konfiguration."
                    )
                if not _has_compatible_model(
                    models, require_tools=self.requires_tools
                ):
                    raise LLM7Error(
                        "Der aktuelle LLM7-Modellkatalog enthält kein Modell "
                        "für die aktivierte Home-Assistant-Gerätesteuerung."
                    )
            except LLM7Error as err:
                self.last_error = str(err)
                self._notify_listeners()
                raise

            self.models = models
            self.last_update = now
            self.last_error = None
            self.catalog_source = "live"
            await self._store.async_save(
                {
                    "updated_at": self.last_update.isoformat(),
                    "models": self.models,
                }
            )
            await self.async_ensure_valid_model(require_tools=self.requires_tools)
            self._notify_listeners()
            return self.models

    async def async_ensure_valid_model(
        self,
        require_tools: bool = False,
        require_vision: bool = False,
    ) -> str:
        """Return a compatible model and persist a fallback when needed."""
        if not _has_compatible_model(
            self.models,
            require_tools=require_tools,
            require_vision=require_vision,
        ):
            required = []
            if require_tools:
                required.append("Gerätesteuerung")
            if require_vision:
                required.append("Bildeingaben")
            description = " und ".join(required) or "die aktuelle Anfrage"
            raise LLM7Error(
                f"Kein verfügbares Modell unterstützt {description}."
            )

        selected = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        valid = self.get_model(selected)
        if valid and model_is_compatible(
            valid, require_tools=require_tools, require_vision=require_vision
        ):
            return selected

        preferred = self.entry.options.get(
            CONF_FALLBACK_MODEL, AUTO_FALLBACK_MODEL
        )
        fallback = choose_default_model(
            self.models,
            require_tools=require_tools,
            require_vision=require_vision,
            preferred=preferred,
        )
        if fallback != selected:
            options = dict(self.entry.options)
            options[CONF_CHAT_MODEL] = fallback
            if (
                preferred != AUTO_FALLBACK_MODEL
                and self.get_model(str(preferred)) is None
            ):
                options[CONF_FALLBACK_MODEL] = AUTO_FALLBACK_MODEL
            self.hass.config_entries.async_update_entry(self.entry, options=options)
            self.last_fallback_from = str(selected)
            self.last_fallback_at = dt_util.utcnow()
            self._notify_listeners()
            _LOGGER.warning(
                "Configured model %s is unavailable or incompatible; switched to %s",
                selected,
                fallback,
            )
        return fallback

    async def async_select_model(self, model_id: str) -> None:
        """Select a model from an entity or service call."""
        model = self.get_model(model_id)
        if model is None:
            raise LLM7Error(f"Das Modell {model_id} ist nicht verfügbar.")
        require_tools = self.requires_tools
        if require_tools and not model_supports_tools(model):
            raise LLM7Error(
                f"Das Modell {model_id} unterstützt keine Gerätesteuerung."
            )
        options = dict(self.entry.options)
        options[CONF_CHAT_MODEL] = model_id
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        self._notify_listeners()

    async def async_select_default_model(self) -> str:
        """Select the best current fallback model."""
        require_tools = self.requires_tools
        preferred = self.entry.options.get(
            CONF_FALLBACK_MODEL, AUTO_FALLBACK_MODEL
        )
        model_id = choose_default_model(
            self.models,
            require_tools=require_tools,
            preferred=preferred,
        )
        await self.async_select_model(model_id)
        return model_id

    def get_model(self, model_id: str) -> dict[str, Any] | None:
        """Return model metadata by ID."""
        return next(
            (model for model in self.models if model["id"] == model_id), None
        )

    def selector_options(
        self,
        require_tools: bool = False,
        require_vision: bool = False,
    ) -> list[dict[str, str]]:
        """Return Home Assistant selector options."""
        return [
            {"label": model_label(model), "value": model["id"]}
            for model in self.models
            if model_is_compatible(
                model,
                require_tools=require_tools,
                require_vision=require_vision,
            )
        ]

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a state listener."""
        self._listeners.add(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    async def _async_load_cache(self) -> None:
        cached = await self._store.async_load()
        if not isinstance(cached, dict):
            return

        cached_models = cached.get("models")
        if isinstance(cached_models, list):
            self.models = normalize_models(
                [model for model in cached_models if isinstance(model, dict)],
                allow_paid=self.allow_paid,
            )
            if self.models:
                self.catalog_source = "cache"

        updated_at = cached.get("updated_at")
        if not isinstance(updated_at, str):
            return
        try:
            parsed = datetime.fromisoformat(updated_at)
        except ValueError:
            return
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        self.last_update = parsed

    def _schedule_updates(self) -> None:
        if self._unsub_interval:
            self._unsub_interval()
            self._unsub_interval = None
        if not self.entry.options.get(
            CONF_AUTO_UPDATE_MODELS, DEFAULT_AUTO_UPDATE_MODELS
        ):
            return

        configured_hours = _safe_int(
            self.entry.options.get(
                CONF_MODEL_REFRESH_INTERVAL, DEFAULT_MODEL_REFRESH_INTERVAL
            ),
            DEFAULT_MODEL_REFRESH_INTERVAL,
        )
        hours = max(
            MODEL_REFRESH_MIN_HOURS,
            min(configured_hours, MODEL_REFRESH_MAX_HOURS),
        )

        async def refresh_models(_: datetime) -> None:
            try:
                await self.async_refresh(force=True)
            except LLM7Error as err:
                _LOGGER.warning("Automatic LLM7 model refresh failed: %s", err)

        self._unsub_interval = async_track_time_interval(
            self.hass, refresh_models, timedelta(hours=hours)
        )

    @callback
    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:  # pragma: no cover - defensive entity callback guard
                _LOGGER.exception("Error notifying a model update listener")


def normalize_models(
    raw_models: list[dict[str, Any]], *, allow_paid: bool
) -> list[dict[str, Any]]:
    """Filter and normalize models usable by OpenAI chat completions."""
    candidates: list[dict[str, Any]] = []
    for raw in raw_models:
        model_id = raw.get("id")
        if not isinstance(model_id, str) or not model_id.strip():
            continue
        if raw.get("model_type", "chat") != "chat":
            continue
        endpoints = raw.get("schema_endpoints", ["openai"])
        if isinstance(endpoints, list) and "openai" not in endpoints:
            continue
        if not allow_paid and raw.get("usage_based_only") is True:
            continue

        capabilities = raw.get("capabilities")
        if not isinstance(capabilities, dict):
            capabilities = {}
        modalities = raw.get("modalities")
        if not isinstance(modalities, dict):
            modalities = {}
        context_window = raw.get("context_window")
        if not isinstance(context_window, dict):
            context_window = {}

        candidates.append(
            {
                "id": model_id.strip(),
                "owned_by": raw.get("owned_by") or "",
                "tier": raw.get("tier") or "",
                "usage_based_only": bool(raw.get("usage_based_only", False)),
                "stream": bool(raw.get("stream", capabilities.get("stream", False))),
                "json_mode": bool(
                    raw.get("json_mode", capabilities.get("json_mode", False))
                ),
                "reasoning": bool(
                    raw.get("reasoning", capabilities.get("reasoning", False))
                ),
                "tools_calling": bool(
                    raw.get(
                        "tools_calling",
                        capabilities.get(
                            "tools", capabilities.get("tools_calling", False)
                        ),
                    )
                ),
                "modalities": modalities,
                "context_window": context_window,
                "capabilities": capabilities,
                "supported_image_mime_types": list(
                    raw.get(
                        "supported_image_mime_types",
                        capabilities.get("supported_image_mime_types", []),
                    )
                )
                if isinstance(
                    raw.get(
                        "supported_image_mime_types",
                        capabilities.get("supported_image_mime_types", []),
                    ),
                    list,
                )
                else [],
                "max_reference_image_bytes": raw.get(
                    "max_reference_image_bytes",
                    capabilities.get("max_reference_image_bytes"),
                ),
            }
        )

    return sorted(
        candidates,
        key=lambda item: (
            item.get("usage_based_only", False),
            not model_supports_tools(item),
            not model_supports_vision(item),
            item["id"].casefold(),
        ),
    )



def _has_compatible_model(
    models: list[dict[str, Any]],
    *,
    require_tools: bool = False,
    require_vision: bool = False,
) -> bool:
    """Return whether at least one model satisfies all active requirements."""
    return any(
        model_is_compatible(
            model,
            require_tools=require_tools,
            require_vision=require_vision,
        )
        for model in models
    )

def choose_default_model(
    models: list[dict[str, Any]],
    *,
    require_tools: bool = False,
    require_vision: bool = False,
    preferred: Any = AUTO_FALLBACK_MODEL,
) -> str:
    """Choose a stable fallback from the currently available models."""
    eligible = [
        model
        for model in models
        if model_is_compatible(
            model,
            require_tools=require_tools,
            require_vision=require_vision,
        )
    ]
    if not eligible:
        eligible = [
            model
            for model in models
            if model_is_compatible(model, require_tools=require_tools)
        ]
    if not eligible:
        eligible = models

    ids = {model["id"] for model in eligible}
    if isinstance(preferred, str) and preferred in ids:
        return preferred
    for preferred_id in PREFERRED_FREE_MODELS:
        if preferred_id in ids:
            return preferred_id

    token_free = [model for model in eligible if model_is_token_free(model)]
    if token_free:
        return token_free[0]["id"]
    return eligible[0]["id"] if eligible else DEFAULT_CHAT_MODEL


def model_is_compatible(
    model: dict[str, Any],
    *,
    require_tools: bool = False,
    require_vision: bool = False,
) -> bool:
    """Return whether a model satisfies the requested capabilities."""
    return not (
        (require_tools and not model_supports_tools(model))
        or (require_vision and not model_supports_vision(model))
    )


def model_supports_tools(model: dict[str, Any]) -> bool:
    """Return whether the model advertises tool calling."""
    if "tools_calling" in model:
        return bool(model["tools_calling"])
    capabilities = model.get("capabilities")
    if isinstance(capabilities, dict):
        return bool(
            capabilities.get("tools", capabilities.get("tools_calling", False))
        )
    return False


def model_supports_vision(model: dict[str, Any]) -> bool:
    """Return whether the model accepts image input."""
    modalities = model.get("modalities")
    return bool(
        isinstance(modalities, dict)
        and isinstance(modalities.get("input"), list)
        and "image" in modalities["input"]
    )


def model_supports_streaming(model: dict[str, Any]) -> bool:
    """Return whether the model advertises streaming."""
    if "stream" in model:
        return bool(model["stream"])
    capabilities = model.get("capabilities")
    return bool(isinstance(capabilities, dict) and capabilities.get("stream"))


def model_is_token_free(model: dict[str, Any]) -> bool:
    """Return whether the catalog marks the model as usable without token billing."""
    return not bool(model.get("usage_based_only", False))


def model_label(model: dict[str, Any]) -> str:
    """Build a useful but compact model label."""
    tags: list[str] = []
    tags.append("ohne Token" if model_is_token_free(model) else "Token")
    if model_supports_tools(model):
        tags.append("Geräte")
    if model_supports_vision(model):
        tags.append("Bilder")
    if model_supports_streaming(model):
        tags.append("Streaming")
    if model.get("reasoning"):
        tags.append("Reasoning")

    context_window = model.get("context_window")
    tokens = context_window.get("tokens") if isinstance(context_window, dict) else None
    if isinstance(tokens, int) and tokens > 0:
        tags.append(_format_token_count(tokens))
    return f"{model['id']} — {', '.join(tags)}"


def load_bundled_models(*, allow_paid: bool) -> list[dict[str, Any]]:
    """Load the bundled emergency catalog."""
    path = Path(__file__).with_name("fallback_models.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [
            {
                "id": DEFAULT_CHAT_MODEL,
                "usage_based_only": False,
                "tools_calling": True,
                "stream": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "capabilities": {"tools": True, "stream": True},
            }
        ]
    if not isinstance(data, list):
        return [_minimal_default_model()]
    models = normalize_models(
        [model for model in data if isinstance(model, dict)],
        allow_paid=allow_paid,
    )
    return models or [_minimal_default_model()]


def _minimal_default_model() -> dict[str, Any]:
    return {
        "id": DEFAULT_CHAT_MODEL,
        "usage_based_only": False,
        "tools_calling": True,
        "stream": True,
        "reasoning": False,
        "modalities": {"input": ["text"], "output": ["text"]},
        "context_window": {},
        "capabilities": {"tools": True, "stream": True},
    }


def _format_token_count(tokens: int) -> str:
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:g}M Kontext"
    if tokens >= 1_000:
        return f"{tokens / 1_000:g}k Kontext"
    return f"{tokens} Kontext"


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
