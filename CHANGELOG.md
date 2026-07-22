# Changelog

## 0.1.0 — 2026-07-22

First release. 🐱🍪

Cloud integration for the **MOVA MeowgicPod LR10 Prime**
(`mova.litterbox.q2504w`) self-cleaning cat litter box, talking to the MOVA
cloud with the same protocol as the MOVAhome app.

### Added

- **MOVA cloud client** — login with automatic token refresh, device
  discovery, live property polling over the app command channel, and
  set-property / action commands.
- **Config flow** — sign in with your MOVAhome account (email, password,
  region), pick your device, with re-authentication support.
- **Status sensor** — full device state enum (Standby, Cleaning,
  Emptying, Leveling, their paused/canceling variants, Weighing
  protection, Air purification, Safety escape mode, Device abnormal).
- **Binary sensors** — air purification running, deodorizing spray active,
  do-not-disturb active.
- **Switches** — child lock, key light, key tone, soft stool mode,
  auto-clean DND, air purification during cleaning, auto spray after
  cleaning, air purification DND.
- **Selects** — cleaning mode (automatic/manual), air purification
  duration (quick/standard/long-lasting), auto-spray duration.
- **Number** — cleaning delay (minutes).
- **Diagnostic sensors** — firmware build, serial number, decoded cleaning
  schedule and DND time windows, device clock, plus raw fallback sensors
  for every property the cloud reports.
- **Brand icon**, HACS metadata, and hassfest/HACS validation workflows.

### Known limitations / next up

- Cat visit detection, litter level, and waste bin state are not yet
  mapped (reverse engineering in progress).
- No Clean/Empty/Level action buttons yet (action IDs still to be found).
- State is polled every 60s; MQTT push is planned.

See the [roadmap](README.md#-roadmap) for what's next.
