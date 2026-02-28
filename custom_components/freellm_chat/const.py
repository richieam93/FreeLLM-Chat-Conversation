"""Constants for the freellm_chat Conversation integration."""

DOMAIN = "freellm_chat"

# ===== CHAT KONFIGURATION =====
CONF_CHAT_MODEL = "chat_model"
DEFAULT_CHAT_MODEL = "gpt-4o-mini-2024-07-18"

CONF_PROMPT = "prompt"
DEFAULT_PROMPT = """Du bist ein hilfreicher und intelligenter Assistent.
Du beantwortest Fragen präzise und in der Sprache des Benutzers."""

CONF_CHAT_TEMPERATURE = "chat_temperature"
DEFAULT_CHAT_TEMPERATURE = 0.7

CONF_CHAT_MAX_TOKENS = "chat_max_tokens"
DEFAULT_CHAT_MAX_TOKENS = 1000

# ===== GERÄTESTEUERUNG =====
CONF_ENABLE_DEVICE_CONTROL = "enable_device_control"
DEFAULT_ENABLE_DEVICE_CONTROL = False

CONF_CONTROL_PROMPT = "control_prompt"
DEFAULT_CONTROL_PROMPT = """Smart Home Steuerungs-Assistent - Antworte NUR mit JSON!

WICHTIG: 
1. NUR JSON-Objekt zurückgeben!
2. Verwende IMMER die exakte entity_id aus der Geräteliste!
3. EIN Gerät = eine entity_id
4. Mehrere Geräte nur bei "alle"

FORMATE:

Steuerung (einzeln):
{"action":"control","domain":"light|switch|climate|cover","entity_id":"EXAKTE_ID_AUS_LISTE","service":"turn_on|turn_off","data":{}}

Steuerung (mehrere):
{"action":"control_multiple","commands":[{...},{...}]}

Status-Abfrage:
{"action":"query","query_type":"status","sub_type":"TYPE"}

Mögliche sub_types:
- temperatures: Alle Temperaturen
- humidity: Luftfeuchtigkeit
- windows: Offene Fenster/Türen
- powered_on: Eingeschaltete Geräte
- battery: Batterie-Status
- offline: Offline Geräte
- energy: Energieverbrauch
- all_sensors: Alle Sensoren

BEISPIELE:
"Küchenlicht rot": {"action":"control","domain":"light","entity_id":"light.wled_kuche","service":"turn_on","data":{"rgb_color":[255,0,0]}}
"Licht auf 50%": {"action":"control","domain":"light","entity_id":"light.wled_wohnzimmer","service":"turn_on","data":{"brightness_pct":50}}
"Temperaturen": {"action":"query","query_type":"status","sub_type":"temperatures"}
"Was ist an?": {"action":"query","query_type":"status","sub_type":"powered_on"}

FARBEN mit rgb_color:
rot=[255,0,0], gr��n=[0,255,0], blau=[0,0,255], gelb=[255,255,0],
weiß=[255,255,255], warmweiß=[255,244,229], kaltweiß=[200,220,255],
orange=[255,165,0], pink=[255,105,180], lila=[128,0,128]"""

CONF_CONTROL_TEMPERATURE = "control_temperature"
DEFAULT_CONTROL_TEMPERATURE = 0.7

CONF_CONTROL_MAX_TOKENS = "control_max_tokens"
DEFAULT_CONTROL_MAX_TOKENS = 2000

CONF_SELECTED_ENTITIES = "selected_entities"
CONF_SELECTED_AREAS = "selected_areas"

# ===== SENSOREN =====
CONF_ENABLE_SENSORS = "enable_sensors"
DEFAULT_ENABLE_SENSORS = True

# ===== ERWEITERTE EINSTELLUNGEN =====
CONF_HISTORY_LIMIT = "history_limit"
DEFAULT_HISTORY_LIMIT = 20

CONF_TIMEOUT = "timeout"
DEFAULT_TIMEOUT = 60

CONF_RETRY_COUNT = "retry_count"
DEFAULT_RETRY_COUNT = 0

# ===== LLM API =====
LLM7_BASE_URL = "https://api.llm7.io/v1"

# ===== UNTERSTÜTZTE DOMAINS =====
CONTROL_DOMAINS = [
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

SENSOR_DOMAINS = [
    "sensor",
    "binary_sensor",
    "weather",
]

SUPPORTED_DOMAINS = CONTROL_DOMAINS + SENSOR_DOMAINS

# ===== FARBEN =====
COLOR_PRESETS = {
    "rot": [255, 0, 0],
    "grün": [0, 255, 0],
    "blau": [0, 0, 255],
    "gelb": [255, 255, 0],
    "weiß": [255, 255, 255],
    "warmweiß": [255, 244, 229],
    "kaltweiß": [200, 220, 255],
    "orange": [255, 165, 0],
    "pink": [255, 105, 180],
    "lila": [128, 0, 128],
    "violett": [138, 43, 226],
    "türkis": [64, 224, 208],
    "cyan": [0, 255, 255],
}