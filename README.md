# Aduro – native Home-Assistant-Integration

<img src="custom_components/aduro/brand/logo.png" alt="Aduro-Projektlogo" width="150"/>

- 🇬🇧 **English:** [README.en.md](README.en.md)

Diese Integration bindet einen **Aduro H2** beziehungsweise einen kompatiblen
NBE-Controller direkt in Home Assistant ein. Sie ersetzt die bisherige
Aduro2MQTT-Bridge: Es werden weder ein MQTT-Broker noch ein Add-on oder
MQTT-Discovery benötigt.

## Funktionsumfang

Alle bisher in Home Assistant bereitgestellten Funktionen bleiben erhalten:

| Funktion | Native Home-Assistant-Entität |
|---|---|
| Soll- und Isttemperatur | Climate |
| Automatik- und Festleistungsbetrieb | Climate-Modus |
| Heizbetrieb starten/stoppen | Switch |
| Feste Leistung 10/50/100 % | Select |
| Förderschnecke 0–120 Sekunden | Number |
| Rauchgas- und Raumtemperatur | Sensor |
| Betriebszustand und Zustandsnummern | Sensor |
| Zustandsdauer und aktuelle Leistung | Sensor |

Die im bisherigen Add-on standardmäßig ausgeblendeten Rohsensoren
**Raumtemperatur**, **Statusnummer**, **Unterstatusnummer** und **Statusdauer**
werden weiterhin angelegt, sind aber zunächst deaktiviert. Sie lassen sich in
Home Assistant unter **Gerät → Entitäten** einschalten.

Nach jedem Schreibbefehl wartet die Integration wie bisher 0,6 Sekunden und
liest anschließend sofort neue Werte ein. Reguläres Polling erfolgt
standardmäßig alle 30 Sekunden.

## Installation über HACS

1. Dieses Repository in HACS als benutzerdefiniertes Repository der Kategorie
   **Integration** hinzufügen.
2. **Aduro** installieren.
3. Home Assistant neu starten.
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Aduro** öffnen.
5. Gerätename, lokale IP/Hostname, Seriennummer und PIN eintragen.

Die Verbindung wird bereits während der Einrichtung geprüft. IP-Adresse, PIN
und Abfrageintervall können anschließend über **Konfigurieren** geändert
werden.

## Wechsel vom bisherigen Add-on

> Das Aduro2MQTT-Add-on vor der Einrichtung der nativen Integration stoppen.

PyDuro bindet seine UDP-Anfragen an den lokalen Port 1901. Add-on und native
Integration dürfen deshalb nicht gleichzeitig laufen.

Empfohlene Reihenfolge:

1. Namen und Automationen der bisherigen MQTT-Entitäten notieren.
2. Aduro2MQTT-Add-on stoppen, aber zunächst nicht löschen.
3. Native Aduro-Integration einrichten und alle Werte prüfen.
4. Automationen auf die neuen nativen Entitäten umstellen.
5. Alte MQTT-Discovery-Entitäten und anschließend das Add-on entfernen.

## Technischer Aufbau

- lokale Kommunikation direkt über das NBE-UDP-Protokoll
- PyDuro 3.2.1 als Protokollbibliothek
- zentraler DataUpdateCoordinator
- sämtliche UDP-Zugriffe prozessweit serialisiert, da PyDuro Port 1901 nutzt
- UI-basierte Einrichtung und Optionsverwaltung
- Geräte- und Entitäts-Registry mit stabilen IDs auf Basis der Seriennummer
- automatische Offline-Erkennung und Wiederaufnahme des Pollings

## Unterstützte Geräte

Entwickelt und getestet für den Aduro H2. Weitere Aduro-Hybridöfen mit
kompatiblem NBE-Controller können funktionieren, sofern sie die verwendeten
Status- und Einstellungsgruppen bereitstellen.

## Lizenz und Credits

Apache License 2.0. Die Integration übernimmt das bewährte Verhalten von
[Johnny100dk/aduro2mqtt](https://github.com/Johnny100dk/aduro2mqtt) und nutzt
[PyDuro](https://github.com/clementprevot/pyduro) als externe MIT-lizenzierte
Abhängigkeit. Einzelheiten stehen in [NOTICE](NOTICE).
