"""Entity and area selector helper for freellm_chat."""
from __future__ import annotations

import logging
from typing import Any
from functools import lru_cache

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, entity_registry as er, device_registry as dr

from .const import CONTROL_DOMAINS, SENSOR_DOMAINS, SUPPORTED_DOMAINS

_LOGGER = logging.getLogger(__name__)


class EntitySelector:
    """Helper for selecting entities and areas."""

    @staticmethod
    def get_available_areas(hass: HomeAssistant) -> list[dict[str, str]]:
        """Get all available areas."""
        area_registry = ar.async_get(hass)
        areas = []
        
        for area in area_registry.async_list_areas():
            areas.append({
                "label": area.name,
                "value": area.id
            })
        
        return sorted(areas, key=lambda x: x["label"])

    @staticmethod
    def get_available_entities(
        hass: HomeAssistant, 
        include_sensors: bool = False
    ) -> list[dict[str, str]]:
        """Get all controllable entities."""
        entity_registry = er.async_get(hass)
        area_registry = ar.async_get(hass)
        entities = []
        
        domains = SUPPORTED_DOMAINS if include_sensors else CONTROL_DOMAINS

        for state in hass.states.async_all():
            if state.domain not in domains:
                continue

            entity_entry = entity_registry.async_get(state.entity_id)
            
            # Skip versteckte Entities
            if entity_entry and entity_entry.hidden_by:
                continue

            friendly_name = state.attributes.get('friendly_name', state.entity_id)
            area_name = ""
            
            if entity_entry and entity_entry.area_id:
                area = area_registry.async_get_area(entity_entry.area_id)
                area_name = f" [{area.name}]" if area else ""

            # Füge Domain-Icon hinzu
            domain_icon = EntitySelector._get_domain_icon(state.domain)
            
            entities.append({
                "label": f"{domain_icon} {friendly_name}{area_name}",
                "value": state.entity_id
            })

        return sorted(entities, key=lambda x: x["label"])

    @staticmethod
    def _get_domain_icon(domain: str) -> str:
        """Get emoji icon for domain."""
        icons = {
            "light": "💡",
            "switch": "🔌",
            "climate": "🌡️",
            "cover": "🪟",
            "fan": "🌀",
            "media_player": "🔊",
            "lock": "🔒",
            "sensor": "📊",
            "binary_sensor": "⚡",
            "weather": "🌤️",
            "vacuum": "🧹",
            "humidifier": "💨",
        }
        return icons.get(domain, "📦")

    @staticmethod
    def get_entities_by_area(hass: HomeAssistant, area_id: str) -> list[str]:
        """Get all entities in a specific area."""
        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)
        entities = []

        # Entities direkt einem Bereich zugeordnet
        for entity in entity_registry.entities.values():
            area_match = False
            
            if entity.area_id == area_id:
                area_match = True
            elif entity.device_id:
                device = device_registry.async_get(entity.device_id)
                if device and device.area_id == area_id:
                    area_match = True
            
            if area_match and entity.domain in SUPPORTED_DOMAINS:
                entities.append(entity.entity_id)

        return entities

    @staticmethod
    def get_area_name(hass: HomeAssistant, area_id: str) -> str | None:
        """Get area name by ID."""
        area_registry = ar.async_get(hass)
        area = area_registry.async_get_area(area_id)
        return area.name if area else None