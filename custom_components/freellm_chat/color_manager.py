"""Color management for freellm_chat."""
from __future__ import annotations

import logging
import colorsys
from typing import Any

from .const import COLOR_PRESETS, COLOR_TEMPERATURES

_LOGGER = logging.getLogger(__name__)


class ColorManager:
    """Manager for color operations and conversions."""

    def __init__(self, custom_colors: dict[str, list[int]] | None = None) -> None:
        """Initialize the color manager."""
        self.colors = {**COLOR_PRESETS}
        if custom_colors:
            self.colors.update(custom_colors)
        self.temperatures = COLOR_TEMPERATURES

    def get_rgb_color(self, color_name: str) -> list[int] | None:
        """Get RGB color from name."""
        color_name_lower = color_name.lower().strip()
        
        # Direkt aus Presets
        if color_name_lower in self.colors:
            return self.colors[color_name_lower]
        
        # Versuche partielle Übereinstimmung
        for name, rgb in self.colors.items():
            if color_name_lower in name or name in color_name_lower:
                return rgb
        
        # Versuche Hex-Farbe zu parsen
        if color_name.startswith('#'):
            return self._hex_to_rgb(color_name)
        
        return None

    def get_color_temp(self, temp_name: str) -> int | None:
        """Get color temperature in Kelvin from name."""
        temp_name_lower = temp_name.lower().strip()
        
        if temp_name_lower in self.temperatures:
            return self.temperatures[temp_name_lower]
        
        # Versuche Zahl zu parsen
        try:
            kelvin = int(temp_name_lower.replace('k', '').strip())
            if 1500 <= kelvin <= 10000:
                return kelvin
        except ValueError:
            pass
        
        return None

    def _hex_to_rgb(self, hex_color: str) -> list[int]:
        """Convert hex color to RGB."""
        hex_color = hex_color.lstrip('#')
        return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

    def rgb_to_hex(self, rgb: list[int]) -> str:
        """Convert RGB to hex color."""
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    def adjust_brightness(self, rgb: list[int], brightness_pct: int) -> list[int]:
        """Adjust RGB color brightness."""
        factor = brightness_pct / 100.0
        return [int(min(255, c * factor)) for c in rgb]

    def blend_colors(self, color1: list[int], color2: list[int], ratio: float = 0.5) -> list[int]:
        """Blend two colors together."""
        return [
            int(c1 * (1 - ratio) + c2 * ratio)
            for c1, c2 in zip(color1, color2)
        ]

    def get_complementary(self, rgb: list[int]) -> list[int]:
        """Get complementary color."""
        return [255 - c for c in rgb]

    def get_color_name(self, rgb: list[int]) -> str:
        """Get closest color name for RGB value."""
        min_distance = float('inf')
        closest_name = "unbekannt"
        
        for name, preset_rgb in self.colors.items():
            distance = sum((a - b) ** 2 for a, b in zip(rgb, preset_rgb))
            if distance < min_distance:
                min_distance = distance
                closest_name = name
        
        return closest_name

    def generate_gradient(self, color1: list[int], color2: list[int], steps: int = 5) -> list[list[int]]:
        """Generate a gradient between two colors."""
        gradient = []
        for i in range(steps):
            ratio = i / (steps - 1)
            gradient.append(self.blend_colors(color1, color2, ratio))
        return gradient

    def get_scene_colors(self, scene_name: str) -> dict[str, Any]:
        """Get predefined scene colors."""
        scenes = {
            "sonnenuntergang": {
                "rgb_color": [255, 99, 71],
                "brightness_pct": 60,
                "color_temp_kelvin": 2200
            },
            "romantisch": {
                "rgb_color": [255, 20, 147],
                "brightness_pct": 30,
            },
            "party": {
                "rgb_color": [148, 0, 211],
                "brightness_pct": 100,
            },
            "relax": {
                "rgb_color": [70, 130, 180],
                "brightness_pct": 40,
                "color_temp_kelvin": 2700
            },
            "konzentration": {
                "brightness_pct": 100,
                "color_temp_kelvin": 6000
            },
            "nachtlicht": {
                "rgb_color": [255, 140, 0],
                "brightness_pct": 10,
            },
            "kino": {
                "rgb_color": [25, 25, 112],
                "brightness_pct": 15,
            },
            "gaming": {
                "rgb_color": [0, 255, 127],
                "brightness_pct": 80,
            },
            "lesen": {
                "brightness_pct": 80,
                "color_temp_kelvin": 4000
            },
            "morgen": {
                "brightness_pct": 70,
                "color_temp_kelvin": 4500
            },
            "abend": {
                "brightness_pct": 50,
                "color_temp_kelvin": 2700
            },
            "nacht": {
                "rgb_color": [255, 100, 50],
                "brightness_pct": 5,
            },
        }
        
        scene_lower = scene_name.lower().strip()
        return scenes.get(scene_lower, {})

    def get_all_color_names(self) -> list[str]:
        """Get all available color names."""
        return sorted(self.colors.keys())

    def get_colors_by_category(self) -> dict[str, list[str]]:
        """Get colors organized by category."""
        categories = {
            "Grundfarben": ["rot", "grün", "blau", "gelb", "weiß", "schwarz"],
            "Warme Farben": ["warmweiß", "orange", "gold", "koralle", "lachs", "pfirsich"],
            "Kalte Farben": ["kaltweiß", "cyan", "türkis", "himmelblau", "eisblau"],
            "Violett/Pink": ["lila", "violett", "magenta", "pink", "rosa", "lavendel"],
            "Grüntöne": ["mint", "limette", "olive", "waldgrün", "smaragd"],
            "Szenen": ["sonnenuntergang", "romantisch", "party", "relax", "nachtlicht"],
        }
        return categories