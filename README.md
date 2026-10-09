# FreeLLM Chat Conversation

[![Version](https://img.shields.io/badge/version-3.8.1-blue)](#was-ist-neu-in-381)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.9%2B-41BDF5)](#voraussetzungen)
[![License](https://img.shields.io/badge/license-MIT-green)](#lizenz)

**FreeLLM Chat Conversation** ist eine unabhängige Home-Assistant-Custom-Integration, die externe OpenAI-kompatible KI-Dienste als Konversationsagent einbindet und Home-Assistant-Geräte sicher über Assist/Intent und strukturierte Tools steuern kann.

Version **3.8.1** unterstützt:

- **LLM7.io**
- **OVHcloud AI Endpoints**
- getrennte Zugangsdaten pro Provider
- lokalen Home-Assistant-Intent-Pfad für einfache Gerätebefehle
- einen standardmäßig aktivierten **Token-Sparmodus**
- Tool/Function Calling für komplexere Home-Assistant-Anfragen
- Streaming, lokale Nutzungsstatistiken und Diagnosewerte
- automatische Migration älterer FreeLLM-Konfigurationen und Modell-Caches

> **Unabhängiges Community-Projekt:** FreeLLM Chat Conversation ist kein offizielles Produkt von LLM7.io, OVHcloud oder Home Assistant. Die genannten Marken und Dienste gehören ihren jeweiligen Rechteinhabern.

[Deutsch](#deutsch) · [English](#english)

---

## Projekt unterstützen / Support the project

Entwicklung, Tests und Dokumentation benötigen Zeit. Wenn dir das Projekt hilft, kannst du es hier unterstützen:

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://www.buymeacoffee.com/geartec)

Direkter Link: **https://www.buymeacoffee.com/geartec**

---

# Deutsch

## Inhaltsverzeichnis

- [Überblick](#überblick)
- [Was ist neu in 3.8.1?](#was-ist-neu-in-381)
- [So verarbeitet FreeLLM eine Anfrage](#so-verarbeitet-freellm-eine-anfrage)
- [Provider](#provider)
- [Datenschutz: Was sieht die externe KI?](#datenschutz-was-sieht-die-externe-ki)
- [Hauptfunktionen](#hauptfunktionen)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Einrichtung](#einrichtung)
- [Einstellungen](#einstellungen)
- [Entitäten und Dienste](#entitäten-und-dienste)
- [Home-Assistant-Gerätesteuerung](#home-assistant-gerätesteuerung)
- [Token-Sparmodus](#token-sparmodus)
- [Nutzungsstatistik und Diagnose](#nutzungsstatistik-und-diagnose)
- [Update und Migration](#update-und-migration)
- [Fehlerbehebung](#fehlerbehebung)
- [Bekannte Einschränkungen](#bekannte-einschränkungen)
- [Projektstruktur](#projektstruktur)
- [Lizenz](#lizenz)

## Überblick

FreeLLM Chat Conversation stellt in Home Assistant einen Konversationsagenten bereit. Der Agent kann normale Chatfragen beantworten und – wenn aktiviert – mit Home Assistant interagieren.

Die Integration trennt dabei drei Wege:

```text
Benutzer
   |
   v
FreeLLM Chat
   |
   +-- einfacher Home-Assistant-Befehl
   |       |
   |       +--> lokaler Home-Assistant Intent/Assist
   |              |
   |              +--> verstanden: lokal ausführen, 0 Cloud-Requests
   |              |
   |              +--> nicht verstanden: kompakter Cloud-Tool-Pfad
   |
   +-- normaler Chat
   |       |
   |       +--> ausgewählter externer Provider
   |
   +-- komplexe Geräte-/Statusanfrage
           |
           +--> ausgewählter Provider + kompakte FreeLLM-Tools
                    |
                    +--> Tool wird lokal in Home Assistant ausgeführt
                    |
                    +--> Ergebnis zurück an denselben Provider
```

Es gibt **keinen automatischen Wechsel zwischen Providern**. Wenn OVHcloud ausgewählt ist, wird eine fehlgeschlagene Anfrage nicht heimlich an LLM7.io weitergereicht – und umgekehrt.

## Was ist neu in 3.8.1?

### 3.8.1

- behebt den Startfehler `NotImplementedError` beim Upgrade eines vorhandenen Modell-Caches
- migriert Modell-Cache-Versionen 1–3 automatisch auf das Multi-Provider-Format
- kennzeichnet alte Cache-Einträge korrekt als LLM7-Daten
- kein manuelles Löschen unter `/config/.storage` nötig

### Seit 3.8.0

- Providerwahl zwischen **LLM7.io** und **OVHcloud AI Endpoints**
- separates Feld für den **LLM7 API-Key**
- separates Feld für den **OVHcloud Access-Key**
- providerabhängige Endpoints, Modellkataloge, Limits und Request-Taktung
- OVHcloud-Modelle `gpt-oss-20b` und `gpt-oss-120b`
- kein Cross-Provider-Failover

### Seit 3.7.0

- Token-Sparmodus
- lokale Home-Assistant-Intent-Ausführung vor einem Cloud-Request
- kompakte Tool-Schemata statt des großen HA-Tool-Katalogs im Sparmodus
- Messung der geschätzten Request-Größe

### Seit 3.6.x

- Home-Assistant-2026.9-Kompatibilität über `probatio`
- Runtime-Daten in `ConfigEntry.runtime_data`
- robustere 429-/Retry-After-/5xx-Behandlung
- Request-Taktung gegen kurzfristige Rate Limits
- API-Erfolgsrate sowie Durchschnitts- und P95-Latenz

## So verarbeitet FreeLLM eine Anfrage

### 1. Normale Unterhaltung

Beispiel:

```text
Hallo, wie geht es dir?
```

Im standardmäßig aktivierten Token-Sparmodus werden **keine Home-Assistant-Tools** angehängt, wenn der Text nicht wie eine Geräte-/Statusanfrage aussieht.

Der aktive Provider erhält dann im Wesentlichen:

- die aktuelle Benutzernachricht
- einen kompakten Systemprompt
- einen begrenzten Chatverlauf
- optional eine eigene konfigurierte Systemanweisung
- Bilder nur dann, wenn Vision aktiviert ist und das Modell sie unterstützt

### 2. Einfacher Gerätebefehl

Beispiel:

```text
Küchenlicht einschalten
```

FreeLLM versucht im Token-Sparmodus zuerst Home Assistants **lokale Conversation-/Intent-Verarbeitung**.

Wenn Home Assistant den Befehl lokal versteht:

- kein Request an LLM7.io
- kein Request an OVHcloud
- keine Cloud-Tokens
- der externe Provider sieht den Befehl nicht

### 3. Komplexe oder lokal nicht verstandene Geräteanfrage

Wenn Home Assistant den Befehl lokal nicht auflösen kann, darf FreeLLM – sofern Gerätesteuerung aktiviert ist – den aktiven Provider mit kompakten Tool-Schemata verwenden.

Beispiele:

```text
Schalte alle Küchenlichter auf 35 Prozent und sage mir danach, welche noch an sind.
```

```text
Welche Batteriesensoren liegen unter 20 Prozent?
```

Das Modell kann anschließend ein strukturiertes Tool anfordern. **Die eigentliche Aktion läuft lokal in Home Assistant.** Das Tool-Ergebnis kann danach zur Formulierung der Antwort an denselben Provider zurückgesendet werden.

## Provider

### Providervergleich

| Merkmal | LLM7.io | OVHcloud AI Endpoints |
|---|---|---|
| OpenAI-kompatible Chat-API | Ja | Ja |
| In FreeLLM 3.8.1 auswählbar | Ja | Ja |
| Eigenes Key-Feld | Ja | Ja |
| Streaming | modellabhängig | Ja bei den eingebauten GPT-OSS-Modellen |
| Tool/Function Calling | modell-/tarifabhängig | Ja bei `gpt-oss-20b` und `gpt-oss-120b` |
| Modellkatalog | Live-API + Cache/Fallback | kleiner eingebauter Katalog |
| Provider-Failover zu anderem Dienst | Nein | Nein |

### LLM7.io

Verwendete Schnittstellen:

- Website: https://llm7.io/
- Token/Dashboard: https://dash.llm7.io/
- Modellkatalog: https://api.llm7.io/v1/models
- Chat Completions: `https://api.llm7.io/v1/chat/completions`
- Status: https://status.llm7.io/
- Terms: https://github.com/chigwell/llm7.io/blob/main/TERMS.md

**Stand 9. Oktober 2026:** Die aktuellen LLM7.io-Bedingungen nennen für den API-Zugriff einen über `dash.llm7.io` ausgegebenen Token. Für den kostenlosen Token werden aktuell bis zu **100.000 Tokens pro rollierenden 24 Stunden**, **250 Requests/Stunde**, **60 Requests/Minute** und **1 Request/Sekunde** genannt. LLM7.io weist darauf hin, dass Quoten je nach Nachfrage, Kapazität, Modell und Fair-Use reduziert werden können.

> **Wichtig für 3.8.1:** Die Integration akzeptiert aus Kompatibilitätsgründen weiterhin ein leeres LLM7-Key-Feld. Ob eine Anfrage ohne Token akzeptiert wird, entscheidet jedoch ausschließlich LLM7.io. Die aktuellen Anbieterbedingungen haben Vorrang vor älteren in FreeLLM hinterlegten Referenzwerten.

LLM7.io zählt bei tokenbegrenzten Zugängen **Input + Output** über ein rollierendes Zeitfenster. Systemprompt, Verlauf und Tooldefinitionen können daher deutlich mehr Tokens erzeugen als der sichtbare Benutzersatz allein.

### OVHcloud AI Endpoints

Verwendete Schnittstellen:

- Produktseite: https://www.ovhcloud.com/en/public-cloud/ai-endpoints/
- Katalog: https://www.ovhcloud.com/en/public-cloud/ai-endpoints/catalog/
- Dokumentation: https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-endpoints-getting-started
- Status: https://www.status-ovhcloud.com/
- OpenAI-kompatible Basis-URL: `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1`
- Chat Completions: `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions`

FreeLLM 3.8.1 enthält bewusst nur zwei OVHcloud-Modelle:

| Modell | Kontext | Function Calling | Reasoning | Streaming | Preis-Snapshot* |
|---|---:|---|---|---|---|
| `gpt-oss-20b` | 131k | Ja | Ja | Ja | 0,04 €/M Input · 0,15 €/M Output |
| `gpt-oss-120b` | 131k | Ja | Ja | Ja | 0,08 €/M Input · 0,40 €/M Output |

\* Preis-Snapshot der öffentlichen OVHcloud-Modellseiten, geprüft am 9. Oktober 2026. Preise, Modelle und Bedingungen können sich ändern.

OVHcloud dokumentiert aktuell folgende Rate Limits:

| Zugriff | Limit |
|---|---:|
| anonym | 2 Requests/Minute **pro IP und Modell** |
| mit API Access Key | 400 Requests/Minute **pro Public-Cloud-Projekt und Modell** |

Bei Überschreitung liefert OVHcloud HTTP `429`.

> Der normale OVHcloud-Einrichtungsweg für einen Access-Key benötigt ein Public-Cloud-Projekt; die Abrechnung richtet sich nach dem verwendeten Modell und dem OVHcloud-Konto. FreeLLM selbst verkauft keine Tokens und rechnet keine Providerkosten ab.

## Datenschutz: Was sieht die externe KI?

Das hängt vom Anfrageweg ab.

### Fall A – lokaler Gerätebefehl erfolgreich

Beispiel:

```text
Küchenlicht einschalten
```

Wenn Home Assistant den Befehl lokal versteht, sieht der externe Provider:

```text
nichts
```

Die Verarbeitung bleibt in Home Assistant.

### Fall B – normaler Chat im Token-Sparmodus

Der aktive Provider kann erhalten:

- aktuelle Chatnachricht
- kompakte Systemanweisung
- begrenzten Verlauf; im Sparmodus maximal 12 Nachrichten
- eine eigene konfigurierte Systemanweisung bzw. zusätzlichen Systemkontext
- Bilder der aktuellen Nachricht, falls aktiviert und vom Modell unterstützt

Home-Assistant-Gerätewerkzeuge werden bei normaler Unterhaltung **nicht** mitgesendet.

### Fall C – komplexe Home-Assistant-Anfrage über Cloud-Tools

Der aktive Provider kann zusätzlich erhalten:

- kompakte Tooldefinitionen für die benötigten Geräte-/Abfragefunktionen
- das vom Modell ausgewählte Ziel, z. B. Name, Raum oder Domäne
- Ergebnisse lokaler Tool-Aufrufe
- je nach Tool-Ergebnis z. B. Entity-ID, Anzeigename, Bereich, Etage, Zustand, Erreichbarkeit und Zustand vor/nach einer Aktion

Die Geräteauflösung selbst erfolgt in Home Assistant und ist auf für Assist freigegebene Entitäten begrenzt.

### Wenn der Token-Sparmodus deaktiviert wird

Dann kann Home Assistants größerer LLM-Kontext inklusive zusätzlicher Tool- und Entitätsbeschreibungen an den aktiven Provider weitergegeben werden. Für Datenschutz und Tokenverbrauch wird der Token-Sparmodus deshalb empfohlen.

### Zugangsdaten

- LLM7- und OVHcloud-Key werden getrennt gespeichert.
- Nur der Key des **aktiven** Providers wird für dessen Requests verwendet.
- Der inaktive Provider erhält seinen gespeicherten Key nicht.
- Diagnosedaten schwärzen beide Keys.
- Es gibt keinen automatischen Cross-Provider-Failover.

Prüfe vor der Nutzung mit personenbezogenen, vertraulichen oder geschäftlichen Daten die aktuellen Datenschutz-, Aufbewahrungs-, Vertrags- und Datenstandortbedingungen des gewählten Providers.

## Hauptfunktionen

### Chat

- OpenAI-kompatible Chat Completions
- Streaming-Antworten
- konfigurierbare Kreativität/Temperatur
- begrenzbare Antwortlänge
- begrenzbarer Chatverlauf
- optionaler eigener Systemprompt
- Bilder bei kompatiblen Modellen
- verständliche Providerfehler mit HTTP-Status und `Retry-After`, soweit vorhanden

### Modelle

- Modellwahl direkt als Home-Assistant-Auswahlentität
- bevorzugtes Fallback-Modell
- automatischer Modell-Fallback **nur innerhalb des aktiven Providers**
- LLM7-Live-Katalog mit lokalem Cache/Fallback
- OVHcloud-Katalog mit `gpt-oss-20b` und `gpt-oss-120b`
- Filter nach benötigten Modellfähigkeiten

### Home Assistant

- lokaler Intent-Pfad für einfache Befehle
- kompakte FreeLLM-Gerätesteuerungswerkzeuge
- zusätzliche nur lesende Geräteabfragen
- nur für Assist freigegebene Entitäten
- genaue und unscharfe Namenssuche
- Raum-/Etagenfilter
- Geräteaktionen mit Prüfung des Ergebnisses
- Schutz vor identischen wiederholten Tool-Aufrufen
- Begrenzung von Tool-Runden und Gesamtaktionen

### Monitoring

- lokale Request- und Tokenstatistiken
- API-Erfolgsrate der letzten 24 Stunden
- durchschnittliche API-Latenz
- P95-Latenz
- letzter HTTP-Status und Fehler
- geschätzte Promptgröße vor der Anfrage
- Modell- und Providerinformationen in der Diagnose

## Voraussetzungen

- Home Assistant **2026.9.0 oder neuer**
- Internetzugang zum gewählten externen Provider für Cloud-Chat
- für lokale Gerätebefehle: Home Assistant Conversation/Intent/Assist
- für komplexe Cloud-Geräteaktionen: Tool/Function-Calling-fähiges Modell
- für OVHcloud mit Access-Key: passender OVHcloud-Public-Cloud-Zugang

## Installation

### HACS

1. HACS öffnen.
2. **Integrationen** auswählen.
3. Dieses Repository als benutzerdefiniertes Repository vom Typ **Integration** hinzufügen.
4. **FreeLLM Chat Conversation** installieren.
5. Home Assistant vollständig neu starten.
6. **Einstellungen → Geräte & Dienste → Integration hinzufügen** öffnen.
7. Nach **FreeLLM Chat** suchen.

### Manuell

1. Backup von `/config/custom_components/freellm_chat` erstellen.
2. Ordner `custom_components/freellm_chat` aus diesem Repository nach `/config/custom_components/freellm_chat` kopieren.
3. Vorhandene Dateien ersetzen.
4. Home Assistant vollständig neu starten.
5. Integration über **Einstellungen → Geräte & Dienste** hinzufügen bzw. kontrollieren.

## Einrichtung

1. **FreeLLM Chat** als Integration hinzufügen.
2. Provider auswählen:
   - `LLM7.io`
   - `OVHcloud AI Endpoints`
3. Optional/entsprechend Provideranforderung den passenden Key eintragen.
4. Disclaimer bestätigen.
5. Startmodell auswählen.
6. FreeLLM als Konversationsagent in Assist auswählen.
7. Für Geräteaktionen nur benötigte Entitäten für Assist freigeben.
8. Token-Sparmodus aktiviert lassen.
9. Erst mit ungefährlichen Befehlen testen.

### Provider später wechseln

**Einstellungen → Geräte & Dienste → FreeLLM Chat → Konfigurieren → Anbieter und API-Zugänge**

Beim Providerwechsel bleiben beide Credentials getrennt gespeichert. Ein für den neuen Provider ungeeignetes Modell wird automatisch durch ein passendes Modell ersetzt.

## Einstellungen

### Anbieter und API-Zugänge

| Einstellung | Bedeutung |
|---|---|
| KI-Anbieter | LLM7.io oder OVHcloud AI Endpoints |
| LLM7 API-Key | nur für LLM7.io verwendet |
| OVHcloud Access-Key | nur für OVHcloud verwendet |

### Chat, Kontext und Ausgabe

| Einstellung | Bedeutung |
|---|---|
| Chatmodell | aktives Modell |
| Kreativität | niedrig = präziser, hoch = kreativer |
| maximale Antwortlänge | Obergrenze der Ausgabetokens |
| maximale Verlaufsnachrichten | begrenzt den übertragenen Verlauf |
| maximale Werkzeugrunden | begrenzt Folgeaktionen |
| Streaming | Text während der Generierung anzeigen |
| Bildeingaben | Bilder aus der aktuellen Nachricht zulassen |
| Timeout | maximale Dauer eines API-Aufrufs |
| Wiederholungen | Retries bei geeigneten temporären Fehlern |
| Systemanweisung | eigene Regeln/Verhalten |

### Modelle und Fallback

| Einstellung | Bedeutung |
|---|---|
| nur Modelle ohne zwingenden API-Key anzeigen | Zugriffsfilter; bedeutet nicht automatisch kostenlos |
| bevorzugtes Fallback-Modell | Ersatz für ungültiges/inkompatibles Modell |
| Modelle automatisch aktualisieren | Live-/Katalogabgleich |
| Aktualisierungsintervall | 1–168 Stunden |

### Home-Assistant-Steuerung

| Einstellung | Bedeutung |
|---|---|
| Geräteaktionen und Zustände verwenden | erlaubt lokale und Tool-basierte Geräteinteraktion |
| Home-Assistant-LLM-APIs | bestimmt verfügbare Assist-Funktionen |
| erweiterte nur lesende Geräteabfragen | Suche, Filter, Raum-/Etagenübersichten |
| maximale Treffer pro Geräteabfrage | reduziert große Ergebnisse und Tokenverbrauch |
| Token-Sparmodus | empfohlen; reduziert Cloud-Kontext und versucht Gerätebefehle zuerst lokal |

### Nutzung und Referenzlimits

Diese Werte sind **lokale Warnschwellen**, keine Providerkontostände.

| Einstellung | Bedeutung |
|---|---|
| Token-Referenzlimit/24 h | lokale Schätzung |
| Requests/Stunde | lokale Schätzung |
| Requests/Minute | lokale Schätzung |
| Requests/Sekunde | lokale Schätzung |

`0` bedeutet automatische Providerreferenz, sofern die Integration dafür einen Wert kennt.

> Provider ändern Limits unabhängig von FreeLLM. Bei Abweichungen ist immer die aktuelle Providerdokumentation maßgeblich. Für LLM7.io kann es sinnvoll sein, die lokale Token-Warnschwelle manuell an den aktuell verwendeten Tarif anzupassen.

## Entitäten und Dienste

### Entitäten

| Typ | Entität | Zweck |
|---|---|---|
| Select | Chatmodell | aktives Modell wechseln |
| Select | Fallback-Modell | bevorzugtes Ersatzmodell oder Automatik |
| Button | Modelle aktualisieren | Katalog des aktiven Providers aktualisieren |
| Button | Standardmodell auswählen | passendes Standard-/Fallback-Modell wählen |
| Button | Lokale Nutzungsstatistik zurücksetzen | nur lokale Zähler löschen |
| Sensor | Modellkatalog-Status | Live/Cache/veraltet/Notfallkatalog |
| Sensor | Verfügbare Modelle | Anzahl/Fähigkeiten |
| Sensor | Konversationsanfragen | Benutzeranfragen |
| Sensor | API-Anfragen | echte Netzwerkversuche |
| Sensor | Tokenverbrauch | Provider-Tokens + Promptschätzung |
| Sensor | Lokale Limit-Schätzung | OK/Warnung/Referenzlimit erreicht |
| Sensor | Letzte API-Anfrage | Zeit, Modell, Status, Fehler |
| Sensor | API-Erfolgsrate (24 h) | prozentualer Erfolg |
| Sensor | API-Latenz (24 h Durchschnitt) | Durchschnitt + P95 als Attribut |

### Home-Assistant-Dienste

#### Modelle aktualisieren

```yaml
action: freellm_chat.refresh_models
data:
  config_entry_id: DEINE_CONFIG_ENTRY_ID
```

#### Standardmodell auswählen

```yaml
action: freellm_chat.select_default_model
data:
  config_entry_id: DEINE_CONFIG_ENTRY_ID
```

#### Lokale Nutzungsstatistik zurücksetzen

```yaml
action: freellm_chat.reset_usage_statistics
data:
  config_entry_id: DEINE_CONFIG_ENTRY_ID
```

Bei nur einer FreeLLM-Konfiguration kann `config_entry_id` weggelassen werden.

## Home-Assistant-Gerätesteuerung

### Unterstützte Zielarten

- exakte Entity-ID
- Gerätename
- unscharfer Name
- Bereich/Raum
- Etage
- Domäne
- alle passenden freigegebenen Geräte eines Bereichs

### Unterstützte Aktionen

Unter anderem:

- Licht/Schalter/Ventilator ein, aus, umschalten
- Lichthelligkeit
- Lichtfarbe
- Farbtemperatur
- Effekt und Übergangszeit
- Cover öffnen/schließen/stoppen/Position
- Ventilator-Prozentwert
- Szenen und Skripte aktivieren
- Buttons drücken
- Staubsauger starten/stoppen/zur Basis

Nicht unterstützte Kombinationen werden zurückgemeldet statt durch geratenen Servicecode ersetzt.

### Nur lesende Abfragen

Die erweiterten Abfragewerkzeuge können unter anderem nach folgenden Kriterien filtern:

- Name/Alias/Entity-ID
- Raum und Etage
- Domäne
- Integration
- Hersteller und Modell
- Geräteklasse
- Zustand
- Einheit
- Erreichbarkeit
- numerischer Wertebereich
- letzte Zustandsänderung

Beispiele:

```text
Welche Lampen sind im Erdgeschoss noch an?
```

```text
Welche Batteriesensoren liegen unter 20 Prozent?
```

```text
Welche Geräte im Wohnzimmer sind nicht erreichbar?
```

```text
Wie hoch sind Minimum, Maximum und Durchschnitt der Temperaturen oben?
```

## Token-Sparmodus

Der Token-Sparmodus ist standardmäßig aktiviert und für die meisten Installationen empfohlen.

Er begrenzt intern zusätzlich:

- Verlauf auf maximal **12 Nachrichten**
- Tool-Runden auf maximal **4**
- Antwortbudget auf maximal **700 Tokens**

Normale Chatfragen erhalten keine Home-Assistant-Tools. Geräte-/Statusanfragen bekommen nur die kompakten FreeLLM-Tools.

Dadurch sinken:

- Input-Tokens
- Kosten bei kostenpflichtigen Providern
- Risiko eines Tokenlimits
- übertragener Home-Assistant-Kontext
- Wahrscheinlichkeit unnötiger Tool-Aufrufe

Wenn der Sparmodus ausgeschaltet wird, gelten wieder die konfigurierten allgemeinen Obergrenzen und Home Assistants größerer LLM-Kontext kann einbezogen werden.

## Nutzungsstatistik und Diagnose

FreeLLM speichert die Statistik **lokal in Home Assistant**.

### Tokenverbrauch-Sensor

Wichtige Attribute:

```text
last_context_mode
last_tool_count
last_message_count
last_payload_chars
last_estimated_input_tokens
last_input_tokens
last_output_tokens
last_total_tokens
```

`last_estimated_input_tokens` ist nur eine lokale Näherung vor dem Request. Maßgeblich für Providerabrechnung/-quota sind die vom Provider gezählten Tokens.

### Qualitätswerte

- erfolgreiche/fehlgeschlagene Requests
- Erfolgsrate 24 h
- durchschnittliche Latenz 24 h
- P95-Latenz 24 h
- letzter HTTP-Status
- letzter Fehler
- aktiver Provider
- aktives Modell

### Diagnosedaten

Die Home-Assistant-Diagnose schwärzt beide Provider-Keys und enthält technische Informationen wie:

- Provider
- Zugriffsart
- Modell und Fähigkeiten
- Katalogstatus
- lokale Nutzungswerte
- API-Qualitätsmetriken

## Update und Migration

### Von 3.7.x / 3.6.x / 3.5.x

Beim Upgrade auf 3.8.1 werden bestehende Einträge migriert:

- bestehender Provider wird zunächst **LLM7.io**
- vorhandener LLM7-Key bleibt erhalten
- OVHcloud-Key wird separat ergänzt
- vorhandene Optionen bleiben soweit möglich erhalten
- Modellwahl wird bei einem Providerwechsel automatisch korrigiert
- alte Modell-Caches werden automatisch migriert

### Storage-Fix 3.8.1

3.8.0 konnte bei einem vorhandenen alten Modell-Cache mit folgendem Fehler abbrechen:

```text
NotImplementedError
```

3.8.1 implementiert die dafür benötigte Home-Assistant-Store-Migration. Ein manuelles Löschen von `.storage` ist nicht nötig.

## Fehlerbehebung

### HTTP 429 bei LLM7.io

Beispiel:

```text
Daily token quota exceeded
```

Das bedeutet nicht zwingend, dass viele sichtbare Chatnachrichten geschrieben wurden. Provider zählen auch:

- Systemprompt
- Verlauf
- Tooldefinitionen
- Tool-Ergebnisse
- Input- und Output-Tokens

LLM7.io verwendet für den kostenlosen Token aktuell ein **rollierendes 24-Stunden-Fenster**. Ein `Retry-After` von vielen Stunden kann daher korrekt sein.

Empfehlungen:

- Token-Sparmodus aktiv lassen
- Verlauf klein halten
- unnötige Tool-Aufrufe vermeiden
- LLM7-Dashboard prüfen
- aktuellen Provider-Tarif/Quota prüfen

### HTTP 429 bei OVHcloud ohne Key

OVHcloud dokumentiert anonym nur **2 Requests/Minute pro IP und Modell**.

Ein Tool-Dialog kann mehrere Requests benötigen. Außerdem gilt das anonyme Limit für die öffentliche IP; bei gemeinsam genutzten IP-Adressen kann ein Limit auch durch andere Nutzung derselben IP beeinflusst werden.

Empfehlungen:

- `Retry-After` abwarten
- einfachen Gerätebefehl lokal über Assist verwenden
- für regelmäßige Nutzung einen OVHcloud Access-Key verwenden
- bei einem Access-Key Kosten/Verbrauch im OVHcloud-Projekt beobachten

### HTTP 401 / 403

Der aktive Provider lehnt das Credential ab.

- prüfen, ob der Key im richtigen Providerfeld steht
- Leerzeichen entfernen
- Gültigkeit/Ablaufdatum prüfen
- bei OVHcloud Projekt- und Zahlungsanforderungen prüfen
- bei LLM7.io aktuellen Token im Dashboard erstellen

### HTTP 502 / 503 / 5xx

Meist ein temporärer Provider-/Upstreamfehler.

FreeLLM kann innerhalb des **gleichen Providers** ein kompatibles Modell versuchen, solange noch keine gestreamte Antwort begonnen hat. Ein automatischer Wechsel zum anderen Provider findet nicht statt.

### Keine Modelle sichtbar

**LLM7.io:**

- `https://api.llm7.io/v1/models` erreichbar?
- Statusseite prüfen
- Modelle manuell aktualisieren
- Cache-/Katalogstatus ansehen

**OVHcloud:**

- 3.8.1 verwendet den eingebauten Katalog `gpt-oss-20b` / `gpt-oss-120b`
- Providerauswahl kontrollieren
- Integration neu laden

### Gerät wird nicht gefunden

- Entität für Assist freigeben
- eindeutigen Anzeigenamen vergeben
- Bereich zuweisen
- Gerätesteuerung aktivieren
- passende Home-Assistant-LLM-API auswählen
- Token-Sparmodus zunächst aktiviert lassen

### Lokaler Gerätebefehl funktioniert nicht

Die lokale Intent-Erkennung kann nur Befehle ausführen, die Home Assistant versteht. Bei komplexeren oder unscharfen Formulierungen fällt FreeLLM auf den Cloud-Tool-Pfad zurück, sofern aktiviert.

### `InvalidSlotInfo`

FreeLLM bereinigt leere optionale Tool-Parameter wie leere Strings, Listen und Geräteklassen. Falls der Fehler weiterhin erscheint:

1. Home Assistant vollständig neu starten.
2. neue Conversation beginnen.
3. Ziel mit eindeutigem Namen und Raum testen.
4. Diagnosedaten/Log prüfen.

## Bekannte Einschränkungen

- Provider können Modelle, Limits, Preise und Zugangsregeln jederzeit ändern.
- LLM7.io hat seine Token-/Zugangsregeln nach älteren FreeLLM-Versionen geändert; aktuelle Providerbedingungen sind maßgeblich.
- OVHcloud-anonym ist mit 2 Requests/Minute/IP/Modell für lange Tool-Ketten nur eingeschränkt geeignet.
- der OVHcloud-Modellkatalog ist in 3.8.1 bewusst auf zwei getestete GPT-OSS-Modelle begrenzt
- die eingebauten OVHcloud-GPT-OSS-Modelle sind Textmodelle; Vision ist dort nicht verfügbar
- lokale Prompt-/Quota-Sensoren sind Schätzungen und kein offizieller Providerkontostand
- ein Sprachmodell kann falsche, unvollständige oder erfundene Antworten liefern
- sicherheitskritische Geräte sollten zusätzlich durch Home-Assistant-Regeln und physische Schutzmechanismen abgesichert werden

## Sicherheitsempfehlungen

- nur notwendige Entitäten für Assist freigeben
- Schlösser, Tore, Alarmanlagen, Kochgeräte und ähnliche kritische Systeme nicht unbeaufsichtigt durch ein LLM steuern lassen
- sensible Daten nicht in Cloud-Chats senden, wenn dies nicht ausdrücklich gewünscht ist
- API-Keys geheim halten
- Providerkonten mit geeigneten Kosten-/Usage-Limits absichern
- vor Updates Backup von `/config/custom_components/freellm_chat` erstellen

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
├── provider.py
├── runtime.py
├── select.py
├── sensor.py
├── services.yaml
├── strings.json
├── translations/
└── usage_manager.py
examples/
LICENSE
README.md
CHANGELOG.md
hacs.json
```

## Support und Fehlerberichte

Bei einem Fehler sind folgende Informationen hilfreich:

- Home-Assistant-Version
- FreeLLM-Version
- aktiver Provider
- aktives Modell
- HTTP-Status
- Servermeldung / `Retry-After`
- relevante Home-Assistant-Logs
- Diagnoseexport, **nach Prüfung auf persönliche Daten**

Keine API-Keys oder andere Geheimnisse in Issues posten.

## Lizenz

MIT License — Copyright 2026 **richieam93**.

Siehe `LICENSE`.

Die MIT-Lizenz gilt für den Integrationscode. Externe Provider, Modelle, Marken, APIs und deren Bedingungen werden dadurch nicht lizenziert oder Bestandteil dieses Projekts.

---

# English

## Overview

**FreeLLM Chat Conversation 3.8.1** is an independent Home Assistant custom integration that connects OpenAI-compatible AI providers to Home Assistant while keeping simple smart-home commands local whenever Home Assistant can handle them directly.

Supported providers:

- **LLM7.io**
- **OVHcloud AI Endpoints**

Core features:

- separate credentials for each provider
- no automatic cross-provider failover
- local Home Assistant Intent/Assist routing for simple device commands
- token-saving context mode enabled by default
- compact tool calling for complex device/state requests
- streaming
- local usage/token/latency telemetry
- automatic config-entry and model-cache migration
- Home Assistant **2026.9.0+** support

## Request flow

```text
User
  |
  v
FreeLLM Chat
  |
  +-- simple HA command --> local Home Assistant Intent --> device action
  |                           (no external AI request when successful)
  |
  +-- ordinary chat -------> selected external provider
  |
  +-- complex HA request --> selected provider + compact tools
                               |
                               +--> tool executed locally in Home Assistant
```

## Privacy and data flow

With token-saving mode enabled:

- ordinary chat does not include the Home Assistant tool catalogue
- simple device commands are first attempted locally
- if local handling succeeds, the external provider receives **no request**
- complex device requests may send compact tool schemas and relevant tool results to the active provider
- only Assist-exposed entities are eligible for FreeLLM device/query tools
- provider credentials are stored separately and only the active provider credential is used
- a failed request is never silently forwarded to the other provider

If token-saving mode is disabled, Home Assistant's larger LLM context and tool information may be included in external requests.

## LLM7.io

Links:

- https://llm7.io/
- https://dash.llm7.io/
- https://api.llm7.io/v1/models
- `https://api.llm7.io/v1/chat/completions`
- https://status.llm7.io/

**Provider information checked 9 October 2026:** current LLM7.io terms state that API access uses a token issued through the dashboard. The free token currently lists up to **100,000 tokens per rolling 24 hours**, **250 requests/hour**, **60 requests/minute**, and **1 request/second**, subject to provider-side capacity/fair-use/model restrictions.

FreeLLM 3.8.1 still accepts an empty LLM7 credential field for backward compatibility, but whether unauthenticated traffic is accepted is controlled by LLM7.io.

## OVHcloud AI Endpoints

Links:

- https://www.ovhcloud.com/en/public-cloud/ai-endpoints/
- https://www.ovhcloud.com/en/public-cloud/ai-endpoints/catalog/
- https://docs.ovhcloud.com/en/guides/public-cloud/ai-machine-learning/ai-endpoints-getting-started
- `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions`
- https://www.status-ovhcloud.com/

Bundled models:

| Model | Context | Function calling | Reasoning | Streaming | Public price snapshot* |
|---|---:|---|---|---|---|
| `gpt-oss-20b` | 131k | Yes | Yes | Yes | €0.04/M input · €0.15/M output |
| `gpt-oss-120b` | 131k | Yes | Yes | Yes | €0.08/M input · €0.40/M output |

\* Checked 9 October 2026. Provider pricing and availability may change.

OVHcloud currently documents:

- anonymous: **2 requests/minute per IP and model**
- API access key: **400 requests/minute per Public Cloud project and model**

Authenticated usage may incur provider charges.

## Installation

### HACS

1. Add this repository to HACS as a custom **Integration** repository.
2. Install **FreeLLM Chat Conversation**.
3. Fully restart Home Assistant.
4. Add **FreeLLM Chat** under **Settings → Devices & services**.

### Manual

1. Back up `/config/custom_components/freellm_chat`.
2. Copy `custom_components/freellm_chat` from this repository to that location.
3. Replace existing files.
4. Fully restart Home Assistant.

## Settings

The options menu contains:

- **Provider and API access**
- **Chat, context, and output**
- **Models and fallback**
- **Home Assistant control**
- **Usage and reference limits**

The recommended default is to keep **token-saving context mode enabled**.

## Token-saving mode

Token-saving mode limits ordinary external chat to a compact context and dynamically attaches Home Assistant tools only when a device/state request is detected.

Internal caps while enabled:

- maximum 12 history messages
- maximum 4 tool rounds
- maximum 700 output tokens

The Token Usage sensor exposes request-size telemetry such as:

```text
last_context_mode
last_tool_count
last_message_count
last_payload_chars
last_estimated_input_tokens
last_input_tokens
last_output_tokens
last_total_tokens
```

## Home Assistant entities

FreeLLM creates model/fallback selects, model/statistics buttons, and sensors for:

- catalogue status
- available models
- conversation requests
- API requests
- token usage
- local quota estimate
- last API request
- 24-hour API success rate
- average/P95 API latency

## Services

```yaml
action: freellm_chat.refresh_models
```

```yaml
action: freellm_chat.select_default_model
```

```yaml
action: freellm_chat.reset_usage_statistics
```

An optional `config_entry_id` can target one FreeLLM configuration when multiple entries exist.

## Upgrade notes

Version 3.8.1 fixes the Home Assistant Store migration failure that could occur when upgrading a model cache created by older versions. Model-cache storage versions 1–3 are migrated automatically; manual deletion of `.storage` is not required.

Existing installations are initially kept on LLM7 during migration. The OVHcloud credential is stored separately and provider-specific model selections are repaired when switching provider.

## Troubleshooting

### 429 from LLM7.io

Check the provider message. Token quotas include input and output and can include system instructions, history and tool definitions. Current free-token quota is a rolling 24-hour window.

### 429 from OVHcloud anonymously

Anonymous access is limited to 2 requests/minute per IP and model. Wait for `Retry-After`, prefer local Home Assistant intents for simple commands, or use an OVHcloud access key for regular usage.

### 401 / 403

The selected provider rejected the credential. Verify that the key is stored in the correct provider field and is still valid.

### 5xx / 502 / 503

Usually a provider/upstream problem. Runtime model failover stays inside the selected provider; FreeLLM does not forward the request to another provider.

## Disclaimer

Large language model output can be inaccurate, incomplete or fabricated. Do not use generated output as the sole basis for emergencies, safety-critical control, legal, medical or financial decisions.

Provider APIs, models, limits, prices, privacy practices and terms can change independently of FreeLLM Chat. Always review the current provider documentation before production use.

## License

MIT License — Copyright 2026 **richieam93**.

See `LICENSE`.
