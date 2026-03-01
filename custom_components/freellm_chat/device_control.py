"""Device control handler for freellm_chat."""
from __future__ import annotations

import asyncio
import logging
import json
import re
import unicodedata
from typing import Any
from datetime import datetime, timedelta
from collections import defaultdict

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, entity_registry as er, device_registry as dr

from .const import CONTROL_DOMAINS, SENSOR_DOMAINS, COLOR_PRESETS
from .sensor_analyzer import SensorAnalyzer
from .color_manager import ColorManager

_LOGGER = logging.getLogger(__name__)


class DeviceController:
    """Handler for device control operations."""

    # Class-level cache
    _entity_cache: dict | None = None
    _cache_time: datetime | None = None
    _cache_duration = timedelta(seconds=5)

    def __init__(
        self, 
        hass: HomeAssistant, 
        selected_entities: list[str] | None, 
        selected_areas: list[str] | None,
        enable_sensors: bool = True,
        custom_colors: dict[str, list[int]] | None = None
    ) -> None:
        """Initialize the device controller."""
        self.hass = hass
        self.selected_entities = selected_entities or []
        self.selected_areas = selected_areas or []
        self.enable_sensors = enable_sensors
        self._entity_registry = er.async_get(hass)
        self._area_registry = ar.async_get(hass)
        self._device_registry = dr.async_get(hass)
        self.color_manager = ColorManager(custom_colors)

    # ==================== TEXT NORMALISIERUNG ====================

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text by removing umlauts and special characters."""
        if not text:
            return ""
        
        # Umlaut-Mapping
        umlaut_map = {
            'ä': 'a', 'Ä': 'A',
            'ö': 'o', 'Ö': 'O',
            'ü': 'u', 'Ü': 'U',
            'ß': 'ss',
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
            'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o',
            'ú': 'u', 'ù': 'u', 'û': 'u',
            'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
            'ñ': 'n',
            'ç': 'c',
        }
        
        result = text.lower()
        
        # Ersetze Umlaute
        for umlaut, replacement in umlaut_map.items():
            result = result.replace(umlaut, replacement)
            result = result.replace(umlaut.upper(), replacement.upper())
        
        # Entferne verbleibende Akzente via Unicode-Normalisierung
        result = unicodedata.normalize('NFKD', result)
        result = ''.join(c for c in result if not unicodedata.combining(c))
        
        return result

    @staticmethod
    def normalize_entity_id(text: str) -> str:
        """Normalize text to match entity_id format."""
        normalized = DeviceController.normalize_text(text)
        
        # Ersetze Trennzeichen durch Unterstriche
        normalized = normalized.replace('-', '_')
        normalized = normalized.replace(' ', '_')
        normalized = normalized.replace('.', '_')
        normalized = normalized.replace('/', '_')
        
        # Entferne nicht-alphanumerische Zeichen (außer Unterstrich)
        normalized = re.sub(r'[^a-z0-9_]', '', normalized)
        
        # Entferne doppelte Unterstriche
        while '__' in normalized:
            normalized = normalized.replace('__', '_')
        
        # Entferne führende/trailing Unterstriche
        normalized = normalized.strip('_')
        
        return normalized

    # ==================== ENTITY SUCHE ====================

    def find_entity_by_name(self, search_term: str) -> str | None:
        """Find entity_id by searching name, allowing for umlaut variations."""
        controlled = self.get_controlled_entities(include_sensors=False)
        
        if not search_term:
            return None
        
        # Normalisiere Suchbegriff
        search_normalized = self.normalize_entity_id(search_term)
        search_lower = search_term.lower()
        
        _LOGGER.debug(f"Searching for entity: '{search_term}' (normalized: '{search_normalized}')")
        
        best_match = None
        best_score = 0
        
        for entity_id, info in controlled.items():
            # Extrahiere verschiedene Vergleichswerte
            eid_short = entity_id.split('.')[-1]  # z.B. "wled_tv_mobel"
            eid_normalized = self.normalize_entity_id(eid_short)
            
            name = info.get('name', '')
            name_lower = name.lower()
            name_normalized = self.normalize_entity_id(name)
            
            # Berechne Übereinstimmungs-Score
            score = 0
            
            # Exakte Übereinstimmung (höchste Priorität)
            if search_lower == eid_short or search_lower == name_lower:
                score = 100
            elif search_normalized == eid_normalized or search_normalized == name_normalized:
                score = 95
            
            # Suchbegriff ist Teil der entity_id
            elif search_normalized in eid_normalized:
                score = 80 + (len(search_normalized) / len(eid_normalized) * 10)
            elif search_lower in eid_short:
                score = 75
            
            # Suchbegriff ist Teil des Namens
            elif search_normalized in name_normalized:
                score = 70 + (len(search_normalized) / len(name_normalized) * 10)
            elif search_lower in name_lower:
                score = 65
            
            # Entity-ID/Name ist Teil des Suchbegriffs
            elif eid_normalized in search_normalized:
                score = 60
            elif name_normalized in search_normalized:
                score = 55
            
            # Wort-basierte Übereinstimmung
            else:
                search_words = set(search_normalized.replace('_', ' ').split())
                eid_words = set(eid_normalized.replace('_', ' ').split())
                name_words = set(name_normalized.replace('_', ' ').split())
                
                common_eid = search_words & eid_words
                common_name = search_words & name_words
                
                if common_eid:
                    score = 30 + len(common_eid) * 10
                if common_name:
                    score = max(score, 25 + len(common_name) * 10)
            
            if score > best_score:
                best_score = score
                best_match = entity_id
                _LOGGER.debug(f"  Candidate: {entity_id} ({info['name']}) - Score: {score}")
        
        if best_match and best_score >= 30:
            _LOGGER.info(f"Found entity '{best_match}' for search '{search_term}' (score: {best_score})")
            return best_match
        
        _LOGGER.debug(f"No entity found for '{search_term}'")
        return None

    # ==================== ENTITY VERWALTUNG ====================

    def get_controlled_entities(self, include_sensors: bool = True) -> dict[str, dict]:
        """Get all entities that can be controlled based on selection."""
        now = datetime.now()
        cache_key = f"{hash(tuple(self.selected_entities))}_{hash(tuple(self.selected_areas))}_{include_sensors}"
        
        if (DeviceController._entity_cache is not None and 
            DeviceController._cache_time is not None and
            now - DeviceController._cache_time < DeviceController._cache_duration):
            cached = DeviceController._entity_cache.get(cache_key)
            if cached:
                return cached

        controlled_entities = {}

        if not self.selected_entities and not self.selected_areas:
            return {}

        allowed_domains = CONTROL_DOMAINS + SENSOR_DOMAINS if (include_sensors and self.enable_sensors) else CONTROL_DOMAINS

        for state in self.hass.states.async_all():
            entity_id = state.entity_id
            
            if state.domain not in allowed_domains:
                continue

            if entity_id in self.selected_entities:
                controlled_entities[entity_id] = self._build_entity_info(state)
                continue

            if self.selected_areas:
                entity_entry = self._entity_registry.async_get(entity_id)
                
                if entity_entry:
                    area_id = entity_entry.area_id
                    
                    if not area_id and entity_entry.device_id:
                        device = self._device_registry.async_get(entity_entry.device_id)
                        if device:
                            area_id = device.area_id
                    
                    if area_id and area_id in self.selected_areas:
                        controlled_entities[entity_id] = self._build_entity_info(state)

        if DeviceController._entity_cache is None:
            DeviceController._entity_cache = {}
        DeviceController._entity_cache[cache_key] = controlled_entities
        DeviceController._cache_time = now

        return controlled_entities

    def _build_entity_info(self, state) -> dict:
        """Build entity information dictionary."""
        entity_entry = self._entity_registry.async_get(state.entity_id)
        area_name = None
        
        if entity_entry:
            area_id = entity_entry.area_id
            
            if not area_id and entity_entry.device_id:
                device = self._device_registry.async_get(entity_entry.device_id)
                if device:
                    area_id = device.area_id
            
            if area_id:
                area = self._area_registry.async_get_area(area_id)
                area_name = area.name if area else None

        friendly_name = state.attributes.get('friendly_name', state.entity_id)
        
        return {
            'name': friendly_name,
            'state': state.state,
            'domain': state.domain,
            'area': area_name,
            'attributes': self._filter_attributes(state.domain, dict(state.attributes)),
            'unit': state.attributes.get('unit_of_measurement', '')
        }

    def _filter_attributes(self, domain: str, attributes: dict) -> dict:
        """Filter important attributes."""
        important = ['friendly_name']
        
        if domain == 'light':
            important.extend(['brightness', 'rgb_color', 'color_temp_kelvin', 'supported_color_modes'])
        elif domain == 'climate':
            important.extend(['temperature', 'current_temperature', 'hvac_mode', 'hvac_modes'])
        elif domain == 'cover':
            important.extend(['current_position'])
        elif domain == 'media_player':
            important.extend(['volume_level', 'media_title', 'source'])
        elif domain in ['sensor', 'binary_sensor']:
            important.extend(['unit_of_measurement', 'device_class', 'state_class'])
        
        return {k: v for k, v in attributes.items() if k in important}

    def generate_context(self) -> str:
        """Generate context for LLM."""
        entities = self.get_controlled_entities(include_sensors=True)
        
        if not entities:
            return "\n\n⚠️ KEINE GERÄTE VERFÜGBAR!"

        context = "\n\n=== VERFÜGBARE GERÄTE ===\n"
        
        by_area: dict[str, dict[str, list]] = {}
        
        for entity_id, info in entities.items():
            area = info['area'] or 'Ohne Bereich'
            domain = info['domain']
            
            if area not in by_area:
                by_area[area] = {'control': [], 'sensor': []}
            
            category = 'sensor' if domain in SENSOR_DOMAINS else 'control'
            by_area[area][category].append((entity_id, info))

        for area in sorted(by_area.keys()):
            categories = by_area[area]
            context += f"\n📍 {area}:\n"
            
            if categories['control']:
                for entity_id, info in sorted(categories['control'], key=lambda x: x[1]['name']):
                    context += f"  • {info['name']} → {entity_id} [{info['state']}]\n"
            
            if categories['sensor']:
                for entity_id, info in sorted(categories['sensor'], key=lambda x: x[1]['name'])[:5]:
                    unit = info.get('unit', '')
                    context += f"  📊 {info['name']}: {info['state']}{unit}\n"

        total_control = sum(len(c['control']) for c in by_area.values())
        total_sensor = sum(len(c['sensor']) for c in by_area.values())
        context += f"\n=== {total_control} Geräte + {total_sensor} Sensoren ===\n"
        
        return context

    # ==================== COMMAND EXECUTION ====================

    async def execute_command(self, response: str) -> str | None:
        """Parse and execute commands from LLM response."""
        _LOGGER.debug(f"Parsing response: {response[:300]}...")
        
        try:
            command = self._parse_llm_response(response)
            
            if command is None:
                _LOGGER.warning(f"Could not parse command from: {response[:200]}")
                return None

            _LOGGER.debug(f"Parsed command: {command}")

            action = command.get("action", "").lower()
            
            if action in ["cont", "ctrl", "control", "c"]:
                action = "control"
            elif action in ["query", "q", "ask", "get", "status", "info"]:
                action = "query"
            elif action in ["control_multiple", "multi", "multiple", "batch"]:
                action = "control_multiple"

            if action == "control":
                return await self._execute_single_command(command)
            elif action == "control_multiple":
                return await self._execute_multiple_commands_parallel(command.get("commands", []))
            elif action == "query":
                return await self._handle_query(command)
            else:
                _LOGGER.warning(f"Unknown action: {action}")
                return None

        except Exception as e:
            _LOGGER.error(f"Error executing command: {e}", exc_info=True)
            return f"❌ Fehler: {str(e)}"

    # ==================== JSON PARSING ====================

    def _parse_llm_response(self, response: str) -> dict | None:
        """Parse LLM response with flexible JSON handling."""
        _LOGGER.debug(f"=== PARSING LLM RESPONSE ===")
        _LOGGER.debug(f"Raw response ({len(response)} chars): {response[:500]}...")
        
        clean = response.strip()
        
        # Entferne Markdown Code-Blöcke
        clean = re.sub(r'^```(?:json)?\s*', '', clean)
        clean = re.sub(r'\s*```$', '', clean)
        clean = clean.strip()
        
        # Entferne <think>...</think> Blöcke (DeepSeek R1 etc.)
        clean = re.sub(r'<think>.*?</think>', '', clean, flags=re.DOTALL)
        clean = clean.strip()
        
        _LOGGER.debug(f"Cleaned response: {clean[:300]}...")
        
        # Methode 1: Versuche gesamte Response als JSON
        try:
            parsed = json.loads(clean)
            if isinstance(parsed, dict):
                _LOGGER.info(f"✓ Direct JSON parse successful: {parsed}")
                return parsed
        except json.JSONDecodeError as e:
            _LOGGER.debug(f"Direct JSON parse failed: {e}")
        
        # Methode 2: Finde JSON-Objekte im Text
        json_objects = self._extract_json_objects(clean)
        _LOGGER.debug(f"Found {len(json_objects)} JSON objects in response")
        
        for i, obj in enumerate(json_objects):
            _LOGGER.debug(f"Trying JSON object {i+1}: {obj[:100]}...")
            try:
                parsed = json.loads(obj)
                if isinstance(parsed, dict) and ("action" in parsed or "entity_id" in parsed):
                    _LOGGER.info(f"✓ Extracted JSON from object {i+1}: {parsed}")
                    return parsed
            except json.JSONDecodeError as e:
                _LOGGER.debug(f"JSON object {i+1} parse failed: {e}")
                continue
        
        # Methode 3: Repariere kaputtes JSON / extrahiere aus Text
        _LOGGER.debug("Attempting JSON repair...")
        repaired = self._repair_json(clean)
        if repaired:
            _LOGGER.info(f"✓ Repaired JSON: {repaired}")
            return repaired
        
        _LOGGER.warning(f"✗ Could not parse any JSON from response")
        return None

    def _extract_json_objects(self, text: str) -> list[str]:
        """Extract JSON objects from text, handling nested braces."""
        objects = []
        i = 0
        while i < len(text):
            if text[i] == '{':
                depth = 0
                start = i
                in_string = False
                escape_next = False
                
                while i < len(text):
                    char = text[i]
                    
                    if escape_next:
                        escape_next = False
                    elif char == '\\':
                        escape_next = True
                    elif char == '"' and not escape_next:
                        in_string = not in_string
                    elif not in_string:
                        if char == '{':
                            depth += 1
                        elif char == '}':
                            depth -= 1
                            if depth == 0:
                                obj = text[start:i+1]
                                objects.append(obj)
                                break
                    i += 1
            i += 1
        return objects

    def _repair_json(self, text: str) -> dict | None:
        """Try to repair broken JSON or extract command from text."""
        _LOGGER.debug(f"=== REPAIRING JSON ===")
        _LOGGER.debug(f"Input text: {text[:300]}...")
        
        try:
            # ===== FINDE ACTION =====
            action_match = re.search(r'"action"\s*:\s*"(\w+)"', text)
            action = action_match.group(1) if action_match else None
            _LOGGER.debug(f"Found action: {action}")
            
            if action in ["cont", "ctrl"]:
                action = "control"
            
            # ===== FINDE ENTITY_ID =====
            entity_id = None
            
            # Format: "entity_id":"light.xxx"
            entity_match = re.search(r'"entity_id"\s*:\s*"([^"]+)"', text)
            if entity_match:
                entity_id = entity_match.group(1)
                _LOGGER.debug(f"Found entity_id in JSON: {entity_id}")
            
            # Alternative: Finde entity_id Pattern im Text
            if not entity_id:
                entity_match = re.search(
                    r'(light|switch|climate|cover|fan|media_player|sensor|binary_sensor)\.[a-z0-9_äöüß]+', 
                    text.lower()
                )
                if entity_match:
                    entity_id = entity_match.group(0)
                    _LOGGER.debug(f"Found entity_id pattern: {entity_id}")
            
            # Normalisiere und suche Entity
            if entity_id:
                controlled = self.get_controlled_entities(include_sensors=False)
                if entity_id not in controlled:
                    _LOGGER.debug(f"Entity '{entity_id}' not in controlled list, searching...")
                    found = self.find_entity_by_name(entity_id)
                    if found:
                        _LOGGER.info(f"Mapped '{entity_id}' -> '{found}'")
                        entity_id = found
            
            # ===== FINDE FARBE =====
            rgb_color = None
            
            # Format: "rgb_color":[0,255,0] oder "color":[0,255,0]
            color_match = re.search(
                r'"(?:color|rgb_color|rgb)"\s*:\s*\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]', 
                text
            )
            if color_match:
                rgb_color = [
                    int(color_match.group(1)), 
                    int(color_match.group(2)), 
                    int(color_match.group(3))
                ]
                _LOGGER.debug(f"Found rgb_color in JSON: {rgb_color}")
            
            # Suche nach Farbnamen im Text (inkl. Umlaute)
            if not rgb_color:
                text_lower = text.lower()
                text_normalized = self.normalize_text(text)
                
                _LOGGER.debug(f"Searching for color names in: {text_normalized[:100]}...")
                
                for color_name, rgb in COLOR_PRESETS.items():
                    color_normalized = self.normalize_text(color_name)
                    
                    # Prüfe beide Varianten
                    if color_name in text_lower or color_normalized in text_normalized:
                        rgb_color = rgb
                        _LOGGER.info(f"Found color name '{color_name}' -> {rgb}")
                        break
            
            # ===== FINDE HELLIGKEIT =====
            brightness = None
            
            # Format: "brightness":100 oder "brightness_pct":50
            brightness_match = re.search(r'"brightness(?:_pct)?"\s*:\s*(\d+)', text)
            if brightness_match:
                brightness = int(brightness_match.group(1))
                _LOGGER.debug(f"Found brightness in JSON: {brightness}")
            
            # Alternative: Finde Prozent im Text
            if brightness is None:
                pct_match = re.search(r'(\d+)\s*(%|prozent)', text.lower())
                if pct_match:
                    brightness = int(pct_match.group(1))
                    _LOGGER.debug(f"Found brightness in text: {brightness}%")
            
            # ===== FINDE SERVICE =====
            service = "turn_on"
            
            # Format: "service":"turn_off"
            state_match = re.search(r'"(?:state|service)"\s*:\s*"(\w+)"', text)
            if state_match:
                state_val = state_match.group(1).lower()
                if state_val in ["off", "aus", "turn_off"]:
                    service = "turn_off"
                elif state_val in ["toggle", "umschalten"]:
                    service = "toggle"
                _LOGGER.debug(f"Found service in JSON: {service}")
            
            # Alternative: Suche nach Schlüsselwörtern
            text_lower = text.lower()
            if any(word in text_lower for word in ["ausschalten", " aus ", "turn off", "ausmachen", "aus!"]):
                service = "turn_off"
                _LOGGER.debug(f"Found 'off' keyword, service: turn_off")
            
            # ===== FÜR QUERY =====
            if action == "query":
                type_match = re.search(r'"(?:type|sub_type|query_type)"\s*:\s*"([^"]+)"', text)
                query_type = type_match.group(1) if type_match else "temperatures"
                
                area_match = re.search(r'"(?:area|room|raum|bereich)"\s*:\s*"([^"]+)"', text)
                area_filter = area_match.group(1) if area_match else None
                
                result = {
                    "action": "query",
                    "query_type": "status",
                    "sub_type": query_type
                }
                if area_filter:
                    result["area"] = area_filter
                
                _LOGGER.info(f"Built query command: {result}")
                return result
            
            # ===== FÜR CONTROL =====
            if entity_id:
                domain = entity_id.split('.')[0] if '.' in entity_id else "light"
                
                result = {
                    "action": "control",
                    "domain": domain,
                    "entity_id": entity_id,
                    "service": service,
                    "data": {}
                }
                
                if rgb_color:
                    result["data"]["rgb_color"] = rgb_color
                
                if brightness is not None:
                    if brightness > 100:
                        result["data"]["brightness_pct"] = int(brightness / 255 * 100)
                    else:
                        result["data"]["brightness_pct"] = brightness
                
                _LOGGER.info(f"Built control command: {result}")
                return result
            
            _LOGGER.debug("Could not build command - no entity_id found")
            return None
            
        except Exception as e:
            _LOGGER.error(f"JSON repair failed with exception: {e}", exc_info=True)
            return None

    # ==================== QUERY HANDLING ====================

    async def _handle_query(self, command: dict) -> str:
        """Handle query commands with flexible parsing."""
        query_type = command.get("query_type", "")
        sub_type = command.get("sub_type", "")
        
        # Alternatives Format: {"action":"query","data":{"type":"..."}}
        if not sub_type and "data" in command:
            data = command.get("data", {})
            if isinstance(data, dict):
                sub_type = data.get("type", "") or data.get("sub_type", "")
        
        # Weiteres alternatives Format
        if not sub_type:
            sub_type = command.get("type", "")
        
        # Fallback: query_type als sub_type verwenden
        if not sub_type and query_type and query_type != "status":
            sub_type = query_type
        
        # Area/Room Filter extrahieren
        area_filter = (
            command.get("area") or 
            command.get("room") or 
            command.get("raum") or 
            command.get("bereich") or
            None
        )
        
        # Auch aus data extrahieren
        if not area_filter and "data" in command:
            data = command.get("data", {})
            if isinstance(data, dict):
                area_filter = (
                    data.get("area") or 
                    data.get("room") or 
                    data.get("raum") or
                    None
                )
        
        # Area aus sub_type extrahieren (z.B. "temperature_wohnzimmer")
        if not area_filter and sub_type:
            area_filter = self._extract_area_from_query(sub_type)
            if area_filter:
                sub_type = self._clean_sub_type(sub_type, area_filter)
        
        _LOGGER.debug(f"Query - query_type: '{query_type}', sub_type: '{sub_type}', area_filter: '{area_filter}'")
        
        # Wenn query_type == "sensor", dann entity_ids abfragen
        if query_type == "sensor":
            return await self._execute_sensor_query(command)
        
        # Status-Abfragen
        effective_type = sub_type or query_type
        if effective_type:
            return await self._execute_status_query(effective_type, area_filter)
        
        # Fallback: Alle Sensoren anzeigen
        return await self._execute_status_query("all_sensors", area_filter)

    def _extract_area_from_query(self, sub_type: str) -> str | None:
        """Extract area name from sub_type string."""
        controlled = self.get_controlled_entities(include_sensors=True)
        
        # Sammle alle verfügbaren Bereichsnamen
        available_areas = {}
        for info in controlled.values():
            if info['area']:
                area_lower = info['area'].lower()
                area_normalized = self.normalize_text(info['area'])
                available_areas[area_lower] = info['area']
                available_areas[area_normalized] = info['area']
        
        if not available_areas:
            return None
        
        sub_type_lower = sub_type.lower()
        sub_type_normalized = self.normalize_text(sub_type)
        
        # Prüfe ob ein Bereichsname im sub_type enthalten ist
        for area_key, area_original in sorted(available_areas.items(), key=lambda x: len(x[0]), reverse=True):
            if area_key in sub_type_lower or area_key in sub_type_normalized:
                return area_original
        
        return None

    def _clean_sub_type(self, sub_type: str, area_name: str) -> str:
        """Remove area name from sub_type and clean it up."""
        # Entferne den Bereichsnamen (beide Varianten)
        cleaned = sub_type.lower()
        cleaned = cleaned.replace(area_name.lower(), '')
        cleaned = cleaned.replace(self.normalize_text(area_name), '')
        
        # Entferne Trennzeichen
        cleaned = cleaned.strip('_ -/')
        cleaned = re.sub(r'[_\-/]+', '', cleaned)
        cleaned = cleaned.strip()
        
        # Wenn nichts übrig bleibt, verwende "temperatures" als Standard
        if not cleaned:
            cleaned = "temperatures"
        
        return cleaned

    async def _execute_sensor_query(self, command: dict) -> str:
        """Execute a sensor query."""
        entity_ids = command.get("entity_ids", [])
        
        # Auch einzelne entity_id unterstützen
        if not entity_ids:
            single_id = command.get("entity_id")
            if single_id:
                entity_ids = [single_id]
        
        if not entity_ids:
            return "❌ Keine Sensoren angegeben"
        
        controlled = self.get_controlled_entities(include_sensors=True)
        results = []
        
        for entity_id in entity_ids:
            # Versuche Entity zu finden (mit Normalisierung)
            if entity_id not in controlled:
                found = self.find_entity_by_name(entity_id)
                if found:
                    entity_id = found
            
            if entity_id not in controlled:
                continue
            
            state = self.hass.states.get(entity_id)
            if state:
                info = controlled[entity_id]
                unit = info.get('unit', '')
                area = f" ({info['area']})" if info['area'] else ""
                results.append(f"{info['name']}{area}: {state.state}{unit}")
        
        if not results:
            return "❌ Keine Sensordaten gefunden"
        
        if len(results) == 1:
            return f"📊 {results[0]}"
        return "📊 Sensorwerte:\n" + "\n".join(f"  • {r}" for r in results)

    async def _execute_status_query(self, sub_type: str, area_filter: str | None = None) -> str:
        """Execute status queries with optional area filter."""
        _LOGGER.debug(f"Executing status query: '{sub_type}', area_filter: '{area_filter}'")
        
        controlled = self.get_controlled_entities(include_sensors=True)
        
        # Filtere nach Bereich wenn angegeben
        if area_filter:
            filtered = {}
            area_filter_lower = area_filter.lower()
            area_filter_normalized = self.normalize_text(area_filter)
            
            for entity_id, info in controlled.items():
                entity_area = info.get('area') or ''
                entity_area_lower = entity_area.lower()
                entity_area_normalized = self.normalize_text(entity_area)
                
                # Flexible Bereichs-Übereinstimmung
                if (area_filter_lower in entity_area_lower or 
                    entity_area_lower in area_filter_lower or
                    area_filter_normalized in entity_area_normalized or
                    entity_area_normalized in area_filter_normalized or
                    area_filter_lower == entity_area_lower):
                    filtered[entity_id] = info
            
            if filtered:
                controlled = filtered
                _LOGGER.debug(f"Filtered to {len(controlled)} entities in area '{area_filter}'")
            else:
                _LOGGER.warning(f"No entities found for area '{area_filter}', using all")
        
        analyzer = SensorAnalyzer(self.hass, controlled)
        
        # Mapping mit vielen Alternativen
        query_map = {
            # Temperatur
            "temperatures": analyzer.analyze_temperatures,
            "temperature": analyzer.analyze_temperatures,
            "temp": analyzer.analyze_temperatures,
            "temperatur": analyzer.analyze_temperatures,
            "temperaturen": analyzer.analyze_temperatures,
            "wie_warm": analyzer.analyze_temperatures,
            "wiewarm": analyzer.analyze_temperatures,
            "wie_kalt": analyzer.analyze_temperatures,
            "grad": analyzer.analyze_temperatures,
            
            # Luftfeuchtigkeit
            "humidity": analyzer.analyze_humidity,
            "feuchtigkeit": analyzer.analyze_humidity,
            "luftfeuchtigkeit": analyzer.analyze_humidity,
            "luftfeuchte": analyzer.analyze_humidity,
            
            # Fenster/Türen
            "windows": analyzer.check_open_windows,
            "fenster": analyzer.check_open_windows,
            "doors": analyzer.check_open_windows,
            "türen": analyzer.check_open_windows,
            "tueren": analyzer.check_open_windows,
            "tür": analyzer.check_open_windows,
            "door": analyzer.check_open_windows,
            
            # Eingeschaltete Geräte
            "powered_on": analyzer.get_powered_on_devices,
            "on": analyzer.get_powered_on_devices,
            "eingeschaltet": analyzer.get_powered_on_devices,
            "aktiv": analyzer.get_powered_on_devices,
            "an": analyzer.get_powered_on_devices,
            "status": analyzer.get_powered_on_devices,
            "was_ist_an": analyzer.get_powered_on_devices,
            "wasistan": analyzer.get_powered_on_devices,
            
            # Batterie
            "battery": analyzer.check_battery_status,
            "batterie": analyzer.check_battery_status,
            "batteries": analyzer.check_battery_status,
            "batterien": analyzer.check_battery_status,
            
            # Offline
            "offline": analyzer.check_offline_devices,
            "unavailable": analyzer.check_offline_devices,
            "nicht_verfügbar": analyzer.check_offline_devices,
            "nichtverfügbar": analyzer.check_offline_devices,
            
            # Energie
            "energy": analyzer.analyze_energy,
            "energie": analyzer.analyze_energy,
            "strom": analyzer.analyze_energy,
            "verbrauch": analyzer.analyze_energy,
            "power": analyzer.analyze_energy,
            
            # Klima
            "climate_overview": analyzer.get_climate_overview,
            "climate": analyzer.get_climate_overview,
            "klima": analyzer.get_climate_overview,
            "heizung": analyzer.get_climate_overview,
            "heating": analyzer.get_climate_overview,
            
            # Bewegung
            "motion": analyzer.check_motion_sensors,
            "bewegung": analyzer.check_motion_sensors,
            "presence": analyzer.check_motion_sensors,
            "präsenz": analyzer.check_motion_sensors,
            "praesenz": analyzer.check_motion_sensors,
            
            # Luftqualität
            "air_quality": analyzer.analyze_air_quality,
            "luft": analyzer.analyze_air_quality,
            "luftqualität": analyzer.analyze_air_quality,
            "luftqualitaet": analyzer.analyze_air_quality,
            "co2": analyzer.analyze_air_quality,
            "airquality": analyzer.analyze_air_quality,
            
            # Alle Sensoren
            "all_sensors": analyzer.get_all_sensors_summary,
            "alle_sensoren": analyzer.get_all_sensors_summary,
            "sensoren": analyzer.get_all_sensors_summary,
            "all": analyzer.get_all_sensors_summary,
            "alle": analyzer.get_all_sensors_summary,
            "allsensors": analyzer.get_all_sensors_summary,
            
            # Zusammenfassung
            "device_summary": analyzer.get_device_summary,
            "summary": analyzer.get_device_summary,
            "zusammenfassung": analyzer.get_device_summary,
            "übersicht": analyzer.get_device_summary,
            "uebersicht": analyzer.get_device_summary,
            "overview": analyzer.get_device_summary,
            
            # Letzte Aktivität
            "last_activity": analyzer.get_last_activities,
            "activity": analyzer.get_last_activities,
            "aktivität": analyzer.get_last_activities,
            "aktivitaet": analyzer.get_last_activities,
            "letzte": analyzer.get_last_activities,
            "recent": analyzer.get_last_activities,
        }
        
        sub_type_lower = sub_type.lower().strip()
        sub_type_normalized = self.normalize_text(sub_type)
        
        # Entferne Leerzeichen und Unterstriche für flexibleres Matching
        sub_type_clean = sub_type_normalized.replace(' ', '').replace('_', '').replace('-', '')
        
        # Direkte Übereinstimmung
        if sub_type_lower in query_map:
            result = query_map[sub_type_lower]()
            if area_filter:
                result = f"📍 **Bereich: {area_filter}**\n\n" + result
            return result
        
        # Normalisierte Übereinstimmung
        if sub_type_normalized in query_map:
            result = query_map[sub_type_normalized]()
            if area_filter:
                result = f"📍 **Bereich: {area_filter}**\n\n" + result
            return result
        
        # Bereinigte Übereinstimmung (ohne Trennzeichen)
        for key, func in query_map.items():
            key_clean = key.replace('_', '').replace(' ', '').replace('-', '')
            key_normalized = self.normalize_text(key)
            
            if sub_type_clean == key_clean or sub_type_clean == key_normalized.replace('_', ''):
                result = func()
                if area_filter:
                    result = f"📍 **Bereich: {area_filter}**\n\n" + result
                return result
        
        # Partielle Übereinstimmung
        for key, func in query_map.items():
            if key in sub_type_lower or sub_type_lower in key:
                result = func()
                if area_filter:
                    result = f"📍 **Bereich: {area_filter}**\n\n" + result
                return result
        
        # Wort-basierte Übereinstimmung
        sub_type_words = set(re.split(r'[_\s\-/]+', sub_type_lower))
        best_match = None
        best_score = 0
        
        for key, func in query_map.items():
            key_words = set(re.split(r'[_\s\-/]+', key))
            common = sub_type_words & key_words
            if len(common) > best_score:
                best_score = len(common)
                best_match = func
        
        if best_match and best_score > 0:
            result = best_match()
            if area_filter:
                result = f"📍 **Bereich: {area_filter}**\n\n" + result
            return result
        
        _LOGGER.warning(f"Unknown status type: '{sub_type}'")
        
        return (
            f"❌ Unbekannter Abfragetyp: '{sub_type}'\n\n"
            f"Verfügbare Abfragen:\n"
            f"  • temperaturen\n"
            f"  • luftfeuchtigkeit\n"
            f"  • fenster\n"
            f"  • eingeschaltet\n"
            f"  • batterie\n"
            f"  • offline\n"
            f"  • energie\n"
            f"  • klima\n"
            f"  • bewegung\n"
            f"  • luftqualität\n"
            f"  • zusammenfassung\n"
            f"  • alle sensoren"
        )

    # ==================== CONTROL EXECUTION ====================

    async def _execute_single_command(self, command: dict) -> str:
        """Execute a single control command."""
        domain = command.get("domain")
        entity_id = command.get("entity_id")
        service = command.get("service", "turn_on")
        service_data = command.get("data", {})
        
        if isinstance(service_data, dict):
            service_data = service_data.copy()
        else:
            service_data = {}

        if not domain and entity_id and '.' in entity_id:
            domain = entity_id.split('.')[0]

        if not entity_id:
            return "❌ Keine Entity-ID angegeben"

        service = self._normalize_service(service)

        controlled = self.get_controlled_entities(include_sensors=False)
        
        # Prüfe ob Entity direkt existiert
        if entity_id not in controlled:
            _LOGGER.debug(f"Entity '{entity_id}' not found directly, trying fuzzy match...")
            
            # Versuche Entity zu finden (mit Umlaut-Normalisierung)
            found_entity = self.find_entity_by_name(entity_id)
            
            if found_entity:
                _LOGGER.info(f"Mapped '{entity_id}' -> '{found_entity}'")
                entity_id = found_entity
                domain = entity_id.split('.')[0]
            else:
                # Versuche nur den Namen-Teil (nach dem Punkt)
                if '.' in entity_id:
                    name_part = entity_id.split('.')[-1]
                    found_entity = self.find_entity_by_name(name_part)
                    if found_entity:
                        _LOGGER.info(f"Mapped name '{name_part}' -> '{found_entity}'")
                        entity_id = found_entity
                        domain = entity_id.split('.')[0]
        
        # Immer noch nicht gefunden?
        if entity_id not in controlled:
            suggestions = self._find_similar_entities(entity_id, controlled)
            if suggestions:
                return f"❌ '{entity_id}' nicht verfügbar.\n\nÄhnliche Geräte:\n{suggestions}"
            return f"❌ '{entity_id}' nicht verfügbar"

        service_data = self._normalize_service_data(service_data)
        service_data["entity_id"] = entity_id

        try:
            _LOGGER.info(f"Executing: {domain}.{service} on {entity_id} with {service_data}")
            
            await self.hass.services.async_call(
                domain, service, service_data, blocking=True
            )

            info = controlled[entity_id]
            return self._build_confirmation(info['name'], service, service_data)

        except Exception as e:
            _LOGGER.error(f"Service call error: {e}")
            return f"❌ Fehler: {str(e)}"

    async def _execute_multiple_commands_parallel(self, commands: list[dict]) -> str:
        """Execute multiple commands in parallel."""
        if not commands:
            return "❌ Keine Befehle"
        
        tasks = [self._execute_single_command_silent(cmd) for cmd in commands]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success = sum(1 for r in results if r is True)
        failed = len(commands) - success
        
        if success == len(commands):
            return f"✅ {success} Gerät(e) erfolgreich gesteuert!"
        elif success > 0:
            return f"⚠️ {success} von {len(commands)} erfolgreich ({failed} fehlgeschlagen)"
        return f"❌ Alle {len(commands)} Befehle fehlgeschlagen"

    async def _execute_single_command_silent(self, command: dict) -> bool:
        """Execute a single command silently (returns True/False)."""
        try:
            domain = command.get("domain")
            entity_id = command.get("entity_id")
            service = command.get("service", "turn_on")
            service_data = command.get("data", {})
            
            if isinstance(service_data, dict):
                service_data = service_data.copy()
            else:
                service_data = {}

            if not domain and entity_id and '.' in entity_id:
                domain = entity_id.split('.')[0]

            if not all([domain, entity_id]):
                return False

            controlled = self.get_controlled_entities(include_sensors=False)
            
            # Versuche Entity zu finden
            if entity_id not in controlled:
                found = self.find_entity_by_name(entity_id)
                if found:
                    entity_id = found
                    domain = entity_id.split('.')[0]
            
            if entity_id not in controlled:
                return False

            service = self._normalize_service(service)
            service_data = self._normalize_service_data(service_data)
            service_data["entity_id"] = entity_id
            
            await self.hass.services.async_call(
                domain, service, service_data, blocking=True
            )
            return True
            
        except Exception as e:
            _LOGGER.error(f"Silent command error: {e}")
            return False

    # ==================== HELPER METHODS ====================

    def _normalize_service(self, service: str | None) -> str:
        """Normalize service name to Home Assistant format."""
        if not service:
            return "turn_on"
        
        service_lower = str(service).lower().strip()
        
        service_map = {
            "on": "turn_on",
            "an": "turn_on",
            "ein": "turn_on",
            "einschalten": "turn_on",
            "anschalten": "turn_on",
            "anmachen": "turn_on",
            "turn_on": "turn_on",
            
            "off": "turn_off",
            "aus": "turn_off",
            "ausschalten": "turn_off",
            "ausmachen": "turn_off",
            "turn_off": "turn_off",
            
            "toggle": "toggle",
            "umschalten": "toggle",
            "wechseln": "toggle",
            
            "set_temperature": "set_temperature",
            "set_hvac_mode": "set_hvac_mode",
            "set_position": "set_position",
            "open_cover": "open_cover",
            "close_cover": "close_cover",
            "stop_cover": "stop_cover",
        }
        
        return service_map.get(service_lower, service)

    def _normalize_service_data(self, data: dict) -> dict:
        """Normalize service data to Home Assistant format."""
        if not isinstance(data, dict):
            return {}
        
        result = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # ===== FARBEN =====
            if key_lower in ["rgb", "color", "rgb_color", "farbe"]:
                if isinstance(value, list) and len(value) >= 3:
                    result["rgb_color"] = [int(v) for v in value[:3]]
            
            # ===== HELLIGKEIT =====
            elif key_lower == "brightness":
                if isinstance(value, (int, float)):
                    if value > 100:
                        result["brightness_pct"] = max(1, min(100, int(value / 255 * 100)))
                    else:
                        result["brightness_pct"] = max(1, min(100, int(value)))
            
            elif key_lower in ["brightness_pct", "helligkeit"]:
                if isinstance(value, (int, float)):
                    result["brightness_pct"] = max(1, min(100, int(value)))
            
            # ===== FARBTEMPERATUR =====
            elif key_lower == "color_temp":
                if isinstance(value, (int, float)) and value > 0:
                    result["color_temp_kelvin"] = int(1000000 / value)
            
            elif key_lower in ["color_temp_kelvin", "kelvin", "farbtemperatur"]:
                if isinstance(value, (int, float)):
                    result["color_temp_kelvin"] = int(value)
            
            # ===== TEMPERATUR (Klima) =====
            elif key_lower in ["temperature", "temperatur", "temp"]:
                result["temperature"] = float(value)
            
            # ===== HVAC MODE =====
            elif key_lower in ["hvac_mode", "mode", "modus"]:
                result["hvac_mode"] = str(value)
            
            # ===== POSITION (Cover) =====
            elif key_lower in ["position", "pos"]:
                if isinstance(value, (int, float)):
                    result["position"] = max(0, min(100, int(value)))
            
            # ===== LAUTSTÄRKE =====
            elif key_lower in ["volume", "volume_level", "lautstärke", "lautstaerke"]:
                if isinstance(value, (int, float)):
                    if value > 1:
                        result["volume_level"] = value / 100
                    else:
                        result["volume_level"] = value
            
            # ===== ALLE ANDEREN =====
            else:
                result[key] = value
        
        return result

    def _build_confirmation(self, name: str, service: str, data: dict) -> str:
        """Build a user-friendly confirmation message."""
        msg = f"✅ {name}"
        
        if service == "turn_on":
            msg += " eingeschaltet"
            
            details = []
            
            if "brightness_pct" in data:
                details.append(f"{data['brightness_pct']}%")
            
            if "rgb_color" in data:
                color_name = self.color_manager.get_color_name(data['rgb_color'])
                details.append(color_name)
            
            if "color_temp_kelvin" in data:
                kelvin = data['color_temp_kelvin']
                if kelvin < 3000:
                    temp_name = "warmweiß"
                elif kelvin < 4500:
                    temp_name = "neutral"
                else:
                    temp_name = "kaltweiß"
                details.append(f"{temp_name} ({kelvin}K)")
            
            if details:
                msg += f" ({', '.join(details)})"
                
        elif service == "turn_off":
            msg += " ausgeschaltet"
            
        elif service == "toggle":
            msg += " umgeschaltet"
            
        elif service == "set_temperature":
            temp = data.get('temperature', '?')
            msg += f" auf {temp}°C eingestellt"
            
        elif service == "set_hvac_mode":
            mode = data.get('hvac_mode', '?')
            msg += f" Modus: {mode}"
            
        elif service in ["open_cover", "close_cover"]:
            action = "geöffnet" if service == "open_cover" else "geschlossen"
            msg += f" {action}"
            
        elif service == "set_position":
            pos = data.get('position', '?')
            msg += f" auf {pos}% eingestellt"
            
        else:
            msg += f" ({service})"
        
        return msg

    def _find_similar_entities(self, entity_id: str, controlled: dict) -> str:
        """Find similar entity IDs for suggestions."""
        suggestions = []
        
        # Normalisiere Suchbegriff
        search_normalized = self.normalize_entity_id(entity_id)
        search_parts = set(search_normalized.replace('_', ' ').split())
        
        for eid, info in controlled.items():
            eid_short = eid.split('.')[-1]
            eid_normalized = self.normalize_entity_id(eid_short)
            name_normalized = self.normalize_entity_id(info['name'])
            
            # Berechne Übereinstimmungen
            eid_words = set(eid_normalized.replace('_', ' ').split())
            name_words = set(name_normalized.replace('_', ' ').split())
            
            matches = len(search_parts & eid_words) + len(search_parts & name_words)
            
            # Teilstring-Übereinstimmung
            if search_normalized in eid_normalized or eid_normalized in search_normalized:
                matches += 3
            if search_normalized in name_normalized or name_normalized in search_normalized:
                matches += 3
            
            if matches > 0:
                suggestions.append((matches, f"  • {info['name']} ({eid})"))
        
        suggestions.sort(key=lambda x: x[0], reverse=True)
        
        return "\n".join(s[1] for s in suggestions[:5])

    def is_entity_controlled(self, entity_id: str) -> bool:
        """Check if an entity is in the controlled list."""
        controlled = self.get_controlled_entities(include_sensors=False)
        
        if entity_id in controlled:
            return True
        
        # Versuche mit Normalisierung
        found = self.find_entity_by_name(entity_id)
        return found is not None

    def clear_cache(self) -> None:
        """Clear the entity cache."""
        DeviceController._entity_cache = None
        DeviceController._cache_time = None
        _LOGGER.debug("Entity cache cleared")