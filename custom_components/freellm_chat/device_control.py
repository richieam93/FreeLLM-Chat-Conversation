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

    async def execute_command(self, response: str) -> str | None:
        """Parse and execute commands from LLM response."""
        try:
            clean_response = self._clean_json_response(response)
            
            try:
                command = json.loads(clean_response)
            except json.JSONDecodeError:
                _LOGGER.debug(f"Could not parse: {clean_response[:100]}")
                return None

            action = command.get("action")

            if action == "control":
                return await self._execute_single_command(command)
            elif action == "control_multiple":
                return await self._execute_multiple_commands_parallel(command.get("commands", []))
            elif action == "query":
                query_type = command.get("query_type")
                
                if query_type == "sensor":
                    return await self._execute_sensor_query(command)
                elif query_type == "status":
                    return await self._execute_status_query(command)
            
            return None

        except Exception as e:
            _LOGGER.error(f"Error executing command: {e}")
            return f"❌ Fehler: {str(e)}"

    def _clean_json_response(self, response: str) -> str:
        """Clean JSON from LLM response."""
        clean = response.strip()
        clean = re.sub(r'^```(?:json)?\s*', '', clean)
        clean = re.sub(r'\s*```$', '', clean)
        
        json_match = re.search(r'\{[\s\S]*\}', clean)
        if json_match:
            return json_match.group()
        
        return clean

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

    async def _execute_status_query(self, command: dict) -> str:
        """Execute status queries."""
        sub_type = command.get("sub_type")
        
        controlled = self.get_controlled_entities(include_sensors=True)
        analyzer = SensorAnalyzer(self.hass, controlled)
        
        query_map = {
            "temperatures": analyzer.analyze_temperatures,
            "humidity": analyzer.analyze_humidity,
            "windows": analyzer.check_open_windows,
            "powered_on": analyzer.get_powered_on_devices,
            "battery": analyzer.check_battery_status,
            "offline": analyzer.check_offline_devices,
            "energy": analyzer.analyze_energy,
            "climate_overview": analyzer.get_climate_overview,
            "motion": analyzer.check_motion_sensors,
            "air_quality": analyzer.analyze_air_quality,
            "all_sensors": analyzer.get_all_sensors_summary,
            "device_summary": analyzer.get_device_summary,
            "last_activity": analyzer.get_last_activities,
        }
        
        if sub_type in query_map:
            return query_map[sub_type]()
        
        return f"❌ Unbekannter Status-Typ: {sub_type}"

    async def _execute_single_command(self, command: dict) -> str:
        """Execute a single control command."""
        domain = command.get("domain")
        entity_id = command.get("entity_id")
        service = command.get("service")
        service_data = command.get("data", {})

        if not all([domain, entity_id, service]):
            return "❌ Unvollständiger Befehl"

        controlled = self.get_controlled_entities(include_sensors=False)
        if entity_id not in controlled:
            suggestions = self._find_similar_entities(entity_id, controlled)
            if suggestions:
                return f"❌ '{entity_id}' nicht verfügbar.\n\nMeintest du:\n{suggestions}"
            return f"❌ '{entity_id}' nicht verfügbar"

        service_data["entity_id"] = entity_id

        try:
            await self.hass.services.async_call(
                domain, service, service_data, blocking=True
            )

            info = controlled[entity_id]
            return self._build_confirmation(info['name'], service, service_data)

        except Exception as e:
            _LOGGER.error(f"Error: {e}")
            return f"❌ Fehler: {str(e)}"

    async def _execute_multiple_commands_parallel(self, commands: list[dict]) -> str:
        """Execute multiple commands in parallel."""
        if not commands:
            return "❌ Keine Befehle"
        
        tasks = [self._execute_single_command_silent(cmd) for cmd in commands]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success = sum(1 for r in results if r is True)
        
        if success == len(commands):
            return f"✅ {success} Gerät(e) erfolgreich gesteuert!"
        elif success > 0:
            return f"⚠️ {success} von {len(commands)} erfolgreich"
        return f"❌ Fehler bei allen {len(commands)} Befehlen"

    async def _execute_single_command_silent(self, command: dict) -> bool:
        """Execute a single command silently."""
        try:
            domain = command.get("domain")
            entity_id = command.get("entity_id")
            service = command.get("service")
            service_data = command.get("data", {})

            if not all([domain, entity_id, service]):
                return False

            controlled = self.get_controlled_entities(include_sensors=False)
            if entity_id not in controlled:
                return False

            service_data["entity_id"] = entity_id
            
            await self.hass.services.async_call(
                domain, service, service_data, blocking=True
            )
            return True
            
        except Exception as e:
            _LOGGER.error(f"Silent command error: {e}")
            return False

    def _build_confirmation(self, name: str, service: str, data: dict) -> str:
        """Build a confirmation message."""
        msg = f"✅ {name}"
        
        if service == "turn_on":
            msg += " eingeschaltet"
            if "brightness_pct" in data:
                msg += f" ({data['brightness_pct']}%)"
            if "rgb_color" in data:
                color_name = self.color_manager.get_color_name(data['rgb_color'])
                msg += f" ({color_name})"
            if "color_temp_kelvin" in data:
                msg += f" ({data['color_temp_kelvin']}K)"
        elif service == "turn_off":
            msg += " ausgeschaltet"
        elif service == "toggle":
            msg += " umgeschaltet"
        elif service == "set_temperature":
            msg += f" auf {data.get('temperature', '?')}°C"
        else:
            msg += f" - {service}"
        
        return msg

    def _find_similar_entities(self, entity_id: str, controlled: dict) -> str:
        """Find similar entity IDs."""
        suggestions = []
        search = entity_id.lower().replace("_", " ").replace(".", " ")
        
        for eid, info in controlled.items():
            eid_lower = eid.lower().replace("_", " ").replace(".", " ")
            name_lower = info['name'].lower()
            
            if any(w in eid_lower or w in name_lower for w in search.split()):
                suggestions.append(f"  • {info['name']} ({eid})")
        
        return "\n".join(suggestions[:5])