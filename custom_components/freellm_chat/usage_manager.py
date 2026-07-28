"""Persistent local usage statistics for FreeLLM Chat."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import LLM7Client
from .const import (
    CONF_REFERENCE_REQUEST_LIMIT_HOUR,
    CONF_REFERENCE_REQUEST_LIMIT_MINUTE,
    CONF_REFERENCE_REQUEST_LIMIT_SECOND,
    CONF_REFERENCE_TOKEN_LIMIT_24H,
)

_STORE_VERSION = 1
_MAX_EVENTS = 10_000
_RETENTION = timedelta(days=7)

# Reference limits published by LLM7.io. They can change without notice and are
# intentionally exposed as estimates, never as authoritative server balances.
ANONYMOUS_TOKEN_LIMIT_24H = 500_000
ANONYMOUS_REQUEST_LIMIT_HOUR = 60
ANONYMOUS_REQUEST_LIMIT_MINUTE = 10
ANONYMOUS_REQUEST_LIMIT_SECOND = 1
FREE_TOKEN_TOKEN_LIMIT_24H = 1_000_000
FREE_TOKEN_REQUEST_LIMIT_HOUR = 250
FREE_TOKEN_REQUEST_LIMIT_MINUTE = 60
FREE_TOKEN_REQUEST_LIMIT_SECOND = 2


class UsageManager:
    """Track local conversations, API calls, tokens, and recent failures."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: LLM7Client,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.total_conversations = 0
        self.total_api_requests = 0
        self.successful_api_requests = 0
        self.failed_api_requests = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.last_request_at: datetime | None = None
        self.last_success_at: datetime | None = None
        self.last_failure_at: datetime | None = None
        self.last_model: str | None = None
        self.last_provider_model: str | None = None
        self.last_latency_ms: int | None = None
        self.last_error: str | None = None
        self.last_status: int | None = None
        self._events: list[dict[str, Any]] = []
        self._listeners: set[Callable[[], None]] = set()
        self._lock = asyncio.Lock()
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORE_VERSION, f"{entry.domain}.usage.{entry.entry_id}"
        )

    @property
    def access_mode(self) -> str:
        """Return the locally detectable access mode."""
        return "token" if self.client.has_api_key else "anonymous"

    @property
    def reference_token_limit_24h(self) -> int:
        """Return the configured or published reference token quota."""
        default = (
            FREE_TOKEN_TOKEN_LIMIT_24H
            if self.client.has_api_key
            else ANONYMOUS_TOKEN_LIMIT_24H
        )
        return self._configured_limit(CONF_REFERENCE_TOKEN_LIMIT_24H, default)

    @property
    def reference_request_limit_hour(self) -> int:
        """Return the configured or published hourly request limit."""
        default = (
            FREE_TOKEN_REQUEST_LIMIT_HOUR
            if self.client.has_api_key
            else ANONYMOUS_REQUEST_LIMIT_HOUR
        )
        return self._configured_limit(CONF_REFERENCE_REQUEST_LIMIT_HOUR, default)

    @property
    def reference_request_limit_minute(self) -> int:
        """Return the configured or published per-minute request limit."""
        default = (
            FREE_TOKEN_REQUEST_LIMIT_MINUTE
            if self.client.has_api_key
            else ANONYMOUS_REQUEST_LIMIT_MINUTE
        )
        return self._configured_limit(CONF_REFERENCE_REQUEST_LIMIT_MINUTE, default)

    @property
    def reference_request_limit_second(self) -> int:
        """Return the configured or published per-second request limit."""
        default = (
            FREE_TOKEN_REQUEST_LIMIT_SECOND
            if self.client.has_api_key
            else ANONYMOUS_REQUEST_LIMIT_SECOND
        )
        return self._configured_limit(CONF_REFERENCE_REQUEST_LIMIT_SECOND, default)

    def _configured_limit(self, key: str, default: int) -> int:
        """Return a positive custom limit, or the access-mode default."""
        value = _safe_non_negative_int(self.entry.options.get(key))
        return value if value > 0 else default

    @property
    def requests_24h(self) -> int:
        return len(self._recent_events(timedelta(hours=24)))

    @property
    def requests_hour(self) -> int:
        return len(self._recent_events(timedelta(hours=1)))

    @property
    def requests_minute(self) -> int:
        return len(self._recent_events(timedelta(minutes=1)))

    @property
    def requests_second(self) -> int:
        return len(self._recent_events(timedelta(seconds=1)))

    @property
    def successful_requests_24h(self) -> int:
        return sum(
            1 for event in self._recent_events(timedelta(hours=24))
            if event.get("success") is True
        )

    @property
    def failed_requests_24h(self) -> int:
        return sum(
            1 for event in self._recent_events(timedelta(hours=24))
            if event.get("success") is False
        )

    @property
    def tokens_24h(self) -> int:
        return sum(
            _safe_non_negative_int(event.get("total_tokens"))
            for event in self._recent_events(timedelta(hours=24))
        )

    @property
    def estimated_tokens_remaining_24h(self) -> int:
        """Return a local estimate; this is not the provider account balance."""
        return max(0, self.reference_token_limit_24h - self.tokens_24h)

    @property
    def quota_usage_percent(self) -> float:
        """Return locally observed 24-hour token use as a percentage."""
        limit = self.reference_token_limit_24h
        return round(min(100.0, self.tokens_24h / limit * 100), 1) if limit else 0.0

    @property
    def request_hour_usage_percent(self) -> float:
        """Return locally observed hourly request use as a percentage."""
        limit = self.reference_request_limit_hour
        return round(min(100.0, self.requests_hour / limit * 100), 1) if limit else 0.0

    @property
    def request_minute_usage_percent(self) -> float:
        """Return locally observed per-minute request use as a percentage."""
        limit = self.reference_request_limit_minute
        return round(min(100.0, self.requests_minute / limit * 100), 1) if limit else 0.0

    @property
    def request_second_usage_percent(self) -> float:
        """Return locally observed per-second request use as a percentage."""
        limit = self.reference_request_limit_second
        return round(min(100.0, self.requests_second / limit * 100), 1) if limit else 0.0

    @property
    def highest_reference_usage_percent(self) -> float:
        """Return the highest locally observed reference-limit percentage."""
        return max(
            self.quota_usage_percent,
            self.request_hour_usage_percent,
            self.request_minute_usage_percent,
            self.request_second_usage_percent,
        )

    @property
    def limiting_metric(self) -> str:
        """Return the reference limit currently closest to exhaustion."""
        values = {
            "tokens_24h": self.quota_usage_percent,
            "requests_hour": self.request_hour_usage_percent,
            "requests_minute": self.request_minute_usage_percent,
            "requests_second": self.request_second_usage_percent,
        }
        return max(values, key=values.get)

    @property
    def estimated_requests_remaining_hour(self) -> int:
        return max(0, self.reference_request_limit_hour - self.requests_hour)

    @property
    def estimated_requests_remaining_minute(self) -> int:
        return max(0, self.reference_request_limit_minute - self.requests_minute)

    @property
    def estimated_requests_remaining_second(self) -> int:
        return max(0, self.reference_request_limit_second - self.requests_second)

    @property
    def quota_status(self) -> str:
        """Return a local reference-limit state."""
        token_ratio = self.tokens_24h / max(1, self.reference_token_limit_24h)
        hour_ratio = self.requests_hour / max(1, self.reference_request_limit_hour)
        minute_ratio = self.requests_minute / max(
            1, self.reference_request_limit_minute
        )
        second_ratio = self.requests_second / max(
            1, self.reference_request_limit_second
        )
        ratio = max(token_ratio, hour_ratio, minute_ratio, second_ratio)
        if ratio >= 1:
            return "limit_reached"
        if ratio >= 0.8:
            return "warning"
        return "ok"

    async def async_initialize(self) -> None:
        """Load persisted statistics."""
        data = await self._store.async_load()
        if not isinstance(data, dict):
            return
        self.total_conversations = _safe_non_negative_int(
            data.get("total_conversations")
        )
        self.total_api_requests = _safe_non_negative_int(
            data.get("total_api_requests")
        )
        self.successful_api_requests = _safe_non_negative_int(
            data.get("successful_api_requests")
        )
        self.failed_api_requests = _safe_non_negative_int(
            data.get("failed_api_requests")
        )
        self.input_tokens = _safe_non_negative_int(data.get("input_tokens"))
        self.output_tokens = _safe_non_negative_int(data.get("output_tokens"))
        self.total_tokens = _safe_non_negative_int(data.get("total_tokens"))
        self.last_request_at = _parse_datetime(data.get("last_request_at"))
        self.last_success_at = _parse_datetime(data.get("last_success_at"))
        self.last_failure_at = _parse_datetime(data.get("last_failure_at"))
        self.last_model = _safe_optional_string(data.get("last_model"))
        self.last_provider_model = _safe_optional_string(
            data.get("last_provider_model")
        )
        self.last_latency_ms = _safe_optional_int(data.get("last_latency_ms"))
        self.last_error = _safe_optional_string(data.get("last_error"))
        self.last_status = _safe_optional_int(data.get("last_status"))
        events = data.get("events")
        if isinstance(events, list):
            self._events = [event for event in events if isinstance(event, dict)]
        self._prune_events()

    async def async_record_conversation(self) -> None:
        """Record one Home Assistant user conversation request."""
        async with self._lock:
            self.total_conversations += 1
            await self._async_save()
        self._notify_listeners()

    async def async_record_api_result(
        self,
        *,
        success: bool,
        model: str,
        data: dict[str, Any] | None = None,
        latency_ms: int | None = None,
        error: str | None = None,
        status: int | None = None,
    ) -> None:
        """Record one completed network attempt, including retries."""
        now = dt_util.utcnow()
        usage = data.get("usage") if isinstance(data, dict) else None
        input_tokens, output_tokens, total_tokens = _extract_usage(usage)
        provider_model = (
            _safe_optional_string(data.get("model"))
            if isinstance(data, dict)
            else None
        )

        async with self._lock:
            self.total_api_requests += 1
            self.last_request_at = now
            self.last_model = model
            self.last_provider_model = provider_model or self.last_provider_model
            self.last_latency_ms = latency_ms
            self.last_status = status
            if success:
                self.successful_api_requests += 1
                self.last_success_at = now
                self.last_error = None
                self.input_tokens += input_tokens
                self.output_tokens += output_tokens
                self.total_tokens += total_tokens
            else:
                self.failed_api_requests += 1
                self.last_failure_at = now
                self.last_error = error

            self._events.append(
                {
                    "timestamp": now.isoformat(),
                    "success": success,
                    "model": model,
                    "provider_model": provider_model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "latency_ms": latency_ms,
                    "status": status,
                }
            )
            self._prune_events()
            await self._async_save()
        self._notify_listeners()

    async def async_reset(self) -> None:
        """Reset all locally collected statistics."""
        async with self._lock:
            self.total_conversations = 0
            self.total_api_requests = 0
            self.successful_api_requests = 0
            self.failed_api_requests = 0
            self.input_tokens = 0
            self.output_tokens = 0
            self.total_tokens = 0
            self.last_request_at = None
            self.last_success_at = None
            self.last_failure_at = None
            self.last_model = None
            self.last_provider_model = None
            self.last_latency_ms = None
            self.last_error = None
            self.last_status = None
            self._events = []
            await self._async_save()
        self._notify_listeners()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(listener)

        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    @callback
    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    def _recent_events(self, period: timedelta) -> list[dict[str, Any]]:
        cutoff = dt_util.utcnow() - period
        return [
            event
            for event in self._events
            if (timestamp := _parse_datetime(event.get("timestamp")))
            and timestamp >= cutoff
        ]

    def _prune_events(self) -> None:
        cutoff = dt_util.utcnow() - _RETENTION
        self._events = [
            event
            for event in self._events
            if (timestamp := _parse_datetime(event.get("timestamp")))
            and timestamp >= cutoff
        ][-_MAX_EVENTS:]

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "total_conversations": self.total_conversations,
                "total_api_requests": self.total_api_requests,
                "successful_api_requests": self.successful_api_requests,
                "failed_api_requests": self.failed_api_requests,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
                "last_request_at": _serialize_datetime(self.last_request_at),
                "last_success_at": _serialize_datetime(self.last_success_at),
                "last_failure_at": _serialize_datetime(self.last_failure_at),
                "last_model": self.last_model,
                "last_provider_model": self.last_provider_model,
                "last_latency_ms": self.last_latency_ms,
                "last_error": self.last_error,
                "last_status": self.last_status,
                "events": self._events,
            }
        )


def _extract_usage(usage: Any) -> tuple[int, int, int]:
    if not isinstance(usage, dict):
        return 0, 0, 0
    input_tokens = _safe_non_negative_int(
        usage.get("prompt_tokens", usage.get("input_tokens"))
    )
    output_tokens = _safe_non_negative_int(
        usage.get("completion_tokens", usage.get("output_tokens"))
    )
    total_tokens = _safe_non_negative_int(usage.get("total_tokens"))
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    return input_tokens, output_tokens, total_tokens


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    return dt_util.as_utc(parsed) if parsed else None


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _safe_non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _safe_optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
