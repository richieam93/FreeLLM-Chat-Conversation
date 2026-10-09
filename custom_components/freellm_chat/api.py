"""Asynchronous OpenAI-compatible provider client for FreeLLM Chat."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import json
from time import monotonic
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import INTEGRATION_VERSION
from .provider import (
    DEFAULT_PROVIDER,
    PROVIDER_LLM7,
    bundled_provider_models,
    normalize_provider,
    provider_chat_url,
    provider_dashboard_url,
    provider_docs_url,
    provider_min_chat_interval,
    provider_models_url,
    provider_name,
    provider_status_url,
    provider_web_url,
)


class LLM7Error(Exception):
    """Base exception for provider errors.

    The historical class name is retained to avoid a breaking internal API change.
    """


class LLM7ConnectionError(LLM7Error):
    """Raised when the configured provider cannot be reached."""


class LLM7ResponseError(LLM7Error):
    """Raised when the configured provider returns an unexpected response."""

    def __init__(
        self,
        message: str,
        status: int | None = None,
        retry_after: float | None = None,
        *,
        partial_response: bool = False,
        provider_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after
        self.partial_response = partial_response
        self.provider_name = provider_name


class LLM7AuthenticationError(LLM7ResponseError):
    """Raised when a configured provider access key is rejected."""


class LLM7Client:
    """Client for the selected OpenAI-compatible provider.

    The class keeps its original name for compatibility with the rest of the
    integration while supporting both LLM7.io and OVHcloud AI Endpoints.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str | None = None,
        *,
        provider: str = DEFAULT_PROVIDER,
    ) -> None:
        self._session = async_get_clientsession(hass)
        self._provider = normalize_provider(provider)
        self._api_key = (api_key or "").strip() or None
        self._chat_rate_lock = asyncio.Lock()
        self._last_chat_request_at: float | None = None

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def provider_name(self) -> str:
        return provider_name(self._provider)

    @property
    def website_url(self) -> str:
        return provider_web_url(self._provider)

    @property
    def dashboard_url(self) -> str:
        return provider_dashboard_url(self._provider)

    @property
    def docs_url(self) -> str:
        return provider_docs_url(self._provider)

    @property
    def status_url(self) -> str:
        return provider_status_url(self._provider)

    @property
    def has_api_key(self) -> bool:
        """Return whether an API access key is configured for the active provider."""
        return self._api_key is not None

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"FreeLLM-HomeAssistant/{INTEGRATION_VERSION}",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def async_get_models(self, timeout: int = 20) -> list[dict[str, Any]]:
        """Fetch or return the provider's supported model catalog."""
        models_url = provider_models_url(self._provider)
        if models_url is None:
            return bundled_provider_models(self._provider)

        data = await self._async_request("GET", models_url, timeout=timeout)
        models = data.get("data") if isinstance(data, dict) else None
        if not isinstance(models, list):
            raise LLM7ResponseError(
                f"{self.provider_name} lieferte keine gültige Modellliste.",
                provider_name=self.provider_name,
            )
        return [model for model in models if isinstance(model, dict)]

    async def async_chat_completion(
        self,
        payload: dict[str, Any],
        timeout: int,
    ) -> dict[str, Any]:
        """Create a non-streaming chat completion."""
        request_payload = dict(payload)
        request_payload["stream"] = False
        await self._async_wait_for_chat_slot()
        data = await self._async_request(
            "POST",
            provider_chat_url(self._provider),
            json_data=request_payload,
            timeout=timeout,
        )
        if not isinstance(data, dict):
            raise LLM7ResponseError(
                f"{self.provider_name} lieferte keine gültige Chat-Antwort.",
                provider_name=self.provider_name,
            )
        return data

    async def async_chat_completion_stream(
        self,
        payload: dict[str, Any],
        timeout: int,
    ) -> AsyncGenerator[dict[str, Any]]:
        """Yield OpenAI-compatible server-sent event chunks."""
        request_payload = dict(payload)
        request_payload["stream"] = True
        await self._async_wait_for_chat_slot()

        try:
            async with asyncio.timeout(timeout):
                async with self._session.post(
                    provider_chat_url(self._provider),
                    json=request_payload,
                    headers=self._headers(),
                ) as response:
                    if response.status >= 400:
                        await _raise_for_response(response, self.provider_name)

                    while not response.content.at_eof():
                        raw_line = await response.content.readline()
                        if not raw_line:
                            break
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line or line.startswith(":"):
                            continue
                        if not line.startswith("data:"):
                            continue

                        event_data = line[5:].strip()
                        if event_data == "[DONE]":
                            return
                        try:
                            chunk = json.loads(event_data)
                        except json.JSONDecodeError as err:
                            raise LLM7ResponseError(
                                "Die Streaming-Antwort enthielt ungültiges JSON.",
                                provider_name=self.provider_name,
                            ) from err
                        if isinstance(chunk, dict):
                            yield chunk
        except TimeoutError as err:
            raise LLM7ConnectionError(
                f"Zeitüberschreitung bei {self.provider_name}."
            ) from err
        except aiohttp.ClientError as err:
            raise LLM7ConnectionError(
                f"Verbindung zu {self.provider_name} fehlgeschlagen: {err}"
            ) from err

    async def _async_wait_for_chat_slot(self) -> None:
        """Space chat requests according to published provider access limits."""
        min_interval = provider_min_chat_interval(
            self._provider, self.has_api_key
        )
        async with self._chat_rate_lock:
            now = monotonic()
            if self._last_chat_request_at is not None:
                delay = min_interval - (now - self._last_chat_request_at)
                if delay > 0:
                    await asyncio.sleep(delay)
            self._last_chat_request_at = monotonic()

    async def _async_request(
        self,
        method: str,
        url: str,
        *,
        json_data: dict[str, Any] | None = None,
        timeout: int,
    ) -> dict[str, Any]:
        try:
            async with asyncio.timeout(timeout):
                async with self._session.request(
                    method,
                    url,
                    json=json_data,
                    headers=self._headers(),
                ) as response:
                    if response.status >= 400:
                        await _raise_for_response(response, self.provider_name)
                    data = await _read_json(
                        response, provider_name=self.provider_name
                    )
                    if not isinstance(data, dict):
                        raise LLM7ResponseError(
                            "Die API lieferte kein gültiges JSON-Objekt.",
                            response.status,
                            provider_name=self.provider_name,
                        )
                    return data
        except TimeoutError as err:
            raise LLM7ConnectionError(
                f"Zeitüberschreitung bei {self.provider_name}."
            ) from err
        except aiohttp.ClientError as err:
            raise LLM7ConnectionError(
                f"Verbindung zu {self.provider_name} fehlgeschlagen: {err}"
            ) from err


async def _raise_for_response(
    response: aiohttp.ClientResponse, provider_display_name: str
) -> None:
    """Raise a useful exception for an unsuccessful response."""
    data = await _read_json(
        response, allow_text=True, provider_name=provider_display_name
    )
    if response.status in (401, 403):
        raise LLM7AuthenticationError(
            f"Der API-Key für {provider_display_name} wurde abgelehnt. "
            "Für anonymen Zugriff kann das Feld leer bleiben, sofern der Anbieter "
            "dies für das gewählte Modell unterstützt.",
            response.status,
            provider_name=provider_display_name,
        )

    retry_after = _parse_retry_after(response.headers.get("Retry-After"))
    message = _extract_error_message(data) or f"HTTP {response.status}"
    raise LLM7ResponseError(
        message,
        response.status,
        retry_after,
        provider_name=provider_display_name,
    )


async def _read_json(
    response: aiohttp.ClientResponse,
    *,
    allow_text: bool = False,
    provider_name: str | None = None,
) -> Any:
    """Read JSON and optionally preserve a short text error body."""
    try:
        return await response.json(content_type=None)
    except (aiohttp.ContentTypeError, ValueError, json.JSONDecodeError):
        text = await response.text()
        if allow_text:
            return {"message": text[:500]}
        raise LLM7ResponseError(
            f"Ungültige API-Antwort: {text[:200]}",
            response.status,
            provider_name=provider_name,
        )


def _parse_retry_after(value: str | None) -> float | None:
    """Parse Retry-After as seconds or an HTTP date."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())


def _extract_error_message(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    error = data.get("error")
    if isinstance(error, str):
        return error
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
    message = data.get("message")
    return message if isinstance(message, str) else None
