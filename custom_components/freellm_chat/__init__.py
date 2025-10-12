"""The freellm_chat Conversation integration."""
from __future__ import annotations

import logging
from typing import Literal

import requests
import json

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import intent, template

from .const import (
    CONF_CHAT_MODEL,
    CONF_PROMPT,
    DEFAULT_CHAT_MODEL,
    DEFAULT_PROMPT,
    DOMAIN,
    LLM7_BASE_URL,
)

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
        model_name = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        raw_prompt = self.entry.options.get(CONF_PROMPT, DEFAULT_PROMPT)
        conversation_id = user_input.conversation_id

        try:
            prompt = self._async_generate_prompt(raw_prompt)
        except TemplateError as err:
            _LOGGER.error("Error rendering prompt: %s", err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Sorry, I had a problem with my template: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )

        if conversation_id not in self.history:
            self.history[conversation_id] = [{"role": "system", "content": prompt}]

        self.history[conversation_id].append({"role": "user", "content": user_input.text})
        
        try:
            response_text = await self._async_query_llm(model_name, self.history[conversation_id])
        except Exception as e:
            _LOGGER.error("Error querying LLM: %s", e)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Sorry, I had a problem talking to the LLM: {e}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )

        _LOGGER.debug("Response %s", response_text)
        self.history[conversation_id].append({"role": "assistant", "content": response_text})

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)
        return conversation.ConversationResult(
            response=intent_response, conversation_id=conversation_id
        )

    def _async_generate_prompt(self, raw_prompt: str) -> str:
        """Generate a prompt for the user."""
        return template.Template(raw_prompt, self.hass).async_render(
            {
                "ha_name": self.hass.config.location_name,
            },
            parse_result=False,
        )

    async def _async_query_llm(self, model_name: str, messages: list[dict]) -> str:
        """Send a query to the LLM."""
        url = f"{LLM7_BASE_URL}/chat/completions"
        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_name,
            "messages": messages
        }

        try:
            def make_request(url, headers, json_payload):
                return requests.post(url, headers=headers, json=json_payload)

            response = await self.hass.async_add_executor_job(
                make_request, url, headers, payload
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            response_json = response.json()

            # Die Antwort von LLM7.io hat eine andere Struktur als die von Hugging Face.
            # Wir müssen die generierte Antwort aus dem JSON extrahieren.
            if "choices" in response_json and len(response_json["choices"]) > 0 and "message" in response_json["choices"][0] and "content" in response_json["choices"][0]["message"]:
                response_text = response_json["choices"][0]["message"]["content"].strip()
            else:
                response_text = str(response_json)

            return response_text

        except requests.exceptions.RequestException as e:
            _LOGGER.error("Error during request to LLM7.io API: %s", e)
            raise