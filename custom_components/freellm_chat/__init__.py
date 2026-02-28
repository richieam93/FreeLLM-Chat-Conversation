"""The freellm_chat Conversation integration."""
from __future__ import annotations

import logging
from typing import Literal

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
        self.optimizer = PromptOptimizer()

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

        enable_control = self.entry.options.get(
            CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
        )

        # Prüfe auf Steuerungs- oder Abfrage-Anfrage
        is_control_or_query = enable_control and self._is_control_or_query(user_text)

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
            "luftfeuchtigkeit", "feuchtigkeit", "humidity",
            "sensor", "wert", "messung", "status",
            "zeig mir", "was ist", "wie ist", "welche",
            "fenster", "tür", "offen", "geschlossen",
            "eingeschaltet", "ausgeschaltet", "batterie", "offline",
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)

    async def _handle_control_request(
        self, 
        user_input: conversation.ConversationInput,
        conversation_id: str
    ) -> conversation.ConversationResult:
        """Handle device control and sensor query requests."""
        model_name = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        control_prompt = self.entry.options.get(CONF_CONTROL_PROMPT, DEFAULT_CONTROL_PROMPT)
        control_temperature = self.entry.options.get(CONF_CONTROL_TEMPERATURE, DEFAULT_CONTROL_TEMPERATURE)
        control_max_tokens = self.entry.options.get(CONF_CONTROL_MAX_TOKENS, DEFAULT_CONTROL_MAX_TOKENS)
        selected_entities = self.entry.options.get(CONF_SELECTED_ENTITIES, [])
        selected_areas = self.entry.options.get(CONF_SELECTED_AREAS, [])
        enable_sensors = self.entry.options.get(CONF_ENABLE_SENSORS, DEFAULT_ENABLE_SENSORS)
        enable_cache = self.entry.options.get(CONF_ENABLE_CACHE, DEFAULT_ENABLE_CACHE)
        optimize_prompts = self.entry.options.get(CONF_OPTIMIZE_PROMPTS, DEFAULT_OPTIMIZE_PROMPTS)

        controller = DeviceController(
            self.hass, selected_entities, selected_areas, enable_sensors
        )
        
        controlled = controller.get_controlled_entities(include_sensors=True)
        if not controlled:
            return self._create_response(
                "⚠️ Keine Geräte konfiguriert.",
                user_input.language,
                conversation_id
            )
        
        # Optimiere Prompt bei vielen Geräten
        if optimize_prompts:
            control_prompt = self.optimizer.simplify_control_prompt(
                control_prompt, len(controlled)
            )
            entity_context = self.optimizer.compress_entity_list(controlled)
        else:
            entity_context = controller.generate_context()
        
        full_prompt = control_prompt + entity_context

        # Prüfe Cache
        cached_response = None
        if enable_cache:
            cached_response = self.cache.get(full_prompt, user_input.text)
        
        if cached_response:
            _LOGGER.debug("Using cached response")
            response_text = cached_response
        else:
            try:
                messages = [
                    {"role": "system", "content": full_prompt},
                    {"role": "user", "content": user_input.text}
                ]

                response_text = await self._async_query_llm(
                    model_name, 
                    messages,
                    temperature=control_temperature,
                    max_tokens=control_max_tokens
                )
                
                _LOGGER.debug(f"LLM Response: {response_text}")

                result = await controller.execute_command(response_text)

                if result:
                    response_text = result
                    
                    # Cache speichern
                    if enable_cache:
                        self.cache.set(full_prompt, user_input.text, response_text)
                else:
                    response_text = "Befehl nicht verstanden. Beispiel: 'Schalte das Licht an'"

            except asyncio.TimeoutError:
                response_text = "⏱️ Zeitüberschreitung."
            except Exception as e:
                _LOGGER.error(f"Error: {e}")
                response_text = f"❌ Fehler: {str(e)}"

        return self._create_response(response_text, user_input.language, conversation_id)

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

        try:
            prompt = template.Template(raw_prompt, self.hass).async_render(
                {"ha_name": self.hass.config.location_name},
                parse_result=False,
            )
        except TemplateError as err:
            return self._create_error_response(
                f"Template-Fehler: {err}", user_input.language, conversation_id
            )

        if conversation_id not in self.history:
            self.history[conversation_id] = [{"role": "system", "content": prompt}]

        self.history[conversation_id].append({"role": "user", "content": user_input.text})

        # Limit history
        if len(self.history[conversation_id]) > 21:
            self.history[conversation_id] = (
                [self.history[conversation_id][0]] +
                self.history[conversation_id][-20:]
            )

        try:
            response_text = await self._async_query_llm(
                model_name, 
                self.history[conversation_id],
                temperature=chat_temperature,
                max_tokens=chat_max_tokens
            )
            self.history[conversation_id].append({
                "role": "assistant", 
                "content": response_text
            })
        except Exception as e:
            _LOGGER.error(f"Error: {e}")
            response_text = f"❌ Fehler: {str(e)}"

        return self._create_response(response_text, user_input.language, conversation_id)

    async def _async_query_llm(
        self, 
        model_name: str, 
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Send a query to the LLM."""
        url = f"{LLM7_BASE_URL}/chat/completions"
        
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        session = async_get_clientsession(self.hass)
        
        try:
            async with asyncio.timeout(30):
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()

            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"].strip()
            
            return str(data)

        except asyncio.TimeoutError:
            _LOGGER.error("LLM timeout")
            raise
        except aiohttp.ClientError as e:
            _LOGGER.error(f"LLM Error: {e}")
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