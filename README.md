# Aduro2MQTT – Home-Assistant Add-on

Bridgt deinen **Aduro H2** (bzw. kompatible Aduro-Kessel) nach **MQTT** und legt die wichtigsten Entitäten in Home Assistant **automatisch** per MQTT Discovery an.

## Basis / Credits
Dieses Add-on verpackt und automatisiert das Upstream-Projekt:
- Upstream: `Johnny100dk/aduro2mqtt` (MQTT-Bridge & Logik)  
- Inspiration/Fork-Historie: `freol35241/aduro2mqtt`

## Idee
- **Add-on** statt eigenem Docker-Setup: 1-Klick-Installation direkt im HA Add-on Store.  
- **Auto-Erkennung (MQTT Discovery)**: Sensoren, Schalter & Selects werden als Geräte/Entitäten in der **MQTT-Integration** automatisch angelegt (und bei Bedarf aufgeräumt).

---

## Voraussetzungen
- Home Assistant (Supervised/OS)
- **MQTT-Broker** (empfohlen: **Mosquitto** Add-on)
- Netzwerkzugriff zum Aduro-Ofen (IP), Seriennummer & PIN

---

## Installation (Schritt für Schritt)

1) **MQTT-Broker installieren**  
   - Add-on Store → **Mosquitto broker** installieren & starten.  
   - In **Einstellungen → Geräte & Dienste → MQTT** sicherstellen, dass die Integration eingerichtet ist (Discovery aktiv).

2) **Add-on Repository hinzufügen**  
   - Add-on Store → oben rechts **⋮ → Repositories** → dein Aduro2MQTT-Repository hinzufügen.  
   - Danach erscheint **Aduro2MQTT** im Store.

3) **MQTT-Benutzer anlegen (empfohlen)**  
   - Einstellungen → Personen & Zonen → **Benutzer** → neuen Benutzer anlegen (z. B. `aduro`) mit **starkem Passwort**.  
   - In Mosquitto (falls nötig) die Anmeldedaten freigeben (Standard-HA-Setup übernimmt das).

4) **Aduro2MQTT Add-on installieren & konfigurieren**  
   - Add-on öffnen → **Konfiguration**:
     - **MQTT**
       - `mqtt_host`: `core-mosquitto` (bei Mosquitto-Add-on) oder IP/Host deines Brokers  
       - `mqtt_port`: `1883`  
       - `mqtt_client_id`: z. B. `aduro2mqtt`  
       - `mqtt_user` / `mqtt_password`: **der eben angelegte Benutzer**
       - `mqtt_base_topic`: `aduro2mqtt` (Standard)
     - **Aduro**
       - `aduro_host`: IP deines Ofens (z. B. `192.168.x.y`)  
       - `aduro_serial`: Seriennummer  
       - `aduro_pin`: PIN  
       - `aduro_poll_interval`: z. B. `30` Sekunden
     - **Discovery (optional)**
       - `discovery_enable`: `true`  
       - `discovery_prefix`: `homeassistant`  
       - `device_name`: `Aduro H2`  
       - `device_id`: `aduro_h2`  
       - `discovery_exclude`: Liste von Keys, die **nicht** veröffentlicht werden sollen (z. B. `boiler_pump_state`, `return_temp`)
   - **Speichern** → **Starten**.

5) **Geräte/Entitäten erscheinen automatisch**  
   - Home Assistant → **Einstellungen → Geräte & Dienste → MQTT**  
   - Dort sollte ein **Gerät „Aduro H2“** mit Sensoren/Entitäten auftauchen (Temperaturen, Leistung, Exhaust Speed, CO, …).  
   - Ein **Schalter** („Aduro H2 Toggle“) und **Select** („Fixed power (%)“) werden ebenfalls per Discovery bereitgestellt.

---

## Beispiel-Konfiguration (Add-on → „Konfiguration“)
```yaml
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_client_id: aduro2mqtt
mqtt_user: aduro
mqtt_password: !secret mqtt_aduro_password
mqtt_base_topic: aduro2mqtt

aduro_host: 192.168.177.74
aduro_serial: "84956"
aduro_pin: "4438539130"
aduro_poll_interval: 30

discovery_enable: true
discovery_prefix: homeassistant
device_name: Aduro H2
device_id: aduro_h2
discovery_exclude:
  - boiler_pump_state
  - return_temp

log_level: INFO
```

---

## Was wird angelegt?
- **Sensoren** (Auswahl):  
  - `Room Temp`, `Shaft Temp`, `Smoke Temp`, `Oxygen`, `Power Pct`, `Exhaust Speed`, `CO (ppm)`, `Total Hours`  
- **Schalter**:  
  - „Aduro H2 Toggle“ (Start/Stop)  
- **Select**:  
  - „Fixed power (%)“ (10/50/100)

> Hinweis: Die Menge der Sensoren ist bewusst kuratiert. Über `discovery_exclude` kannst du einzelne Keys ausblenden.

---

## Tipps & Troubleshooting
- **Keine Geräte sichtbar?**  
  - MQTT-Integration in HA aktiv?  
  - Broker-Login korrekt (`mqtt_user`/`mqtt_password`)?  
  - In den Add-on-Logs sollte „publish …/config“ auftauchen.
- **CO-Wert ist 0?**  
  - Der Ofen liefert teils `0` im Idle. Während des Betriebs prüfen.  
- **Aduro antwortet nicht?**  
  - IP/Netzwerk prüfen, Seriennummer+PIN korrekt, Poll-Intervall ggf. auf 60 s erhöhen.

---

## Lizenz & Danksagung
- Dieses Add-on bündelt die Arbeit von `Johnny100dk/aduro2mqtt` (Lizenz des Upstreams beachten).  
- Danke an die Community-Forks (u. a. `freol35241`) für Ideen & Beispiele.
