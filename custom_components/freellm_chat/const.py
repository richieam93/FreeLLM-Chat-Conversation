"""Constants for the FreeLLM Chat integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "freellm_chat"
INTEGRATION_VERSION = "3.8.1"

CONF_API_KEY = "api_key"  # legacy/current LLM7 key
CONF_OVH_API_KEY = "ovh_api_key"
CONF_PROVIDER = "provider"
CONF_ACCEPT_DISCLAIMER = "accept_disclaimer"
CONF_CHAT_MODEL = "chat_model"
CONF_FALLBACK_MODEL = "fallback_model"
CONF_PROMPT = "prompt"
CONF_TEMPERATURE = "temperature"
CONF_MAX_TOKENS = "max_tokens"
CONF_TIMEOUT = "timeout"
CONF_RETRY_COUNT = "retry_count"
CONF_HISTORY_LIMIT = "history_limit"
CONF_MAX_TOOL_ITERATIONS = "max_tool_iterations"
CONF_ENABLE_STREAMING = "enable_streaming"
CONF_ENABLE_VISION = "enable_vision"
CONF_ENABLE_DEVICE_CONTROL = "enable_device_control"
CONF_TOKEN_SAVING_MODE = "token_saving_mode"
CONF_ENABLE_EXTENDED_DEVICE_QUERIES = "enable_extended_device_queries"
CONF_DEVICE_QUERY_MAX_RESULTS = "device_query_max_results"
CONF_AUTO_UPDATE_MODELS = "auto_update_models"
CONF_MODEL_REFRESH_INTERVAL = "model_refresh_interval"
CONF_ONLY_FREE_MODELS = "only_free_models"
CONF_REFERENCE_TOKEN_LIMIT_24H = "reference_token_limit_24h"
CONF_REFERENCE_REQUEST_LIMIT_HOUR = "reference_request_limit_hour"
CONF_REFERENCE_REQUEST_LIMIT_MINUTE = "reference_request_limit_minute"
CONF_REFERENCE_REQUEST_LIMIT_SECOND = "reference_request_limit_second"

PROJECT_URL = "https://github.com/richieam93/FreeLLM-Chat-Conversation"

DEFAULT_CHAT_MODEL = "codestral-latest"
DEFAULT_OVHCLOUD_MODEL = "gpt-oss-20b"
AUTO_FALLBACK_MODEL = "__auto__"
PREFERRED_FREE_MODELS = (
    "gpt-oss-20b",
    "codestral-latest",
    "minimax-m2.7",
)
DEFAULT_PROMPT = """Du bist ein zuverlässiger Assistent für Home Assistant.
Antworte in der Sprache des Benutzers klar, natürlich und kompakt.
Nenne keine internen Werkzeugnamen.

Geräte erkennen und abfragen:
- Nutze die bereitgestellten Home-Assistant-Werkzeuge selbstständig, sobald
  eine Anfrage Geräte, Lichter, Räume, Etagen, Szenen, Routinen oder aktuelle
  Zustände betrifft.
- Erfinde keine Entitäten, Bereiche, Etagen, Geräte oder Zustände. Nutze nur
  Treffer, die Home Assistant tatsächlich zurückgibt.
- Bei reinen Statusfragen führst du niemals eine Änderung aus.
- Bei Listen nennst du Name, Bereich, Zustand und Erreichbarkeit. Bei langen
  Listen weist du auf eine Begrenzung hin.

Geräte steuern:
- Ein ausdrücklich genannter Gerätename bezeichnet genau dieses Gerät.
- „Licht in der Küche“ oder „Küchenlicht“ ohne weiteren Eigennamen bezeichnet
  alle freigegebenen Lichter im Bereich Küche. Wähle nicht willkürlich nur eine
  einzelne Lampe aus.
- Verwende bei einem benannten Gerät nur den Namen beziehungsweise die Entity-ID
  und die Domäne. Verwende bei einer Raumaktion nur Bereich und Domäne.
- Sende keine leeren Strings, leeren Listen oder leeren Geräteklassen.
- Führe mehrere unabhängige Aktionen in derselben Anfrage aus. Bei voneinander
  abhängigen Aktionen wartest du das jeweilige Werkzeugergebnis ab.
- Wiederhole keine erfolgreich ausgeführte Aktion. Nach einem Fehler korrigierst
  du die Zielangabe oder fragst nach, statt denselben Aufruf unverändert zu senden.
- Behaupte eine Änderung nur, wenn Home Assistant sie erfolgreich bestätigt hat.
  Nenne nicht gefundene, nicht erreichbare oder mehrdeutige Ziele verständlich.
- Frage nach, wenn mehrere Geräte gleich gut passen oder eine sicherheitsrelevante
  Aktion nicht ausdrücklich verlangt wurde.

Antworten:
- Fasse erfolgreiche Aktionen und wichtige Ergebnisse kompakt zusammen.
- Bei fehlenden Informationen sagst du das offen, statt Werte zu erfinden.
- Verwende für Temperaturen, Prozentwerte und andere Messungen die Einheit aus
  Home Assistant und vermische keine unterschiedlichen Einheiten."""
DEFAULT_TEMPERATURE = 0.4
DEFAULT_MAX_TOKENS = 1200
DEFAULT_TIMEOUT = 60
DEFAULT_RETRY_COUNT = 1
DEFAULT_HISTORY_LIMIT = 40
DEFAULT_MAX_TOOL_ITERATIONS = 8
DEFAULT_ENABLE_STREAMING = True
DEFAULT_ENABLE_VISION = True
DEFAULT_ENABLE_DEVICE_CONTROL = True
DEFAULT_TOKEN_SAVING_MODE = True
DEFAULT_ENABLE_EXTENDED_DEVICE_QUERIES = True
DEFAULT_DEVICE_QUERY_MAX_RESULTS = 30
DEFAULT_AUTO_UPDATE_MODELS = True
DEFAULT_MODEL_REFRESH_INTERVAL = 24
DEFAULT_ONLY_FREE_MODELS = False
DEFAULT_REFERENCE_LIMIT = 0

# Token-saving mode keeps ordinary chat free of the large Home Assistant LLM
# prompt/tool catalogue and activates only the compact FreeLLM device tools when
# the current user message actually looks like a Home Assistant request.
LEAN_HISTORY_LIMIT = 12
LEAN_MAX_TOOL_ITERATIONS = 4
LEAN_MAX_TOKENS = 700
LEAN_DEFAULT_PROMPT = """Du bist ein hilfreicher Assistent in Home Assistant.
Antworte in der Sprache des Benutzers klar, natürlich und kompakt.
Erfinde keine Fakten oder Gerätezustände. Nenne keine internen Werkzeugnamen."""
LEAN_DEVICE_PROMPT = """Diese Nachricht betrifft Home Assistant. Nutze die verfügbaren Werkzeuge, wenn ein Zustand abgefragt oder ein Gerät gesteuert werden soll. Führe Änderungen nur am eindeutig verlangten Ziel aus und bestätige sie nur nach erfolgreichem Werkzeugergebnis. Bei Mehrdeutigkeit frage kurz nach."""

MODEL_CACHE_MAX_AGE = timedelta(days=7)
MODEL_REFRESH_MIN_HOURS = 1
MODEL_REFRESH_MAX_HOURS = 168
MODEL_REFRESH_THROTTLE = timedelta(minutes=5)
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
MAX_TOTAL_ATTACHMENT_BYTES = 20 * 1024 * 1024
MAX_IMAGE_ATTACHMENTS = 4
MAX_TOOL_CALLS_PER_ROUND = 12
MAX_TOTAL_TOOL_CALLS = 24
MAX_TOOL_RESULT_CHARS = 12000
MAX_RUNTIME_MODEL_FAILOVERS = 2
SUPPORTED_IMAGE_MIME_TYPES = (
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
)


SERVICE_REFRESH_MODELS = "refresh_models"
SERVICE_SELECT_DEFAULT_MODEL = "select_default_model"
SERVICE_RESET_USAGE_STATISTICS = "reset_usage_statistics"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
