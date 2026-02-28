"""The freellm_chat Conversation integration."""
from __future__ import annotations

import logging
from typing import Literal

import requests

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import intent, template

from .const import (
    CONF_CHAT_MODEL,
    CONF_PROMPT,
    CONF_ENABLE_DEVICE_CONTROL,
    CONF_CONTROL_PROMPT,
    CONF_SELECTED_ENTITIES,
    CONF_SELECTED_AREAS,
    DEFAULT_CHAT_MODEL,
    DEFAULT_PROMPT,
    DEFAULT_ENABLE_DEVICE_CONTROL,
    DEFAULT_CONTROL_PROMPT,
    DOMAIN,
    LLM7_BASE_URL,
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

        # Prüfe ob Gerätesteuerung aktiviert ist
        enable_control = self.entry.options.get(
            CONF_ENABLE_DEVICE_CONTROL, DEFAULT_ENABLE_DEVICE_CONTROL
        )

        # Bestimme ob es eine Steuerungsanfrage ist
        is_control_request = enable_control and self._is_control_request(user_text)

        if is_control_request:
            result = await self._handle_control_request(user_input, conversation_id)
        else:
            result = await self._handle_chat_request(user_input, conversation_id)

        return result

    def _is_control_request(self, text: str) -> bool:
        """Check if the request is a device control request."""
        control_keywords = [
            # Deutsch
            "schalte", "schalt", "mach", "mache", "stelle", "stell",
            "dimme", "dimm", "erhöhe", "erhöh", "verringere", "verringer",
            "öffne", "öffn", "schließe", "schließ", "fahre", "fahr",
            "starte", "start", "stoppe", "stopp", "spiele", "spiel",
            "pausiere", "pausier", "aktiviere", "aktivier", "deaktiviere",
            "licht", "lampe", "leuchte", "heizung", "thermostat",
            "jalousie", "rollladen", "rollo", "rolladen",
            "musik", "fernseher", "tv", "lautsprecher",
            "ventilator", "lüfter", "klimaanlage", "klima",
            " an", " aus", " ein", "anmachen", "ausmachen", "einschalten", "ausschalten",
            # Englisch
            "turn on", "turn off", "switch on", "switch off",
            "set", "dim", "brighten", "open", "close",
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in control_keywords)

    async def _handle_control_request(
        self, 
        user_input: conversation.ConversationInput,
        conversation_id: str
    ) -> conversation.ConversationResult:
        """Handle device control requests."""
        model_name = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        control_prompt = self.entry.options.get(CONF_CONTROL_PROMPT, DEFAULT_CONTROL_PROMPT)
        selected_entities = self.entry.options.get(CONF_SELECTED_ENTITIES, [])
        selected_areas = self.entry.options.get(CONF_SELECTED_AREAS, [])

        # Initialize device controller
        controller = DeviceController(self.hass, selected_entities, selected_areas)
        
        # Check if any entities are available
        controlled_entities = controller.get_controlled_entities()
        if not controlled_entities:
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(
                "⚠️ Es sind keine Geräte zur Steuerung konfiguriert. "
                "Bitte wähle zuerst Geräte oder Bereiche in den Einstellungen aus."
            )
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=conversation_id
            )
        
        # Add entity context to prompt
        full_prompt = control_prompt + controller.generate_context()

        try:
            # Create temporary conversation for control
            messages = [
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": user_input.text}
            ]

            response_text = await self._async_query_llm(model_name, messages)
            _LOGGER.debug(f"Control LLM Response: {response_text}")

            # Execute the command
            result = await controller.execute_control_command(response_text)

            if result:
                response_text = result
            else:
                # Fallback: Zeige die LLM-Antwort wenn keine Steuerung erkannt wurde
                response_text = (
                    "Ich konnte den Befehl leider nicht verstehen. "
                    "Bitte formuliere ihn anders.\n\n"
                    f"Beispiele:\n"
                    f"• 'Schalte das Licht in der Küche an'\n"
                    f"• 'Mache das Wohnzimmer grün'\n"
                    f"• 'Dimme das Schlafzimmer auf 50%'"
                )

        except Exception as e:
            _LOGGER.error(f"Error in control request: {e}")
            response_text = f"❌ Fehler bei der Steuerung: {str(e)}"

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)
        
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=conversation_id
        )

    async def _handle_chat_request(
        self,
        user_input: conversation.ConversationInput,
        conversation_id: str
    ) -> conversation.ConversationResult:
        """Handle normal chat requests."""
        model_name = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        raw_prompt = self.entry.options.get(CONF_PROMPT, DEFAULT_PROMPT)

        try:
            prompt = template.Template(raw_prompt, self.hass).async_render(
                {"ha_name": self.hass.config.location_name},
                parse_result=False,
            )
        except TemplateError as err:
            _LOGGER.error(f"Error rendering prompt: {err}")
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Template-Fehler: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=conversation_id
            )

        # Manage conversation history
        if conversation_id not in self.history:
            self.history[conversation_id] = [{"role": "system", "content": prompt}]

        self.history[conversation_id].append({"role": "user", "content": user_input.text})

        # Limit history to last 20 messages to avoid token limits
        if len(self.history[conversation_id]) > 21:  # 1 system + 20 messages
            self.history[conversation_id] = (
                [self.history[conversation_id][0]] +  # Keep system prompt
                self.history[conversation_id][-20:]    # Keep last 20 messages
            )

        try:
            response_text = await self._async_query_llm(
                model_name, self.history[conversation_id]
            )
            self.history[conversation_id].append({
                "role": "assistant", 
                "content": response_text
            })
        except Exception as e:
            _LOGGER.error(f"Error querying LLM: {e}")
            response_text = f"❌ Fehler bei der Anfrage: {str(e)}"

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)
        
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=conversation_id
        )

    async def _async_query_llm(self, model_name: str, messages: list[dict]) -> str:
        """Send a query to the LLM."""
        url = f"{LLM7_BASE_URL}/chat/completions"
        headers = {"Content-Type": "application/json"}

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }

        def make_request(url, headers, json_payload):
            return requests.post(url, headers=headers, json=json_payload, timeout=60)

        try:
            response = await self.hass.async_add_executor_job(
                make_request, url, headers, payload
            )
            response.raise_for_status()
            response_json = response.json()

            if "choices" in response_json and len(response_json["choices"]) > 0:
                if "message" in response_json["choices"][0]:
                    return response_json["choices"][0]["message"]["content"].strip()
            
            _LOGGER.warning(f"Unexpected API response: {response_json}")
            return str(response_json)

        except requests.exceptions.Timeout:
            _LOGGER.error("LLM API request timed out")
            raise Exception("Die Anfrage hat zu lange gedauert. Bitte versuche es erneut.")
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"LLM API Error: {e}")
            raise