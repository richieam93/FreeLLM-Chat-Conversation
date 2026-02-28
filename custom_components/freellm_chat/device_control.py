"""Device control handler for freellm_chat."""
from __future__ import annotations

import logging
import json
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, entity_registry as er, device_registry as dr
from homeassistant.exceptions import HomeAssistantError

from .const import SUPPORTED_DOMAINS

_LOGGER = logging.getLogger(__name__)


class DeviceController:
    """Handler for device control operations."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        selected_entities: list[str] | None, 
        selected_areas: list[str] | None
    ) -> None:
        """Initialize the device controller."""
        self.hass = hass
        self.selected_entities = selected_entities or []
        self.selected_areas = selected_areas or []
        self._entity_registry = er.async_get(hass)
        self._area_registry = ar.async_get(hass)
        self._device_registry = dr.async_get(hass)

    def get_controlled_entities(self) -> dict[str, dict]:
        """Get all entities that can be controlled based on selection."""
        controlled_entities = {}

        # Wenn keine Auswahl getroffen wurde, keine Entities zurückgeben
        if not self.selected_entities and not self.selected_areas:
            return {}

        for state in self.hass.states.async_all():
            entity_id = state.entity_id
            
            # Nur unterstützte Domains
            if state.domain not in SUPPORTED_DOMAINS:
                continue

            # Prüfe ob Entity direkt ausgewählt ist
            if entity_id in self.selected_entities:
                controlled_entities[entity_id] = self._build_entity_info(state)
                continue

            # Prüfe ob der Bereich des Entity ausgewählt ist
            if self.selected_areas:
                entity_entry = self._entity_registry.async_get(entity_id)
                
                if entity_entry:
                    area_id = entity_entry.area_id
                    
                    # Wenn Entity keinen Bereich hat, prüfe Device
                    if not area_id and entity_entry.device_id:
                        device = self._device_registry.async_get(entity_entry.device_id)
                        if device:
                            area_id = device.area_id
                    
                    if area_id and area_id in self.selected_areas:
                        controlled_entities[entity_id] = self._build_entity_info(state)

        return controlled_entities

    def _build_entity_info(self, state) -> dict:
        """Build entity information dictionary."""
        entity_entry = self._entity_registry.async_get(state.entity_id)
        area_name = None
        
        if entity_entry:
            area_id = entity_entry.area_id
            
            # Wenn Entity keinen Bereich hat, prüfe Device
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
            'attributes': self._filter_attributes(dict(state.attributes))
        }

    def _filter_attributes(self, attributes: dict) -> dict:
        """Filter important attributes for LLM context."""
        important_attrs = [
            'brightness',
            'brightness_pct',
            'rgb_color',
            'hs_color',
            'color_temp',
            'color_temp_kelvin',
            'temperature',
            'current_temperature',
            'target_temperature',
            'hvac_mode',
            'hvac_modes',
            'fan_mode',
            'fan_modes',
            'swing_mode',
            'position',
            'current_position',
            'volume_level',
            'media_title',
            'source',
            'source_list',
            'supported_color_modes',
            'min_temp',
            'max_temp',
        ]
        
        return {k: v for k, v in attributes.items() if k in important_attrs}

    def generate_context(self) -> str:
        """Generate context information about controlled entities for the LLM."""
        entities = self.get_controlled_entities()
        
        if not entities:
            return "\n\n⚠️ KEINE GERÄTE ZUR STEUERUNG VERFÜGBAR!\nBitte wähle zuerst Geräte oder Bereiche in den Einstellungen aus."

        context = "\n\n=== VERFÜGBARE GERÄTE ZUR STEUERUNG ===\n"
        
        # Gruppiere nach Bereichen
        by_area: dict[str, list] = {}
        for entity_id, info in entities.items():
            area = info['area'] or 'Ohne Bereich'
            if area not in by_area:
                by_area[area] = []
            by_area[area].append((entity_id, info))

        for area, area_entities in sorted(by_area.items()):
            context += f"\n📍 {area}:\n"
            for entity_id, info in sorted(area_entities, key=lambda x: x[1]['name']):
                context += f"  • {info['name']}\n"
                context += f"    Entity-ID: {entity_id}\n"
                context += f"    Domain: {info['domain']}\n"
                context += f"    Status: {info['state']}\n"
                
                # Zusätzliche Infos für bestimmte Domains
                if info['domain'] == 'light' and info['state'] == 'on':
                    attrs = info['attributes']
                    if 'brightness_pct' in attrs:
                        context += f"    Helligkeit: {attrs['brightness_pct']}%\n"
                    elif 'brightness' in attrs:
                        brightness_pct = round(attrs['brightness'] / 255 * 100)
                        context += f"    Helligkeit: {brightness_pct}%\n"
                    if 'rgb_color' in attrs:
                        context += f"    Farbe (RGB): {attrs['rgb_color']}\n"
                    if 'color_temp_kelvin' in attrs:
                        context += f"    Farbtemperatur: {attrs['color_temp_kelvin']}K\n"
                        
                elif info['domain'] == 'climate':
                    attrs = info['attributes']
                    if 'temperature' in attrs:
                        context += f"    Zieltemperatur: {attrs['temperature']}°C\n"
                    if 'current_temperature' in attrs:
                        context += f"    Aktuelle Temperatur: {attrs['current_temperature']}°C\n"
                    if 'hvac_mode' in attrs:
                        context += f"    Modus: {attrs['hvac_mode']}\n"
                
                elif info['domain'] == 'cover':
                    attrs = info['attributes']
                    if 'current_position' in attrs:
                        context += f"    Position: {attrs['current_position']}%\n"
                
                elif info['domain'] == 'media_player':
                    attrs = info['attributes']
                    if 'volume_level' in attrs:
                        context += f"    Lautstärke: {int(attrs['volume_level'] * 100)}%\n"
                    if 'media_title' in attrs:
                        context += f"    Spielt: {attrs['media_title']}\n"

        context += f"\n=== GESAMT: {len(entities)} Geräte verfügbar ===\n"
        
        return context

    async def execute_control_command(self, response: str) -> str | None:
        """Parse and execute control commands from LLM response."""
        try:
            # Bereinige die Antwort von möglichen Markdown-Code-Blöcken
            clean_response = response.strip()
            clean_response = re.sub(r'^```json\s*', '', clean_response)
            clean_response = re.sub(r'^```\s*', '', clean_response)
            clean_response = re.sub(r'\s*```$', '', clean_response)
            
            # Extrahiere JSON aus der Antwort
            json_match = re.search(r'\{[\s\S]*"action"[\s\S]*\}', clean_response)
            
            if json_match:
                json_str = json_match.group()
            else:
                # Versuche die gesamte Antwort als JSON zu parsen
                json_str = clean_response

            try:
                command = json.loads(json_str)
            except json.JSONDecodeError:
                _LOGGER.debug(f"Could not parse as JSON: {clean_response}")
                return None

            action = command.get("action")

            if action == "control":
                return await self._execute_single_command(command)
            elif action == "control_multiple":
                return await self._execute_multiple_commands(command.get("commands", []))
            else:
                _LOGGER.debug(f"Unknown action: {action}")
                return None

        except json.JSONDecodeError as e:
            _LOGGER.error(f"JSON decode error: {e}")
            _LOGGER.debug(f"Response was: {response}")
            return None
        except Exception as e:
            _LOGGER.error(f"Error executing control command: {e}")
            return f"❌ Fehler beim Ausführen: {str(e)}"

    async def _execute_single_command(self, command: dict) -> str:
        """Execute a single control command."""
        domain = command.get("domain")
        entity_id = command.get("entity_id")
        service = command.get("service")
        service_data = command.get("data", {})

        if not all([domain, entity_id, service]):
            return "❌ Fehler: Unvollständiger Befehl (domain, entity_id oder service fehlt)"

        # Prüfe ob Entity gesteuert werden darf
        controlled_entities = self.get_controlled_entities()
        if entity_id not in controlled_entities:
            # Versuche ähnliche Entity zu finden
            suggestions = self._find_similar_entities(entity_id, controlled_entities)
            if suggestions:
                return f"❌ Das Gerät '{entity_id}' ist nicht zur Steuerung freigegeben.\n\nMeintest du vielleicht:\n{suggestions}"
            return f"❌ Das Gerät '{entity_id}' ist nicht zur Steuerung freigegeben"

        # Bereite Service-Daten vor
        service_data["entity_id"] = entity_id

        try:
            await self.hass.services.async_call(
                domain,
                service,
                service_data,
                blocking=True
            )

            entity_state = self.hass.states.get(entity_id)
            friendly_name = entity_state.attributes.get('friendly_name', entity_id) if entity_state else entity_id

            _LOGGER.info(f"✓ Executed: {domain}.{service} on {entity_id} with data: {service_data}")
            
            # Baue Bestätigungsnachricht
            confirmation = f"✅ {friendly_name} wurde erfolgreich gesteuert!"
            
            # Füge Details hinzu
            if service == "turn_on":
                if "brightness_pct" in service_data:
                    confirmation += f"\n   Helligkeit: {service_data['brightness_pct']}%"
                if "rgb_color" in service_data:
                    confirmation += f"\n   Farbe: RGB{tuple(service_data['rgb_color'])}"
                if "temperature" in service_data:
                    confirmation += f"\n   Temperatur: {service_data['temperature']}°C"
            
            return confirmation

        except Exception as e:
            _LOGGER.error(f"Error executing service {domain}.{service}: {e}")
            return f"❌ Fehler bei {entity_id}: {str(e)}"

    async def _execute_multiple_commands(self, commands: list[dict]) -> str:
        """Execute multiple control commands."""
        if not commands:
            return "❌ Keine Befehle zum Ausführen"
        
        results = []
        success_count = 0
        
        for cmd in commands:
            result = await self._execute_single_command(cmd)
            if result and "✅" in result:
                success_count += 1
            results.append(result)

        if success_count == len(commands):
            return f"✅ Alle {len(commands)} Befehle erfolgreich ausgeführt!"
        elif success_count > 0:
            return f"⚠️ {success_count} von {len(commands)} Befehlen erfolgreich:\n" + "\n".join(results)
        else:
            return f"❌ Keine Befehle konnten ausgeführt werden:\n" + "\n".join(results)

    def _find_similar_entities(self, entity_id: str, controlled_entities: dict) -> str:
        """Find similar entity IDs for suggestions."""
        suggestions = []
        search_term = entity_id.lower().replace("_", " ").replace(".", " ")
        
        for eid, info in controlled_entities.items():
            eid_lower = eid.lower().replace("_", " ").replace(".", " ")
            name_lower = info['name'].lower()
            
            # Prüfe auf Übereinstimmungen
            if any(word in eid_lower or word in name_lower for word in search_term.split()):
                suggestions.append(f"  • {info['name']} ({eid})")
        
        return "\n".join(suggestions[:5])  # Max 5 Vorschläge

    def is_entity_controlled(self, entity_id: str) -> bool:
        """Check if an entity is controlled."""
        return entity_id in self.get_controlled_entities()