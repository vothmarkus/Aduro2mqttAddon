# Changelog

## 1.3.1
- Export `MQTT_BROKER_*` env vars required by upstream.
- Same features as 1.3.0 (discovery, excludes, backoff, pinned deps).

## 1.3.0
- Robust run loop (auto-restart on transient errors).
- Discovery pruned (CO, temps, power, exhaust speed, etc.).
- `discovery_exclude` option added.
- Dependency pins (paho<2, marshmallow>=3.13).
