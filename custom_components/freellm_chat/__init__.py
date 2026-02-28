"""The freellm_chat Conversation integration."""
from __future__ import annotations

import logging
from typing import Literal
import time

import aiohttp
import asyncio

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import intent, template
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DOMAIN,
    LLM7_BASE_URL,
)
from .device_control import DeviceController
from .response_cache import ResponseCache
from .prompt_optimizer import PromptOptimizer

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up freellm_chat Conversation from a config entry."""
    conversation.async_set_agent(hass, entry, FreeLLMChatAgent(hass, entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload freellm_chat."""
    conversation.async_unset_agent(hass, entry)
    return True


class FreeLLMChatAgent(conversation.AbstractConversationAgent):
    """freellm_chat conversation agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.history: dict[str, list[dict]] = {}
        
        # Cache initialisieren
        cache_duration = entry.options.get(CONF_CACHE_DURATION, DEFAULT_CACHE_DURATION)
        self.cache = ResponseCache(max_age_seconds=cache_duration)
        
        # Prompt Optimizer
        compression_level = entry.options.get(CONF_COMPRESSION_LEVEL, DEFAULT_COMPRESSION_LEVEL)
        self.optimizer = PromptOptimizer(compression_level=compression_level)

    @property
    def attribution(self):
        """Return the attribution."""
        return {
            "name": "Powered by LLM7.io",
            "url": "https://api.llm7.io",
        }

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        conversation_id = user_input.conversation_id
        user_text = user_input.text
        
        _LOGGER.debug(f"Processing: '{user_text}'")

        enable_control = self.entry.options.get(
            CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
        )

        # Prüfe auf Steuerungs- oder Abfrage-Anfrage
        is_control_or_query = enable_control and self._is_control_or_query(user_text)
        
        _LOGGER.debug(f"Is control/query: {is_control_or_query}")

        if is_control_or_query:
            result = await self._handle_control_request(user_input, conversation_id)
        else:
            result = await self._handle_chat_request(user_input, conversation_id)

        return result

    def _is_control_or_query(self, text: str) -> bool:
        """Check if the request is a device control or sensor query."""
        keywords = [
            # Steuerung
            "schalte", "schalt", "mach", "mache", "stelle", "stell",
            "dimme", "dimm", "erhöhe", "verringere", "öffne", "schließe",
            "starte", "stoppe", "spiele", "pausiere", "aktiviere",
            "licht", "lampe", "heizung", "jalousie", "rollladen",
            " an", " aus", " ein",
            # Abfragen
            "temperatur", "wie warm", "wie kalt", "wie viel grad",
            "luftfeuchtigkeit", "feuchtigkeit",
            "sensor", "status",
            "zeig mir", "was ist", "wie ist", "welche",
            "fenster", "tür", "offen", "geschlossen",
            "eingeschaltet", "batterie", "offline",
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)

    async def _handle_control_request(
        self, 
        user_input: conversation.ConversationInput,
        conversation_id: str
    ) -> conversation.ConversationResult:
        """Handle device control and sensor query requests."""
        start_time = time.time()
        
        # Hole alle Einstellungen
        model_name = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        control_prompt = self.entry.options.get(CONF_CONTROL_PROMPT, DEFAULT_CONTROL_PROMPT)
        control_temperature = self.entry.options.get(CONF_CONTROL_TEMPERATURE, DEFAULT_CONTROL_TEMPERATURE)
        control_max_tokens = self.entry.options.get(CONF_CONTROL_MAX_TOKENS, DEFAULT_CONTROL_MAX_TOKENS)
        selected_entities = self.entry.options.get(CONF_SELECTED_ENTITIES, [])
        selected_areas = self.entry.options.get(CONF_SELECTED_AREAS, [])
        enable_sensors = self.entry.options.get(CONF_ENABLE_SENSORS, DEFAULT_ENABLE_SENSORS)
        enable_cache = self.entry.options.get(CONF_ENABLE_CACHE, DEFAULT_ENABLE_CACHE)
        optimize_prompts = self.entry.options.get(CONF_OPTIMIZE_PROMPTS, DEFAULT_OPTIMIZE_PROMPTS)
        timeout = self.entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        retry_count = self.entry.options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)

        _LOGGER.debug(f"Control request - Model: {model_name}, Timeout: {timeout}s")

        # Controller initialisieren
        controller = DeviceController(
            self.hass, selected_entities, selected_areas, enable_sensors
        )
        
        # Prüfe ob Geräte verfügbar
        controlled = controller.get_controlled_entities(include_sensors=True)
        entity_count = len(controlled)
        
        _LOGGER.debug(f"Found {entity_count} controllable entities")
        
        if not controlled:
            return self._create_response(
                "⚠️ Keine Geräte konfiguriert. Bitte wähle zuerst Geräte oder Bereiche in den Einstellungen aus.",
                user_input.language,
                conversation_id
            )
        
        # Prompt erstellen - IMMER optimieren wenn viele Geräte
        if optimize_prompts or entity_count > 20:
            _LOGGER.debug(f"Optimizing prompt for {entity_count} entities")
            optimized_prompt = self.optimizer.optimize_prompt(
                control_prompt, 
                entity_count,
                include_examples=(entity_count < 20)
            )
            entity_context = self.optimizer.compress_entity_list(controlled, max_per_area=5)
        else:
            optimized_prompt = control_prompt
            entity_context = controller.generate_context()
        
        full_prompt = optimized_prompt + entity_context
        prompt_length = len(full_prompt)
        
        _LOGGER.debug(f"Prompt length: {prompt_length} chars")
        
        # WARNUNG wenn Prompt zu lang
        if prompt_length > 8000:
            _LOGGER.warning(f"Prompt very long ({prompt_length} chars), forcing high compression")
            optimized_prompt = self.optimizer._high_compression()
            entity_context = self.optimizer.compress_entity_list(controlled, max_per_area=3)
            full_prompt = optimized_prompt + entity_context
            _LOGGER.debug(f"Compressed prompt length: {len(full_prompt)} chars")

        # Prüfe Cache
        if enable_cache:
            cached_response = self.cache.get(full_prompt, user_input.text)
            if cached_response:
                _LOGGER.debug("Cache HIT - using cached response")
                result = await controller.execute_command(cached_response)
                if result:
                    return self._create_response(result, user_input.language, conversation_id)

        # LLM-Anfrage
        _LOGGER.info(f"Sending LLM request - Model: {model_name}, Prompt: {len(full_prompt)} chars")
        
        response_text = None
        last_error = None
        
        for attempt in range(retry_count + 1):
            try:
                messages = [
                    {"role": "system", "content": full_prompt},
                    {"role": "user", "content": user_input.text}
                ]
                
                _LOGGER.debug(f"Attempt {attempt + 1}/{retry_count + 1}")

                response_text = await self._async_query_llm(
                    model_name, 
                    messages,
                    temperature=control_temperature,
                    max_tokens=control_max_tokens,
                    timeout=timeout
                )
                
                elapsed = time.time() - start_time
                _LOGGER.info(f"LLM response received in {elapsed:.1f}s")
                _LOGGER.debug(f"Response: {response_text[:200] if response_text else 'None'}...")
                break
                
            except Exception as e:
                last_error = e
                _LOGGER.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retry_count:
                    await asyncio.sleep(0.5)

        if response_text is None:
            elapsed = time.time() - start_time
            _LOGGER.error(f"All {retry_count + 1} attempts failed after {elapsed:.1f}s")
            return self._create_response(
                f"❌ Fehler nach {retry_count + 1} Versuchen: {last_error}\n\n"
                f"💡 Tipp: Erhöhe den Timeout in den erweiterten Einstellungen.",
                user_input.language,
                conversation_id
            )

        # Befehl ausführen
        result = await controller.execute_command(response_text)

        if result:
            # Cache speichern für Abfragen
            if enable_cache and not any(w in user_input.text.lower() for w in ['schalte', 'mach', 'an', 'aus']):
                self.cache.set(full_prompt, user_input.text, response_text)
            
            elapsed = time.time() - start_time
            _LOGGER.info(f"Control request completed in {elapsed:.1f}s")
            return self._create_response(result, user_input.language, conversation_id)
        else:
            _LOGGER.warning(f"Could not parse response: {response_text[:100]}")
            return self._create_response(
                "Ich konnte den Befehl nicht verstehen.\n\n"
                "Beispiele:\n"
                "• 'Schalte das Licht an'\n"
                "• 'Mache die Küche rot'\n"
                "• 'Temperaturen in allen Räumen'",
                user_input.language,
                conversation_id
            )

    async def _handle_chat_request(
        self,
        user_input: conversation.ConversationInput,
        conversation_id: str
    ) -> conversation.ConversationResult:
        """Handle normal chat requests."""
        model_name = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        raw_prompt = self.entry.options.get(CONF_PROMPT, DEFAULT_PROMPT)
        chat_temperature = self.entry.options.get(CONF_CHAT_TEMPERATURE, DEFAULT_CHAT_TEMPERATURE)
        chat_max_tokens = self.entry.options.get(CONF_CHAT_MAX_TOKENS, DEFAULT_CHAT_MAX_TOKENS)
        history_limit = self.entry.options.get(CONF_HISTORY_LIMIT, DEFAULT_HISTORY_LIMIT)
        timeout = self.entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        retry_count = self.entry.options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)

        try:
            prompt = template.Template(raw_prompt, self.hass).async_render(
                {"ha_name": self.hass.config.location_name},
                parse_result=False,
            )
        except TemplateError as err:
            return self._create_error_response(
                f"Template-Fehler: {err}", user_input.language, conversation_id
            )

        # Konversationsverlauf verwalten
        if conversation_id not in self.history:
            self.history[conversation_id] = [{"role": "system", "content": prompt}]

        self.history[conversation_id].append({"role": "user", "content": user_input.text})

        # Limit history
        max_messages = history_limit + 1
        if len(self.history[conversation_id]) > max_messages:
            self.history[conversation_id] = (
                [self.history[conversation_id][0]] +
                self.history[conversation_id][-(history_limit):]
            )

        # LLM-Anfrage
        response_text = None
        last_error = None
        
        for attempt in range(retry_count + 1):
            try:
                response_text = await self._async_query_llm(
                    model_name, 
                    self.history[conversation_id],
                    temperature=chat_temperature,
                    max_tokens=chat_max_tokens,
                    timeout=timeout
                )
                
                self.history[conversation_id].append({
                    "role": "assistant", 
                    "content": response_text
                })
                break
                
            except Exception as e:
                last_error = e
                _LOGGER.warning(f"Chat attempt {attempt + 1} failed: {e}")
                if attempt < retry_count:
                    await asyncio.sleep(0.5)

        if response_text is None:
            response_text = f"❌ Fehler: {last_error}"

        return self._create_response(response_text, user_input.language, conversation_id)

    async def _async_query_llm(
        self, 
        model_name: str, 
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        timeout: int = 30
    ) -> str:
        """Send a query to the LLM using async HTTP."""
        url = f"{LLM7_BASE_URL}/chat/completions"
        
        # Berechne ungefähre Token-Anzahl
        total_chars = sum(len(m.get('content', '')) for m in messages)
        estimated_tokens = total_chars // 4
        
        _LOGGER.debug(f"LLM Request - Model: {model_name}, ~{estimated_tokens} input tokens, max {max_tokens} output")
        
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        session = async_get_clientsession(self.hass)
        
        start_time = time.time()
        
        try:
            async with asyncio.timeout(timeout):
                async with session.post(url, json=payload) as response:
                    elapsed = time.time() - start_time
                    _LOGGER.debug(f"HTTP response status: {response.status} in {elapsed:.1f}s")
                    
                    response.raise_for_status()
                    data = await response.json()

            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")
                return content.strip() if content else str(data)
            
            _LOGGER.warning(f"Unexpected API response: {data}")
            return str(data)

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            _LOGGER.error(f"LLM request timed out after {elapsed:.1f}s (limit: {timeout}s)")
            raise Exception(f"Zeitüberschreitung ({timeout}s)")
        except aiohttp.ClientResponseError as e:
            _LOGGER.error(f"LLM API HTTP Error {e.status}: {e.message}")
            raise Exception(f"API Fehler: {e.status}")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"LLM API Connection Error: {e}")
            raise

    def _create_response(
        self, text: str, language: str, conversation_id: str
    ) -> conversation.ConversationResult:
        """Create a conversation response."""
        intent_response = intent.IntentResponse(language=language)
        intent_response.async_set_speech(text)
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=conversation_id
        )

    def _create_error_response(
        self, error: str, language: str, conversation_id: str
    ) -> conversation.ConversationResult:
        """Create an error response."""
        intent_response = intent.IntentResponse(language=language)
        intent_response.async_set_error(
            intent.IntentResponseErrorCode.UNKNOWN, error
        )
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=conversation_id
        )