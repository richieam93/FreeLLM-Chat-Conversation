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
DEFAULT_CONTROL_PROMPT = """Du bist ein Smart Home Controller. Antworte AUSSCHLIESSLICH mit JSON!

REGELN:
1. NUR ein JSON-Objekt zurückgeben - KEIN Text davor oder danach!
2. KEINE Erklärungen, KEINE Markdown-Formatierung!
3. Verwende die EXAKTE entity_id aus der Geräteliste!
4. Bei Farbänderungen: service="turn_on" mit rgb_color im data-Feld!

STEUERUNG FORMAT:
{"action":"control","domain":"light","entity_id":"light.xxx","service":"turn_on","data":{"rgb_color":[R,G,B]}}

ABFRAGE FORMAT:
{"action":"query","query_type":"status","sub_type":"TYPE","area":"OPTIONAL_AREA"}

BEISPIELE:

Licht einschalten:
{"action":"control","domain":"light","entity_id":"light.wled_tv_mobel","service":"turn_on","data":{}}

Licht ausschalten:
{"action":"control","domain":"light","entity_id":"light.wled_tv_mobel","service":"turn_off","data":{}}

Licht auf GRÜN:
{"action":"control","domain":"light","entity_id":"light.wled_tv_mobel","service":"turn_on","data":{"rgb_color":[0,255,0]}}

Licht auf ROT mit 50% Helligkeit:
{"action":"control","domain":"light","entity_id":"light.wled_tv_mobel","service":"turn_on","data":{"rgb_color":[255,0,0],"brightness_pct":50}}

Licht auf BLAU:
{"action":"control","domain":"light","entity_id":"light.xxx","service":"turn_on","data":{"rgb_color":[0,0,255]}}

Alle Temperaturen:
{"action":"query","query_type":"status","sub_type":"temperatures"}

Temperaturen im Wohnzimmer:
{"action":"query","query_type":"status","sub_type":"temperatures","area":"Wohnzimmer"}

Was ist eingeschaltet:
{"action":"query","query_type":"status","sub_type":"powered_on"}

FARBEN (rgb_color):
- rot: [255,0,0]
- grün: [0,255,0]
- blau: [0,0,255]
- gelb: [255,255,0]
- weiß: [255,255,255]
- warmweiß: [255,244,229]
- orange: [255,165,0]
- pink: [255,105,180]
- lila: [128,0,128]
- türkis: [64,224,208]
- cyan: [0,255,255]

WICHTIG: Antworte NUR mit dem JSON-Objekt! Kein anderer Text!"""

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

# ===== FARBEN (RGB) =====
COLOR_PRESETS = {
    # Grundfarben
    "rot": [255, 0, 0],
    "grün": [0, 255, 0],
    "blau": [0, 0, 255],
    "gelb": [255, 255, 0],
    "cyan": [0, 255, 255],
    "magenta": [255, 0, 255],
    "weiß": [255, 255, 255],
    "schwarz": [0, 0, 0],
    
    # Warme Farben
    "warmweiß": [255, 244, 229],
    "orange": [255, 165, 0],
    "gold": [255, 215, 0],
    "koralle": [255, 127, 80],
    "lachs": [250, 128, 114],
    "pfirsich": [255, 218, 185],
    
    # Kalte Farben
    "kaltweiß": [200, 220, 255],
    "türkis": [64, 224, 208],
    "himmelblau": [135, 206, 235],
    "eisblau": [173, 216, 230],
    "marineblau": [0, 0, 128],
    
    # Violett/Pink
    "lila": [128, 0, 128],
    "violett": [138, 43, 226],
    "pink": [255, 105, 180],
    "rosa": [255, 182, 193],
    "lavendel": [230, 230, 250],
    "fuchsia": [255, 0, 255],
    
    # Grüntöne
    "mint": [152, 255, 152],
    "limette": [50, 205, 50],
    "olive": [128, 128, 0],
    "waldgrün": [34, 139, 34],
    "smaragd": [0, 201, 87],
    
    # Brauntöne
    "braun": [139, 69, 19],
    "beige": [245, 245, 220],
    "schokolade": [210, 105, 30],
    
    # Grautöne
    "grau": [128, 128, 128],
    "silber": [192, 192, 192],
    "dunkelgrau": [64, 64, 64],
    "hellgrau": [211, 211, 211],
}

# ===== FARBTEMPERATUREN (KELVIN) =====
COLOR_TEMPERATURES = {
    # Sehr warm (Kerzenlicht)
    "kerze": 1900,
    "kerzenlicht": 1900,
    "romantisch": 2000,
    
    # Warm (Glühbirne)
    "warmweiß": 2700,
    "warm": 2700,
    "gemütlich": 2700,
    "glühbirne": 2700,
    "abend": 2700,
    "entspannt": 2700,
    
    # Neutral
    "neutral": 4000,
    "neutralweiß": 4000,
    "normal": 4000,
    
    # Tageslicht
    "tageslicht": 5500,
    "tag": 5500,
    "natürlich": 5500,
    "morgen": 5000,
    
    # Kalt (Konzentration)
    "kaltweiß": 6500,
    "kalt": 6500,
    "konzentration": 6500,
    "arbeiten": 6500,
    "büro": 6000,
    "lesen": 5000,
    
    # Sehr kalt
    "blaulicht": 8000,
    "blau": 9000,
}

# ===== SZENEN-PRESETS =====
SCENE_PRESETS = {
    "sonnenuntergang": {
        "rgb_color": [255, 99, 71],
        "brightness_pct": 60,
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
    },
    "konzentration": {
        "brightness_pct": 100,
        "color_temp_kelvin": 6000,
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
        "color_temp_kelvin": 4000,
    },
    "morgen": {
        "brightness_pct": 70,
        "color_temp_kelvin": 4500,
    },
    "abend": {
        "brightness_pct": 50,
        "color_temp_kelvin": 2700,
    },
    "nacht": {
        "rgb_color": [255, 100, 50],
        "brightness_pct": 5,
    },
    "energie": {
        "brightness_pct": 100,
        "color_temp_kelvin": 6500,
    },
    "schlaf": {
        "rgb_color": [255, 100, 50],
        "brightness_pct": 5,
    },
}

# ===== HELLIGKEITS-PRESETS =====
BRIGHTNESS_PRESETS = {
    "aus": 0,
    "minimum": 1,
    "sehr dunkel": 5,
    "dunkel": 10,
    "gedimmt": 25,
    "niedrig": 30,
    "mittel": 50,
    "normal": 75,
    "hell": 85,
    "sehr hell": 95,
    "maximum": 100,
    "voll": 100,
}

# ===== KLIMA-PRESETS =====
CLIMATE_PRESETS = {
    "heizen": "heat",
    "kühlen": "cool",
    "auto": "auto",
    "aus": "off",
    "lüften": "fan_only",
    "entfeuchten": "dry",
}

# ===== COVER-PRESETS =====
COVER_PRESETS = {
    "öffnen": "open_cover",
    "schließen": "close_cover",
    "stoppen": "stop_cover",
    "auf": "open_cover",
    "zu": "close_cover",
    "stop": "stop_cover",
    "hoch": "open_cover",
    "runter": "close_cover",
}