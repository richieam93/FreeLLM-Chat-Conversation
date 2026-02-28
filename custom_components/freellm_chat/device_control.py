"""Device control handler for freellm_chat."""
from __future__ import annotations

import asyncio
import logging
import json
import re
from typing import Any
from datetime import datetime, timedelta

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

    def get_controlled_entities(self, include_sensors: bool = True) -> dict[str, dict]:
        """Get all entities that can be controlled based on selection."""
        # Cache prüfen
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

            # Prüfe ob Entity direkt ausgewählt
            if entity_id in self.selected_entities:
                controlled_entities[entity_id] = self._build_entity_info(state)
                continue

            # Prüfe Bereich
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

        # Cache aktualisieren
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
                    context += f"  • {info['name']}({entity_id.split('.')[-1]})[{info['state']}]\n"
            
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
        _LOGGER.debug(f"Parsing response: {response[:200]}...")
        
        try:
            # Bereinige und parse JSON
            command = self._parse_llm_response(response)
            
            if command is None:
                _LOGGER.warning(f"Could not parse command from: {response[:100]}")
                return None

            _LOGGER.debug(f"Parsed command: {command}")

            action = command.get("action", "").lower()
            
            # Korrigiere abgekürzte Actions
            if action in ["cont", "ctrl", "control", "c"]:
                action = "control"
            elif action in ["query", "q", "ask", "get"]:
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
            _LOGGER.error(f"Error executing command: {e}")
            return f"❌ Fehler: {str(e)}"

    def _parse_llm_response(self, response: str) -> dict | None:
        """Parse LLM response with flexible JSON handling."""
        # Bereinige Response
        clean = response.strip()
        
        # Entferne Markdown Code-Blöcke
        clean = re.sub(r'^```(?:json)?\s*', '', clean)
        clean = re.sub(r'\s*```$', '', clean)
        clean = clean.strip()
        
        # Versuche JSON zu finden und zu parsen
        json_patterns = [
            r'\{[^{}]*\}',  # Einfaches JSON ohne verschachtelte Objekte
            r'\{.*?\}',      # Minimal greedy
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, clean, re.DOTALL)
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict) and ("action" in parsed or "entity_id" in parsed):
                        return parsed
                except json.JSONDecodeError:
                    continue
        
        # Versuche gesamte Response als JSON
        try:
            parsed = json.loads(clean)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        
        # Letzter Versuch: Repariere kaputtes JSON
        repaired = self._repair_json(clean)
        if repaired:
            return repaired
        
        return None

    def _repair_json(self, text: str) -> dict | None:
        """Try to repair broken JSON."""
        try:
            # Finde action
            action_match = re.search(r'"action"\s*:\s*"(\w+)"', text)
            action = action_match.group(1) if action_match else None
            
            # Korrigiere abgekürzte Actions
            if action in ["cont", "ctrl"]:
                action = "control"
            
            # Finde entity_id
            entity_match = re.search(r'"entity_id"\s*:\s*"([^"]+)"', text)
            entity_id = entity_match.group(1) if entity_match else None
            
            # Finde Farbe (verschiedene Formate)
            rgb_color = None
            
            # Format: "rgb":[0,255,0] oder "color":[0,255,0] oder "rgb_color":[0,255,0]
            color_match = re.search(r'"(?:color|rgb_color|rgb)"\s*:\s*\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', text)
            if color_match:
                rgb_color = [int(color_match.group(1)), int(color_match.group(2)), int(color_match.group(3))]
            
            # Finde Helligkeit
            brightness = None
            brightness_match = re.search(r'"brightness(?:_pct)?"\s*:\s*(\d+)', text)
            if brightness_match:
                brightness = int(brightness_match.group(1))
            
            # Finde state/service
            service = "turn_on"
            state_match = re.search(r'"(?:state|service)"\s*:\s*"(\w+)"', text)
            if state_match:
                state_val = state_match.group(1).lower()
                if state_val in ["off", "aus", "turn_off"]:
                    service = "turn_off"
                elif state_val in ["toggle", "umschalten"]:
                    service = "toggle"
            
            # Für Query
            if action == "query":
                # Suche nach type/sub_type
                type_match = re.search(r'"(?:type|sub_type)"\s*:\s*"(\w+)"', text)
                query_type = type_match.group(1) if type_match else "temperatures"
                return {
                    "action": "query",
                    "query_type": "status",
                    "sub_type": query_type
                }
            
            # Für Control
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
                
                _LOGGER.info(f"Repaired JSON: {result}")
                return result
            
            return None
            
        except Exception as e:
            _LOGGER.debug(f"JSON repair failed: {e}")
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
        
        _LOGGER.debug(f"Query - query_type: {query_type}, sub_type: {sub_type}")
        
        # Wenn query_type == "sensor", dann entity_ids abfragen
        if query_type == "sensor":
            return await self._execute_sensor_query(command)
        
        # Status-Abfragen
        effective_type = sub_type or query_type
        if effective_type:
            return await self._execute_status_query(effective_type)
        
        return "❌ Unbekannter Abfragetyp"

    async def _execute_sensor_query(self, command: dict) -> str:
        """Execute a sensor query."""
        entity_ids = command.get("entity_ids", [])
        
        if not entity_ids:
            return "❌ Keine Sensoren angegeben"
        
        controlled = self.get_controlled_entities(include_sensors=True)
        results = []
        
        for entity_id in entity_ids:
            if entity_id not in controlled:
                continue
            
            state = self.hass.states.get(entity_id)
            if state:
                info = controlled[entity_id]
                unit = info.get('unit', '')
                results.append(f"{info['name']}: {state.state}{unit}")
        
        if not results:
            return "❌ Keine Sensordaten gefunden"
        
        if len(results) == 1:
            return f"📊 {results[0]}"
        return "📊 Sensorwerte:\n" + "\n".join(f"  • {r}" for r in results)

    async def _execute_status_query(self, sub_type: str) -> str:
        """Execute status queries."""
        _LOGGER.debug(f"Executing status query: {sub_type}")
        
        controlled = self.get_controlled_entities(include_sensors=True)
        analyzer = SensorAnalyzer(self.hass, controlled)
        
        # Mapping mit vielen Alternativen
        query_map = {
            # Temperatur
            "temperatures": analyzer.analyze_temperatures,
            "temperature": analyzer.analyze_temperatures,
            "temp": analyzer.analyze_temperatures,
            "temperatur": analyzer.analyze_temperatures,
            "temperaturen": analyzer.analyze_temperatures,
            
            # Luftfeuchtigkeit
            "humidity": analyzer.analyze_humidity,
            "feuchtigkeit": analyzer.analyze_humidity,
            "luftfeuchtigkeit": analyzer.analyze_humidity,
            
            # Fenster/Türen
            "windows": analyzer.check_open_windows,
            "fenster": analyzer.check_open_windows,
            "doors": analyzer.check_open_windows,
            "türen": analyzer.check_open_windows,
            "tueren": analyzer.check_open_windows,
            
            # Eingeschaltete Geräte
            "powered_on": analyzer.get_powered_on_devices,
            "on": analyzer.get_powered_on_devices,
            "eingeschaltet": analyzer.get_powered_on_devices,
            "aktiv": analyzer.get_powered_on_devices,
            "an": analyzer.get_powered_on_devices,
            
            # Batterie
            "battery": analyzer.check_battery_status,
            "batterie": analyzer.check_battery_status,
            "batteries": analyzer.check_battery_status,
            "batterien": analyzer.check_battery_status,
            
            # Offline
            "offline": analyzer.check_offline_devices,
            "unavailable": analyzer.check_offline_devices,
            "nicht_verfügbar": analyzer.check_offline_devices,
            
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
            
            # Bewegung
            "motion": analyzer.check_motion_sensors,
            "bewegung": analyzer.check_motion_sensors,
            "presence": analyzer.check_motion_sensors,
            
            # Luftqualität
            "air_quality": analyzer.analyze_air_quality,
            "luft": analyzer.analyze_air_quality,
            "luftqualität": analyzer.analyze_air_quality,
            "co2": analyzer.analyze_air_quality,
            
            # Alle Sensoren
            "all_sensors": analyzer.get_all_sensors_summary,
            "alle_sensoren": analyzer.get_all_sensors_summary,
            "sensoren": analyzer.get_all_sensors_summary,
            "all": analyzer.get_all_sensors_summary,
            "alle": analyzer.get_all_sensors_summary,
            
            # Zusammenfassung
            "device_summary": analyzer.get_device_summary,
            "summary": analyzer.get_device_summary,
            "zusammenfassung": analyzer.get_device_summary,
            "übersicht": analyzer.get_device_summary,
            "uebersicht": analyzer.get_device_summary,
            
            # Letzte Aktivität
            "last_activity": analyzer.get_last_activities,
            "activity": analyzer.get_last_activities,
            "aktivität": analyzer.get_last_activities,
            "aktivitaet": analyzer.get_last_activities,
            "letzte": analyzer.get_last_activities,
        }
        
        sub_type_lower = sub_type.lower().strip()
        
        # Direkte Übereinstimmung
        if sub_type_lower in query_map:
            return query_map[sub_type_lower]()
        
        # Partielle Übereinstimmung
        for key, func in query_map.items():
            if key in sub_type_lower or sub_type_lower in key:
                return func()
        
        _LOGGER.warning(f"Unknown status type: {sub_type}")
        return (
            f"❌ Unbekannter Status-Typ: {sub_type}\n\n"
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
            f"  • zusammenfassung"
        )

    # ==================== CONTROL EXECUTION ====================

    async def _execute_single_command(self, command: dict) -> str:
        """Execute a single control command."""
        domain = command.get("domain")
        entity_id = command.get("entity_id")
        service = command.get("service", "turn_on")
        service_data = command.get("data", {})
        
        # Kopie der Daten erstellen
        if isinstance(service_data, dict):
            service_data = service_data.copy()
        else:
            service_data = {}

        # Fallback: domain aus entity_id extrahieren
        if not domain and entity_id and '.' in entity_id:
            domain = entity_id.split('.')[0]

        if not entity_id:
            return "❌ Keine Entity-ID angegeben"

        # Korrigiere Service-Namen
        service = self._normalize_service(service)

        # Prüfe ob Entity steuerbar
        controlled = self.get_controlled_entities(include_sensors=False)
        if entity_id not in controlled:
            suggestions = self._find_similar_entities(entity_id, controlled)
            if suggestions:
                return f"❌ '{entity_id}' nicht verfügbar.\n\nÄhnliche Geräte:\n{suggestions}"
            return f"❌ '{entity_id}' nicht verfügbar"

        # Korrigiere Daten-Format für Home Assistant
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
            
            # Kopie erstellen
            if isinstance(service_data, dict):
                service_data = service_data.copy()
            else:
                service_data = {}

            if not domain and entity_id and '.' in entity_id:
                domain = entity_id.split('.')[0]

            if not all([domain, entity_id]):
                return False

            controlled = self.get_controlled_entities(include_sensors=False)
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
            # An/Ein
            "on": "turn_on",
            "an": "turn_on",
            "ein": "turn_on",
            "einschalten": "turn_on",
            "turn_on": "turn_on",
            
            # Aus
            "off": "turn_off",
            "aus": "turn_off",
            "ausschalten": "turn_off",
            "turn_off": "turn_off",
            
            # Toggle
            "toggle": "toggle",
            "umschalten": "toggle",
            "wechseln": "toggle",
            
            # Spezielle Services
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
            # rgb, color → rgb_color
            if key_lower in ["rgb", "color", "rgb_color", "farbe"]:
                if isinstance(value, list) and len(value) >= 3:
                    result["rgb_color"] = [int(v) for v in value[:3]]
            
            # ===== HELLIGKEIT =====
            # brightness (0-255) → brightness_pct (0-100)
            elif key_lower == "brightness":
                if isinstance(value, (int, float)):
                    if value > 100:
                        # 0-255 Format → 0-100
                        result["brightness_pct"] = max(1, min(100, int(value / 255 * 100)))
                    else:
                        # Bereits 0-100
                        result["brightness_pct"] = max(1, min(100, int(value)))
            
            # brightness_pct direkt übernehmen
            elif key_lower in ["brightness_pct", "helligkeit"]:
                if isinstance(value, (int, float)):
                    result["brightness_pct"] = max(1, min(100, int(value)))
            
            # ===== FARBTEMPERATUR =====
            # color_temp (Mired) → color_temp_kelvin
            elif key_lower == "color_temp":
                if isinstance(value, (int, float)) and value > 0:
                    # Mired to Kelvin: K = 1,000,000 / Mired
                    result["color_temp_kelvin"] = int(1000000 / value)
            
            # color_temp_kelvin direkt übernehmen
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
            elif key_lower in ["volume", "volume_level", "lautstärke"]:
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
            
            # Helligkeit
            if "brightness_pct" in data:
                msg += f" ({data['brightness_pct']}%)"
            
            # Farbe
            if "rgb_color" in data:
                color_name = self.color_manager.get_color_name(data['rgb_color'])
                msg += f" ({color_name})"
            
            # Farbtemperatur
            if "color_temp_kelvin" in data:
                kelvin = data['color_temp_kelvin']
                if kelvin < 3000:
                    temp_name = "warmweiß"
                elif kelvin < 4500:
                    temp_name = "neutral"
                else:
                    temp_name = "kaltweiß"
                msg += f" ({temp_name}, {kelvin}K)"
                
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
        
        # Extrahiere Suchbegriffe
        search_parts = entity_id.lower().replace("_", " ").replace(".", " ").split()
        
        for eid, info in controlled.items():
            eid_lower = eid.lower().replace("_", " ").replace(".", " ")
            name_lower = info['name'].lower()
            
            # Prüfe ob Suchbegriffe matchen
            matches = sum(1 for word in search_parts if word in eid_lower or word in name_lower)
            
            if matches > 0:
                suggestions.append((matches, f"  • {info['name']} ({eid})"))
        
        # Sortiere nach Übereinstimmungen
        suggestions.sort(key=lambda x: x[0], reverse=True)
        
        return "\n".join(s[1] for s in suggestions[:5])

    def is_entity_controlled(self, entity_id: str) -> bool:
        """Check if an entity is in the controlled list."""
        return entity_id in self.get_controlled_entities(include_sensors=False)

    def clear_cache(self) -> None:
        """Clear the entity cache."""
        DeviceController._entity_cache = None
        DeviceController._cache_time = None
        _LOGGER.debug("Entity cache cleared")