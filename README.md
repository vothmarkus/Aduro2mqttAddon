# Aduro2MQTT Add-on Repository

This repository contains a Home Assistant add-on that packages the upstream **aduro2mqtt** service
(bridge between Aduro/NBE pellet stove and MQTT).

## How to use

### Option A: Local add-on (quickest)
1. In your Home Assistant host, create the folder `/addons/aduro2mqtt` (via Samba, SSH, or File Editor).
2. Copy the contents of the `aduro2mqtt/` folder from this repo into `/addons/aduro2mqtt`.
3. In Home Assistant, go to **Settings → Add-ons → Add-on Store → ⋮ (menu) → Check for updates**.  
   A new section **Local add-ons** should appear with *Aduro2MQTT*.
4. Open the add-on, set your options (MQTT and Aduro settings), **Save**, then **Start**.

### Option B: Repository
1. Push this repository to GitHub (change the URL in `repository.yaml`).
2. In Home Assistant, go to **Settings → Add-ons → Add-on Store → ⋮ (menu) → Repositories**.
3. Add the GitHub URL of this repository. Then install the add-on from the store.

See `aduro2mqtt/README.md` for add-on specific details.
