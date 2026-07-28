"""Conversation entity for FreeLLM Chat."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import AsyncGenerator, AsyncIterable
from dataclasses import dataclass, field, replace
import json
import logging
from pathlib import Path
from time import monotonic
from typing import Any, Literal, override

from voluptuous_openapi import convert

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import LLM7Client, LLM7ConnectionError, LLM7Error, LLM7ResponseError
from .const import (
    CONF_DEVICE_QUERY_MAX_RESULTS,
    CONF_ENABLE_DEVICE_CONTROL,
    CONF_ENABLE_EXTENDED_DEVICE_QUERIES,
    CONF_ENABLE_STREAMING,
    CONF_ENABLE_VISION,
    CONF_HISTORY_LIMIT,
    CONF_MAX_TOKENS,
    CONF_MAX_TOOL_ITERATIONS,
    CONF_RETRY_COUNT,
    CONF_TEMPERATURE,
    CONF_TIMEOUT,
    DATA_CLIENT,
    DATA_MODEL_MANAGER,
    DATA_USAGE_MANAGER,
    DEFAULT_DEVICE_QUERY_MAX_RESULTS,
    DEFAULT_ENABLE_DEVICE_CONTROL,
    DEFAULT_ENABLE_EXTENDED_DEVICE_QUERIES,
    DEFAULT_ENABLE_STREAMING,
    DEFAULT_ENABLE_VISION,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_TOOL_ITERATIONS,
    DEFAULT_PROMPT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAX_ATTACHMENT_BYTES,
    MAX_IMAGE_ATTACHMENTS,
    MAX_TOOL_CALLS_PER_ROUND,
    MAX_TOOL_RESULT_CHARS,
    MAX_TOTAL_ATTACHMENT_BYTES,
    MAX_TOTAL_TOOL_CALLS,
    SUPPORTED_IMAGE_MIME_TYPES,
)
from .device_control import (
    DEVICE_CONTROL_PROMPT,
    prepare_device_control_tools,
    sanitize_tool_input,
)
from .device_query import (
    DEVICE_QUERY_PROMPT,
    append_device_query_tools,
    is_device_query_tool,
)
from .entity import service_device_info
from .model_manager import (
    model_supports_streaming,
    model_supports_vision,
)
from .usage_manager import UsageManager

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the conversation entity."""
    async_add_entities([FreeLLMConversationEntity(entry)])


class FreeLLMConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
):
    """LLM7-backed Home Assistant conversation agent."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_attribution = "External AI service: LLM7.io"
    _attr_supports_streaming = True

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = service_device_info(entry)
        if self._control_enabled:
            self._attr_supported_features = (
                conversation.ConversationEntityFeature.CONTROL
            )

    @property
    def _control_enabled(self) -> bool:
        return bool(
            self.entry.options.get(
                CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
            )
            and self.entry.options.get(CONF_LLM_HASS_API)
        )

    @property
    @override
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return all supported languages."""
        return MATCH_ALL

    @override
    async def async_added_to_hass(self) -> None:
        """Register this entity as a conversation agent."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Unregister the conversation agent."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    @override
    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Process input, execute Home Assistant tools, and return the reply."""
        runtime = self.hass.data[DOMAIN][self.entry.entry_id]
        client: LLM7Client = runtime[DATA_CLIENT]
        model_manager = runtime[DATA_MODEL_MANAGER]
        usage_manager: UsageManager = runtime[DATA_USAGE_MANAGER]
        options = self.entry.options
        await usage_manager.async_record_conversation()

        control_enabled = self._control_enabled
        selected_apis = options.get(CONF_LLM_HASS_API) if control_enabled else None
        query_enabled = bool(
            control_enabled
            and options.get(
                CONF_ENABLE_EXTENDED_DEVICE_QUERIES,
                DEFAULT_ENABLE_EXTENDED_DEVICE_QUERIES,
            )
        )
        prompt = options.get(CONF_PROMPT, DEFAULT_PROMPT)
        if control_enabled:
            prompt = f"{prompt}\n\n{DEVICE_CONTROL_PROMPT}"
        if query_enabled:
            prompt = f"{prompt}\n\n{DEVICE_QUERY_PROMPT}"

        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                selected_apis,
                prompt,
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        if chat_log.llm_api:
            device_result_limit = _bounded_int(
                options.get(CONF_DEVICE_QUERY_MAX_RESULTS),
                DEFAULT_DEVICE_QUERY_MAX_RESULTS,
                minimum=5,
                maximum=100,
            )
            if control_enabled:
                prepare_device_control_tools(
                    chat_log.llm_api, device_result_limit, user_input.text
                )
            if query_enabled:
                append_device_query_tools(chat_log.llm_api, device_result_limit)

        image_requested = _has_image_attachments(chat_log.content)
        if _has_unsupported_image_attachments(chat_log.content):
            return _error_result(
                user_input,
                chat_log,
                "Unterstützt werden nur JPEG-, PNG-, WebP- und GIF-Bilder.",
            )
        vision_enabled = bool(
            options.get(CONF_ENABLE_VISION, DEFAULT_ENABLE_VISION)
        )
        if image_requested and not vision_enabled:
            return _error_result(
                user_input,
                chat_log,
                "Bildeingaben sind in den FreeLLM-Chat-Einstellungen deaktiviert.",
            )

        try:
            model = await model_manager.async_ensure_valid_model(
                require_tools=control_enabled,
                require_vision=image_requested,
            )
        except LLM7Error as err:
            return _error_result(user_input, chat_log, str(err))
        model_metadata = model_manager.get_model(model) or {}
        if image_requested and not model_supports_vision(model_metadata):
            return _error_result(
                user_input,
                chat_log,
                "Für die Bildeingabe ist aktuell kein geeignetes Modell verfügbar.",
            )

        tools = _format_tools(chat_log)
        timeout = _bounded_int(
            options.get(CONF_TIMEOUT), DEFAULT_TIMEOUT, minimum=10, maximum=300
        )
        retry_count = _bounded_int(
            options.get(CONF_RETRY_COUNT),
            DEFAULT_RETRY_COUNT,
            minimum=0,
            maximum=5,
        )
        history_limit = _bounded_int(
            options.get(CONF_HISTORY_LIMIT),
            DEFAULT_HISTORY_LIMIT,
            minimum=4,
            maximum=200,
        )
        max_iterations = _bounded_int(
            options.get(CONF_MAX_TOOL_ITERATIONS),
            DEFAULT_MAX_TOOL_ITERATIONS,
            minimum=1,
            maximum=20,
        )
        attachment_cache: dict[Path, tuple[str, int] | None] = {}
        tool_call_tracker = _ToolCallTracker()

        for _iteration in range(max_iterations):
            try:
                messages = await _async_convert_chat_log(
                    self.hass,
                    chat_log.content,
                    history_limit=history_limit,
                    include_images=image_requested,
                    attachment_cache=attachment_cache,
                )
            except LLM7Error as err:
                return _error_result(user_input, chat_log, str(err))

            payload = _build_payload(
                model=model,
                model_metadata=model_metadata,
                messages=messages,
                tools=tools,
                temperature=float(
                    options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
                ),
                max_tokens=_bounded_int(
                    options.get(CONF_MAX_TOKENS),
                    DEFAULT_MAX_TOKENS,
                    minimum=100,
                    maximum=32000,
                ),
            )

            streaming = bool(
                options.get(CONF_ENABLE_STREAMING, DEFAULT_ENABLE_STREAMING)
                and model_supports_streaming(model_metadata)
            )

            completed = False
            adapted_parameters: set[str] = set()
            refreshed_model = False
            while True:
                try:
                    if streaming:
                        content_stream = chat_log.async_add_delta_content_stream(
                            self.entity_id or self.entry.entry_id,
                            _transform_stream(
                                chat_log,
                                _stream_with_retries(
                                    client,
                                    payload,
                                    timeout=timeout,
                                    retry_count=retry_count,
                                    usage_manager=usage_manager,
                                    model=model,
                                ),
                                model,
                                tool_call_tracker,
                            ),
                        )
                        async for streamed_content in content_stream:
                            if isinstance(streamed_content, conversation.ToolResultContent):
                                tool_call_tracker.observe(streamed_content)
                    else:
                        data = await _request_with_retries(
                            client,
                            payload,
                            timeout=timeout,
                            retry_count=retry_count,
                            usage_manager=usage_manager,
                            model=model,
                        )
                        message = _extract_message(data)
                        if message is None:
                            raise LLM7ResponseError(
                                "LLM7.io hat keine verwertbare Chat-Antwort geliefert."
                            )
                        assistant_content = _assistant_content_from_message(
                            self.entity_id or self.entry.entry_id,
                            message,
                        )
                        assistant_content = _guard_assistant_tool_calls(
                            assistant_content, tool_call_tracker
                        )
                        if (
                            not assistant_content.content
                            and not assistant_content.tool_calls
                        ):
                            raise LLM7ResponseError(
                                "Das Modell hat eine leere Antwort geliefert."
                            )
                        _trace_usage(chat_log, data, model)
                        async for tool_result in chat_log.async_add_assistant_content(
                            assistant_content
                        ):
                            tool_call_tracker.observe(tool_result)
                    completed = True
                    break
                except LLM7ResponseError as err:
                    if _adapt_payload_for_error(payload, err, adapted_parameters):
                        continue
                    if not refreshed_model and _looks_like_missing_model(err):
                        refreshed_model = True
                        try:
                            await model_manager.async_refresh(force=True)
                            model = await model_manager.async_ensure_valid_model(
                                require_tools=control_enabled,
                                require_vision=image_requested,
                            )
                            model_metadata = model_manager.get_model(model) or {}
                            payload = _build_payload(
                                model=model,
                                model_metadata=model_metadata,
                                messages=messages,
                                tools=tools,
                                temperature=float(
                                    options.get(
                                        CONF_TEMPERATURE, DEFAULT_TEMPERATURE
                                    )
                                ),
                                max_tokens=_bounded_int(
                                    options.get(CONF_MAX_TOKENS),
                                    DEFAULT_MAX_TOKENS,
                                    minimum=100,
                                    maximum=32000,
                                ),
                            )
                            streaming = bool(
                                options.get(
                                    CONF_ENABLE_STREAMING, DEFAULT_ENABLE_STREAMING
                                )
                                and model_supports_streaming(model_metadata)
                            )
                            continue
                        except LLM7Error as refresh_err:
                            return _error_result(
                                user_input,
                                chat_log,
                                "Das gewählte Modell ist nicht mehr verfügbar: "
                                f"{refresh_err}",
                            )
                    return _error_result(user_input, chat_log, str(err))
                except LLM7Error as err:
                    return _error_result(user_input, chat_log, str(err))

            if not completed:
                return _error_result(
                    user_input,
                    chat_log,
                    "Die Anfrage konnte nicht abgeschlossen werden.",
                )
            if not chat_log.unresponded_tool_results:
                break
        else:
            return _error_result(
                user_input,
                chat_log,
                "Zu viele aufeinanderfolgende Geräteabfragen oder Aktionen. "
                "Die Ausführung wurde aus Sicherheitsgründen beendet.",
            )

        return conversation.async_get_result_from_chat_log(user_input, chat_log)



def _build_payload(
    *,
    model: str,
    model_metadata: dict[str, Any],
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Build a conservative OpenAI-compatible chat payload."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if _model_accepts_temperature(model, model_metadata):
        payload["temperature"] = max(0.0, min(float(temperature), 2.0))
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    return payload


def _model_accepts_temperature(
    model: str, model_metadata: dict[str, Any]
) -> bool:
    """Avoid parameters known to be rejected by reasoning-first models."""
    normalized = model.casefold()
    if normalized.startswith(("gpt-5", "o1", "o3", "o4")):
        return False
    return not bool(model_metadata.get("temperature_unsupported", False))


def _adapt_payload_for_error(
    payload: dict[str, Any],
    err: LLM7ResponseError,
    adapted_parameters: set[str],
) -> bool:
    """Remove or translate one optional parameter rejected by a model."""
    text = str(err).casefold()
    if not any(
        word in text
        for word in ("unsupported", "not supported", "unknown parameter")
    ):
        return False

    for parameter in ("temperature", "tool_choice"):
        if (
            parameter in payload
            and parameter in text
            and parameter not in adapted_parameters
        ):
            payload.pop(parameter, None)
            adapted_parameters.add(parameter)
            _LOGGER.info("Retrying without unsupported parameter %s", parameter)
            return True

    if (
        "max_tokens" in payload
        and "max_tokens" in text
        and "max_tokens" not in adapted_parameters
    ):
        payload["max_completion_tokens"] = payload.pop("max_tokens")
        adapted_parameters.add("max_tokens")
        _LOGGER.info("Retrying with max_completion_tokens instead of max_tokens")
        return True
    return False


def _guard_assistant_tool_calls(
    content: conversation.AssistantContent,
    tracker: "_ToolCallTracker",
) -> conversation.AssistantContent:
    """Validate and limit tool calls before Home Assistant executes them."""
    if not content.tool_calls:
        return content
    guarded = tracker.guard(content.tool_calls)
    return replace(content, tool_calls=guarded or None)


@dataclass(slots=True)
class _ToolCallTracker:
    """Track attempts and results without blocking a corrected retry after failure."""

    attempts: dict[str, int] = field(default_factory=dict)
    successful: set[str] = field(default_factory=set)
    call_signatures: dict[str, str] = field(default_factory=dict)
    total_calls: int = 0

    def guard(self, tool_calls: list[llm.ToolInput]) -> list[llm.ToolInput]:
        """Sanitize, deduplicate, and bound one round of tool calls."""
        if len(tool_calls) > MAX_TOOL_CALLS_PER_ROUND:
            raise LLM7ResponseError(
                "Das Modell hat zu viele Geräteabfragen oder Aktionen gleichzeitig angefordert."
            )

        guarded: list[llm.ToolInput] = []
        round_signatures: set[str] = set()
        for raw_tool_call in tool_calls:
            tool_call = sanitize_tool_input(raw_tool_call)
            signature = _tool_call_signature(tool_call)
            if signature in round_signatures:
                continue
            if signature in self.successful:
                if is_device_query_tool(tool_call.tool_name):
                    raise LLM7ResponseError(
                        "Das Modell wollte dieselbe bereits erfolgreiche Geräteabfrage "
                        "wiederholen. Die Abfrageschleife wurde beendet."
                    )
                raise LLM7ResponseError(
                    "Das Modell wollte dieselbe bereits erfolgreiche Geräteaktion "
                    "wiederholen. Die automatische Ausführung wurde beendet."
                )
            if self.attempts.get(signature, 0) >= 2:
                if is_device_query_tool(tool_call.tool_name):
                    raise LLM7ResponseError(
                        "Dieselbe Geräteabfrage ist zweimal fehlgeschlagen. "
                        "Bitte die Anfrage genauer formulieren."
                    )
                raise LLM7ResponseError(
                    "Dieselbe Geräteaktion ist zweimal fehlgeschlagen. "
                    "Die automatische Ausführung wurde beendet."
                )
            round_signatures.add(signature)
            guarded.append(tool_call)
            self.attempts[signature] = self.attempts.get(signature, 0) + 1
            self.call_signatures[tool_call.id] = signature

        if self.total_calls + len(guarded) > MAX_TOTAL_TOOL_CALLS:
            raise LLM7ResponseError(
                "Die Anfrage enthält zu viele automatische Geräteabfragen oder Aktionen."
            )
        self.total_calls += len(guarded)
        return guarded

    def observe(self, result: conversation.ToolResultContent) -> None:
        """Mark only a genuinely successful call as protected from repetition."""
        signature = self.call_signatures.get(result.tool_call_id)
        if signature and _tool_result_succeeded(result.tool_result):
            self.successful.add(signature)


def _tool_result_succeeded(result: Any) -> bool:
    """Return whether a Home Assistant tool result represents success."""
    if not isinstance(result, dict):
        return True
    if result.get("error"):
        return False
    if str(result.get("response_type", "")).casefold() == "error":
        return False
    if str(result.get("result", "")).casefold() in {
        "ambiguous",
        "failed",
        "no_match",
        "unsupported",
        "unsupported_action",
    }:
        return False
    data = result.get("data")
    if isinstance(data, dict):
        failed = data.get("failed")
        success = data.get("success")
        if failed and not success:
            return False
    return True

def _tool_call_signature(tool_call: llm.ToolInput) -> str:
    """Return a stable signature independent of the provider call ID."""
    arguments = json.dumps(
        tool_call.tool_args,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return f"{tool_call.tool_name}:{arguments}"


def _sanitize_tool_schema(value: Any) -> Any:
    """Remove unsupported schema combinators while preserving useful constraints."""
    if isinstance(value, list):
        return [_sanitize_tool_schema(item) for item in value]
    if not isinstance(value, dict):
        return value

    unsupported = {"oneOf", "anyOf", "allOf", "not"}
    sanitized = {
        key: _sanitize_tool_schema(item)
        for key, item in value.items()
        if key not in unsupported
    }
    if sanitized.get("type") == "array":
        sanitized.setdefault("minItems", 1)
    return sanitized


def _serialize_tool_result(result: Any) -> str:
    """Serialize tool results without allowing a single result to flood context."""
    serialized = json.dumps(result, ensure_ascii=False, default=str)
    if len(serialized) <= MAX_TOOL_RESULT_CHARS:
        return serialized
    return json.dumps(
        {
            "truncated": True,
            "original_length": len(serialized),
            "preview": serialized[:MAX_TOOL_RESULT_CHARS],
        },
        ensure_ascii=False,
    )


async def _request_with_retries(
    client: LLM7Client,
    payload: dict[str, Any],
    *,
    timeout: int,
    retry_count: int,
    usage_manager: UsageManager,
    model: str,
) -> dict[str, Any]:
    """Retry transient failures and record every completed API attempt."""
    last_error: LLM7Error | None = None
    for attempt in range(retry_count + 1):
        started = monotonic()
        try:
            data = await client.async_chat_completion(payload, timeout)
            await usage_manager.async_record_api_result(
                success=True,
                model=model,
                data=data,
                latency_ms=round((monotonic() - started) * 1000),
                status=200,
            )
            return data
        except LLM7ConnectionError as err:
            last_error = err
            await usage_manager.async_record_api_result(
                success=False,
                model=model,
                latency_ms=round((monotonic() - started) * 1000),
                error=str(err),
            )
            if attempt >= retry_count:
                raise
            delay = min(0.5 * (2**attempt), 4.0)
        except LLM7ResponseError as err:
            last_error = err
            await usage_manager.async_record_api_result(
                success=False,
                model=model,
                latency_ms=round((monotonic() - started) * 1000),
                error=str(err),
                status=err.status,
            )
            retryable = err.status == 429 or (
                err.status is not None and err.status >= 500
            )
            if not retryable or attempt >= retry_count:
                raise
            delay = min(err.retry_after or 0.5 * (2**attempt), 10.0)
        await asyncio.sleep(delay)

    assert last_error is not None
    raise last_error


async def _stream_with_retries(
    client: LLM7Client,
    payload: dict[str, Any],
    *,
    timeout: int,
    retry_count: int,
    usage_manager: UsageManager,
    model: str,
) -> AsyncGenerator[dict[str, Any]]:
    """Retry an untouched stream and record each network attempt."""
    for attempt in range(retry_count + 1):
        emitted = False
        started = monotonic()
        usage_data: dict[str, Any] = {}
        provider_model: str | None = None
        try:
            async for chunk in client.async_chat_completion_stream(payload, timeout):
                if isinstance(chunk.get("error"), dict):
                    message = chunk["error"].get("message") or "Streaming-Fehler"
                    raise LLM7ResponseError(str(message))
                emitted = True
                if isinstance(chunk.get("usage"), dict):
                    usage_data = chunk["usage"]
                if isinstance(chunk.get("model"), str):
                    provider_model = chunk["model"]
                yield chunk
            result_data: dict[str, Any] = {}
            if usage_data:
                result_data["usage"] = usage_data
            if provider_model:
                result_data["model"] = provider_model
            await usage_manager.async_record_api_result(
                success=True,
                model=model,
                data=result_data,
                latency_ms=round((monotonic() - started) * 1000),
                status=200,
            )
            return
        except LLM7ConnectionError as err:
            await usage_manager.async_record_api_result(
                success=False,
                model=model,
                latency_ms=round((monotonic() - started) * 1000),
                error=str(err),
            )
            if emitted or attempt >= retry_count:
                raise
            delay = min(0.5 * (2**attempt), 4.0)
        except LLM7ResponseError as err:
            await usage_manager.async_record_api_result(
                success=False,
                model=model,
                latency_ms=round((monotonic() - started) * 1000),
                error=str(err),
                status=err.status,
            )
            retryable = err.status == 429 or (
                err.status is not None and err.status >= 500
            )
            if emitted or not retryable or attempt >= retry_count:
                raise
            delay = min(err.retry_after or 0.5 * (2**attempt), 10.0)
        await asyncio.sleep(delay)


async def _transform_stream(
    chat_log: conversation.ChatLog,
    chunks: AsyncIterable[dict[str, Any]],
    model: str,
    tracker: _ToolCallTracker,
) -> AsyncGenerator[conversation.AssistantContentDeltaDict]:
    """Transform OpenAI chat-completion chunks to Home Assistant deltas."""
    yield {"role": "assistant"}
    tool_buffers: dict[int, dict[str, str]] = {}
    received = False
    finish_reason: str | None = None

    async for data in chunks:
        if isinstance(data.get("error"), dict):
            message = data["error"].get("message") or "Streaming-Fehler"
            raise LLM7ResponseError(str(message))

        usage = data.get("usage")
        if isinstance(usage, dict):
            _trace_usage(chat_log, {"usage": usage}, model)

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            continue
        choice = choices[0]
        if not isinstance(choice, dict):
            continue
        if isinstance(choice.get("finish_reason"), str):
            finish_reason = choice["finish_reason"]
        delta = choice.get("delta")
        if not isinstance(delta, dict):
            continue

        text = _extract_text(delta.get("content"))
        if text:
            received = True
            yield {"content": text}

        raw_calls = delta.get("tool_calls")
        if not isinstance(raw_calls, list):
            continue
        for raw_call in raw_calls:
            if not isinstance(raw_call, dict):
                continue
            index = raw_call.get("index", 0)
            if not isinstance(index, int):
                index = 0
            buffer = tool_buffers.setdefault(
                index, {"id": "", "name": "", "arguments": ""}
            )
            if raw_call.get("id"):
                buffer["id"] = str(raw_call["id"])
            function = raw_call.get("function")
            if not isinstance(function, dict):
                continue
            if function.get("name"):
                buffer["name"] += str(function["name"])
            if function.get("arguments"):
                buffer["arguments"] += str(function["arguments"])

    tool_inputs = tracker.guard(_tool_inputs_from_buffers(tool_buffers))
    if tool_inputs:
        received = True
        yield {"tool_calls": tool_inputs}

    if finish_reason == "content_filter":
        raise LLM7ResponseError("Die Antwort wurde vom Inhaltsfilter blockiert.")
    if not received:
        raise LLM7ResponseError(
            "Das Modell hat eine leere Streaming-Antwort geliefert."
        )


def _format_tools(chat_log: conversation.ChatLog) -> list[dict[str, Any]]:
    """Convert Home Assistant tools to OpenAI chat-completions format."""
    if not chat_log.llm_api:
        return []

    result: list[dict[str, Any]] = []
    for tool in chat_log.llm_api.tools:
        schema = convert(
            tool.parameters,
            custom_serializer=chat_log.llm_api.custom_serializer,
        )
        schema = _sanitize_tool_schema(schema)
        result.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema,
                },
            }
        )
    return result


async def _async_convert_chat_log(
    hass: HomeAssistant,
    contents: list[conversation.Content],
    *,
    history_limit: int,
    include_images: bool,
    attachment_cache: dict[Path, tuple[str, int] | None],
) -> list[dict[str, Any]]:
    """Convert bounded Home Assistant chat history to OpenAI messages."""
    trimmed = _trim_content(contents, history_limit)
    prepared_images: dict[Path, str] = {}
    if include_images:
        prepared_images = await _async_prepare_images(
            hass, trimmed, attachment_cache
        )
        if _has_image_attachments(trimmed) and not prepared_images:
            raise LLM7Error(
                "Die angehängten Bilder konnten nicht gelesen werden oder sind zu groß."
            )

    messages: list[dict[str, Any]] = []
    for content in trimmed:
        if isinstance(content, conversation.ToolResultContent):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": content.tool_call_id,
                    "name": content.tool_name,
                    "content": _serialize_tool_result(content.tool_result),
                }
            )
            continue

        message: dict[str, Any] = {"role": content.role}
        if isinstance(content, conversation.UserContent) and content.attachments:
            parts: list[dict[str, Any]] = [
                {"type": "text", "text": content.content}
            ]
            for attachment in content.attachments:
                if image_url := prepared_images.get(attachment.path):
                    parts.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url, "detail": "auto"},
                        }
                    )
            message["content"] = parts if len(parts) > 1 else content.content
        elif content.content is not None:
            message["content"] = content.content

        if isinstance(content, conversation.AssistantContent) and content.tool_calls:
            message.setdefault("content", None)
            message["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.tool_name,
                        "arguments": json.dumps(
                            tool_call.tool_args,
                            ensure_ascii=False,
                            default=str,
                        ),
                    },
                }
                for tool_call in content.tool_calls
                if not tool_call.external
            ]
        messages.append(message)
    return messages


def _trim_content(
    contents: list[conversation.Content], history_limit: int
) -> list[conversation.Content]:
    """Keep the system prompt and the newest complete user turns."""
    system = [content for content in contents if content.role == "system"][:1]
    non_system = [content for content in contents if content.role != "system"]
    if len(non_system) <= history_limit:
        return [*system, *non_system]

    turns: list[list[conversation.Content]] = []
    current: list[conversation.Content] = []
    for content in non_system:
        if isinstance(content, conversation.UserContent) and current:
            turns.append(current)
            current = [content]
        else:
            current.append(content)
    if current:
        turns.append(current)

    kept: list[list[conversation.Content]] = []
    count = 0
    for turn in reversed(turns):
        if kept and count + len(turn) > history_limit:
            break
        kept.append(turn)
        count += len(turn)
    kept.reverse()
    return [*system, *(item for turn in kept for item in turn)]


async def _async_prepare_images(
    hass: HomeAssistant,
    contents: list[conversation.Content],
    cache: dict[Path, tuple[str, int] | None],
) -> dict[Path, str]:
    """Prepare image attachments from the newest user message only."""
    latest_user = _latest_user_content(contents)
    attachments = (
        [
            attachment
            for attachment in latest_user.attachments
            if attachment.mime_type in SUPPORTED_IMAGE_MIME_TYPES
        ]
        if latest_user and latest_user.attachments
        else []
    )

    selected: dict[Path, str] = {}
    total_bytes = 0
    for attachment in attachments:
        if len(selected) >= MAX_IMAGE_ATTACHMENTS:
            break
        prepared = cache.get(attachment.path)
        if attachment.path not in cache:
            prepared = await hass.async_add_executor_job(
                _read_image_data_url,
                attachment.path,
                attachment.mime_type,
            )
            cache[attachment.path] = prepared
        if prepared is None:
            continue
        data_url, size = prepared
        if total_bytes + size > MAX_TOTAL_ATTACHMENT_BYTES:
            continue
        selected[attachment.path] = data_url
        total_bytes += size
    return selected


def _read_image_data_url(path: Path, mime_type: str) -> tuple[str, int] | None:
    """Read and encode one image outside the event loop."""
    try:
        if not path.is_file():
            return None
        size = path.stat().st_size
        if size <= 0 or size > MAX_ATTACHMENT_BYTES:
            return None
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return None
    return f"data:{mime_type};base64,{encoded}", size


def _latest_user_content(
    contents: list[conversation.Content],
) -> conversation.UserContent | None:
    """Return the newest user message."""
    return next(
        (
            content
            for content in reversed(contents)
            if isinstance(content, conversation.UserContent)
        ),
        None,
    )


def _has_unsupported_image_attachments(
    contents: list[conversation.Content],
) -> bool:
    """Return whether the newest user message has an unsupported image type."""
    latest_user = _latest_user_content(contents)
    return bool(
        latest_user
        and latest_user.attachments
        and any(
            attachment.mime_type.startswith("image/")
            and attachment.mime_type not in SUPPORTED_IMAGE_MIME_TYPES
            for attachment in latest_user.attachments
        )
    )


def _has_image_attachments(contents: list[conversation.Content]) -> bool:
    """Return whether the newest user message has a supported image."""
    latest_user = _latest_user_content(contents)
    return bool(
        latest_user
        and latest_user.attachments
        and any(
            attachment.mime_type in SUPPORTED_IMAGE_MIME_TYPES
            for attachment in latest_user.attachments
        )
    )


def _extract_message(data: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the first chat-completion message safely."""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    return message if isinstance(message, dict) else None


def _assistant_content_from_message(
    agent_id: str,
    message: dict[str, Any],
) -> conversation.AssistantContent:
    """Convert an OpenAI assistant message to Home Assistant content."""
    raw_calls = message.get("tool_calls")
    if not isinstance(raw_calls, list):
        raw_calls = []

    legacy_call = message.get("function_call")
    if not raw_calls and isinstance(legacy_call, dict):
        raw_calls = [{"id": "legacy_function_call", "function": legacy_call}]

    tool_inputs: list[llm.ToolInput] = []
    for call in raw_calls:
        if not isinstance(call, dict):
            continue
        function = call.get("function")
        if not isinstance(function, dict):
            continue
        tool_name = function.get("name")
        if not isinstance(tool_name, str) or not tool_name:
            continue
        tool_inputs.append(
            llm.ToolInput(
                id=str(call.get("id") or f"tool_{len(tool_inputs)}"),
                tool_name=tool_name,
                tool_args=_parse_tool_arguments(function.get("arguments")),
            )
        )

    return conversation.AssistantContent(
        agent_id=agent_id,
        content=_extract_text(message.get("content")),
        tool_calls=tool_inputs or None,
    )


def _tool_inputs_from_buffers(
    buffers: dict[int, dict[str, str]],
) -> list[llm.ToolInput]:
    result: list[llm.ToolInput] = []
    for index in sorted(buffers):
        buffer = buffers[index]
        if not buffer["name"]:
            continue
        result.append(
            llm.ToolInput(
                id=buffer["id"] or f"tool_{index}",
                tool_name=buffer["name"],
                tool_args=_parse_tool_arguments(buffer["arguments"]),
            )
        )
    return result


def _parse_tool_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if not isinstance(arguments, str) or not arguments.strip():
        return {}
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError as err:
        _LOGGER.warning("Model returned invalid tool arguments: %s", arguments[:300])
        raise LLM7ResponseError(
            "Das Modell hat ungültige Parameter für eine Geräteaktion geliefert."
        ) from err
    return parsed if isinstance(parsed, dict) else {}


def _extract_text(raw_content: Any) -> str | None:
    """Extract text from string or OpenAI-style content parts."""
    if isinstance(raw_content, str):
        return raw_content or None
    if not isinstance(raw_content, list):
        return None

    parts: list[str] = []
    for part in raw_content:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str):
            parts.append(text)
    combined = "".join(parts)
    return combined or None


def _trace_usage(
    chat_log: conversation.ChatLog,
    data: dict[str, Any],
    model: str,
) -> None:
    """Add model and token usage to the Home Assistant conversation trace."""
    details: dict[str, Any] = {"model": model}
    usage = data.get("usage")
    if isinstance(usage, dict):
        details["stats"] = {
            key: value
            for key, value in {
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            }.items()
            if isinstance(value, int)
        }
    chat_log.async_trace(details)


def _looks_like_missing_model(err: LLM7ResponseError) -> bool:
    text = str(err).casefold()
    return err.status == 404 or (
        "model" in text
        and any(
            word in text
            for word in ("not found", "unknown", "invalid", "exist")
        )
    )


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def _error_result(
    user_input: conversation.ConversationInput,
    chat_log: conversation.ChatLog,
    message: str,
) -> conversation.ConversationResult:
    """Return a user-visible conversation error without losing chat history."""
    _LOGGER.error("FreeLLM Chat request failed: %s", message)
    chat_log.async_add_assistant_content_without_tools(
        conversation.AssistantContent(
            agent_id=str(user_input.agent_id or DOMAIN),
            content=f"Fehler bei der Anfrage: {message}",
        )
    )
    return conversation.async_get_result_from_chat_log(user_input, chat_log)
