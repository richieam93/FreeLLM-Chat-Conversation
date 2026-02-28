"""Constants for the freellm_chat Conversation integration."""

DOMAIN = "freellm_chat"

# Chat Konfiguration
CONF_CHAT_MODEL = "chat_model"
DEFAULT_CHAT_MODEL = "gpt-4o-mini-2024-07-18"
CONF_PROMPT = "prompt"
DEFAULT_PROMPT = """Du bist ein hilfreicher und intelligenter Assistent.
Du beantwortest Fragen präzise und in der Sprache des Benutzers."""

# Gerätesteuerung Konfiguration
CONF_ENABLE_DEVICE_CONTROL = "enable_device_control"
DEFAULT_ENABLE_DEVICE_CONTROL = False

CONF_CONTROL_PROMPT = "control_prompt"
DEFAULT_CONTROL_PROMPT = """Du bist ein Smart Home Steuerungs-Assistent.
Deine Aufgabe ist es, Befehle zur Gerätesteuerung zu verstehen und in JSON umzuwandeln.

WICHTIG: Antworte NUR mit einem JSON-Objekt, nichts anderes!

Format für EINZELNE Geräte:
{
  "action": "control",
  "domain": "light|switch|climate|cover|fan|media_player",
  "entity_id": "die_entity_id",
  "service": "turn_on|turn_off|toggle|set_temperature|etc",
  "data": {}
}

Format für MEHRERE Geräte:
{
  "action": "control_multiple",
  "commands": [
    {"domain": "light", "entity_id": "light.kuche", "service": "turn_on"},
    {"domain": "light", "entity_id": "light.wohnzimmer", "service": "turn_on"}
  ]
}

Beispiele:
1. "Schalte das Licht in der Küche an"
   {"action": "control", "domain": "light", "entity_id": "light.kuche", "service": "turn_on"}

2. "Mache das Wohnzimmer grün"
   {"action": "control", "domain": "light", "entity_id": "light.wohnzimmer", "service": "turn_on", "data": {"rgb_color": [0, 255, 0]}}

3. "Dimme das Schlafzimmer auf 30%"
   {"action": "control", "domain": "light", "entity_id": "light.schlafzimmer", "service": "turn_on", "data": {"brightness_pct": 30}}

4. "Stelle die Heizung auf 22 Grad"
   {"action": "control", "domain": "climate", "entity_id": "climate.heizung", "service": "set_temperature", "data": {"temperature": 22}}

5. "Schalte alle Lichter im Wohnzimmer an"
   {"action": "control_multiple", "commands": [{"domain": "light", "entity_id": "light.wohnzimmer_decke", "service": "turn_on"}, {"domain": "light", "entity_id": "light.wohnzimmer_stehlampe", "service": "turn_on"}]}

Farben (rgb_color):
- rot: [255, 0, 0]
- grün: [0, 255, 0]
- blau: [0, 0, 255]
- gelb: [255, 255, 0]
- lila: [128, 0, 128]
- orange: [255, 165, 0]
- pink: [255, 192, 203]
- weiß: [255, 255, 255]
- warmweiß: [255, 244, 229]

Antworte NUR mit dem JSON-Objekt, keine zusätzlichen Erklärungen!"""

CONF_SELECTED_ENTITIES = "selected_entities"
CONF_SELECTED_AREAS = "selected_areas"

# LLM API
LLM7_BASE_URL = "https://api.llm7.io/v1"

# Unterstützte Domains für Steuerung
SUPPORTED_DOMAINS = [
    "light",
    "switch",
    "climate",
    "cover",
    "fan",
    "media_player",
    "lock",
    "scene",
    "script",
    "automation",
    "input_boolean",
    "input_select",
    "input_number",
    "vacuum",
    "humidifier",
]