# Design

This is the target design. What gets built when is in [ROADMAP.md](ROADMAP.md).

## 1. Architecture

Plant Manager is a **custom integration** (`custom_components/plant_manager`) installed through
HACS. It works on every Home Assistant install type (OS, Supervised, Container, Core).

| Part | Responsibility |
| --- | --- |
| Config flow | One-time setup without questions. Options for identification, care data, reminders, and weather. |
| Storage layer | SQLite database at `/config/plant_manager/plants.db`, with schema migrations. |
| Photo store | Files in `/config/plant_manager/photos/`, served through an authenticated HTTP view with signed URLs. Photos taken for identification wait in `photos/_staging/` for an hour. |
| Manager | Owns the database, advances every plant's water balance every 10 minutes, and pushes updates to entities and the panel. |
| Care model | Pure functions (`care.py`): interval, water balance, status, problems, forecast. |
| Knowledge | Built-in species database, OpenPlantbook, and AI Task care profiles (`species_db.py`, `knowledge.py`). |
| Identification | Pl@ntNet, Plant.id or AI Task (`identify.py`). |
| Vacation planning | Pure functions (`vacation.py`): what to water before leaving, measures, and the sitter's visits. |
| Import / export | CSV in and out (`transfer.py`), JSON export, backup zip and restore. |
| Panel | A custom sidebar panel (web component) to add, identify, edit, and care for plants. Talks to the backend over a websocket API. |
| HA surface | Per-plant devices with sensors, binary sensors, and buttons; a to-do list, a calendar, actions, and events. |

Identification and the optional data sources are cloud services the user opts into. Without them,
everything works locally with the built-in species database.

## 2. Data model

### plant
| Field | Notes |
| --- | --- |
| `id` | UUID |
| `name` | e.g. "Monty" |
| `species`, `common_name`, `family` | botanical name, from identification or typed |
| `area_id` | HA area, also the device's area |
| `placement` | `indoor` · `outdoor_covered` · `outdoor` (gets rain) |
| `light` | light at the plant's spot: `low` · `medium` · `bright_indirect` · `direct` |
| `pot_diameter_cm`, `pot_material` | `plastic`, `terracotta`, `ceramic`, `fabric`, `self_watering`, `no_drainage` |
| `temperature_sensor`, `humidity_sensor`, `moisture_sensor`, `illuminance_sensor` | optional HA sensors |
| `profile` | care profile, see below |
| `profile_sources` | where the profile came from |
| `notes`, `acquired_date` | |
| model state | `dryness`, `last_tick`, `learned_factor`, 24 h moving averages of temperature and humidity, last soil moisture, daily light maximum |

### care profile
| Field | Notes |
| --- | --- |
| `base_interval_days` | days between waterings under reference conditions (15 cm plastic pot, medium indirect light, 21 °C, 50 % humidity, summer) |
| `winter_dormancy` | rests in winter: waters much less, no fertilizer |
| `fertilize_interval_days` | in the growing season, 0 = never |
| `min/max_temp`, `min/max_humidity` | air, °C and % |
| `min/max_soil_moisture` | water below / too wet above, % |
| `min/max_light_lux` | expected daily peak light |
| `light_preference`, `toxic_to_pets`, `notes` | shown in the panel |

### Other tables
- **photos**: `plant_id`, file name, position (the first is the cover).
- **care_events**: `plant_id`, `kind` (water, fertilize, snooze, repot, prune, mist, note), `at`,
  `feedback`, `notes`, `source` (manual, button, todo, service, sensor, import), and the model state
  before the event (for undo).
- **vacations**: `start_date` (leaving in the morning), `end_date` (back in the evening), `sitter`,
  `sitter_notify`, `notes`, `ended_at` (back early). One is planned or going on at a time.

## 3. Care profiles

A profile is built when a plant is created (and again on request):

1. **Generic defaults.**
2. **Built-in database** (~70 houseplants, herbs, and garden plants): looked up by botanical name,
   synonym, common name, genus (`Philodendron birkin` → philodendron), or family (`Cactaceae`).
3. **OpenPlantbook** (optional, free account): measured temperature, humidity, soil moisture, and
   light ranges overwrite the database ranges.
4. **AI Task** (optional): for species missing from the database, an AI estimates the whole profile.
   Measured OpenPlantbook ranges win over AI estimates.

Every value can be edited in the panel.

## 4. Watering model

### Interval
```
interval = base_interval × pot size × pot material × light × climate × season × placement × learned
```
- **Pot size**: `(diameter / 15 cm) ^ 0.6`, clamped to 0.45–2.5. Bigger pots hold more water per
  evaporating surface.
- **Pot material**: terracotta 0.8, fabric 0.7, self-watering 2.0, no drainage 1.15.
- **Light**: low 1.35, medium 1.0, bright indirect 0.85, direct sun 0.7.
- **Climate**: `(VPD_ref / VPD) ^ 0.5` from the vapour pressure deficit of the 24 h moving average of
  the room's temperature and humidity (Tetens equation), clamped to 0.5–2.5. Below 10 °C plants
  barely drink, which adds to the factor.
- **Season**: the growth level is 1 in mid-summer and 0 in mid-winter (by latitude; mirrored in the
  southern hemisphere; flat near the equator). Factor `0.9 + (1 − growth) × 0.7` for dormant species,
  `× 0.35` for the rest.
- **Placement**: outdoor 0.75, sheltered outdoor 0.85.
- **Learned**: feedback "too dry" × 0.85, "too wet" or "still moist" × 1.15 / 1.1, clamped to 0.4–2.5.

### Water balance
Instead of fixing a due date at watering time, each plant integrates **dryness**: every tick adds
`elapsed days / current interval`. A watered plant is at 0 and needs water at 1 (`needs_water`),
from 1.25 it is `overdue`, and within a day of 1 it is `water_soon`. So a heat wave or a heated,
dry room pulls the due date forward while it lasts.

- **Soil moisture sensor**: dryness follows the sensor (`(max − moisture) / (max − min)`), and a rise
  of 10 points or more between ticks logs a watering (`source: sensor`).
- **Rain**: for `outdoor` plants, the weather entity's condition removes dryness per hour of rain
  (rainy 0.3, lightning-rainy 0.5, pouring 1.0).
- **Back-dated waterings** start the balance at `elapsed / interval`. Logging a watering older than
  the latest one only adds it to the log.
- **Undo** (last 15 minutes) or removing the latest watering recomputes the balance from the
  previous watering.

### Problems
From the current readings: too cold or hot, air too dry or humid, soil too wet; from yesterday's
peak light: too dark or too much direct light; and overdue watering.

### Fertilizing
Due `fertilize_interval_days` after the last fertilizing (or after the plant was added), paused while
a dormant species rests in winter (growth level below 0.25).

## 5. Vacation

Each plant's water balance is projected through the trip (you leave at 08:00 on the first day and
are back at 18:00 on the last), with its current room climate and the growth level in the middle
of the trip:

1. **Until you leave** the plant is watered whenever it is due, as usual.
2. If it would not last until you are back and is at least 0.3 dry when you leave, it is **watered
   right before leaving** (wetter plants are not watered again, to avoid rot).
3. If it still runs dry, **measures** are tried: out of direct sun (light becomes medium) and a
   cachepot around terracotta or fabric pots (becomes plastic). The interval is recomputed with them.
4. If that is not enough, the **plant sitter** comes. Visits are planned at noon on the days a plant
   would otherwise run dry before the next possible visit; on each visit the sitter also waters the
   other plants that are at least 0.6 dry and would not last until you are back, so visits are
   shared.

The plan is recomputed on every refresh. Once you have left, it starts from the current balance, so
it follows the sitter's actual waterings. During the trip the schedule and calendar show the visits
instead of the projected waterings, fertilizing moves to the day you are back, and waterings after
the trip continue from the projected balance on your return.

Notifications: a checklist (water before leaving, measures, number of visits) from two days before
leaving; the daily reminder the day before leaving includes it; while away, the daily reminder goes
to the sitter's notify action on visit days (or to yours if the sitter has none). Events
`plant_manager_vacation_started` and `_ended` fire on the transitions.

## 6. Home Assistant surface

### Entities
| Entity | Purpose |
| --- | --- |
| `sensor.plant_manager_plants` / `_plants_needing_water` / `_plants_with_problems` | counts, with plant lists as attributes |
| `sensor.plant_manager_next_watering` | the earliest next watering |
| `sensor.<plant>_watering_status` | `ok` · `water_soon` · `needs_water` · `overdue`, with problems and the care profile |
| `sensor.<plant>_next_watering`, `_last_watered`, `_next_fertilization` | timestamps |
| `sensor.<plant>_estimated_water_reserve` | 100 % right after watering, 0 % when due |
| `sensor.<plant>_watering_interval` | with the factors and the actual average interval |
| `binary_sensor.<plant>_needs_water`, `_problem` | for automations |
| `button.<plant>_watered`, `_soil_still_moist`, `_fertilized` | log care |
| `todo.plant_manager_plant_care` | due care; checking an item off logs it |
| `calendar.plant_manager_plant_care` | projected waterings and fertilizing, the vacation and the sitter's visits |
| `binary_sensor.plant_manager_vacation` | on while away; dates, sitter, next visit as attributes |

Plant devices are added and removed as plants are created and deleted in the panel.

### Actions
`water` (plant_id, at, feedback), `snooze`, `fertilize`, `log_care` (kind, notes), `send_reminder`,
`identify` (camera or image file; returns candidates). `set_vacation` (start_date, end_date, sitter,
sitter_notify, notes), `end_vacation`.

### Events
`plant_manager_watering_due` (a plant starts needing water), `plant_manager_care_logged`,
`plant_manager_alert`, `plant_manager_alert_cleared`. `plant_manager_vacation_started`,
`plant_manager_vacation_ended`.

### Alerts and reminders
Alerts have a stable key and are announced once (keys are stored across restarts):
- **Water** and **fertilize**: one Home Assistant notification each, listing all plants, kept up to
  date and dismissed when nothing is due.
- **Problems**: one notification per plant and set of problems, also sent to the notify action
  right away.
- **Daily reminder** (default 09:00): a summary of what to water and fertilize today, sent to the
  notify action.
- **Per user** (stored in `.storage/plant_manager.notifications`): each Home Assistant user picks
  phones (mobile_app devices, theirs first), a time for the summary, and whether problems are sent
  right away. A phone picked by a user is left out of the integration's notify action, so nothing
  arrives twice.

### Lovelace card
`custom:plant-manager-card` lists plants that need attention with a 💧 button, and counts. It is
served by the integration and registered automatically.

## 7. Panel

- **Plants**: grid of plants with photo, species, water reserve bar, due text, and problem badge;
  search, area, and status filters; a 💧 quick action on each card.
- **Today**: problems, plants that need water or will soon (Watered / Was too dry / Still moist),
  and fertilizing.
- **Schedule**: the next four weeks, by day.
- **Vacation**: plan a trip (with a live preview of the plan), what to do before leaving, the sitter's
  visits (send, copy, print), and how long each plant lasts.
- **Import / export** (on the Plants tab): CSV export and import, JSON export, backup and restore.
- **Plant dialog**: identify from a photo (on a phone, the camera opens directly), pick a candidate,
  and the species, common name, name, and care profile fill in; photos; details; sensors; the care
  profile; the current care with an explanation of the interval ("why every 5.3 days"), care
  actions, and the care log.

Photos are scaled down in the browser (longest side 1600 px, JPEG) before upload.

## 8. Identification

| Provider | Notes |
| --- | --- |
| Pl@ntNet | free key, 500 identifications a day; `organs=auto`; returns species with family and common names |
| Plant.id (Kindwise) | paid key; detects "not a plant" |
| AI Task | any AI integration with image support; the photo is attached through the integration's media source (`media-source://plant_manager/staged/<id>`) |

The panel posts the photo to `/api/plant_manager/identify`, which stages it, identifies it, and
returns up to five candidates. Saving the plant attaches the staged photo.

## 9. Import, export, backup

`transfer.py` writes and reads the same CSV columns, validated with the same schema as the
websocket API (`schema.py`). Areas are written by name and matched by name or id on import. Choice
values accept common spellings ("Direct sun", "clay"). The care profile is looked up for the species
and the profile columns in the row win; `last_watered` creates a watering in the care log. The JSON
export dumps every table. A backup is a zip with an online-backup copy of the SQLite database and the
photo files. Restoring (admins only) validates it (a Plant Manager database with a known schema
version), keeps the current database and photos as `*.before-restore`, swaps the files, reopens the
database, and removes the devices of plants that are no longer there. It does not reload the
integration, so the panel stays open.
