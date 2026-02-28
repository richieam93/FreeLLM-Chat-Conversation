"""Advanced prompt optimization for freellm_chat."""
from __future__ import annotations

import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)


class PromptOptimizer:
    """Advanced optimizer for reducing prompt size while maintaining quality."""

    def __init__(self, compression_level: str = "auto") -> None:
        """Initialize the optimizer."""
        self.compression_level = compression_level

    def optimize_prompt(
        self, 
        original_prompt: str, 
        entity_count: int,
        include_examples: bool = True
    ) -> str:
        """Optimize prompt based on entity count and settings."""
        level = self._determine_level(entity_count)
        
        _LOGGER.debug(f"Optimizing prompt - Level: {level}, Entities: {entity_count}")
        
        if level == "none":
            return original_prompt
        elif level == "medium":
            return self._medium_compression(original_prompt, include_examples)
        else:  # high
            return self._high_compression()

    def _determine_level(self, entity_count: int) -> str:
        """Determine compression level based on entity count."""
        if self.compression_level != "auto":
            return self.compression_level
        
        if entity_count < 15:
            return "none"
        elif entity_count < 50:
            return "medium"
        else:
            return "high"

    def _medium_compression(self, original: str, include_examples: bool) -> str:
        """Medium compression - remove verbose parts."""
        lines = original.split('\n')
        compressed = []
        skip_until_empty = False
        
        for line in lines:
            # Skip example blocks if not needed
            if not include_examples and ('Beispiel' in line or 'BEISPIEL' in line or 'Example' in line):
                skip_until_empty = True
                continue
            
            if skip_until_empty:
                if line.strip() == '':
                    skip_until_empty = False
                continue
            
            # Remove verbose explanations
            if any(phrase in line.lower() for phrase in [
                'wichtig:', 'hinweis:', 'note:', 'beachte:', 'tipp:'
            ]):
                # Behalte die Zeile aber kürze sie
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts[1]) > 50:
                        line = parts[0] + ':' + parts[1][:50] + '...'
            
            compressed.append(line)
        
        return '\n'.join(compressed)

    def _high_compression(self) -> str:
        """High compression - minimal prompt."""
        return """Smart Home Control - JSON only!

Control: {"action":"control","domain":"D","entity_id":"ID","service":"S","data":{}}
Multiple: {"action":"control_multiple","commands":[...]}
Query: {"action":"query","query_type":"status","sub_type":"TYPE"}

Status Types: temperatures, humidity, windows, powered_on, battery, offline, energy, climate_overview, motion, air_quality, all_sensors, device_summary, last_activity

Colors RGB: rot=[255,0,0], grün=[0,255,0], blau=[0,0,255], gelb=[255,255,0], weiß=[255,255,255], warmweiß=[255,244,229], orange=[255,165,0], pink=[255,105,180], lila=[128,0,128]

Brightness: "data":{"brightness_pct":50}
Color Temp: "data":{"color_temp_kelvin":2700}"""

    def compress_entity_list(
        self, 
        entities: dict[str, dict],
        max_per_area: int = 10
    ) -> str:
        """Create highly compressed entity list."""
        if not entities:
            return "\n\n⚠️ KEINE GERÄTE!"

        # Gruppiere und komprimiere
        by_domain: dict[str, dict[str, list]] = {}
        
        for entity_id, info in entities.items():
            domain = info['domain']
            area = info['area'] or '?'
            
            if domain not in by_domain:
                by_domain[domain] = {}
            if area not in by_domain[domain]:
                by_domain[domain][area] = []
            
            # Sehr kompakte Info
            short_id = entity_id.split('.')[-1]
            state = info['state']
            state_short = state[:3] if len(state) > 3 else state
            
            by_domain[domain][area].append(f"{info['name']}:{short_id}[{state_short}]")
        
        # Erstelle kompakten String
        result = "\n\n=== DEVICES ===\n"
        
        icons = {
            'light': '💡', 
            'switch': '🔌', 
            'climate': '🌡️', 
            'sensor': '📊', 
            'binary_sensor': '⚡', 
            'cover': '🪟',
            'media_player': '🔊',
            'fan': '🌀',
            'vacuum': '🧹',
            'lock': '🔒'
        }
        
        for domain in sorted(by_domain.keys()):
            icon = icons.get(domain, '📦')
            total = sum(len(devs) for devs in by_domain[domain].values())
            result += f"\n{icon} {domain}({total}):\n"
            
            for area in sorted(by_domain[domain].keys()):
                devices = by_domain[domain][area][:max_per_area]
                result += f"  {area}: {', '.join(devices)}\n"
                
                remaining = len(by_domain[domain][area]) - max_per_area
                if remaining > 0:
                    result += f"    +{remaining} more\n"
        
        return result

    def extract_intent(self, user_input: str) -> dict[str, Any]:
        """Extract intent from user input for faster processing."""
        input_lower = user_input.lower()
        
        intent = {
            'type': 'unknown',
            'action': None,
            'target': None,
            'value': None,
            'color': None,
            'area': None
        }
        
        # Steuerungsintent
        control_words = ['schalte', 'mach', 'turn', 'switch', 'dimme', 'stelle']
        if any(w in input_lower for w in control_words):
            intent['type'] = 'control'
            if any(w in input_lower for w in ['an', 'ein', 'on']):
                intent['action'] = 'turn_on'
            elif any(w in input_lower for w in ['aus', 'off']):
                intent['action'] = 'turn_off'
        
        # Abfrageintent
        query_words = ['temperatur', 'wie warm', 'status', 'was ist', 'zeig', 'welche']
        if any(w in input_lower for w in query_words):
            intent['type'] = 'query'
            
            if any(w in input_lower for w in ['temperatur', 'warm', 'kalt', 'grad']):
                intent['action'] = 'temperatures'
            elif any(w in input_lower for w in ['feucht', 'humidity']):
                intent['action'] = 'humidity'
            elif any(w in input_lower for w in ['fenster', 'tür', 'offen']):
                intent['action'] = 'windows'
            elif any(w in input_lower for w in ['eingeschaltet', 'an', 'aktiv']):
                intent['action'] = 'powered_on'
            elif 'batterie' in input_lower:
                intent['action'] = 'battery'
            elif 'offline' in input_lower:
                intent['action'] = 'offline'
            elif any(w in input_lower for w in ['energie', 'strom', 'verbrauch']):
                intent['action'] = 'energy'
        
        # Farbextraktion
        colors = ['rot', 'grün', 'blau', 'gelb', 'weiß', 'orange', 'pink', 'lila', 'violett', 'cyan', 'türkis']
        for color in colors:
            if color in input_lower:
                intent['color'] = color
                break
        
        # Helligkeitsextraktion
        brightness_match = re.search(r'(\d+)\s*%', input_lower)
        if brightness_match:
            intent['value'] = int(brightness_match.group(1))
        
        # Temperatur-Extraktion (für Klima)
        temp_match = re.search(r'(\d+)\s*(?:°|grad)', input_lower)
        if temp_match and intent['type'] != 'query':
            intent['value'] = int(temp_match.group(1))
        
        return intent

    def get_stats(self) -> dict[str, Any]:
        """Get optimizer statistics."""
        return {
            'compression_level': self.compression_level
        }