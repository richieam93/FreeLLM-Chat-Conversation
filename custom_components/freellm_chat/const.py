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
2. EIN Gerät = eine entity_id
3. Mehrere Geräte nur bei "alle"

FORMATE:

Steuerung (einzeln):
{"action":"control","domain":"light|switch|climate|cover","entity_id":"ID","service":"turn_on|turn_off","data":{}}

Steuerung (mehrere):
{"action":"control_multiple","commands":[{...},{...}]}

Sensor-Abfrage:
{"action":"query","query_type":"sensor","entity_ids":["sensor.temp"]}

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
- climate_overview: Klima-Übersicht
- motion: Bewegungssensoren
- air_quality: Luftqualität
- all_sensors: Alle Sensoren
- device_summary: Zusammenfassung aller Geräte
- last_activity: Letzte Aktivitäten

BEISPIELE:
"Küchenlicht rot": {"action":"control","domain":"light","entity_id":"light.kuche","service":"turn_on","data":{"rgb_color":[255,0,0]}}
"Licht auf 50%": {"action":"control","domain":"light","entity_id":"light.wohnzimmer","service":"turn_on","data":{"brightness_pct":50}}
"Temperaturen": {"action":"query","query_type":"status","sub_type":"temperatures"}
"Was ist an?": {"action":"query","query_type":"status","sub_type":"powered_on"}
"Energie heute": {"action":"query","query_type":"status","sub_type":"energy"}

FARBEN mit rgb_color:
rot=[255,0,0], grün=[0,255,0], blau=[0,0,255], gelb=[255,255,0],
weiß=[255,255,255], warmweiß=[255,244,229], kaltweiß=[200,220,255],
orange=[255,165,0], pink=[255,105,180], lila=[128,0,128], violett=[138,43,226],
türkis=[64,224,208], cyan=[0,255,255], magenta=[255,0,255], gold=[255,215,0],
koralle=[255,127,80], lachs=[250,128,114], mint=[152,255,152], lavendel=[230,230,250]

FARBTEMPERATUR mit color_temp_kelvin:
kerze=2000, warmweiß=2700, neutral=4000, tageslicht=5500, kaltweiß=6500"""

CONF_CONTROL_TEMPERATURE = "control_temperature"
DEFAULT_CONTROL_TEMPERATURE = 0.3

CONF_CONTROL_MAX_TOKENS = "control_max_tokens"
DEFAULT_CONTROL_MAX_TOKENS = 500

CONF_SELECTED_ENTITIES = "selected_entities"
CONF_SELECTED_AREAS = "selected_areas"

# ===== SENSOREN =====
CONF_ENABLE_SENSORS = "enable_sensors"
DEFAULT_ENABLE_SENSORS = True

# ===== CACHING =====
CONF_ENABLE_CACHE = "enable_cache"
DEFAULT_ENABLE_CACHE = True

CONF_CACHE_DURATION = "cache_duration"
DEFAULT_CACHE_DURATION = 300

CONF_CACHE_CONTROL_RESPONSES = "cache_control_responses"
DEFAULT_CACHE_CONTROL_RESPONSES = False  # Steuerungsbefehle nicht cachen

# ===== PROMPT OPTIMIERUNG =====
CONF_OPTIMIZE_PROMPTS = "optimize_prompts"
DEFAULT_OPTIMIZE_PROMPTS = True

CONF_COMPRESSION_LEVEL = "compression_level"
DEFAULT_COMPRESSION_LEVEL = "auto"  # auto, none, medium, high

# ===== ERWEITERTE EINSTELLUNGEN =====
CONF_ENABLE_STATISTICS = "enable_statistics"
DEFAULT_ENABLE_STATISTICS = True

CONF_HISTORY_LIMIT = "history_limit"
DEFAULT_HISTORY_LIMIT = 20

CONF_TIMEOUT = "timeout"
DEFAULT_TIMEOUT = 30

CONF_RETRY_COUNT = "retry_count"
DEFAULT_RETRY_COUNT = 2

# ===== FARBEN =====
CONF_CUSTOM_COLORS = "custom_colors"
DEFAULT_CUSTOM_COLORS = {}

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
    "water_heater",
    "remote",
    "button",
    "siren",
]

SENSOR_DOMAINS = [
    "sensor",
    "binary_sensor",
    "weather",
    "device_tracker",
    "person",
    "sun",
    "zone",
]

SUPPORTED_DOMAINS = CONTROL_DOMAINS + SENSOR_DOMAINS

# ===== FARB-DEFINITIONEN =====
COLOR_PRESETS = {
    # Grundfarben
    "rot": [255, 0, 0],
    "red": [255, 0, 0],
    "grün": [0, 255, 0],
    "green": [0, 255, 0],
    "blau": [0, 0, 255],
    "blue": [0, 0, 255],
    "gelb": [255, 255, 0],
    "yellow": [255, 255, 0],
    "weiß": [255, 255, 255],
    "white": [255, 255, 255],
    "schwarz": [0, 0, 0],
    "black": [0, 0, 0],
    
    # Warme Farben
    "warmweiß": [255, 244, 229],
    "warm white": [255, 244, 229],
    "orange": [255, 165, 0],
    "gold": [255, 215, 0],
    "bernstein": [255, 191, 0],
    "amber": [255, 191, 0],
    "koralle": [255, 127, 80],
    "coral": [255, 127, 80],
    "lachs": [250, 128, 114],
    "salmon": [250, 128, 114],
    "pfirsich": [255, 218, 185],
    "peach": [255, 218, 185],
    "apricot": [251, 206, 177],
    
    # Kalte Farben
    "kaltweiß": [200, 220, 255],
    "cool white": [200, 220, 255],
    "cyan": [0, 255, 255],
    "türkis": [64, 224, 208],
    "turquoise": [64, 224, 208],
    "aqua": [0, 255, 255],
    "teal": [0, 128, 128],
    "himmelblau": [135, 206, 235],
    "sky blue": [135, 206, 235],
    "eisblau": [175, 238, 238],
    "ice blue": [175, 238, 238],
    "marineblau": [0, 0, 128],
    "navy": [0, 0, 128],
    
    # Violett/Pink
    "lila": [128, 0, 128],
    "purple": [128, 0, 128],
    "violett": [138, 43, 226],
    "violet": [138, 43, 226],
    "magenta": [255, 0, 255],
    "pink": [255, 105, 180],
    "rosa": [255, 182, 193],
    "rose": [255, 0, 127],
    "fuchsia": [255, 0, 255],
    "lavendel": [230, 230, 250],
    "lavender": [230, 230, 250],
    "pflaume": [221, 160, 221],
    "plum": [221, 160, 221],
    "orchidee": [218, 112, 214],
    "orchid": [218, 112, 214],
    
    # Grüntöne
    "mint": [152, 255, 152],
    "mintgrün": [152, 255, 152],
    "limette": [50, 205, 50],
    "lime": [50, 205, 50],
    "olive": [128, 128, 0],
    "waldgrün": [34, 139, 34],
    "forest green": [34, 139, 34],
    "seegrün": [46, 139, 87],
    "sea green": [46, 139, 87],
    "smaragd": [0, 201, 87],
    "emerald": [0, 201, 87],
    
    # Brauntöne
    "braun": [139, 69, 19],
    "brown": [139, 69, 19],
    "schokolade": [210, 105, 30],
    "chocolate": [210, 105, 30],
    "beige": [245, 245, 220],
    "sand": [244, 164, 96],
    "terrakotta": [204, 78, 92],
    "terracotta": [204, 78, 92],
    
    # Szenen-Farben
    "sonnenuntergang": [255, 99, 71],
    "sunset": [255, 99, 71],
    "sonnenaufgang": [255, 160, 122],
    "sunrise": [255, 160, 122],
    "romantisch": [255, 20, 147],
    "romantic": [255, 20, 147],
    "party": [148, 0, 211],
    "relax": [70, 130, 180],
    "konzentration": [255, 255, 240],
    "focus": [255, 255, 240],
    "nachtlicht": [255, 140, 0],
    "nightlight": [255, 140, 0],
    "kino": [25, 25, 112],
    "cinema": [25, 25, 112],
    "gaming": [0, 255, 127],
    "natur": [34, 139, 34],
    "nature": [34, 139, 34],
    "ozean": [0, 105, 148],
    "ocean": [0, 105, 148],
    "wald": [0, 100, 0],
    "forest": [0, 100, 0],
    "feuer": [255, 69, 0],
    "fire": [255, 69, 0],
}

# Farbtemperaturen in Kelvin
COLOR_TEMPERATURES = {
    "kerze": 2000,
    "candle": 2000,
    "warmweiß": 2700,
    "warm": 2700,
    "gemütlich": 2700,
    "cozy": 2700,
    "neutral": 4000,
    "normal": 4000,
    "tageslicht": 5500,
    "daylight": 5500,
    "kaltweiß": 6500,
    "cool": 6500,
    "konzentration": 6000,
    "focus": 6000,
}