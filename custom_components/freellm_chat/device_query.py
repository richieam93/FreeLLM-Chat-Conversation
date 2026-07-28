"""Read-only Home Assistant tools for reliable device and state queries."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
import re
from typing import Any

import voluptuous as vol

from homeassistant.components.homeassistant import exposed_entities
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
    llm,
)
from homeassistant.util.json import JsonObjectType

DEVICE_QUERY_TOOL_NAMES = frozenset(
    {
        "FreeLLMGetEntityState",
        "FreeLLMSearchEntities",
        "FreeLLMSummarizeLocation",
    }
)

DEVICE_QUERY_PROMPT = """
Erweiterte Geräte- und Zustandsabfragen / Extended device and state queries:
- Verwende FreeLLMGetEntityState für ein bestimmtes Gerät oder einen bestimmten Sensor.
- Verwende FreeLLMSearchEntities für Listen und Filter, zum Beispiel eingeschaltete
  Lichter, nicht erreichbare Geräte, Batterien unter einem Grenzwert oder kürzlich
  geänderte Zustände.
- Verwende FreeLLMSummarizeLocation für eine Übersicht eines Raums oder einer Etage.
- Diese drei Werkzeuge sind nur lesend. Nutze für reine Statusfragen niemals ein
  Werkzeug, das Geräte verändert.
- Unterscheide unknown von unavailable. Erfinde keine Werte und leite keinen Zustand
  nur aus einem Gerätenamen ab.
- Wenn mehrere Treffer gleich gut passen, nenne die Bereiche oder frage nach.
- Vergleiche Zahlenwerte nur mit derselben Einheit. Weise auf abgeschnittene Listen hin.
- GetEntityState is for one named entity. SearchEntities is for filtered lists and
  numeric thresholds. SummarizeLocation is for room or floor overviews.
""".strip()

_COMMON_ATTRIBUTE_KEYS = (
    "battery_level",
    "brightness",
    "color_mode",
    "color_temp_kelvin",
    "current_humidity",
    "current_position",
    "current_temperature",
    "fan_mode",
    "friendly_name",
    "hvac_action",
    "hvac_mode",
    "media_album_name",
    "media_artist",
    "media_content_type",
    "media_title",
    "mode",
    "percentage",
    "preset_mode",
    "rgb_color",
    "source",
    "target_temp_high",
    "target_temp_low",
    "temperature",
    "volume_level",
)


_CONTROL_ACTIONS_BY_DOMAIN: dict[str, tuple[str, ...]] = {
    "light": ("turn_on", "turn_off", "toggle", "brightness", "color"),
    "switch": ("turn_on", "turn_off", "toggle"),
    "fan": ("turn_on", "turn_off", "toggle", "set_percentage"),
    "input_boolean": ("turn_on", "turn_off", "toggle"),
    "media_player": ("turn_on", "turn_off", "toggle", "stop"),
    "humidifier": ("turn_on", "turn_off"),
    "climate": ("turn_on", "turn_off"),
    "cover": ("open", "close", "stop", "set_position"),
    "scene": ("activate",),
    "script": ("activate",),
    "button": ("press",),
    "input_button": ("press",),
    "vacuum": ("start", "stop", "return_to_base"),
}

_ACTIVE_STATES = {
    "cleaning",
    "cool",
    "dry",
    "fan_only",
    "heat",
    "on",
    "open",
    "opening",
    "playing",
    "unlocked",
}


@dataclass(slots=True)
class EntityRecord:
    """Prepared metadata for one exposed Home Assistant state."""

    state: State
    entity_id: str
    domain: str
    name: str
    aliases: tuple[str, ...]
    device_name: str | None
    integration: str | None
    manufacturer: str | None
    model: str | None
    area_id: str | None
    area_name: str | None
    floor_id: str | None
    floor_name: str | None
    device_class: str | None
    unit: str | None
    numeric_value: float | None

    @property
    def available(self) -> bool:
        return self.state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)

    @property
    def searchable_names(self) -> tuple[str, ...]:
        return tuple(
            value
            for value in (
                self.entity_id,
                self.name,
                *self.aliases,
                self.device_name,
                self.manufacturer,
                self.model,
            )
            if value
        )


class FreeLLMGetEntityStateTool(llm.Tool):
    """Return detailed state data for a named exposed entity."""

    name = "FreeLLMGetEntityState"
    description = (
        "Read the current state of one named Home Assistant entity. Supports fuzzy "
        "name matching and optional area or floor filters. Read-only. Use this before "
        "answering a question about a specific device or sensor."
    )

    def __init__(self, max_results: int) -> None:
        self._max_results = max_results
        self.parameters = vol.Schema(
            {
                vol.Required("query"): vol.All(str, vol.Length(min=1, max=160)),
                vol.Optional("area"): vol.All(str, vol.Length(min=1, max=100)),
                vol.Optional("floor"): vol.All(str, vol.Length(min=1, max=100)),
                vol.Optional("limit", default=min(8, max_results)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=max_results)
                ),
            }
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        args = tool_input.tool_args
        records = _get_exposed_records(hass)
        records = _filter_location(
            hass,
            records,
            area=args.get("area"),
            floor=args.get("floor"),
        )
        query = str(args["query"])
        ranked = _rank_records(records, query)
        limit = min(int(args.get("limit", 8)), self._max_results)
        matches = [record for score, record in ranked if score >= 56][:limit]

        if not matches:
            suggestions = [
                _record_summary(record)
                for score, record in ranked[: min(5, limit)]
                if score >= 35
            ]
            return {
                "result": "no_match",
                "query": query,
                "suggestions": suggestions,
                "message": "No exposed entity matched the requested name.",
            }

        best_score = ranked[0][0]
        close_matches = [
            record
            for score, record in ranked
            if score >= 56 and score >= best_score - 4
        ]
        exact_entity_id = any(
            _normalize(record.entity_id) == _normalize(query)
            for record in close_matches
        )
        ambiguous = len(close_matches) > 1 and not exact_entity_id
        selected = close_matches[:limit] if ambiguous else matches
        return {
            "result": "ambiguous" if ambiguous else "match",
            "query": query,
            "count": len(selected),
            "entities": [_record_details(record) for record in selected],
            "message": (
                "Several exposed entities match. Use the area or floor to disambiguate."
                if ambiguous
                else "Current state returned."
            ),
        }


class FreeLLMSearchEntitiesTool(llm.Tool):
    """Search exposed entities using structured filters."""

    name = "FreeLLMSearchEntities"
    description = (
        "Search multiple exposed Home Assistant entities by name, room, floor, domain, "
        "integration, manufacturer, model, device class, state, availability, numeric "
        "threshold, or recent change time. "
        "Read-only. Good for questions such as which lights are on, which devices are "
        "unavailable, or which battery sensors are below 20 percent."
    )

    def __init__(self, max_results: int) -> None:
        self._max_results = max_results
        self.parameters = vol.Schema(
            {
                vol.Optional("query"): vol.All(str, vol.Length(min=1, max=160)),
                vol.Optional("area"): vol.All(str, vol.Length(min=1, max=100)),
                vol.Optional("floor"): vol.All(str, vol.Length(min=1, max=100)),
                vol.Optional("domain"): vol.All(str, vol.Length(min=1, max=80)),
                vol.Optional("integration"): vol.All(
                    str, vol.Length(min=1, max=100)
                ),
                vol.Optional("manufacturer"): vol.All(
                    str, vol.Length(min=1, max=100)
                ),
                vol.Optional("model"): vol.All(str, vol.Length(min=1, max=120)),
                vol.Optional("device_class"): vol.All(
                    str, vol.Length(min=1, max=80)
                ),
                vol.Optional("state"): vol.All(str, vol.Length(min=1, max=100)),
                vol.Optional("unit"): vol.All(str, vol.Length(min=1, max=40)),
                vol.Optional("availability", default="all"): vol.In(
                    ("all", "available", "unavailable")
                ),
                vol.Optional("min_value"): vol.Coerce(float),
                vol.Optional("max_value"): vol.Coerce(float),
                vol.Optional("changed_within_minutes"): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=10080)
                ),
                vol.Optional("sort_by", default="relevance"): vol.In(
                    (
                        "relevance",
                        "name",
                        "state",
                        "last_changed",
                        "numeric_value",
                    )
                ),
                vol.Optional("descending", default=False): bool,
                vol.Optional("limit", default=min(25, max_results)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=max_results)
                ),
            }
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        args = tool_input.tool_args
        meaningful_filters = {
            key
            for key in (
                "query",
                "area",
                "floor",
                "domain",
                "integration",
                "manufacturer",
                "model",
                "device_class",
                "state",
                "unit",
                "min_value",
                "max_value",
                "changed_within_minutes",
            )
            if args.get(key) not in (None, "")
        }
        if args.get("availability", "all") != "all":
            meaningful_filters.add("availability")
        if not meaningful_filters:
            raise HomeAssistantError(
                "At least one search filter is required to avoid listing every entity."
            )

        records = _get_exposed_records(hass)
        records = _filter_location(
            hass,
            records,
            area=args.get("area"),
            floor=args.get("floor"),
        )

        domain = _normalize_domain(args.get("domain"))
        integration = _normalize(args.get("integration"))
        manufacturer = _normalize(args.get("manufacturer"))
        model = _normalize(args.get("model"))
        device_class = _normalize_device_class(args.get("device_class"))
        requested_state = _normalize_state(args.get("state"))
        requested_unit = _normalize_unit(args.get("unit"))
        availability = args.get("availability", "all")
        min_value = args.get("min_value")
        max_value = args.get("max_value")
        changed_minutes = args.get("changed_within_minutes")
        now = datetime.now(UTC)

        filtered: list[EntityRecord] = []
        for record in records:
            if domain and record.domain != domain:
                continue
            if integration and _normalize(record.integration) != integration:
                continue
            if manufacturer and manufacturer not in _normalize(record.manufacturer):
                continue
            if model and model not in _normalize(record.model):
                continue
            if (
                device_class
                and _normalize_device_class(record.device_class) != device_class
            ):
                continue
            if requested_state and _normalize_state(record.state.state) != requested_state:
                continue
            if requested_unit and _normalize_unit(record.unit) != requested_unit:
                continue
            if availability == "available" and not record.available:
                continue
            if availability == "unavailable" and record.available:
                continue
            if changed_minutes is not None:
                age_minutes = (now - record.state.last_changed).total_seconds() / 60
                if age_minutes > int(changed_minutes):
                    continue
            filtered.append(record)

        if (min_value is not None or max_value is not None) and not requested_unit:
            units = {
                _normalize_unit(record.unit)
                for record in filtered
                if record.numeric_value is not None and record.unit
            }
            if len(units) > 1:
                visible_units = ", ".join(
                    sorted({record.unit for record in filtered if record.unit})
                )
                raise HomeAssistantError(
                    "The numeric query matches multiple units "
                    f"({visible_units}). Add the unit filter before comparing values."
                )

        if min_value is not None:
            filtered = [
                record
                for record in filtered
                if record.numeric_value is not None
                and record.numeric_value >= float(min_value)
            ]
        if max_value is not None:
            filtered = [
                record
                for record in filtered
                if record.numeric_value is not None
                and record.numeric_value <= float(max_value)
            ]

        query = args.get("query")
        if query:
            ranked = _rank_records(filtered, str(query))
            filtered = [record for score, record in ranked if score >= 44]

        sort_by = args.get("sort_by", "relevance")
        reverse = bool(args.get("descending", False))
        if sort_by != "relevance" or not query:
            effective_sort = "name" if sort_by == "relevance" else sort_by
            filtered.sort(
                key=lambda record: _sort_key(record, effective_sort), reverse=reverse
            )
        elif reverse:
            filtered.reverse()

        total = len(filtered)
        limit = min(int(args.get("limit", 25)), self._max_results)
        selected = filtered[:limit]
        return {
            "result": "matches" if selected else "no_match",
            "count": total,
            "returned": len(selected),
            "truncated": total > len(selected),
            "filters": {
                key: value
                for key, value in args.items()
                if value not in (None, "", "all", False)
            },
            "entities": [_record_details(record) for record in selected],
            "summary": _search_summary(filtered),
        }


class FreeLLMSummarizeLocationTool(llm.Tool):
    """Return a compact overview for one room or floor."""

    name = "FreeLLMSummarizeLocation"
    description = (
        "Summarize the exposed entities and measurements in one Home Assistant area "
        "or floor. Read-only. Returns availability, state counts, numeric measurement "
        "ranges, and a bounded entity list."
    )

    def __init__(self, max_results: int) -> None:
        self._max_results = max_results
        self.parameters = vol.Schema(
            {
                vol.Required("location"): vol.All(
                    str, vol.Length(min=1, max=100)
                ),
                vol.Optional("location_type", default="auto"): vol.In(
                    ("auto", "area", "floor")
                ),
                vol.Optional("domain"): vol.All(str, vol.Length(min=1, max=80)),
                vol.Optional("include_entities", default=True): bool,
                vol.Optional("limit", default=min(30, max_results)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=max_results)
                ),
            }
        )

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        args = tool_input.tool_args
        location = _resolve_location(
            hass,
            str(args["location"]),
            str(args.get("location_type", "auto")),
        )
        records = _get_exposed_records(hass)
        if location["type"] == "area":
            records = [record for record in records if record.area_id == location["id"]]
        else:
            records = [record for record in records if record.floor_id == location["id"]]

        domain = _normalize_domain(args.get("domain"))
        if domain:
            records = [record for record in records if record.domain == domain]
        records.sort(key=lambda record: (_normalize(record.domain), _normalize(record.name)))

        total = len(records)
        available = sum(record.available for record in records)
        states_by_domain: dict[str, dict[str, int]] = {}
        for record in records:
            states_by_domain.setdefault(record.domain, {})
            states_by_domain[record.domain][record.state.state] = (
                states_by_domain[record.domain].get(record.state.state, 0) + 1
            )

        measurements = _measurement_summary(records)
        unavailable = [
            _record_summary(record) for record in records if not record.available
        ][: min(15, self._max_results)]
        active = [
            _record_summary(record)
            for record in records
            if record.available and _normalize(record.state.state) in _ACTIVE_STATES
        ][: min(15, self._max_results)]

        result: dict[str, Any] = {
            "result": "summary",
            "location": location,
            "count": total,
            "available": available,
            "unavailable": total - available,
            "states_by_domain": states_by_domain,
            "integrations": dict(
                Counter(
                    record.integration for record in records if record.integration
                ).most_common(20)
            ),
            "manufacturers": dict(
                Counter(
                    record.manufacturer for record in records if record.manufacturer
                ).most_common(20)
            ),
            "measurements": measurements,
            "unavailable_entities": unavailable,
            "active_entities": active,
        }
        if bool(args.get("include_entities", True)):
            limit = min(int(args.get("limit", 30)), self._max_results)
            result["entities"] = [_record_details(record) for record in records[:limit]]
            result["truncated"] = total > limit
        return result


def append_device_query_tools(api_instance: llm.APIInstance, max_results: int) -> None:
    """Add FreeLLM's read-only tools to one request-local API instance."""
    existing = {tool.name for tool in api_instance.tools}
    tools: list[llm.Tool] = [
        FreeLLMGetEntityStateTool(max_results),
        FreeLLMSearchEntitiesTool(max_results),
        FreeLLMSummarizeLocationTool(max_results),
    ]
    api_instance.tools.extend(tool for tool in tools if tool.name not in existing)


def is_device_query_tool(tool_name: str) -> bool:
    """Return whether a tool is one of FreeLLM's read-only query tools."""
    return tool_name in DEVICE_QUERY_TOOL_NAMES


def _get_exposed_records(hass: HomeAssistant) -> list[EntityRecord]:
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)
    floor_registry = fr.async_get(hass)
    records: list[EntityRecord] = []

    for state in hass.states.async_all():
        if not exposed_entities.async_should_expose(
            hass, "conversation", state.entity_id
        ):
            continue

        entity_entry = entity_registry.async_get(state.entity_id)
        device = None
        area_id = getattr(entity_entry, "area_id", None) if entity_entry else None
        device_id = getattr(entity_entry, "device_id", None) if entity_entry else None
        if device_id:
            device = device_registry.async_get(device_id)
        if not area_id and device:
            area_id = device.area_id

        area = area_registry.async_get_area(area_id) if area_id else None
        floor_id = area.floor_id if area else None
        floor = floor_registry.async_get_floor(floor_id) if floor_id else None

        friendly_name = state.attributes.get(ATTR_FRIENDLY_NAME)
        registry_name = getattr(entity_entry, "name", None) if entity_entry else None
        original_name = (
            getattr(entity_entry, "original_name", None) if entity_entry else None
        )
        name = str(friendly_name or registry_name or original_name or state.entity_id)
        aliases = tuple(
            str(alias)
            for alias in (getattr(entity_entry, "aliases", None) or ())
            if alias
        )
        device_name = None
        if device:
            device_name = device.name_by_user or device.name

        domain = state.entity_id.split(".", 1)[0]
        device_class_raw = state.attributes.get(ATTR_DEVICE_CLASS)
        unit_raw = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        records.append(
            EntityRecord(
                state=state,
                entity_id=state.entity_id,
                domain=domain,
                name=name,
                aliases=aliases,
                device_name=str(device_name) if device_name else None,
                integration=(
                    str(getattr(entity_entry, "platform", "")) or None
                    if entity_entry
                    else None
                ),
                manufacturer=(
                    str(device.manufacturer) if device and device.manufacturer else None
                ),
                model=str(device.model) if device and device.model else None,
                area_id=area.id if area else None,
                area_name=area.name if area else None,
                floor_id=(
                    str(getattr(floor, "floor_id", floor_id)) if floor else None
                ),
                floor_name=floor.name if floor else None,
                device_class=(
                    str(device_class_raw) if device_class_raw is not None else None
                ),
                unit=str(unit_raw) if unit_raw is not None else None,
                numeric_value=_parse_numeric(state.state),
            )
        )
    return records


def _filter_location(
    hass: HomeAssistant,
    records: list[EntityRecord],
    *,
    area: Any = None,
    floor: Any = None,
) -> list[EntityRecord]:
    if area:
        resolved = _resolve_location(hass, str(area), "area")
        records = [record for record in records if record.area_id == resolved["id"]]
    if floor:
        resolved = _resolve_location(hass, str(floor), "floor")
        records = [record for record in records if record.floor_id == resolved["id"]]
    return records


def _resolve_location(
    hass: HomeAssistant, query: str, location_type: str
) -> dict[str, str]:
    candidates: list[dict[str, Any]] = []
    if location_type in ("auto", "area"):
        for area in ar.async_get(hass).async_list_areas():
            names = (area.name, *(area.aliases or ()))
            candidates.append(
                {
                    "type": "area",
                    "id": area.id,
                    "name": area.name,
                    "score": _best_text_score(query, names),
                }
            )
    if location_type in ("auto", "floor"):
        for floor in fr.async_get(hass).async_list_floors():
            names = (floor.name, *(floor.aliases or ()))
            candidates.append(
                {
                    "type": "floor",
                    "id": str(floor.floor_id),
                    "name": floor.name,
                    "score": _best_text_score(query, names),
                }
            )

    candidates.sort(key=lambda item: (-item["score"], item["name"].casefold()))
    if not candidates or candidates[0]["score"] < 56:
        suggestions = ", ".join(item["name"] for item in candidates[:5])
        raise HomeAssistantError(
            f'Location "{query}" was not found. Suggestions: {suggestions or "none"}.'
        )
    best = candidates[0]
    equally_good = [
        item for item in candidates if item["score"] >= best["score"] - 3
    ]
    if len(equally_good) > 1 and best["score"] < 100:
        names = ", ".join(
            f'{item["name"]} ({item["type"]})' for item in equally_good[:5]
        )
        raise HomeAssistantError(
            f'Location "{query}" is ambiguous. Matching locations: {names}.'
        )
    return {"type": best["type"], "id": best["id"], "name": best["name"]}


def _rank_records(
    records: list[EntityRecord], query: str
) -> list[tuple[float, EntityRecord]]:
    ranked = [(_best_text_score(query, record.searchable_names), record) for record in records]
    ranked.sort(
        key=lambda item: (
            -item[0],
            _normalize(item[1].area_name),
            _normalize(item[1].name),
        )
    )
    return ranked


def _best_text_score(query: str, candidates: tuple[str, ...] | list[str]) -> float:
    normalized_query = _normalize(query)
    if not normalized_query:
        return 0
    best = 0.0
    query_tokens = set(normalized_query.split())
    for candidate in candidates:
        normalized_candidate = _normalize(candidate)
        if not normalized_candidate:
            continue
        if normalized_candidate == normalized_query:
            score = 100.0
        elif normalized_candidate.startswith(normalized_query):
            score = 90.0
        elif normalized_query in normalized_candidate:
            score = 82.0
        elif query_tokens and query_tokens.issubset(set(normalized_candidate.split())):
            score = 76.0
        else:
            score = SequenceMatcher(
                None, normalized_query, normalized_candidate
            ).ratio() * 70
        best = max(best, score)
    return best


def _record_summary(record: EntityRecord) -> dict[str, Any]:
    result: dict[str, Any] = {
        "entity_id": record.entity_id,
        "name": record.name,
        "state": record.state.state,
        "available": record.available,
    }
    if record.area_name:
        result["area"] = record.area_name
    if record.floor_name:
        result["floor"] = record.floor_name
    if record.unit:
        result["unit"] = record.unit
    return result


def _record_details(record: EntityRecord) -> dict[str, Any]:
    result = _record_summary(record)
    result.update(
        {
            "domain": record.domain,
            "device_class": record.device_class,
            "last_changed": record.state.last_changed.isoformat(),
            "last_updated": record.state.last_updated.isoformat(),
        }
    )
    if record.device_name:
        result["device"] = record.device_name
    if record.integration:
        result["integration"] = record.integration
    if record.manufacturer:
        result["manufacturer"] = record.manufacturer
    if record.model:
        result["model"] = record.model
    if record.numeric_value is not None:
        result["numeric_value"] = record.numeric_value
    if actions := _CONTROL_ACTIONS_BY_DOMAIN.get(record.domain):
        result["control_actions"] = list(actions)
    result["active"] = bool(
        record.available and _normalize_state(record.state.state) in _ACTIVE_STATES
    )
    brightness = record.state.attributes.get("brightness")
    if isinstance(brightness, (int, float)):
        result["brightness_percent"] = round(float(brightness) / 255 * 100)
    attributes = _selected_attributes(record.state)
    if attributes:
        result["attributes"] = attributes
    return result


def _selected_attributes(state: State) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in _COMMON_ATTRIBUTE_KEYS:
        if key not in state.attributes or key == ATTR_FRIENDLY_NAME:
            continue
        safe = _safe_json_value(state.attributes[key])
        if safe is not None:
            result[key] = safe
    return result


def _safe_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:500]
    if isinstance(value, (list, tuple)):
        result = []
        for item in value[:20]:
            safe = _safe_json_value(item)
            if safe is not None:
                result.append(safe)
        return result
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in list(value.items())[:20]:
            safe = _safe_json_value(item)
            if safe is not None:
                result[str(key)[:100]] = safe
        return result
    return str(value)[:500]


def _measurement_summary(records: list[EntityRecord]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[tuple[float, EntityRecord]]] = defaultdict(list)
    for record in records:
        if record.numeric_value is None or not record.available:
            continue
        metric = record.device_class or record.domain
        unit = record.unit or ""
        groups[(metric, unit)].append((record.numeric_value, record))

    result: list[dict[str, Any]] = []
    for (metric, unit), values in sorted(groups.items()):
        numbers = [value for value, _record in values]
        minimum_value, minimum_record = min(values, key=lambda item: item[0])
        maximum_value, maximum_record = max(values, key=lambda item: item[0])
        item: dict[str, Any] = {
            "metric": metric,
            "count": len(numbers),
            "minimum": round(minimum_value, 3),
            "minimum_entity": minimum_record.name,
            "maximum": round(maximum_value, 3),
            "maximum_entity": maximum_record.name,
            "average": round(sum(numbers) / len(numbers), 3),
        }
        if unit:
            item["unit"] = unit
        result.append(item)
        if len(result) >= 20:
            break
    return result


def _search_summary(records: list[EntityRecord]) -> dict[str, Any]:
    return {
        "available": sum(record.available for record in records),
        "unavailable": sum(not record.available for record in records),
        "domains": dict(Counter(record.domain for record in records)),
        "integrations": dict(
            Counter(
                record.integration for record in records if record.integration
            ).most_common(20)
        ),
        "states": dict(Counter(record.state.state for record in records)),
        "measurements": _measurement_summary(records),
    }


def _sort_key(record: EntityRecord, sort_by: str) -> Any:
    if sort_by == "state":
        return (_normalize(record.state.state), _normalize(record.name))
    if sort_by == "last_changed":
        return record.state.last_changed
    if sort_by == "numeric_value":
        return (
            record.numeric_value is None,
            record.numeric_value if record.numeric_value is not None else 0,
            _normalize(record.name),
        )
    return (_normalize(record.area_name), _normalize(record.name))


def _parse_numeric(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).casefold().replace("_", " ").replace("-", " ")
    return " ".join(re.findall(r"[\w]+", text, flags=re.UNICODE))


def _normalize_state(value: Any) -> str:
    normalized = _normalize(value).replace(" ", "_")
    aliases = {
        "an": "on",
        "aus": "off",
        "offen": "open",
        "geöffnet": "open",
        "geschlossen": "closed",
        "nicht_erreichbar": "unavailable",
        "nicht_verfügbar": "unavailable",
        "unbekannt": "unknown",
        "verriegelt": "locked",
        "entriegelt": "unlocked",
        "spielt": "playing",
        "pausiert": "paused",
        "zuhause": "home",
        "abwesend": "not_home",
    }
    return aliases.get(normalized, normalized)


def _normalize_device_class(value: Any) -> str:
    normalized = _normalize(value).replace(" ", "_")
    aliases = {
        "batterie": "battery",
        "temperatur": "temperature",
        "luftfeuchtigkeit": "humidity",
        "feuchtigkeit": "humidity",
        "leistung": "power",
        "energie": "energy",
        "spannung": "voltage",
        "strom": "current",
        "signalstärke": "signal_strength",
        "signalstaerke": "signal_strength",
        "bewegung": "motion",
        "belegung": "occupancy",
        "anwesenheit": "presence",
        "fenster": "window",
        "tür": "door",
        "tuer": "door",
        "rauch": "smoke",
        "gas": "gas",
        "problem": "problem",
    }
    return aliases.get(normalized, normalized)


def _normalize_unit(value: Any) -> str:
    if value is None:
        return ""
    normalized = str(value).strip().casefold().replace("°", "deg")
    aliases = {
        "c": "degc",
        "celsius": "degc",
        "grad celsius": "degc",
        "f": "degf",
        "fahrenheit": "degf",
        "grad fahrenheit": "degf",
        "prozent": "%",
        "percent": "%",
    }
    return aliases.get(normalized, normalized)


def _normalize_domain(value: Any) -> str:
    normalized = _normalize(value).replace(" ", "_")
    aliases = {
        "lights": "light",
        "lichter": "light",
        "lampen": "light",
        "switches": "switch",
        "schalter": "switch",
        "sensors": "sensor",
        "sensoren": "sensor",
        "covers": "cover",
        "rollladen": "cover",
        "jalousien": "cover",
        "climate": "climate",
        "heizung": "climate",
        "media_players": "media_player",
        "medienplayer": "media_player",
    }
    return aliases.get(normalized, normalized)
