"""Asynchronous client for the LLM7 OpenAI-compatible API."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
import json
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import LLM7_CHAT_URL, LLM7_MODELS_URL


class LLM7Error(Exception):
    """Base exception for LLM7 errors."""


class LLM7AuthenticationError(LLM7Error):
    """Raised when the optional API token is rejected."""


class LLM7ConnectionError(LLM7Error):
    """Raised when LLM7 cannot be reached."""


class LLM7ResponseError(LLM7Error):
    """Raised when LLM7 returns an unexpected response."""

    def __init__(
        self,
        message: str,
        status: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class LLM7Client:
    """Client for model discovery and chat completions."""

    def __init__(self, hass: HomeAssistant, api_key: str | None = None) -> None:
        self._session = async_get_clientsession(hass)
        self._api_key = (api_key or "").strip() or None

    @property
    def has_api_key(self) -> bool:
        """Return whether an API token is configured."""
        return self._api_key is not None

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "FreeLLM-HomeAssistant/3.5.0",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def async_get_models(self, timeout: int = 20) -> list[dict[str, Any]]:
        """Fetch all models from LLM7."""
        data = await self._async_request("GET", LLM7_MODELS_URL, timeout=timeout)
        models = data.get("data") if isinstance(data, dict) else None
        if not isinstance(models, list):
            raise LLM7ResponseError("Die Modell-API lieferte keine gültige Liste.")
        return [model for model in models if isinstance(model, dict)]

    async def async_chat_completion(
        self,
        payload: dict[str, Any],
        timeout: int,
    ) -> dict[str, Any]:
        """Create a non-streaming chat completion."""
        request_payload = dict(payload)
        request_payload["stream"] = False
        data = await self._async_request(
            "POST", LLM7_CHAT_URL, json_data=request_payload, timeout=timeout
        )
        if not isinstance(data, dict):
            raise LLM7ResponseError("Die Chat-API lieferte keine gültige Antwort.")
        return data

    async def async_chat_completion_stream(
        self,
        payload: dict[str, Any],
        timeout: int,
    ) -> AsyncGenerator[dict[str, Any]]:
        """Yield OpenAI-compatible server-sent event chunks."""
        request_payload = dict(payload)
        request_payload["stream"] = True

        try:
            async with asyncio.timeout(timeout):
                async with self._session.post(
                    LLM7_CHAT_URL,
                    json=request_payload,
                    headers=self._headers(),
                ) as response:
                    if response.status >= 400:
                        await _raise_for_response(response)

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
                                "Die Streaming-Antwort enthielt ungültiges JSON."
                            ) from err
                        if isinstance(chunk, dict):
                            yield chunk
        except TimeoutError as err:
            raise LLM7ConnectionError("Zeitüberschreitung bei LLM7.io.") from err
        except aiohttp.ClientError as err:
            raise LLM7ConnectionError(
                f"Verbindung zu LLM7.io fehlgeschlagen: {err}"
            ) from err

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
                        await _raise_for_response(response)
                    data = await _read_json(response)
                    if not isinstance(data, dict):
                        raise LLM7ResponseError(
                            "Die API lieferte kein gültiges JSON-Objekt.",
                            response.status,
                        )
                    return data
        except TimeoutError as err:
            raise LLM7ConnectionError("Zeitüberschreitung bei LLM7.io.") from err
        except aiohttp.ClientError as err:
            raise LLM7ConnectionError(
                f"Verbindung zu LLM7.io fehlgeschlagen: {err}"
            ) from err


async def _raise_for_response(response: aiohttp.ClientResponse) -> None:
    """Raise a useful exception for an unsuccessful response."""
    data = await _read_json(response, allow_text=True)
    if response.status in (401, 403):
        raise LLM7AuthenticationError(
            "Der API-Token wurde abgelehnt. Ohne Token kann das Feld leer bleiben."
        )

    retry_after: float | None = None
    raw_retry_after = response.headers.get("Retry-After")
    if raw_retry_after:
        try:
            retry_after = max(0.0, float(raw_retry_after))
        except ValueError:
            retry_after = None

    message = _extract_error_message(data) or f"HTTP {response.status}"
    raise LLM7ResponseError(message, response.status, retry_after)


async def _read_json(
    response: aiohttp.ClientResponse,
    *,
    allow_text: bool = False,
) -> Any:
    """Read JSON and optionally preserve a short text error body."""
    try:
        return await response.json(content_type=None)
    except (aiohttp.ContentTypeError, ValueError, json.JSONDecodeError):
        text = await response.text()
        if allow_text:
            return {"message": text[:500]}
        raise LLM7ResponseError(
            f"Ungültige API-Antwort: {text[:200]}", response.status
        )


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
