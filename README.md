# FreeLLM Chat Conversation Integration 🤖

💬 **Free LLM/AI Chat for Home Assistant**

💬 **Kostenloser LLM/AI Chat für Home Assistant**

[English](#-english) | [Deutsch](#-deutsch)

---

## ⚠️ Status

| Feature | Status |
|---------|--------|
| 🇩🇪 German UI | ✅ Ready |
| 🇬🇧 English UI | ✅ Ready |
| 🔌 HACS | ✅ Ready |

---

# 🇬🇧 English

This integration allows you to interact with various Large Language Models (LLMs) via the free LLM7.io API in your Home Assistant environment.

**No API key needed – completely free!**

---

## 🎯 What does it do?

Use natural language to control your smart home, get information, and more.

| Feature | Description |
|---------|-------------|
| 🗣️ **Voice Control** | Control devices with natural language |
| 📊 **Information** | Get weather, news, and other data |
| 🤖 **Automation** | Automate tasks through conversation |
| 🔗 **Integration** | Use in your existing automations |
| 🧠 **Multiple Models** | Choose from various LLM models |

---

## ✨ Use Cases

- "Turn on the living room lights"
- "What's the weather like today?"
- "Set a reminder for 5pm"
- "Create an automation for..."
- Ask anything!

---

## 📁 Ready-to-use Examples / Fertige Beispiele

In folder **[/Automatisierungen](https://github.com/richieam93/FreeLLM-Chat-Conversation/tree/main/Automatisierungen)** you'll find **18 automation examples**:

| Example | Description |
|---------|-------------|
| 🌅 Tägliche Morgenbegrüßung | Daily morning greeting with AI |
| 🎬 Film-Empfehlung am Abend | Movie recommendation in the evening |
| 🍳 Kochrezept basierend auf Kühlschrank | Recipe based on fridge contents |
| 🛡️ Intelligenter Einbruchalarm | Smart burglar alarm with AI analysis |
| 🚪 Intelligente Türklingel-Ansage | Smart doorbell announcement |
| ⚡ Intelligenter Energiebericht | Smart energy report |
| 🌡️ Intelligente Klimasteuerung | Smart climate control with explanation |
| 🏠 Intelligente Abwesenheits-Checkliste | Smart away-from-home checklist |
| 🚨 Intelligente Notfall-Benachrichtigung | Smart emergency notification |
| 👋 Personalisierte Willkommens-Nachricht | Personalized welcome message |
| 🪴 Pflanzenpflege-Erinnerung | Plant care reminder |
| 😴 Schlafenszeit-Erinnerung | Bedtime reminder |
| 🏃 Bewegungs-Erinnerung | Movement reminder for long sitting |
| 🛒 Einkaufslisten-Assistent | Shopping list assistant |
| 📊 Tages-Zusammenfassung | Daily summary script |
| 🔒 Täglicher Sicherheitsbericht | Daily security report |
| ❓ Universelles KI-Frage Script | Universal AI question script |
| ⚙️ Input Helpers | Input helpers for AI automations |

---

## 📋 Requirements

| Requirement | Details |
|-------------|---------|
| **Home Assistant** | 2023.1 or higher |
| **HACS** | Home Assistant Community Store |
| **Internet** | For LLM7.io API access |

---

## 🚀 Installation

1. Add this repository to HACS:
   - URL: github.com/richieam93/FreeLLM-Chat-Conversation
   - Category: Integration
2. Search and install "FreeLLM Chat Conversation" via HACS
3. Restart Home Assistant
4. Go to **Settings → Integrations → + Add Integration**
5. Search for "FreeLLM Chat Conversation"
6. Select your preferred LLM model and prompt

---

## ⚙️ Configuration

1. Go to **Settings → Integrations**
2. Click **"+ Add Integration"**
3. Search for **"FreeLLM Chat Conversation"**
4. Choose your LLM model
5. Configure the prompt
6. Done!

---

## 💡 Usage

After installation, use the conversation.process service:

Send a request with text to the LLM and the integration will process the response.

---

## 🔒 Privacy

This integration uses the LLM7.io API:

| Privacy | Details |
|---------|---------|
| **Anonymous** | Only anonymous usage data collected |
| **No personal data** | No personal data stored or used |
| **Free** | No API key or payment needed |

More info: llm7.io

---

## ⚠️ Disclaimer

- Responses may be inaccurate ("hallucinations")
- Don't rely on results for legal, medical, or financial advice
- Service provided "as is" without warranties
- LLM7.io may change models without notice

---

# 🇩🇪 Deutsch

Diese Integration ermöglicht es dir, mit verschiedenen Large Language Models (LLMs) über die kostenlose LLM7.io API in deiner Home Assistant Umgebung zu interagieren.

**Kein API-Key nötig – komplett kostenlos!**

---

## 🎯 Was macht es?

Nutze natürliche Sprache, um dein Smart Home zu steuern, Informationen abzurufen und vieles mehr.

| Feature | Beschreibung |
|---------|--------------|
| 🗣️ **Sprachsteuerung** | Geräte mit natürlicher Sprache steuern |
| 📊 **Informationen** | Wetter, Nachrichten und andere Daten abrufen |
| 🤖 **Automatisierung** | Aufgaben durch Konversation automatisieren |
| 🔗 **Integration** | In bestehende Automatisierungen einbinden |
| 🧠 **Mehrere Modelle** | Aus verschiedenen LLM-Modellen wählen |

---

## ✨ Anwendungsbeispiele

- "Schalte das Wohnzimmerlicht ein"
- "Wie ist das Wetter heute?"
- "Erinnere mich um 17 Uhr"
- "Erstelle eine Automatisierung für..."
- Frag einfach alles!

---

## 📁 Fertige Automatisierungen

Im Ordner **[/Automatisierungen](https://github.com/richieam93/FreeLLM-Chat-Conversation/tree/main/Automatisierungen)** findest du **18 fertige Beispiele**:

| Beispiel | Beschreibung |
|----------|--------------|
| 🌅 Tägliche Morgenbegrüßung | KI begrüsst dich morgens |
| 🎬 Film-Empfehlung am Abend | Filmvorschlag basierend auf Stimmung |
| 🍳 Kochrezept aus Kühlschrank | Rezept basierend auf vorhandenen Zutaten |
| 🛡️ Intelligenter Einbruchalarm | KI analysiert verdächtige Aktivitäten |
| 🚪 Intelligente Türklingel-Ansage | Smarte Türklingel mit KI |
| ⚡ Intelligenter Energiebericht | Täglicher Energieverbrauch-Report |
| 🌡️ Intelligente Klimasteuerung | Klima mit KI-Erklärung |
| 🏠 Abwesenheits-Checkliste | Checkliste wenn du gehst |
| 🚨 Notfall-Benachrichtigung | Smarte Notfall-Meldung |
| 👋 Willkommens-Nachricht | Personalisierte Begrüssung |
| 🪴 Pflanzenpflege-Erinnerung | Giess-Erinnerung |
| 😴 Schlafenszeit-Erinnerung | Zeit fürs Bett |
| 🏃 Bewegungs-Erinnerung | Steh mal auf! |
| 🛒 Einkaufslisten-Assistent | Smarte Einkaufsliste |
| 📊 Tages-Zusammenfassung | Was ist heute passiert? |
| 🔒 Täglicher Sicherheitsbericht | Alles sicher? |
| ❓ Universelles KI-Frage Script | Frag die KI alles |
| ⚙️ Input Helpers | Helfer für KI-Automatisierungen |

---

## 📋 Voraussetzungen

| Anforderung | Details |
|-------------|---------|
| **Home Assistant** | 2023.1 oder höher |
| **HACS** | Home Assistant Community Store |
| **Internet** | Für LLM7.io API Zugriff |

---

## 🚀 Installation

1. Repository zu HACS hinzufügen:
   - URL: github.com/richieam93/FreeLLM-Chat-Conversation
   - Kategorie: Integration
2. "FreeLLM Chat Conversation" über HACS suchen und installieren
3. Home Assistant neu starten
4. Gehe zu **Einstellungen → Integrationen → + Integration hinzufügen**
5. Suche nach "FreeLLM Chat Conversation"
6. LLM-Modell und Prompt auswählen

---

## ⚙️ Konfiguration

1. Gehe zu **Einstellungen → Integrationen**
2. Klicke **"+ Integration hinzufügen"**
3. Suche nach **"FreeLLM Chat Conversation"**
4. LLM-Modell auswählen
5. Prompt konfigurieren
6. Fertig!

---

## 💡 Verwendung

Nach der Installation nutze den conversation.process Dienst:

Sende eine Anfrage mit Text an das LLM und die Integration verarbeitet die Antwort.

---

## 🔒 Datenschutz

Diese Integration verwendet die LLM7.io API:

| Datenschutz | Details |
|-------------|---------|
| **Anonym** | Nur anonyme Nutzungsdaten |
| **Keine persönlichen Daten** | Keine persönlichen Daten gespeichert |
| **Kostenlos** | Kein API-Key oder Zahlung nötig |

Mehr Infos: llm7.io

---

## ⚠️ Haftungsausschluss

- Antworten können ungenau sein ("Halluzinationen")
- Nicht für rechtliche, medizinische oder finanzielle Beratung
- Service wird "wie besehen" bereitgestellt
- LLM7.io kann Modelle ohne Vorankündigung ändern

---

## ☕ Support this Project / Unterstütze dieses Projekt

This project is **free and open source**. Dieses Projekt ist **gratis und Open Source**.

If it helps you, I'd appreciate a coffee. Wenn es dir hilft, freue ich mich über einen Kaffee:

<a href="https://www.buymeacoffee.com/geartec" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a>

---

## 📝 Feedback & Support

- 🐛 **Issues:** [GitHub Issues](https://github.com/richieam93/FreeLLM-Chat-Conversation/issues)
- 💬 **Questions / Fragen:** Just open an issue!

---


Made with ❤️ in Switzerland 🇨🇭 | Entwickelt mit ❤️ in der Schweiz 🇨🇭


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

## Datenschutz
Diese Integration verwendet die LLM7.io API, um Anfragen an Large Language Models zu senden und Antworten zu empfangen. Bitte beachte folgende Punkte:

Anonyme Nutzungsdaten: LLM7.io sammelt anonyme Nutzungsdaten, um den Dienst zu verbessern.
Keine personenbezogenen Daten: Es werden keine personenbezogenen Daten von LLM7.io gespeichert oder verwendet.
LLM7.io Datenschutzrichtlinien: Bitte beachte die Nutzungsbedingungen und Datenschutzbestimmungen von LLM7.io.
Haftungsausschluss
Diese Integration verwendet den LLM7.io Dienst. Bitte beachte Sie die folgenden Hinweise:

Genauigkeit: Die von LLM7.io generierten Antworten können ungenau oder irreführend sein ("Halluzinationen"). Verlassen Sie sich nicht auf die Ergebnisse als rechtliche, medizinische, finanzielle oder andere professionelle Beratung. Sie müssen alle kritischen Ausgaben vor der Verwendung unabhängig überprüfen.
Service "wie besehen": Der Dienst wird "wie besehen" und "wie verfügbar" ohne jegliche Garantien (ausdrücklich oder stillschweigend) bereitgestellt, einschließlich der Marktgängigkeit, der Eignung für einen bestimmten Zweck und der Nichtverletzung von Rechten.
Haftungsbeschränkung: LLM7.io und seine Mitwirkenden haften nicht für direkte, indirekte, zufällige, besondere, Folge- oder Strafverluste oder -schäden (einschließlich Datenverlust, Betriebsunterbrechung oder entgangener Gewinn), die sich aus Ihrer Nutzung des Dienstes ergeben.
Datenschutz: Anonyme Nutzungsdaten werden gesammelt, um den Dienst zu verbessern. Es werden keine personenbezogenen Daten von LLM7.io gespeichert oder verwendet. Weitere Informationen finden Sie in den Nutzungsbedingungen und Datenschutzbestimmungen von LLM7.io.
Änderungen: LLM7.io kann Modelle und Funktionen jederzeit ohne Vorankündigung ändern, ersetzen oder zurückziehen.
Bekannte Probleme
Die Antworten von LLM7.io können manchmal ungenau oder irrelevant sein.
Die Integration kann bei hoher Auslastung der LLM7.io API langsam sein.
https://llm7.io/

## Beitrag
Beiträge sind willkommen! Bitte erstelle einen Pull Request mit deinen Änderungen.

## Lizenz
MIT License

Copyright (c) 2024 richieam93

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
