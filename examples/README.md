# FreeLLM examples / FreeLLM-Beispiele

[Deutsch](#deutsch) · [English](#english)

## Deutsch

Diese Vorlagen verwenden die aktuelle Home-Assistant-Aktionssyntax mit `action:`, `conversation.process` und `response_variable`.

Vor der Verwendung:

1. FreeLLM als Konversationsagent einrichten.
2. Für Geräteaktionen nur die benötigten Entitäten für Assist freigeben.
3. Platzhalter wie `conversation.DEINE_FREELLM_ENTITAET`, `tts.DEINE_TTS_ENTITAET`, `media_player.DEIN_LAUTSPRECHER` und `notify.DEIN_BENACHRICHTIGUNGSDIENST` ersetzen.
4. Jede Automation zuerst mit einer ungefährlichen Anfrage testen.
5. Sicherheitskritische Geräte nicht unbeaufsichtigt durch ein Sprachmodell steuern.

### Dateien

- `freellm_chat_script.yaml`: wiederverwendbares Skript für Fragen, Statusabfragen und Gerätebefehle.
- `lichter_und_geraete_test.yaml`: geführte Tests für Lichtlisten, exakt benannte Lichter, Bereichslichter und Gerätezustände.
- `erweiterte_geraeteabfrage.yaml`: schreibgeschütztes Skript für gefilterte Zustands-, Raum-, Batterie- und Erreichbarkeitsabfragen.
- `freellm_mit_sprachausgabe.yaml`: sendet eine FreeLLM-Antwort an einen auswählbaren TTS-Dienst und Lautsprecher.
- `modelle_taeglich_aktualisieren.yaml`: täglicher Modellabgleich.
- `modellkatalog_status_melden.yaml`: meldet einen veralteten oder nicht erreichbaren Katalog.
- `lokale_nutzungswarnung.yaml`: meldet eine lokal geschätzte Annäherung an veröffentlichte Referenzlimits.
- `taegliche_statuszusammenfassung.yaml`: liest freigegebene Zustände ohne Geräteänderung und sendet die Antwort.
- `blueprints/zeitgesteuerter_geraetebefehl.yaml`: zeitgesteuerter Assist-Befehl.
- `blueprints/ereignisgesteuerter_geraetebefehl.yaml`: Assist-Befehl bei einem definierten Entitätszustand.

Für `erweiterte_geraeteabfrage.yaml` müssen die erweiterten Geräteabfragen in den Integrationsoptionen aktiviert sein. Die Abfrage berücksichtigt ausschließlich für Assist freigegebene Entitäten.

Die Nutzungswerte sind lokale Schätzungen und kein offizieller LLM7.io-Kontostand. Ersetze auch die Platzhalter der neuen Nutzungswarnung durch die tatsächlichen Sensor-Entitäten.

Die YAML-Dateien sind Vorlagen. Automationen können im YAML-Editor eingefügt oder in die eigene Paketstruktur übernommen werden. Blueprints nach `/config/blueprints/automation/richieam93/` kopieren und anschließend die Automationen neu laden.

## English

These templates use the current Home Assistant action syntax with `action:`, `conversation.process`, and `response_variable`.

Before use:

1. Configure FreeLLM as a conversation agent.
2. For device actions, expose only the required entities to Assist.
3. Replace placeholders such as `conversation.YOUR_FREELLM_ENTITY`, `tts.YOUR_TTS_ENTITY`, `media_player.YOUR_SPEAKER`, and `notify.YOUR_NOTIFICATION_ENTITY`.
4. Test every automation with a harmless request first.
5. Do not allow a language model to control safety-critical devices unattended.

### Files

- `freellm_chat_script.yaml`: reusable script for questions, state queries, and device commands.
- `lichter_und_geraete_test.yaml`: guided tests for light lists, exactly named lights, area lights, and device states.
- `erweiterte_geraeteabfrage.yaml`: read-only script for filtered state, room, battery, and availability queries.
- `freellm_mit_sprachausgabe.yaml`: sends a FreeLLM response to a selectable TTS service and speaker.
- `modelle_taeglich_aktualisieren.yaml`: daily model refresh.
- `modellkatalog_status_melden.yaml`: reports a stale or unreachable model catalogue.
- `lokale_nutzungswarnung.yaml`: reports a locally estimated approach to published reference limits.
- `taegliche_statuszusammenfassung.yaml`: reads exposed states without changing devices and sends the response.
- `blueprints/zeitgesteuerter_geraetebefehl.yaml`: time-triggered Assist command.
- `blueprints/ereignisgesteuerter_geraetebefehl.yaml`: Assist command when an entity reaches a configured state.

For `erweiterte_geraeteabfrage.yaml`, extended device queries must be enabled in the integration options. Queries include only entities exposed to Assist.

Usage values are local estimates, not an official LLM7.io account balance. Replace the usage-warning placeholders with the actual sensor entities as well.

The YAML files are templates. Automations can be pasted into the YAML editor or added to your own package structure. Copy blueprints to `/config/blueprints/automation/richieam93/` and reload automations afterward.
