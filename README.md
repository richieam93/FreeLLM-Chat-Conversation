# FreeLLM Chat Conversation Integration für Home Assistant

[![HACS Default](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

Diese Integration ermöglicht es dir, mit verschiedenen Large Language Models (LLMs) über die LLM7.io API in deiner Home Assistant Umgebung zu interagieren. Nutze natürliche Sprache, um dein Smart Home zu steuern, Informationen abzurufen und vieles mehr.

## Funktionen

- **Sprachsteuerung:** Steuere deine Geräte per Sprachbefehl.
- **Informationsabruf:** Rufe Informationen wie Wetter, Nachrichten oder andere Daten ab.
- **Automatisierung:** Automatisiere Aufgaben durch Konversation.
- **Integration:** Integriere die LLM-Funktionen in deine bestehenden Home Assistant Automatisierungen.
- **Unterstützung verschiedener Modelle:** Wähle aus verschiedenen LLM-Modellen von LLM7.io.

## Installation

1.  Füge dieses Repository zu [HACS](https://hacs.xyz/) als benutzerdefiniertes Repository hinzu.
    - URL: `https://github.com/richieam93/FreeLLM-Chat-Conversation`
    - Kategorie: Integration
2.  Suche und installiere die "FreeLLM Chat Conversation" Integration über HACS.
3.  Starte Home Assistant neu.
4.  Konfiguriere die Integration über das Home Assistant UI unter "Einstellungen" -> "Integrationen".

## Konfiguration

1.  Gehe zu "Einstellungen" -> "Integrationen" und klicke auf "+ Integration hinzufügen".
2.  Suche nach "FreeLLM Chat Conversation" und wähle es aus.
3.  Folge den Anweisungen zur Konfiguration der Integration. Du kannst das gewünschte LLM-Modell und den Prompt auswählen.

## Verwendung

Nach der Installation und Konfiguration kannst du die Integration verwenden, indem du den `conversation.process` Dienst in Home Assistant verwendest. Sende eine Anfrage mit dem Text, den du an das LLM senden möchtest, und die Integration wird die Antwort verarbeiten.

```yaml
service: conversation.process
data:
  text: "Wie ist das Wetter heute?"
