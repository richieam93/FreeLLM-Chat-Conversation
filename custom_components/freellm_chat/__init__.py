"""The freellm_chat Conversation integration."""
from __future__ import annotations

import logging
from typing import Literal
import time
import re

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
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DOMAIN,
    LLM7_BASE_URL,
    COLOR_PRESETS,
)
from .device_control import DeviceController

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

        is_control_or_query = enable_control and self._is_control_or_query(user_text)
        
        _LOGGER.debug(f"Is control/query: {is_control_or_query}")

        if is_control_or_query:
            result = await self._handle_control_request(user_input, conversation_id)
        else:
            result = await self._handle_chat_request(user_input, conversation_id)

        return result

    def _is_control_or_query(self, text: str) -> bool:
        """Check if the request is a device control or sensor query."""
        text_lower = text.lower()
        
        # Aktions-Keywords (Steuerung)
        action_keywords = [
            # Schalten
            "schalte", "schalt", "mach", "mache", "stelle", "stell",
            "schalten", "einschalten", "ausschalten", "anschalten",
            # Dimmen
            "dimme", "dimm", "erhöhe", "verringere", "heller", "dunkler",
            # Öffnen/Schließen
            "öffne", "schließe", "öffnen", "schließen",
            # Starten/Stoppen
            "starte", "stoppe", "spiele", "pausiere", "aktiviere", "deaktiviere",
            # Setzen/Ändern
            "setze", "ändere", "ändern", "wechsle", "wechsel",
            # Farben
            "färbe", "farbe", "färben",
            # Direkte Befehle
            " an", " aus", " ein", "anmachen", "ausmachen",
            # Englisch
            "turn on", "turn off", "switch", "toggle",
        ]
        
        # Farb-Keywords
        color_keywords = list(COLOR_PRESETS.keys()) + [
            "rot", "grün", "blau", "gelb", "weiß", "schwarz",
            "orange", "pink", "lila", "violett", "türkis", "cyan",
            "warm", "kalt", "bunt", "regenbogen",
        ]
        
        # Geräte-Keywords
        device_keywords = [
            "licht", "lampe", "lampen", "lichter", "leuchte",
            "heizung", "thermostat", "klimaanlage", "klima",
            "jalousie", "rollladen", "rollo", "rolladen",
            "steckdose", "schalter", "stecker",
            "fernseher", "tv", "musik", "lautsprecher", "speaker",
            "ventilator", "lüfter", "fan",
            "wled", "led", "stripe", "streifen",
        ]
        
        # Abfrage-Keywords (Sensoren)
        query_keywords = [
            "temperatur", "wie warm", "wie kalt", "grad", "celsius",
            "luftfeuchtigkeit", "feuchtigkeit", "humidity",
            "sensor", "sensoren", "status", "zustand",
            "zeig mir", "zeige mir", "was ist", "wie ist", "welche",
            "fenster", "tür", "türen", "offen", "geschlossen",
            "eingeschaltet", "ausgeschaltet", "aktiv",
            "batterie", "batterien", "akku",
            "offline", "nicht erreichbar", "verfügbar",
            "energie", "strom", "verbrauch", "watt",
            "übersicht", "zusammenfassung", "alle",
        ]
        
        # Entity-ID Pattern (light.xxx, switch.xxx, etc.)
        entity_pattern = r'\b(light|switch|climate|cover|fan|media_player|sensor|binary_sensor)\.[a-z0-9_]+\b'
        if re.search(entity_pattern, text_lower):
            _LOGGER.debug(f"Entity ID pattern found in: {text}")
            return True
        
        # Prüfe auf Aktions-Keywords
        for keyword in action_keywords:
            if keyword in text_lower:
                _LOGGER.debug(f"Action keyword found: {keyword}")
                return True
        
        # Prüfe auf Kombination: Gerät + Farbe
        has_device = any(kw in text_lower for kw in device_keywords)
        has_color = any(kw in text_lower for kw in color_keywords)
        if has_device and has_color:
            _LOGGER.debug(f"Device + Color combination found")
            return True
        
        # Prüfe auf Abfrage-Keywords
        for keyword in query_keywords:
            if keyword in text_lower:
                _LOGGER.debug(f"Query keyword found: {keyword}")
                return True
        
        # Prüfe auf Prozent-Angaben (Helligkeit)
        if re.search(r'\d+\s*(%|prozent)', text_lower):
            _LOGGER.debug(f"Percentage found")
            return True
        
        # Prüfe auf "bitte" + Gerätename (höfliche Befehle)
        if "bitte" in text_lower and has_device:
            _LOGGER.debug(f"Polite device command found")
            return True
        
        return False

    async def _handle_control_request(
        self, 
        user_input: conversation.ConversationInput,
        conversation_id: str
    ) -> conversation.ConversationResult:
        """Handle device control and sensor query requests."""
        start_time = time.time()
        
        model_name = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        control_prompt = self.entry.options.get(CONF_CONTROL_PROMPT, DEFAULT_CONTROL_PROMPT)
        control_temperature = float(self.entry.options.get(CONF_CONTROL_TEMPERATURE, DEFAULT_CONTROL_TEMPERATURE))
        control_max_tokens = int(self.entry.options.get(CONF_CONTROL_MAX_TOKENS, DEFAULT_CONTROL_MAX_TOKENS))
        selected_entities = self.entry.options.get(CONF_SELECTED_ENTITIES, [])
        selected_areas = self.entry.options.get(CONF_SELECTED_AREAS, [])
        enable_sensors = self.entry.options.get(CONF_ENABLE_SENSORS, DEFAULT_ENABLE_SENSORS)
        timeout = int(self.entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))
        retry_count = int(self.entry.options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT))

        _LOGGER.debug(f"Control request - Model: {model_name}, Timeout: {timeout}s")

        controller = DeviceController(
            self.hass, selected_entities, selected_areas, enable_sensors
        )
        
        controlled = controller.get_controlled_entities(include_sensors=True)
        entity_count = len(controlled)
        
        _LOGGER.debug(f"Found {entity_count} controllable entities")
        
        if not controlled:
            return self._create_response(
                "⚠️ Keine Geräte konfiguriert. Bitte wähle zuerst Geräte oder Bereiche in den Einstellungen aus.",
                user_input.language,
                conversation_id
            )
        
        entity_context = controller.generate_context()
        
        # Verstärke den Prompt mit deutlicherer Anweisung
        reinforced_prompt = (
            "WICHTIG: Du bist ein Smart Home Controller. "
            "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt! "
            "KEIN erklärender Text, KEINE Markdown-Formatierung, NUR JSON!\n\n"
            + control_prompt 
            + entity_context
        )
        
        _LOGGER.debug(f"Prompt length: {len(reinforced_prompt)} chars")
        _LOGGER.info(f"User command: {user_input.text}")

        response_text = None
        last_error = None
        
        for attempt in range(retry_count + 1):
            try:
                messages = [
                    {"role": "system", "content": reinforced_prompt},
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
                _LOGGER.info(f"LLM Response: {response_text[:500] if response_text else 'None'}")
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
                f"💡 Tipp: Erhöhe den Timeout in den Einstellungen.",
                user_input.language,
                conversation_id
            )

        # Versuche Befehl auszuführen
        result = await controller.execute_command(response_text)

        if result:
            elapsed = time.time() - start_time
            _LOGGER.info(f"Control request completed in {elapsed:.1f}s")
            return self._create_response(result, user_input.language, conversation_id)
        else:
            # Fallback: Versuche den Befehl direkt zu parsen (ohne LLM)
            _LOGGER.warning(f"LLM response not valid, trying direct parse")
            direct_result = await self._try_direct_command(user_input.text, controller)
            
            if direct_result:
                return self._create_response(direct_result, user_input.language, conversation_id)
            
            _LOGGER.warning(f"Could not parse response: {response_text[:200]}")
            return self._create_response(
                f"Ich konnte den Befehl nicht verstehen.\n\n"
                f"LLM Antwort war kein gültiges JSON.\n\n"
                f"Beispiele:\n"
                f"• 'Schalte das Licht an'\n"
                f"• 'Mache die Küche rot'\n"
                f"• 'light.wled_tv_mobel auf grün'",
                user_input.language,
                conversation_id
            )

    async def _try_direct_command(self, text: str, controller: DeviceController) -> str | None:
        """Try to parse and execute command directly without LLM."""
        text_lower = text.lower()
        
        controlled = controller.get_controlled_entities(include_sensors=False)
        
        # Suche nach Entity-ID im Text
        entity_id = None
        for eid in controlled.keys():
            eid_lower = eid.lower()
            eid_short = eid.split('.')[-1]
            
            if eid_lower in text_lower or eid_short in text_lower.replace('-', '_').replace(' ', '_'):
                entity_id = eid
                break
        
        # Suche nach Gerätenamen im Text
        if not entity_id:
            for eid, info in controlled.items():
                name_lower = info['name'].lower()
                # Normalisiere Namen für Vergleich
                name_normalized = name_lower.replace('-', ' ').replace('_', ' ')
                text_normalized = text_lower.replace('-', ' ').replace('_', ' ')
                
                if name_lower in text_lower or name_normalized in text_normalized:
                    entity_id = eid
                    break
        
        if not entity_id:
            return None
        
        _LOGGER.info(f"Direct parse found entity: {entity_id}")
        
        # Bestimme Service
        service = "turn_on"
        if any(word in text_lower for word in ["aus", "off", "ausschalten", "ausmachen"]):
            service = "turn_off"
        elif any(word in text_lower for word in ["toggle", "umschalten", "wechseln"]):
            service = "toggle"
        
        # Bestimme Farbe
        rgb_color = None
        for color_name, rgb in COLOR_PRESETS.items():
            if color_name in text_lower:
                rgb_color = rgb
                _LOGGER.info(f"Direct parse found color: {color_name} = {rgb}")
                break
        
        # Bestimme Helligkeit
        brightness_pct = None
        brightness_match = re.search(r'(\d+)\s*(%|prozent)', text_lower)
        if brightness_match:
            brightness_pct = int(brightness_match.group(1))
            _LOGGER.info(f"Direct parse found brightness: {brightness_pct}%")
        
        # Baue Command
        domain = entity_id.split('.')[0]
        data = {}
        
        if rgb_color:
            data["rgb_color"] = rgb_color
        if brightness_pct:
            data["brightness_pct"] = brightness_pct
        
        command = {
            "action": "control",
            "domain": domain,
            "entity_id": entity_id,
            "service": service,
            "data": data
        }
        
        _LOGGER.info(f"Direct command: {command}")
        
        return await controller.execute_command(str(command))

    async def _handle_chat_request(
        self,
        user_input: conversation.ConversationInput,
        conversation_id: str
    ) -> conversation.ConversationResult:
        """Handle normal chat requests."""
        model_name = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        raw_prompt = self.entry.options.get(CONF_PROMPT, DEFAULT_PROMPT)
        chat_temperature = float(self.entry.options.get(CONF_CHAT_TEMPERATURE, DEFAULT_CHAT_TEMPERATURE))
        chat_max_tokens = int(self.entry.options.get(CONF_CHAT_MAX_TOKENS, DEFAULT_CHAT_MAX_TOKENS))
        history_limit = int(self.entry.options.get(CONF_HISTORY_LIMIT, DEFAULT_HISTORY_LIMIT))
        timeout = int(self.entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))
        retry_count = int(self.entry.options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT))

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

        max_messages = history_limit + 1
        if len(self.history[conversation_id]) > max_messages:
            self.history[conversation_id] = (
                [self.history[conversation_id][0]] +
                self.history[conversation_id][-(history_limit):]
            )

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
        timeout: int = 60
    ) -> str:
        """Send a query to the LLM."""
        url = f"{LLM7_BASE_URL}/chat/completions"
        
        total_chars = sum(len(str(m.get('content', ''))) for m in messages)
        estimated_tokens = total_chars // 4
        
        _LOGGER.debug(f"LLM Request - Model: {model_name}, ~{estimated_tokens} input tokens")
        
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
            
            return str(data)

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            _LOGGER.error(f"LLM request timed out after {elapsed:.1f}s")
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