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
