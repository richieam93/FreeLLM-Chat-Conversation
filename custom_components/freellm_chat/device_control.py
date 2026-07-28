"""Reliable control tools and argument cleanup for Home Assistant devices."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.util.json import JsonObjectType

from .device_query import (
    EntityRecord,
    _filter_location,
    _get_exposed_records,
    _normalize,
    _normalize_domain,
    _rank_records,
    _record_summary,
)

CONTROL_TOOL_NAME = "FreeLLMControlEntities"

DEVICE_CONTROL_PROMPT = """
Zuverlässige Gerätesteuerung / Reliable device control:
- Verwende FreeLLMControlEntities bevorzugt für Lichter, Schalter, Ventilatoren,
  Mediengeräte, Klimageräte, Abdeckungen, Szenen, Skripte und Tasten.
- Für ein namentlich genanntes Gerät verwende query oder entity_id. Beispiel:
  „wled_küche einschalten“ -> action=turn_on, query=wled_küche, domain=light.
- „Küchenlicht einschalten“ oder „Licht in der Küche einschalten“ bezeichnet die
  freigegebenen Lichter im Bereich Küche: action=turn_on, area=Küche, domain=light,
  all_matches=true. Wähle nicht willkürlich nur eine Lampe aus.
- Verwende niemals leere Strings, leere Listen oder leere device_class-Werte.
- Mische für ein eindeutig benanntes Gerät nicht unnötig name/query mit area und floor.
- Bei mehreren gleich guten Treffern führe nichts aus, sondern frage anhand der
  zurückgegebenen Namen und Bereiche nach.
- Nach einem Fehler lies error/message und korrigiere die Parameter. Wiederhole nicht
  unverändert dieselbe fehlgeschlagene Aktion.
- Verwende FreeLLMSearchEntities zum Auflisten. Nenne bei Lichtlisten mindestens Name,
  Bereich, Zustand und Erreichbarkeit; Entity-IDs nur, wenn sie hilfreich sind.
- Use query/entity_id for a named device and area+domain+all_matches for all matching
  devices in a room. Never invent a target and never report success before the tool did.
""".strip()

# Actions are deliberately limited to standardized, reversible Home Assistant services.
_ACTION_SERVICES: dict[str, dict[str, tuple[str, str]]] = {
    "turn_on": {
        domain: (domain, "turn_on")
        for domain in (
            "light",
            "switch",
            "fan",
            "input_boolean",
            "media_player",
            "humidifier",
            "climate",
            "remote",
            "siren",
        )
    },
    "turn_off": {
        domain: (domain, "turn_off")
        for domain in (
            "light",
            "switch",
            "fan",
            "input_boolean",
            "media_player",
            "humidifier",
            "climate",
            "remote",
            "siren",
        )
    },
    "toggle": {
        domain: (domain, "toggle")
        for domain in (
            "light",
            "switch",
            "fan",
            "input_boolean",
            "media_player",
        )
    },
    "open": {"cover": ("cover", "open_cover")},
    "close": {"cover": ("cover", "close_cover")},
    "stop": {
        "cover": ("cover", "stop_cover"),
        "media_player": ("media_player", "media_stop"),
        "vacuum": ("vacuum", "stop"),
    },
    "set_position": {"cover": ("cover", "set_cover_position")},
    "set_percentage": {"fan": ("fan", "set_percentage")},
    "press": {
        "button": ("button", "press"),
        "input_button": ("input_button", "press"),
    },
    "activate": {
        "scene": ("scene", "turn_on"),
        "script": ("script", "turn_on"),
    },
    "start": {"vacuum": ("vacuum", "start")},
    "return_to_base": {"vacuum": ("vacuum", "return_to_base")},
}

_ACTION_VALUES = tuple(_ACTION_SERVICES)

_GENERIC_TARGET_WORDS = {
    "licht",
    "lichter",
    "lampe",
    "lampen",
    "light",
    "lights",
    "schalter",
    "switch",
    "ventilator",
    "fan",
    "rollladen",
    "jalousie",
    "cover",
    "gerät",
    "geräte",
    "gerat",
    "gerate",
    "device",
    "devices",
}


class SanitizedHomeAssistantTool(llm.Tool):
    """Wrap a Home Assistant tool and remove malformed optional arguments."""

    def __init__(self, tool: llm.Tool, user_text: str = "") -> None:
        self._tool = tool
        self._user_text = user_text
        self.name = tool.name
        self.parameters = tool.parameters
        fallback_note = (
            " Prefer FreeLLMControlEntities for named lights and area-wide device "
            "control; use this Home Assistant intent as a fallback."
            if _base_tool_name(tool.name) in {"HassTurnOn", "HassTurnOff", "HassLightSet"}
            else ""
        )
        extra = (
            " Omit optional fields when they are unknown. Never send empty strings, "
            "empty arrays, or empty device_class values. For one named device prefer "
            "name and domain; for all devices in a room prefer area and domain."
            f"{fallback_note}"
        )
        self.description = f"{tool.description or ''}{extra}".strip()

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        return await self._tool.async_call(
            hass,
            sanitize_tool_input(tool_input, self._user_text),
            llm_context,
        )


class FreeLLMControlEntitiesTool(llm.Tool):
    """Resolve exposed entities safely and execute a standardized action."""

    name = CONTROL_TOOL_NAME
    description = (
        "Reliably control exposed Home Assistant entities by exact entity_id, fuzzy name, "
        "area, floor, and domain. Supports lights, switches, fans, media players, climate, "
        "covers, scenes, scripts, buttons, and vacuums. Returns resolved targets and their "
        "states before and after the action. Use this instead of HassTurnOn/HassTurnOff "
        "when controlling named lights or all lights in an area."
    )

    def __init__(self, max_results: int, user_text: str = "") -> None:
        self._max_results = min(max(1, max_results), 50)
        self._user_text = user_text
        self.parameters = vol.Schema(
            {
                vol.Required("action"): vol.In(_ACTION_VALUES),
                vol.Optional("entity_id"): vol.All(str, vol.Length(min=1, max=255)),
                vol.Optional("query"): vol.All(str, vol.Length(min=1, max=160)),
                vol.Optional("name"): vol.All(str, vol.Length(min=1, max=160)),
                vol.Optional("area"): vol.All(str, vol.Length(min=1, max=100)),
                vol.Optional("floor"): vol.All(str, vol.Length(min=1, max=100)),
                vol.Optional("domain"): vol.All(str, vol.Length(min=1, max=80)),
                vol.Optional("all_matches", default=False): bool,
                vol.Optional("confirm_all_home", default=False): bool,
                vol.Optional("brightness"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=100)
                ),
                vol.Optional("color"): vol.All(str, vol.Length(min=1, max=80)),
                vol.Optional("color_temperature_kelvin"): vol.All(
                    vol.Coerce(int), vol.Range(min=1000, max=40000)
                ),
                vol.Optional("effect"): vol.All(str, vol.Length(min=1, max=120)),
                vol.Optional("transition"): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=300)
                ),
                vol.Optional("position"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=100)
                ),
                vol.Optional("percentage"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=100)
                ),
                vol.Optional("limit", default=min(25, self._max_results)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=self._max_results)
                ),
            }
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        raw_args = _clean_mapping(tool_input.tool_args)
        if "query" not in raw_args and "name" in raw_args:
            raw_args["query"] = raw_args.pop("name")
        if isinstance(raw_args.get("domain"), list):
            domains = [
                str(item).strip()
                for item in raw_args["domain"]
                if str(item).strip()
            ]
            if len(domains) != 1:
                raise HomeAssistantError("domain must contain exactly one value")
            raw_args["domain"] = domains[0]
        if "action" in raw_args:
            raw_args["action"] = _normalize_action(raw_args["action"])
        args = self.parameters(raw_args)
        action = str(args["action"])
        limit = min(int(args.get("limit", 25)), self._max_results)
        records = _get_exposed_records(hass)
        selected_or_result = _resolve_control_targets(
            hass, records, args, limit, self._user_text
        )
        if isinstance(selected_or_result, dict):
            return selected_or_result
        selected = selected_or_result

        supported: list[EntityRecord] = []
        unsupported: list[dict[str, Any]] = []
        unavailable: list[dict[str, Any]] = []
        for record in selected:
            if record.domain not in _ACTION_SERVICES[action]:
                item = _record_summary(record)
                item["reason"] = f'action "{action}" is not supported for {record.domain}'
                unsupported.append(item)
                continue
            if not record.available and record.domain not in (
                "scene",
                "script",
                "button",
                "input_button",
            ):
                item = _record_summary(record)
                item["reason"] = "entity is unavailable or unknown"
                unavailable.append(item)
                continue
            supported.append(record)

        if not supported:
            return {
                "result": "failed",
                "action": action,
                "message": "No resolved target can execute the requested action.",
                "unsupported": unsupported,
                "unavailable": unavailable,
            }

        before = {record.entity_id: record.state.state for record in supported}
        groups: dict[tuple[str, str], list[EntityRecord]] = defaultdict(list)
        for record in supported:
            groups[_ACTION_SERVICES[action][record.domain]].append(record)

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        for (service_domain, service), group in groups.items():
            entity_ids = [record.entity_id for record in group]
            if not hass.services.has_service(service_domain, service):
                failed.extend(
                    {
                        "entity_id": entity_id,
                        "error": f"Service {service_domain}.{service} is not available",
                    }
                    for entity_id in entity_ids
                )
                continue
            service_data = _service_data(action, service_domain, entity_ids, args)
            try:
                await hass.services.async_call(
                    service_domain,
                    service,
                    service_data,
                    blocking=True,
                    context=llm_context.context,
                )
            except HomeAssistantError as err:
                failed.extend(
                    {"entity_id": entity_id, "error": str(err)}
                    for entity_id in entity_ids
                )
            else:
                succeeded.extend(entity_ids)

        targets: list[dict[str, Any]] = []
        by_id = {record.entity_id: record for record in supported}
        for entity_id in succeeded:
            old_record = by_id[entity_id]
            current = hass.states.get(entity_id)
            item = _record_summary(old_record)
            item["before"] = before[entity_id]
            item["after"] = current.state if current else None
            item["state_changed"] = bool(
                current and current.state != before[entity_id]
            )
            targets.append(item)

        had_failures = bool(failed or unsupported or unavailable)
        result = (
            "success"
            if succeeded and not had_failures
            else "partial"
            if succeeded
            else "failed"
        )
        return {
            "result": result,
            "action": action,
            "requested": len(selected),
            "succeeded": len(succeeded),
            "failed_count": len(failed) + len(unsupported) + len(unavailable),
            "targets": targets,
            "failed": failed,
            "unsupported": unsupported,
            "unavailable": unavailable,
            "message": (
                "Action executed for the resolved exposed entities."
                if result == "success"
                else "The action was only partly successful; inspect the failed targets."
                if result == "partial"
                else "The action could not be executed."
            ),
        }


def prepare_device_control_tools(
    api_instance: llm.APIInstance, max_results: int, user_text: str = ""
) -> None:
    """Clean built-in intent tools and prepend the reliable control tool."""
    wrapped: list[llm.Tool] = []
    existing_names: set[str] = set()
    for tool in api_instance.tools:
        existing_names.add(tool.name)
        if _should_sanitize_tool(tool.name):
            wrapped.append(SanitizedHomeAssistantTool(tool, user_text))
        else:
            wrapped.append(tool)

    if CONTROL_TOOL_NAME not in existing_names:
        wrapped.insert(0, FreeLLMControlEntitiesTool(max_results, user_text))
    api_instance.tools[:] = wrapped


def sanitize_tool_input(
    tool_input: llm.ToolInput, user_text: str = ""
) -> llm.ToolInput:
    """Return a tool input without blank, malformed, or conflicting slots."""
    args = _clean_mapping(tool_input.tool_args)
    base_name = _base_tool_name(tool_input.tool_name)

    if base_name.startswith("Hass"):
        for key in ("domain", "device_class"):
            value = args.get(key)
            if isinstance(value, str):
                args[key] = [value]
            elif isinstance(value, list):
                values = [str(item).strip() for item in value if str(item).strip()]
                if values:
                    args[key] = list(dict.fromkeys(values))
                else:
                    args.pop(key, None)

        # Home Assistant intent tools expect either a concrete name+domain or an
        # area+domain for a generic room action. Models sometimes send both. Resolve
        # that conflict from the original request instead of forwarding invalid slots.
        _resolve_intent_slot_conflict(args, user_text)

        # A floor is redundant when a concrete name or area is already supplied.
        if args.get("name") or args.get("area"):
            args.pop("floor", None)

    return replace(tool_input, tool_args=args)


def _resolve_intent_slot_conflict(args: dict[str, Any], user_text: str) -> None:
    """Choose name or area when a built-in intent receives both slots."""
    name = str(args.get("name", "")).strip()
    area = str(args.get("area", "")).strip()
    if not name or not area:
        return

    normalized_text = _normalize(user_text)
    normalized_name = _normalize(name)
    normalized_area = _normalize(area)
    if not normalized_text:
        # A concrete name is safer than broadening an action to a complete room.
        args.pop("area", None)
        return

    name_tokens = {
        token
        for token in normalized_name.split()
        if len(token) >= 2 and token not in _GENERIC_TARGET_WORDS
    }
    text_tokens = set(normalized_text.split())
    area_tokens = {token for token in normalized_area.split() if len(token) >= 3}
    area_mentioned = normalized_area in normalized_text or any(
        text_token.startswith(area_token) or area_token.startswith(text_token)
        for text_token in text_tokens
        for area_token in area_tokens
        if len(text_token) >= 3
    )
    generic_target_mentioned = any(
        generic_word == text_token
        or (len(generic_word) >= 4 and generic_word in text_token)
        for text_token in text_tokens
        for generic_word in _GENERIC_TARGET_WORDS
    )
    explicitly_named = (
        normalized_name in normalized_text
        or bool(name_tokens & text_tokens)
    )
    generic_area_request = (
        area_mentioned and generic_target_mentioned and not explicitly_named
    )

    if generic_area_request:
        args.pop("name", None)
    else:
        args.pop("area", None)


def _resolve_control_targets(
    hass: HomeAssistant,
    records: list[EntityRecord],
    args: dict[str, Any],
    limit: int,
    user_text: str,
) -> list[EntityRecord] | JsonObjectType:
    entity_id = str(args.get("entity_id", "")).strip()
    query = str(args.get("query", "")).strip()
    domain = _normalize_domain(args.get("domain"))
    area = args.get("area")
    floor = args.get("floor")
    all_matches = bool(args.get("all_matches", False))

    if entity_id:
        exact_entity = [
            record
            for record in records
            if record.entity_id.casefold() == entity_id.casefold()
        ]
        if exact_entity:
            if domain and exact_entity[0].domain != domain:
                return {
                    "result": "no_match",
                    "query": entity_id,
                    "message": f"The entity exists, but it is not in domain {domain}.",
                    "suggestions": [_record_summary(exact_entity[0])],
                }
            return exact_entity

        # Models occasionally construct an entity_id from a friendly name. Fall back to
        # fuzzy name resolution instead of failing immediately.
        if "." in entity_id:
            guessed_domain, guessed_name = entity_id.split(".", 1)
            if not domain:
                domain = _normalize_domain(guessed_domain)
            if not query:
                query = guessed_name
        elif not query:
            query = entity_id

    records = _filter_location(hass, records, area=area, floor=floor)
    if domain:
        records = [record for record in records if record.domain == domain]

    if query:
        ranked = _rank_records(records, query)
        candidates = [(score, record) for score, record in ranked if score >= 56]
        if not candidates:
            return {
                "result": "no_match",
                "query": query,
                "message": "No exposed entity matched the requested name.",
                "suggestions": [
                    _record_summary(record)
                    for score, record in ranked[:5]
                    if score >= 35
                ],
            }

        exact = [
            record
            for score, record in candidates
            if score >= 99
            or _normalize(query) == _normalize(record.entity_id)
            or _normalize(query) == _normalize(record.name)
            or any(_normalize(query) == _normalize(alias) for alias in record.aliases)
        ]
        if len(exact) == 1:
            return exact
        if len(exact) > 1:
            if all_matches and (area or floor):
                return exact[:limit]
            return {
                "result": "ambiguous",
                "query": query,
                "message": "Several exposed entities have the same matching name.",
                "matches": [_record_summary(record) for record in exact[:limit]],
            }

        best_score = candidates[0][0]
        close = [
            record
            for score, record in candidates
            if score >= best_score - 4
        ]
        if all_matches:
            matches = [record for score, record in candidates if score >= 70][:limit]
            if len(matches) > 1 and not area and not floor:
                _require_homewide_confirmation(args, user_text)
            return matches
        if len(close) == 1:
            return close
        return {
            "result": "ambiguous",
            "query": query,
            "message": "Several exposed entities match. Ask for the area or exact name.",
            "matches": [_record_summary(record) for record in close[:limit]],
        }

    if not domain:
        raise HomeAssistantError(
            "A domain is required when no entity_id or device name is supplied."
        )
    if not area and not floor:
        _require_homewide_confirmation(args, user_text)
    if not all_matches:
        raise HomeAssistantError(
            "Room-, floor-, or home-wide control requires all_matches=true."
        )
    if not records:
        return {
            "result": "no_match",
            "message": "No exposed entities match the requested location and domain.",
        }
    return records[:limit]


def _service_data(
    action: str,
    domain: str,
    entity_ids: list[str],
    args: dict[str, Any],
) -> dict[str, Any]:
    data: dict[str, Any] = {"entity_id": entity_ids}
    if domain == "light" and action == "turn_on":
        if "brightness" in args:
            data["brightness_pct"] = int(args["brightness"])
        if "color" in args:
            data["color_name"] = str(args["color"])
        if "color_temperature_kelvin" in args:
            data["color_temp_kelvin"] = int(args["color_temperature_kelvin"])
        if "effect" in args:
            data["effect"] = str(args["effect"])
        if "transition" in args:
            data["transition"] = float(args["transition"])
    elif domain == "cover" and action == "set_position":
        if "position" not in args:
            raise HomeAssistantError("position is required for set_position")
        data["position"] = int(args["position"])
    elif domain == "fan" and action == "set_percentage":
        if "percentage" not in args:
            raise HomeAssistantError("percentage is required for set_percentage")
        data["percentage"] = int(args["percentage"])
    return data



def _require_homewide_confirmation(
    args: dict[str, Any], user_text: str
) -> None:
    if not bool(args.get("confirm_all_home", False)):
        raise HomeAssistantError(
            "Controlling every matching entity in the home requires "
            "confirm_all_home=true."
        )
    if not _explicit_all_home_request(user_text):
        raise HomeAssistantError(
            "The user's message did not explicitly request a home-wide action."
        )

def _explicit_all_home_request(user_text: str) -> bool:
    normalized = _normalize(user_text)
    phrases = (
        "alle lampen",
        "alle lichter",
        "alle schalter",
        "alle geräte",
        "alle geraete",
        "im ganzen haus",
        "überall",
        "ueberall",
        "all lights",
        "all devices",
        "every light",
        "every device",
        "throughout the house",
        "whole house",
    )
    return any(_normalize(phrase) in normalized for phrase in phrases)


def _normalize_action(value: Any) -> str:
    normalized = _normalize(value).replace(" ", "_")
    aliases = {
        "einschalten": "turn_on",
        "anschalten": "turn_on",
        "an": "turn_on",
        "ausschalten": "turn_off",
        "abschalten": "turn_off",
        "aus": "turn_off",
        "umschalten": "toggle",
        "öffnen": "open",
        "oeffnen": "open",
        "schließen": "close",
        "schliessen": "close",
        "position": "set_position",
        "prozent": "set_percentage",
        "drücken": "press",
        "druecken": "press",
        "aktivieren": "activate",
        "starten": "start",
        "zur_basis": "return_to_base",
    }
    return aliases.get(normalized, normalized)


def _should_sanitize_tool(tool_name: str) -> bool:
    return _base_tool_name(tool_name).startswith("Hass")


def _base_tool_name(tool_name: str) -> str:
    return tool_name.rsplit("__", 1)[-1].rsplit(".", 1)[-1]


def _clean_mapping(values: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values.items():
        cleaned = _clean_value(value)
        if cleaned is not None:
            result[str(key)] = cleaned
    return result


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    if isinstance(value, list):
        cleaned = [
            item
            for item in (_clean_value(item) for item in value)
            if item is not None
        ]
        return cleaned or None
    if isinstance(value, tuple):
        cleaned = [
            item
            for item in (_clean_value(item) for item in value)
            if item is not None
        ]
        return cleaned or None
    if isinstance(value, dict):
        cleaned = _clean_mapping(value)
        return cleaned or None
    return value
