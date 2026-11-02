# Plant Manager

A Home Assistant integration (HACS) that reminds you to water your plants, tuned to each plant.

> Status: Phase 1 done, plus vacation mode and import/export. See the [roadmap](docs/ROADMAP.md).

Take a photo of a plant and Plant Manager tells you what it is, looks up how to care for it, and
keeps track of the rest:

- **Identify from a photo**: [Pl@ntNet](https://my.plantnet.org) (free key, 500 a day),
  [Plant.id](https://plant.id) (paid), or any AI integration through AI Task. Or pick the species yourself.
- **Care profiles**: a built-in database of about 70 houseplants, herbs, and garden plants, measured
  ranges from [OpenPlantbook](https://open.plantbook.io) (free), and AI estimates for anything else.
  Every value is editable.
- **Watering tuned to the plant**: its species, pot size and type, light, the room's temperature and
  humidity (from your sensors), the season (by your location and hemisphere), indoor or outdoor,
  and what it learns from your feedback.
- **Water balance**: instead of a fixed schedule, each plant's water reserve is updated every 10
  minutes, so a heat wave or a dry, heated room brings the next watering forward.
- **Soil moisture sensors** take over from the estimate and log waterings by themselves; **rain**
  counts for plants outside.
- **Problems**: too cold, too hot, dry air, soggy soil, too dark, too much sun.
- **Reminders**: a to-do list (check an item off to log the watering), a calendar, Home Assistant
  notifications, a daily summary to your phone, and events for your own automations.
- **Vacation mode**: enter when you leave and come back, and Plant Manager works out what to water
  right before leaving, what to move out of the sun, and on which days a plant sitter has to come.
  The sitter gets a printable plan and a reminder on each of those days.
- **Import & export**: CSV in and out (a spreadsheet template for adding many plants), JSON
  export, and a backup zip with all photos that can be restored.

## Installation

1. In HACS, add `https://github.com/l4zs/ha-plant-manager` as a custom repository (type: Integration).
2. Install **Plant Manager** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration → Plant Manager**.

A **Plants** entry appears in the sidebar. Your data lives in `/config/plant_manager/` (an SQLite
database and the photos folder), so it is included in Home Assistant backups.

To identify plants from photos, open the integration's **Configure → Plant identification and care
data** and choose a service.

## Usage

### Adding plants
Open the Plants panel and choose **+ Add plant**:
1. **Take photo** (on a phone, the camera opens) or **Upload**. The plant is identified and the best
   match is filled in; pick another suggestion if it is wrong, or type the species.
2. The care profile is looked up for the species. The name defaults to the common name.
3. Set the pot size and type, the light at its spot, indoor or outdoor, the area, and optionally
   the room's temperature and humidity sensors, a soil moisture sensor, and a light sensor.
4. Set when it was last watered, then **Save**.

### Daily care
- **Today** lists what needs water, what will soon, what could use fertilizer, and problems.
- **💧 Watered** logs a watering. **Was too dry** also tells Plant Manager to remind you earlier next
  time; **Still moist** postpones the reminder and learns a longer interval. Every action can be
  undone for a few minutes.
- **Schedule** shows the next four weeks.
- Open a plant to see **why** it gets water every N days (pot, light, room climate, season, what
  it learned), its care log (repotted, pruned, misted, notes), and its photos.

### Reminders
**On your phone:** install the Home Assistant app and log in, then open the Plants panel, tap
**🔔**, tick your phone, and choose:
- a **daily summary** of what to water and fertilize, at your own time (only on days with something
  to do; while on vacation it says what the plant sitter waters),
- **problems right away** (too cold, too dark, soil too wet, ...).

**Save and send a test** checks that it arrives. These settings are per Home Assistant user, so
everyone in the household picks their own phones and time.

Under **Configure → Reminders and weather**:
- Home Assistant notifications for plants that need water or fertilizer, and for problems.
- **Send to phone**: a phone (picked by name) or any notify action that gets problems and the daily
  summary at the reminder time (default 09:00) for everyone. A phone that a user picked under
  **🔔** follows that user's settings instead, so it isn't notified twice.
- A weather entity: outdoor plants without their own sensors use its temperature and humidity, and
  rain counts as watering for plants that get rain.

The to-do list **Plant care** and the calendar **Plant care** work with every Home Assistant app.

### Vacation
Open **Vacation** in the panel and enter the day you leave (in the morning) and the day you are
back (in the evening). Optionally add who waters, their notify action (e.g.
`notify.mobile_app_anna`), and notes such as where the key is. Before saving, the plan is shown
for the dates:
- **Before you leave**: plants to water thoroughly the day before or the morning you leave, and
  measures that make the water last longer (out of direct sun, a cachepot around terracotta), with
  how many days they gain.
- **Plant sitter**: the days someone has to come and what to water then. Visits are shared: when one
  plant needs water, the sitter also waters the others that are dry enough and would not last.
  **Send** it to the sitter, **Copy** it, or **Print** it (with photos and check boxes).
- **All plants**: how long each plant lasts and whether it needs the sitter.

The plan uses each plant's water balance, the room climate, and the season in the middle of the
trip. While you are away, the daily reminder goes to the sitter on visit days (or to you, if the
sitter has no notify action), the schedule and calendar show the visits, and the plan follows the
sitter's waterings. Two days before leaving, a notification lists what to do. **I'm back** ends
the vacation early.

`binary_sensor.plant_manager_vacation` is on while you are away (with the next visit as
attributes); the actions `set_vacation` and `end_vacation` and the events
`plant_manager_vacation_started` and `plant_manager_vacation_ended` are there for automations.

### Import, export, and backups
On the **Plants** tab, under **Import / export**:
- **Export CSV** / **Import CSV**: one row per plant with the same columns both ways (`name`,
  `species`, `common_name`, `area` (name), `placement`, `light`, `pot_diameter_cm`,
  `pot_material`, the sensors, `last_watered`, `notes`, and the care profile such as
  `base_interval_days`, `min_temp`, `toxic_to_pets`). Only `name` and `species` are needed; the
  care profile is looked up for the species and the profile columns you fill in win. Commas or
  semicolons both work, and values like "Direct sun" or "clay" are understood. Rows with errors are
  reported and skipped.
- **Export JSON**: everything, for other tools.
- **Download backup** / **Restore backup…** (administrators): a zip with the database and all photos.
  Restoring replaces everything; the previous data is kept next to it as `*.before-restore`.

Home Assistant's own backups include `/config/plant_manager/` as well.

### Lovelace card
The card is registered automatically. Edit a dashboard, **Add card**, switch to **By card**, and
pick **Plant Manager**; the title and the counts can be changed in the visual editor. In YAML:

```yaml
type: custom:plant-manager-card
title: Plants        # optional
show_counts: true    # optional
```

### Entities and actions
Per plant (a device per plant): watering status (with problems and the care profile), next watering,
last watered, estimated water reserve, watering interval (with the factors), next fertilization;
binary sensors **Needs water** and **Problem**; buttons **Watered**, **Soil still moist**, and
**Fertilized**. Overall: plants, plants needing water, plants with problems, next watering;
the **Vacation** binary sensor; the **Plant care** to-do list and calendar.

Actions: `water` (with optional `feedback`), `snooze`, `fertilize`, `log_care`, `send_reminder`,
`identify` (from a camera or an image file, returns the candidates), `set_vacation`, `end_vacation`,
all under `plant_manager.`.
Plant IDs are shown in each plant's dialog.

Events: `plant_manager_watering_due`, `plant_manager_care_logged`, `plant_manager_alert`,
`plant_manager_alert_cleared`, `plant_manager_vacation_started`, `plant_manager_vacation_ended`.

```yaml
automation:
  - alias: Plant needs water
    triggers:
      - trigger: event
        event_type: plant_manager_watering_due
    actions:
      - action: notify.mobile_app_my_phone
        data:
          message: "{{ trigger.event.data.name }} needs water 💧"
```

## Languages

English and German. The panel and the card follow each user's language from their Home Assistant profile and switch right away when it changes. Texts the integration writes itself follow the same rule where it knows the reader: phone notifications a user set up under 🔔 come in that user's language, and the sitter's plan from the panel comes in the language of whoever sends it. The calendar, to-do list, Home Assistant notifications and the shared notify action use Home Assistant's language. Built-in species get German common names and care tips, and can be found by their German name (e.g. "Bogenhanf").

To use one language for everyone on a Home Assistant, choose it under Settings → Devices & services → Plant Manager → Configure → Language. It covers everything Plant Manager writes: the panel, the cards, notifications, the calendar, plant identification and the sidebar title, which otherwise uses Home Assistant's language because there is one title per instance. The same page has a field to set your own sidebar title. Refresh open browser tabs afterwards. Home Assistant's own menus keep following each user's profile.

## Development

Tests run in Docker, because Home Assistant's test harness doesn't install on Windows:

```bash
docker build -f scripts/Dockerfile.test -t plant-manager-test .
docker run --rm -v "$PWD:/src" -w /src plant-manager-test pytest -q
```

`scripts/e2e/run.sh` starts a fresh Home Assistant with the integration, onboards it, and drives the
panel with a headless browser. Screenshots are saved to `scripts/e2e/out/`.

For a dev instance, mount `config/` and `custom_components/`:

```bash
docker run -d --name plant-manager-ha -p 8123:8123 \
  -v "$PWD/config:/config" -v "$PWD/custom_components:/config/custom_components" \
  ghcr.io/home-assistant/home-assistant:stable
```

## Docs

- [Design](docs/DESIGN.md): architecture, data model, the watering model, entities and services
- [Roadmap](docs/ROADMAP.md): phased feature plan
