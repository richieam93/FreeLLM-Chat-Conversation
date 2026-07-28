# FreeLLM Chat Conversation

Home-Assistant-Konversationsintegration für die OpenAI-kompatible API von **LLM7.io**. Sie unterstützt anonymen Chat ohne API-Key, einen optionalen API-Key, dynamische Modelle, lokale Nutzungsstatistiken, Streaming, Bilder und Home Assistants offizielle Assist-Werkzeuge für Geräteaktionen.

Home Assistant conversation integration for the OpenAI-compatible **LLM7.io** API. It supports anonymous chat without an API key, an optional API key, dynamic models, local usage statistics, streaming, images, and Home Assistant's official Assist tools for device actions.

[Deutsch](#deutsch) · [English](#english)

## Projekt unterstützen / Support the project

Entwicklung, Tests und Dokumentation benötigen Zeit. Du kannst das Projekt hier unterstützen:

Development, testing, and documentation take time. You can support the project here:

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://www.buymeacoffee.com/geartec)

Direkter Link / Direct link: **https://www.buymeacoffee.com/geartec**

---

# Deutsch

## Überblick

FreeLLM Chat Conversation fügt **LLM7.io als externen KI-Dienst** zu Home Assistant hinzu. Die Integration selbst wird unabhängig von **richieam93** entwickelt und ist weder ein offizielles Produkt von LLM7.io noch von Home Assistant.

Der normale Chat funktioniert ohne API-Key. Bei der Einrichtung wird direkt auf das LLM7.io-Dashboard verlinkt, damit ein kostenloser Key erstellt werden kann. Ohne Key werden mindestens drei kompatible Modelle angeboten; abhängig vom aktuellen Live-Katalog können es mehr sein. Die tatsächliche Zahl wird während der Einrichtung und später über einen Sensor angezeigt, weil LLM7.io Modelle ohne Vorankündigung ändern kann.

### Verwendete externe Seiten

- Webseite: **https://llm7.io/**
- API-Key erstellen und verwalten: **https://dash.llm7.io/**
- Dokumentation: **https://docs.llm7.io/**
- Dienststatus: **https://status.llm7.io/**
- Modell-API: **https://api.llm7.io/v1/models**

## Hauptfunktionen

### Chat und Modelle

- Chat ohne API-Key
- optionaler API-Key mit direktem Link im Einrichtungsdialog
- dynamischer Modellkatalog statt fest eingebauter Modellnamen
- manueller Button zum Aktualisieren der Modelle
- automatische Aktualisierung in einem einstellbaren Intervall
- lokaler Cache und kleiner Offline-Notfallkatalog
- automatischer Ersatz, wenn ein Modell entfernt oder inkompatibel wird
- auswählbares bevorzugtes Ersatzmodell
- optional ausschließlich Modelle ohne nutzungsabhängige Abrechnung anzeigen
- Modellwahl direkt als Home-Assistant-Auswahlentität
- Filterung nach Chat, Tool Calling, Vision und Streaming
- Streaming-Antworten
- begrenzbarer Chatverlauf
- Bildanhänge für geeignete Modelle
- Retry- und Rate-Limit-Behandlung

### Home-Assistant-Gerätesteuerung und Geräteabfragen

- offizielle Home-Assistant-LLM-/Assist-Werkzeuge statt eigener Service-Heuristik
- Geräte über Namen, Bereiche und natürlich formulierte Befehle steuern
- mehrere unabhängige Geräteaktionen in einer Anfrage
- aufeinanderfolgende, voneinander abhängige Aktionen
- drei zusätzliche, ausschließlich lesende Werkzeuge für zuverlässige Geräteabfragen
- genaue und unscharfe Suche nach Entitätsname, Alias oder Entity-ID
- Filter nach Raum, Etage, Domäne, Integration, Hersteller, Modell, Geräteklasse, Zustand, Einheit und Erreichbarkeit
- einheitensichere Zahlenfilter, zum Beispiel Batterien unter 20 Prozent oder Temperaturen über einem Grenzwert
- Abfragen nach kürzlich geänderten Zuständen
- kompakte Raum- und Etagenübersichten mit Messwert-Minimum, -Maximum und -Durchschnitt
- klare Unterscheidung zwischen `unknown` und `unavailable`
- nur für Assist freigegebene Entitäten
- Validierung durch Home Assistant vor der Ausführung
- Begrenzung der Werkzeugrunden, Trefferlisten und Gesamtaktionen
- Erkennung identischer wiederholter Aktionen und Abfragen
- Abbruch endloser oder übergroßer Werkzeugketten
- klare Rückmeldung bei nicht gefundenen oder mehrdeutigen Zielen

**Wichtig:** LLM7.io dokumentiert Function Calling derzeit als kostenpflichtige Funktion. Deshalb ist die automatische Gerätesteuerung bei einer neuen anonymen Einrichtung standardmäßig deaktiviert. Chat ohne Key bleibt trotzdem möglich. Geräteaktionen können aktiviert werden, wenn ein geeigneter Zugang und ein werkzeugfähiges Modell vorhanden sind.

### Lokale Nutzungsstatistik

Die Integration zählt lokal in Home Assistant:

- Benutzeranfragen an den Konversationsagenten
- tatsächliche API-Anfragen einschließlich Wiederholungen und Werkzeugrunden
- erfolgreiche und fehlgeschlagene API-Anfragen
- Anfragen der letzten 24 Stunden, Stunde und Minute
- Eingabe-, Ausgabe- und Gesamttokens, soweit LLM7.io diese im API-Ergebnis meldet
- letzte Anfrage, Modell, Antwortzeit, HTTP-Status und letzten Fehler
- geschätzte Auslastung der veröffentlichten Referenzlimits

Diese Daten werden lokal gespeichert und können über einen Button oder den Dienst `freellm_chat.reset_usage_statistics` zurückgesetzt werden.

> **Keine offizielle Kontostandsanzeige:** LLM7.io stellt in der öffentlich dokumentierten API derzeit keinen persönlichen Verbrauchs- oder Restlimit-Endpunkt bereit. Die Sensoren zeigen deshalb nur lokal beobachtete Werte. Andere Clients, serverseitige Zählweisen, Cache-Tokens oder ein Pro-Tarif können abweichen.

## Veröffentlichte Referenzlimits

Stand der LLM7.io-Hauptseite: **28. Juli 2026**. LLM7.io kann Limits jederzeit ändern. Einzelne Dokumentationsseiten können zeitweise abweichende Werte zeigen; deshalb lassen sich alle lokalen Warnschwellen in den Integrationsoptionen anpassen.

| Zugriffsart | Tokens pro 24 Stunden | Anfragen pro Stunde | Anfragen pro Minute | Anfragen pro Sekunde |
|---|---:|---:|---:|---:|
| anonym, ohne Key | 500.000 | 60 | 10 | 1 |
| kostenloser API-Key | 1.000.000 | 250 | 60 | 2 |

Die Integration verwendet diese Werte nur als Referenz für lokale Warnungen. Der Wert `0` in den Nutzungseinstellungen bedeutet automatische Auswahl anhand des vorhandenen API-Keys. Eigene Token-, Stunden-, Minuten- und Sekundenlimits können eingetragen werden. Bei einem kostenpflichtigen Tarif können andere Regeln gelten.

## Voraussetzungen

- Home Assistant **2025.12.0 oder neuer**
- Internetzugang zu `api.llm7.io`
- für Geräteaktionen: eine Home-Assistant-LLM-API wie Assist und entsprechend freigegebene Entitäten
- für Function Calling gegebenenfalls ein passender LLM7.io-Zugang

## Installation mit HACS

1. HACS öffnen.
2. Zu **Integrationen** wechseln.
3. Dieses Repository als benutzerdefiniertes Repository hinzufügen.
4. Kategorie **Integration** auswählen.
5. **FreeLLM Chat Conversation** installieren.
6. Home Assistant neu starten.
7. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach `FreeLLM Chat` suchen.

## Manuelle Installation

1. Den Ordner `custom_components/freellm_chat` nach `/config/custom_components/freellm_chat` kopieren.
2. Home Assistant vollständig neu starten.
3. Die Integration über **Einstellungen → Geräte & Dienste** hinzufügen.

## Einrichtung

1. FreeLLM Chat als neue Integration öffnen.
2. Den API-Key leer lassen oder über den verlinkten LLM7.io-Dashboard-Link einen Key erstellen.
3. Den Hinweis zu externem Dienst, möglichen Halluzinationen und fehlender Gewähr bestätigen.
4. Ein Startmodell aus dem aktuellen Katalog wählen.
5. FreeLLM als bevorzugten Konversationsagenten in Assist auswählen.
6. Für Geräteaktionen nur die tatsächlich benötigten Entitäten für Assist freigeben.
7. Gerätesteuerung in den Integrationsoptionen erst nach einem ungefährlichen Test aktivieren.

## Entitäten

| Entität | Funktion |
|---|---|
| Chatmodell | aktives Modell direkt wechseln |
| Modelle aktualisieren | Live-Katalog sofort neu laden |
| Standardmodell auswählen | geeignetes Ersatzmodell wählen |
| Nutzungsstatistik zurücksetzen | lokale Zähler löschen |
| Modellkatalogstatus | Live, Cache, veralteter Cache oder Notfallkatalog |
| Verfügbare Modelle | Anzahl und Fähigkeiten der geladenen Modelle |
| Konversationsanfragen | Anzahl der Benutzeranfragen |
| API-Anfragen | Netzwerkaufrufe einschließlich Retries und Werkzeugrunden |
| Tokenverbrauch | lokal erfasste Eingabe-, Ausgabe- und Gesamttokens |
| Limitstatus | `ok`, `warning` oder `limit_reached` als lokale Schätzung |
| Letzte API-Anfrage | Zeitpunkt, Modell, Laufzeit, Status und Fehlerdetails |

Der Katalogsensor enthält zusätzlich direkte Links zu Webseite, Dashboard, Dokumentation und Statusseite des Anbieters.

## Dienste

### Modelle aktualisieren

```yaml
action: freellm_chat.refresh_models
data:
  config_entry_id: DEINE_CONFIG_ENTRY_ID
```

### Standardmodell auswählen

```yaml
action: freellm_chat.select_default_model
data:
  config_entry_id: DEINE_CONFIG_ENTRY_ID
```

### Lokale Nutzungsstatistik zurücksetzen

```yaml
action: freellm_chat.reset_usage_statistics
data:
  config_entry_id: DEINE_CONFIG_ENTRY_ID
```

Bei nur einer FreeLLM-Konfiguration kann `config_entry_id` weggelassen werden. Bei mehreren Konfigurationen muss sie angegeben werden.

## Konversationsagent verwenden

```yaml
action: conversation.process
data:
  agent_id: conversation.DEINE_FREELLM_ENTITAET
  text: "Wie ist der Zustand der freigegebenen Wohnzimmergeräte?"
response_variable: freellm_antwort
```

Der Antworttext befindet sich anschließend normalerweise unter:

```jinja2
{{ freellm_antwort.response.speech.plain.speech }}
```

## Erweiterte Geräteabfragen

Version 3.4.0 ergänzt die normalen Home-Assistant-Werkzeuge um eine lokale, nur lesende Abfrageschicht. Sie sendet keine zusätzlichen Home-Assistant-Daten an einen anderen Dienst als die ohnehin für die Chat-Anfrage verwendete LLM7.io-API. Vor der Übertragung werden ausschließlich Entitäten berücksichtigt, die für den Assistenten `conversation` freigegeben sind.

Die Abfrageschicht stellt dem Modell drei strukturierte Werkzeuge bereit:

| Werkzeugzweck | Geeignet für |
|---|---|
| einzelnes Gerät oder Sensor | Name, Alias oder Entity-ID mit optionalem Raum-/Etagenfilter |
| gefilterte Entitätsliste | Domäne, Integration, Hersteller, Modell, Geräteklasse, Zustand, Einheit, Erreichbarkeit, Zahlenbereich oder letzte Änderung |
| Raum-/Etagenübersicht | Zustandsverteilung, nicht erreichbare Geräte und zusammengefasste Messwerte |

Beispiele für natürliche Abfragen:

- „Welche Lichter sind im Erdgeschoss noch eingeschaltet?“
- „Welche Geräte im Wohnzimmer sind nicht erreichbar?“
- „Zeige alle Batteriesensoren unter 20 Prozent.“
- „Wie hoch sind Minimum, Maximum und Durchschnitt der Temperaturen im Obergeschoss?“
- „Welche Zustände haben sich in den letzten 30 Minuten geändert?“
- „Wie ist der genaue Zustand von Fenster Küche? Falls es mehrere Treffer gibt, nenne die Räume.“

Die Ergebnisse enthalten, soweit vorhanden, Entity-ID, Anzeigename, Raum, Etage, Domäne, Integration, Hersteller, Modell, Geräteklasse, Zustand, Einheit, ausgewählte nützliche Attribute sowie Zeitpunkte der letzten Änderung und Aktualisierung. Deutsche Zustands- und Geräteklassenbegriffe werden normalisiert. Zahlenwerte mit unterschiedlichen Einheiten werden nicht still miteinander verglichen. Große Trefferlisten werden begrenzt; der Assistent soll dann darauf hinweisen und eine genauere Abfrage vorschlagen.

**Datenschutz und Sicherheit:** Nicht für Assist freigegebene Entitäten werden nicht zurückgegeben. Die zusätzlichen Abfragewerkzeuge sind schreibgeschützt und können selbst keine Geräte verändern. Normale Assist-Aktionswerkzeuge bleiben getrennt und werden weiterhin durch Home Assistant validiert.

## Zuverlässige Licht- und Gerätesteuerung

Version 3.5.0 ergänzt eine robuste Zielauflösung für Lichter und häufige Geräte. Sie behebt insbesondere Werkzeugaufrufe, bei denen Modelle leere Werte wie `floor: ""` oder `device_class: []` erzeugen und Home Assistant darauf mit `InvalidSlotInfo` antwortet. Solche leeren optionalen Felder werden nun vor der Ausführung entfernt. Die normalen Home-Assistant-Werkzeuge bleiben erhalten und werden ebenfalls bereinigt.

Für Licht- und Geräteaktionen gelten klare Zielregeln:

| Formulierung | Auflösung |
|---|---|
| „wled_küche einschalten“ | genau das passend benannte, freigegebene Licht |
| „Essens-Lampe-02 einschalten“ | genau diese freigegebene Entität |
| „Küchenlicht einschalten“ | alle freigegebenen Lichter im Bereich Küche |
| „Licht in der Küche auf 40 Prozent“ | alle freigegebenen Küchenlichter mit Helligkeit 40 % |
| „alle Lampen auflisten“ | nur lesende Liste mit Name, Bereich, Zustand und Erreichbarkeit |
| „welche Wohnzimmergeräte sind an?“ | nur lesende gefilterte Zustandsabfrage |

Unterstützte standardisierte Aktionen umfassen unter anderem Ein-/Ausschalten und Umschalten, Lichthelligkeit, Farbe, Farbtemperatur, Effekte und Übergangszeit, Ventilator-Prozentwert, Abdeckung öffnen/schließen/stoppen/positionieren, Szenen und Skripte aktivieren, Tasten drücken sowie Staubsauger starten, stoppen oder zur Basis schicken. Nicht unterstützte Kombinationen werden zurückgemeldet und nicht durch geratenen Servicecode ersetzt.

Das Steuerwerkzeug liefert strukturierte Ergebnisse mit aufgelösten Zielen, Zustand vor und nach der Aktion, nicht erreichbaren Entitäten, Teilerfolgen und Fehlern. Mehrdeutige Namen führen zu keiner Aktion; stattdessen werden passende Namen und Bereiche für eine Rückfrage zurückgegeben. Ein fehlgeschlagener Aufruf darf einmal mit korrigierten Parametern wiederholt werden. Eine bereits erfolgreiche identische Aktion wird weiterhin blockiert.

Auch diese Steuerung ist strikt auf Entitäten begrenzt, die für Assist freigegeben sind. Für hausweite Aktionen muss die Benutzeranfrage ausdrücklich alle passenden Geräte betreffen; die interne Werkzeugstruktur verlangt dafür eine zusätzliche Bestätigung.

## Gerätesteuerung sicher einrichten

1. Unter **Einstellungen → Sprachassistenten → Entitäten freigeben** nur notwendige Entitäten aktivieren.
2. In den FreeLLM-Optionen **Home-Assistant-Steuerung** öffnen.
3. Gerätesteuerung aktivieren und die passende LLM-API auswählen.
4. Mit ungefährlichen Befehlen testen, zum Beispiel einer Lampe.
5. Sicherheitskritische Geräte wie Schlösser, Tore, Alarmanlagen, Kochgeräte oder Heizungen nicht unbeaufsichtigt steuern lassen.

### Gute Beispiele

- „Schalte die Stehlampe im Wohnzimmer ein.“
- „Setze die beiden Lampen im Büro auf 35 Prozent.“
- „Welche Lampen im Wohnzimmer sind gerade an? Verändere nichts.“
- „Zeige alle nicht erreichbaren Geräte im Obergeschoss.“
- „Welche Batteriesensoren liegen unter 20 Prozent?“
- „Wie hoch sind die Temperaturen im Schlafzimmer und Büro, jeweils mit Einheit?“
- „Schalte zuerst die Steckdose am Schreibtisch ein und danach die Arbeitslampe.“
- „Aktiviere die Szene Filmabend, aber ändere sonst nichts.“

### Schutzmechanismen

- Statusfragen führen nicht automatisch Änderungen aus.
- Nicht freigegebene Entitäten stehen dem Modell nicht zur Verfügung.
- Mehrdeutige oder sicherheitsrelevante Befehle sollen eine Rückfrage auslösen.
- Identische wiederholte Werkzeugaufrufe werden gestoppt.
- Werkzeugaufrufe pro Runde und pro Anfrage sind begrenzt.
- Große Werkzeugergebnisse werden gekürzt.
- Eine Geräteänderung wird nur als erfolgreich gemeldet, wenn Home Assistant sie bestätigt.

Trotzdem bleibt ein Sprachmodell probabilistisch. Automatische Geräteaktionen immer mit passenden Home-Assistant-Sicherheitsregeln, Zeitbedingungen und physischen Schutzmaßnahmen absichern.

## Einstellungen

### Chat, Kontext und Ausgabe

| Einstellung | Bedeutung |
|---|---|
| Chatmodell | aktives Modell |
| Kreativität | niedriger für präzisere, höher für kreativere Antworten |
| maximale Antwortlänge | maximale Ausgabetokens |
| maximale Verlaufsnachrichten | begrenzt übertragene Historie |
| maximale Werkzeugrunden | begrenzt Folgeaktionen |
| Streaming | zeigt Text während der Generierung |
| Bildeingaben | erlaubt Bilder der neuesten Benutzernachricht |
| Timeout | maximale Wartezeit pro API-Aufruf |
| Wiederholungen | erneute Versuche bei temporären Fehlern |
| Systemanweisung | Verhalten und zusätzliche Regeln |

### Modelle und Fallback

| Einstellung | Bedeutung |
|---|---|
| nur tokenfreie Modelle | blendet nutzungsabhängige Modelle aus |
| bevorzugtes Ersatzmodell | wird bei einem ungültigen aktiven Modell bevorzugt |
| Modelle automatisch aktualisieren | regelmäßiger Live-Abgleich |
| Aktualisierungsintervall | 1 bis 168 Stunden |

### Home-Assistant-Steuerung und Geräteabfragen

| Einstellung | Bedeutung |
|---|---|
| Geräteaktionen und Zustände verwenden | aktiviert Home Assistants offizielle LLM-Werkzeuge |
| erweiterte nur lesende Geräteabfragen | ergänzt genaue Suche, Filter sowie Raum- und Etagenübersichten |
| maximale Treffer pro Geräteabfrage | begrenzt Ergebnisgröße und Tokenverbrauch auf 5 bis 100 Treffer |
| Home-Assistant-LLM-APIs | bestimmt verfügbare Assist-Werkzeuge |

### Nutzung und Referenzlimits

| Einstellung | Bedeutung |
|---|---|
| Token-Referenzlimit pro 24 Stunden | lokale Warnschwelle, `0` verwendet den automatischen Anbieterwert |
| Anfrage-Referenzlimit pro Stunde | anpassbare lokale Warnschwelle |
| Anfrage-Referenzlimit pro Minute | anpassbare lokale Warnschwelle |
| Anfrage-Referenzlimit pro Sekunde | erkennt kurze lokale Lastspitzen |

Diese Werte beeinflussen nur Home-Assistant-Sensoren und ändern weder Tarif noch Limit beim Anbieter.

## Modellwechsel und Fallback

Die Integration prüft bei Start, Aktualisierung und vor einer Anfrage, ob das gewählte Modell verfügbar ist und die benötigten Fähigkeiten besitzt. Bei Bedarf wird ein passendes Ersatzmodell gewählt. Für eine Bildanfrage wird ein Vision-Modell benötigt; für Gerätesteuerung ein Modell mit Tool Calling.

LLM7.io empfiehlt für langfristig stabile Anwendungen Modellselektoren wie `default` oder `fast`, kann aber einzelne IDs ändern oder entfernen. Die Integration hält deshalb keine dauerhaft garantierte Liste fest.

## Bilder

- nur Bilder aus der neuesten Benutzernachricht
- JPEG, PNG, WebP und GIF
- maximal vier Bilder
- maximal 8 MiB pro Bild
- maximal 20 MiB zusammen
- automatischer Wechsel auf ein vision-fähiges Modell, wenn möglich

Bilder werden an den externen Anbieter übertragen. Keine vertraulichen oder personenbezogenen Bilder senden, wenn dies nicht ausdrücklich gewünscht ist.

## Beispiele

Im Ordner `examples` befinden sich bereinigte Vorlagen für:

- wiederverwendbaren Chat und Gerätebefehl
- geführte Licht- und Gerätetests (`examples/lichter_und_geraete_test.yaml`)
- Sprachausgabe
- tägliche Modellaktualisierung
- Warnung bei einem veralteten Modellkatalog
- lokale Nutzungs-/Limitwarnung (`examples/lokale_nutzungswarnung.yaml`)
- erweiterte schreibgeschützte Geräteabfrage
- tägliche Statuszusammenfassung
- zeitgesteuerten Gerätebefehl als Blueprint
- ereignisgesteuerten Gerätebefehl als Blueprint

Alle Platzhalter müssen an die eigene Installation angepasst werden.

## Datenschutz

Je nach Anfrage können an LLM7.io übertragen werden:

- der aktuelle Benutzertext
- ein begrenzter Gesprächsverlauf
- die Systemanweisung
- Beschreibungen der von Assist freigegebenen Werkzeuge und Entitäten
- Ergebnisse ausgeführter Werkzeuge
- Bilder der neuesten Nachricht

Der API-Key wird als Konfigurationswert gespeichert und in Diagnosedaten geschwärzt. Lokale Nutzungsstatistiken verbleiben in Home Assistant, bis sie zurückgesetzt oder die Integration entfernt werden.

## Disclaimer und Haftung

- Antworten können ungenau oder erfunden sein („Halluzinationen“).
- Ergebnisse nicht als rechtliche, medizinische oder finanzielle Beratung verwenden.
- Ergebnisse nicht als alleinige Grundlage für Notfälle oder sicherheitskritische Entscheidungen verwenden.
- Die Integration und der externe Dienst werden „wie besehen“ und ohne Gewähr bereitgestellt.
- LLM7.io kann Modelle, Funktionen, Preise, Verfügbarkeit und Limits ohne Vorankündigung ändern.
- Externe Ausfälle, API-Änderungen, Modellfehler und daraus entstehende Automationsfehler können nicht ausgeschlossen werden.
- Soweit gesetzlich zulässig, übernimmt **richieam93** keine Haftung für direkte oder indirekte Schäden aus Installation, Konfiguration, KI-Antworten oder Geräteaktionen.

Dies ist keine Rechtsberatung. Es gelten zusätzlich die aktuellen Bedingungen von LLM7.io und Home Assistant.

## Urheberrecht, Marken und Unabhängigkeit

- Integrationscode und Dokumentation: Copyright 2026 **richieam93**.
- Lizenz: MIT, siehe `LICENSE`.
- Zusätzliche Anbieter- und Haftungshinweise:  Anhang in `LICENSE`.
- LLM7.io, Home Assistant und andere Produktnamen oder Marken gehören ihren jeweiligen Rechteinhabern.
- Dieses Projekt enthält keinen kopierten LLM7.io-Servercode und verwendet nur die öffentlich erreichbare API-Schnittstelle.

## Aktualisierung auf 3.5.0

1. Backup der bisherigen Integration erstellen.
2. Ordner `custom_components/freellm_chat` ersetzen.
3. Home Assistant neu starten.
4. Integration öffnen und Optionen kontrollieren.
5. Modellkatalog einmal manuell aktualisieren.
6. Erweiterte Geräteabfragen und maximale Trefferzahl in den Steuerungsoptionen prüfen.
7. Neue Nutzungsentitäten gegebenenfalls im Entitätsregister aktivieren.
8. Erst „alle Lampen auflisten“, danach `wled_küche einschalten` und anschließend eine ungefährliche Bereichsaktion testen.

Bestehende Einträge werden migriert. Die Disclaimer-Bestätigung wird nur bei neuen Einrichtungen verlangt und blockiert bestehende Konfigurationen nicht.

## Fehlerbehebung

### Keine Modelle sichtbar

- Erreichbarkeit von `https://api.llm7.io/v1/models` prüfen.
- Anbieterstatus öffnen.
- Modelle über den Button aktualisieren.
- API-Key testweise entfernen oder neu eintragen.
- Katalogstatus und letzten Fehler ansehen.

### API-Key wird abgelehnt

- Key im LLM7.io-Dashboard neu erstellen.
- Leerzeichen am Anfang oder Ende entfernen.
- Bei weiterhin fehlerhaftem Key anonymen Chat ohne Key testen.

### Geräte werden nicht gefunden

- Entität für Assist freigeben.
- eindeutigen Namen und Bereich vergeben.
- richtige LLM-API auswählen.
- prüfen, ob das Modell Tool Calling unterstützt.
- beachten, dass LLM7.io Function Calling derzeit als kostenpflichtig dokumentiert.

### `InvalidSlotInfo` bei Licht- oder Geräteaktionen

Version 3.5.0 entfernt leere optionale Slots automatisch. Nach dem Update Home Assistant vollständig neu starten. Bleibt der Fehler bestehen, in den Assist-Details prüfen, ob wirklich die FreeLLM-Entität der Version 3.5.0 verwendet wird. Anschließend zuerst `alle Lampen auflisten` und dann den exakten zurückgegebenen Namen verwenden.

### Aktion wird nach einem Fehler wiederholt

Ein identischer fehlgeschlagener Aufruf darf nur einmal erneut versucht werden. Danach soll der Assistent nachfragen. Wird bereits der erste Aufruf weiterhin als Wiederholung beendet, Integration neu laden und einen neuen Chat beziehungsweise eine neue Conversation-ID beginnen, damit kein alter Werkzeugverlauf fortgeführt wird.

### Limitwarnung erscheint zu früh oder zu spät

Die Warnung basiert ausschließlich auf lokal beobachteten Anfragen. Andere Geräte, andere Anwendungen, providerseitige Tokenberechnung oder ein anderer Tarif werden nicht vollständig erfasst. Den echten Anbieterstatus und das Dashboard prüfen.

### API-Anfragen sind höher als Konversationsanfragen

Eine Benutzeranfrage kann mehrere API-Aufrufe erzeugen: Streaming-Verbindung, Wiederholung nach einem temporären Fehler oder zusätzliche Runden für Geräteaktionen.

### Nur Cache oder Notfallkatalog

Der Live-Abruf ist fehlgeschlagen. Chat kann mit vorhandenen Daten weiterlaufen, aber Modelle und Fähigkeiten können veraltet sein.

## Projektstruktur

```text
custom_components/freellm_chat/
├── __init__.py
├── api.py
├── button.py
├── config_flow.py
├── const.py
├── conversation.py
├── device_control.py
├── device_query.py
├── diagnostics.py
├── entity.py
├── fallback_models.json
├── manifest.json
├── model_manager.py
├── select.py
├── sensor.py
├── services.yaml
├── strings.json
├── translations/
└── usage_manager.py
examples/
LICENSE
NOTICE.md
README.md
CHANGELOG.md
```

## Lizenz

MIT License — Copyright 2026 **richieam93**.

Die MIT-Lizenz gilt für dieses Repository. Der zusätzliche Drittanbieterhinweis erläutert lediglich die Verwendung des externen Dienstes und ändert die MIT-Lizenz des Quellcodes nicht.

---

# English

## Overview

FreeLLM Chat Conversation adds **LLM7.io as an external AI service** to Home Assistant. The integration is independently developed by **richieam93** and is not an official product of LLM7.io or Home Assistant.

Normal chat works without an API key. During setup, the integration links directly to the LLM7.io dashboard where a free key can be created. Without a key, at least three compatible models are offered; the current live catalogue may contain more. The actual count is shown during setup and by a sensor because LLM7.io may change models without notice.

### External sites used

- Website: **https://llm7.io/**
- Create or manage an API key: **https://dash.llm7.io/**
- Documentation: **https://docs.llm7.io/**
- Service status: **https://status.llm7.io/**
- Model API: **https://api.llm7.io/v1/models**

## Main features

### Chat and models

- chat without an API key
- optional API key with a direct setup link
- dynamic catalogue instead of hard-coded model names
- manual model refresh button
- automatic refresh at a configurable interval
- local cache and compact bundled emergency catalogue
- automatic replacement when a model disappears or becomes incompatible
- selectable preferred fallback model
- optional filter for models marked as usable without usage billing
- direct model selection entity
- filtering by chat, tool calling, vision, and streaming capabilities
- streamed responses
- configurable conversation-history limit
- image attachments for compatible models
- retry and rate-limit handling

### Home Assistant device control and device queries

- official Home Assistant LLM/Assist tools instead of custom service heuristics
- natural device and area names
- multiple independent actions in one request
- sequential dependent actions
- three additional read-only tools for reliable device queries
- exact and fuzzy matching by entity name, alias, or entity ID
- filters for room, floor, domain, integration, manufacturer, model, device class, state, unit, and availability
- unit-safe numeric thresholds such as batteries below 20 percent or temperatures above a value
- queries for recently changed states
- compact room and floor summaries with measurement minimum, maximum, and average
- explicit distinction between `unknown` and `unavailable`
- only entities exposed to Assist
- Home Assistant validates action calls before execution
- limits for tool rounds, result lists, and total calls
- duplicate action and query detection
- protection against endless or oversized tool chains
- clear feedback for missing or ambiguous targets

**Important:** LLM7.io currently documents function calling as a paid feature. Automatic device control is therefore disabled by default for a new anonymous setup. Chat without a key still works. Device actions can be enabled when suitable access and a tool-capable model are available.

### Local usage statistics

The integration records locally in Home Assistant:

- user requests sent to the conversation agent
- actual API requests including retries and tool rounds
- successful and failed API requests
- requests during the last 24 hours, hour, and minute
- input, output, and total tokens when returned by LLM7.io
- last request, model, latency, HTTP status, and error
- estimated use of the published reference limits

The local data can be reset with a button or `freellm_chat.reset_usage_statistics`.

> **Not an official account balance:** LLM7.io currently provides no publicly documented personal usage or remaining-quota endpoint. Sensors therefore show only locally observed values. Other clients, provider counting, cached tokens, and Pro plans can differ.

## Published reference limits

LLM7.io main website checked on **July 28, 2026**. LLM7.io may change limits at any time. Individual documentation pages can temporarily show different values, so all local warning thresholds can be adjusted in the integration options.

| Access mode | Tokens per 24 hours | Requests per hour | Requests per minute | Requests per second |
|---|---:|---:|---:|---:|
| anonymous, no key | 500,000 | 60 | 10 | 1 |
| free API key | 1,000,000 | 250 | 60 | 2 |

These values are used only as local warning references. A value of `0` in usage settings automatically selects a reference based on whether an API key is configured. Custom token, hourly, minute, and second limits can be entered. Paid plans may use different rules.

## Requirements

- Home Assistant **2025.12.0 or newer**
- internet access to `api.llm7.io`
- for device actions: a Home Assistant LLM API such as Assist and exposed entities
- for function calling: suitable LLM7.io access may be required

## Installation with HACS

1. Open HACS.
2. Go to **Integrations**.
3. Add this repository as a custom repository.
4. Select category **Integration**.
5. Install **FreeLLM Chat Conversation**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration** and search for `FreeLLM Chat`.

## Manual installation

1. Copy `custom_components/freellm_chat` to `/config/custom_components/freellm_chat`.
2. Fully restart Home Assistant.
3. Add the integration under **Settings → Devices & services**.

## Setup

1. Add FreeLLM Chat.
2. Leave the key empty or use the linked LLM7.io dashboard to create one.
3. Acknowledge the external-service, hallucination, and no-warranty notice.
4. Select an initial model from the current catalogue.
5. Select FreeLLM as the preferred Assist conversation agent.
6. Expose only the entities required for device actions.
7. Enable device control only after testing a harmless command.

## Entities

| Entity | Purpose |
|---|---|
| Chat model | change the active model |
| Refresh models | immediately reload the live catalogue |
| Select default model | choose a suitable fallback |
| Reset usage statistics | delete local counters |
| Model catalogue status | live, cache, stale cache, or emergency catalogue |
| Available models | count and capability mix |
| Conversation requests | user-request count |
| API requests | network attempts including retries and tool rounds |
| Token usage | locally recorded input, output, and total tokens |
| Quota status | local `ok`, `warning`, or `limit_reached` estimate |
| Last API request | time, model, latency, status, and error details |

The catalogue sensor also exposes direct provider website, dashboard, documentation, and status links.

## Services

### Refresh models

```yaml
action: freellm_chat.refresh_models
data:
  config_entry_id: YOUR_CONFIG_ENTRY_ID
```

### Select the default model

```yaml
action: freellm_chat.select_default_model
data:
  config_entry_id: YOUR_CONFIG_ENTRY_ID
```

### Reset local usage statistics

```yaml
action: freellm_chat.reset_usage_statistics
data:
  config_entry_id: YOUR_CONFIG_ENTRY_ID
```

`config_entry_id` may be omitted when there is only one FreeLLM configuration. It is required when multiple configurations exist.

## Using the conversation agent

```yaml
action: conversation.process
data:
  agent_id: conversation.YOUR_FREELLM_ENTITY
  text: "What is the state of the exposed living-room devices?"
response_variable: freellm_response
```

The plain response is normally available at:

```jinja2
{{ freellm_response.response.speech.plain.speech }}
```

## Extended device queries

Version 3.4.0 adds a local read-only query layer to the normal Home Assistant tools. It does not send Home Assistant data to any additional service beyond the LLM7.io API already used for the chat request. Before data is transferred, only entities exposed to the `conversation` assistant are considered.

The query layer provides three structured capabilities:

| Purpose | Best for |
|---|---|
| single device or sensor | name, alias, or entity ID with optional room/floor filter |
| filtered entity list | domain, integration, manufacturer, model, device class, state, unit, availability, numeric range, or recent changes |
| room/floor summary | state distribution, unavailable devices, and aggregated measurements |

Natural-language examples:

- “Which lights are still on downstairs?”
- “Which living-room devices are unavailable?”
- “Show all battery sensors below 20 percent.”
- “Give me the minimum, maximum, and average temperatures upstairs.”
- “Which states changed during the last 30 minutes?”
- “What is the exact state of Kitchen Window? If there are several matches, list their rooms.”

Results can include the entity ID, display name, area, floor, domain, integration, manufacturer, model, device class, state, unit, selected useful attributes, and last-changed/last-updated timestamps. German state and device-class terms are normalized. Numeric values with different units are not silently compared. Large result sets are bounded; the assistant should mention truncation and suggest a narrower query.

**Privacy and safety:** Entities not exposed to Assist are never returned. The additional query tools are read-only and cannot change devices. Normal Assist action tools remain separate and continue to be validated by Home Assistant.

## Reliable light and device control

Version 3.5.0 adds robust target resolution for lights and common devices. It specifically fixes tool calls where a model generates empty values such as `floor: ""` or `device_class: []`, causing Home Assistant to return `InvalidSlotInfo`. Empty optional fields are now removed before execution. The normal Home Assistant tools remain available and are sanitized as well.

Light and device actions follow explicit target rules:

| Phrase | Resolution |
|---|---|
| “turn on wled_küche” | the single exposed light matching that name |
| “turn on Essens-Lampe-02” | that exact exposed entity |
| “turn on the kitchen light” | all exposed lights in the Kitchen area |
| “set the kitchen lights to 40 percent” | all exposed kitchen lights at 40% brightness |
| “list all lights” | a read-only list with name, area, state, and availability |
| “which living-room devices are on?” | a read-only filtered state query |

Supported standardized actions include on/off/toggle, light brightness, colour, colour temperature, effects and transitions, fan percentage, cover open/close/stop/position, scene and script activation, button presses, and vacuum start/stop/return-to-base. Unsupported action/domain combinations are reported instead of being replaced with guessed service calls.

The control tool returns resolved targets, state before and after the action, unavailable entities, partial success, and errors. Ambiguous names cause no action; matching names and areas are returned for clarification. A failed call may be retried once with corrected parameters. An identical action that already succeeded remains blocked.

This control path is also restricted to entities exposed to Assist. Home-wide actions require the user's request to explicitly cover all matching devices and the internal tool requires an additional confirmation flag.

## Safe device-control setup

1. Under **Settings → Voice assistants → Expose entities**, expose only required entities.
2. Open **Home Assistant control** in the FreeLLM options.
3. Enable device control and select the appropriate LLM API.
4. Test with a harmless device such as one lamp.
5. Do not allow unattended control of locks, doors, alarms, cooking devices, heating systems, or other safety-critical equipment.

### Good examples

- “Turn on the floor lamp in the living room.”
- “Set both office lights to 35 percent.”
- “Which living-room lights are currently on? Do not change anything.”
- “Show all unavailable devices upstairs.”
- “Which battery sensors are below 20 percent?”
- “What are the bedroom and office temperatures, including units?”
- “First turn on the desk socket, then turn on the work light.”
- “Activate the movie-night scene and change nothing else.”

### Safeguards

- state questions do not automatically change devices
- unexposed entities are unavailable to the model
- ambiguous or safety-relevant commands should trigger clarification
- duplicate tool calls are stopped
- tool calls per round and per request are limited
- oversized tool results are truncated
- a change is reported as successful only after Home Assistant confirms it

A language model remains probabilistic. Combine automatic actions with Home Assistant conditions, physical safeguards, and appropriate access controls.

## Settings

### Chat, context, and output

| Setting | Meaning |
|---|---|
| Chat model | active model |
| Creativity | lower for precision, higher for creativity |
| Maximum response length | output-token cap |
| Maximum history messages | limits transferred history |
| Maximum tool rounds | limits follow-up actions |
| Streaming | displays text while generated |
| Image input | permits images from the latest user message |
| Timeout | maximum wait per API call |
| Retry attempts | retries temporary failures |
| System instructions | behavior and additional rules |

### Models and fallback

| Setting | Meaning |
|---|---|
| token-free models only | hides usage-billed models |
| preferred fallback | preferred replacement for an invalid active model |
| update models automatically | periodic live reconciliation |
| refresh interval | 1 to 168 hours |

### Home Assistant control and device queries

| Setting | Meaning |
|---|---|
| use device actions and states | enables Home Assistant official LLM tools |
| extended read-only device queries | adds accurate search, filters, and room/floor summaries |
| maximum results per device query | limits result size and token use to 5 through 100 matches |
| Home Assistant LLM APIs | determines available Assist tools |

### Usage and reference limits

| Setting | Meaning |
|---|---|
| token reference limit per 24 hours | local warning threshold; `0` uses the automatic provider value |
| request reference limit per hour | adjustable local warning threshold |
| request reference limit per minute | adjustable local warning threshold |
| request reference limit per second | detects short local traffic bursts |

These values affect only Home Assistant sensors and do not change the provider plan or provider-side limits.

## Model selection and fallback

At startup, refresh, and before a request, the integration checks whether the selected model is available and supports required capabilities. It chooses a suitable fallback when needed. Images require vision; device control requires tool calling.

LLM7.io recommends selectors such as `default` or `fast` for long-lived applications and may phase out individual IDs. The integration therefore does not claim that any fixed model list is permanent.

## Images

- only images from the latest user message
- JPEG, PNG, WebP, and GIF
- maximum four images
- maximum 8 MiB per image
- maximum 20 MiB total
- automatic vision-capable fallback when possible

Images are sent to the external provider. Do not send confidential or personal images unless explicitly intended.

## Examples

The `examples` directory contains cleaned templates for:

- reusable chat and device commands
- guided light and device tests (`examples/lichter_und_geraete_test.yaml`)
- text-to-speech output
- daily model refresh
- stale-catalog warning
- local usage/quota warning (`examples/lokale_nutzungswarnung.yaml`)
- extended read-only device-query script
- daily state summary
- time-triggered device-command blueprint
- event-triggered device-command blueprint

All placeholders must be adapted to the local installation.

## Privacy

Depending on the request, LLM7.io may receive:

- the current user text
- limited conversation history
- system instructions
- descriptions of Assist-exposed tools and entities
- tool results
- images from the latest message

The API key is stored as configuration data and redacted from diagnostics. Local usage statistics remain in Home Assistant until reset or the integration is removed.

## Disclaimer and liability

- Responses may be inaccurate or fabricated (“hallucinations”).
- Do not use results as legal, medical, or financial advice.
- Do not use results as the sole basis for emergency or safety-critical decisions.
- The integration and external service are provided “as is” without warranties.
- LLM7.io may change models, features, pricing, availability, and limits without notice.
- External outages, API changes, model errors, and resulting automation errors cannot be excluded.
- To the maximum extent permitted by law, **richieam93** is not liable for direct or indirect damage arising from installation, configuration, AI responses, or device actions.

This is not legal advice. The current terms of LLM7.io and Home Assistant also apply.

## Copyright, trademarks, and independence

- Integration code and documentation: Copyright 2026 **richieam93**.
- License: MIT; see `LICENSE`.
- Additional provider and liability notice:  in `LICENSE`.
- LLM7.io, Home Assistant, and other product names or trademarks belong to their respective owners.
- This project contains no copied LLM7.io server code and communicates only through the publicly reachable API.

## Updating to 3.5.0

1. Back up the existing integration.
2. Replace `custom_components/freellm_chat`.
3. Restart Home Assistant.
4. Review the integration options.
5. Refresh the model catalogue once.
6. Review extended device queries and the maximum-result option.
7. Enable new usage entities if they are disabled in the entity registry.
8. Test “list all lights”, then a named light, and finally a harmless area-wide light action.

Existing entries are migrated. The disclaimer acknowledgement is required only for new setups and does not block existing configurations.

## Troubleshooting

### No models are visible

- Check `https://api.llm7.io/v1/models`.
- Open the provider status page.
- Press the refresh-models button.
- Remove or re-enter the API key.
- Inspect catalogue status and last error.

### The API key is rejected

- Create a new key in the LLM7.io dashboard.
- Remove leading or trailing whitespace.
- Test anonymous chat without a key.

### Devices are not found

- expose the entity to Assist
- give it an unambiguous name and area
- select the correct LLM API
- verify tool-calling support
- remember that LLM7.io currently documents function calling as paid

### `InvalidSlotInfo` during light or device actions

Version 3.5.0 removes empty optional slots automatically. Restart Home Assistant completely after updating. If the error remains, inspect the Assist details and verify that the FreeLLM 3.5.0 conversation entity is actually being used. First run `list all lights`, then use the exact returned name.

### An action is repeated after an error

An identical failed call may be attempted only once more. The assistant must then ask for clarification. If the first call is still immediately treated as a duplicate, reload the integration and start a new chat or conversation ID so an old tool history is not continued.

### The quota warning appears early or late

The warning uses only locally observed traffic. Other devices, other applications, provider-side token accounting, or another plan are not fully represented. Check the provider dashboard and status page.

### API requests exceed conversation requests

One user request can generate several API calls because of retries or additional device-action rounds.

### Only cache or emergency catalogue is available

The live request failed. Chat may continue with existing data, but models and capabilities may be outdated.

## Project structure

```text
custom_components/freellm_chat/
├── __init__.py
├── api.py
├── button.py
├── config_flow.py
├── const.py
├── conversation.py
├── device_control.py
├── device_query.py
├── diagnostics.py
├── entity.py
├── fallback_models.json
├── manifest.json
├── model_manager.py
├── select.py
├── sensor.py
├── services.yaml
├── strings.json
├── translations/
└── usage_manager.py
examples/
LICENSE
NOTICE.md
README.md
CHANGELOG.md
```

## License

MIT License — Copyright 2026 **richieam93**.

The MIT License applies to this repository. The separate third-party notice only explains use of the external service and does not modify the source-code MIT licence.
