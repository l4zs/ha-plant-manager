# Roadmap

Phases build on each other. The details of each feature are in [DESIGN.md](DESIGN.md).

## Phase 1: MVP
- [x] Integration skeleton, HACS metadata, config flow with options
- [x] SQLite storage layer with migrations
- [x] Sidebar panel: add, edit, and delete plants, with photos
- [x] Identification from a photo (Pl@ntNet, Plant.id, AI Task), with the camera on phones
- [x] Care profiles: built-in database, OpenPlantbook, AI estimates; editable
- [x] Watering model: pot, light, room climate (VPD), season and hemisphere, placement, learning
- [x] Water balance updated every 10 minutes; soil moisture sensors and rain
- [x] Problems: temperature, humidity, soil moisture, light
- [x] Care log: watering with feedback, snooze, fertilizing, repotting, pruning, misting, notes; undo
- [x] Per-plant devices, to-do list, calendar, actions, events
- [x] Alerts and a daily reminder (HA notifications and a notify action)
- [x] Lovelace card

## Phase 2: Insights
- [ ] History charts: water reserve, actual vs. predicted intervals, climate per plant
- [ ] Stats: waterings per week, most thirsty plants, how often reminders were early or late
- [ ] Learn the interval from the actual watering rhythm, not only from feedback

## Phase 3: More care
- [ ] Repotting reminders (by pot size and growth), seasonal tips
- [x] Vacation mode: water everything before leaving, a plan for the plant sitter
- [ ] Pests and diseases log, with photo identification of the problem
- [ ] Propagation: cuttings as new plants linked to the parent

## Phase 4: Extras
- [x] Import and export (CSV, JSON), backup with photos and restore
- [ ] Several people: who takes care of which plant
- [ ] Watering automation: valves and pumps for self-watering setups
