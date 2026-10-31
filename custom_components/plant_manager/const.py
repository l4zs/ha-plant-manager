"""Constants for Plant Manager."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "plant_manager"
NAME: Final = "Plant Manager"

STORAGE_DIR: Final = "plant_manager"
DB_FILENAME: Final = "plants.db"
PHOTO_DIR: Final = "photos"
STAGING_DIR: Final = "_staging"

PANEL_URL_PATH: Final = "plant-manager"
PANEL_COMPONENT: Final = "plant-manager-panel"
PANEL_TITLE: Final = "Plants"
PANEL_ICON: Final = "mdi:sprout"
STATIC_URL: Final = "/plant_manager_static"
CARD_FILENAME: Final = "plant-manager-card.js"
PANEL_FILENAME: Final = "plant-manager-panel.js"

PHOTO_URL: Final = "/api/plant_manager/photo/{photo_id}"
PHOTO_UPLOAD_URL: Final = "/api/plant_manager/plants/{plant_id}/photos"
STAGED_URL: Final = "/api/plant_manager/staged/{staged_id}"
IDENTIFY_URL: Final = "/api/plant_manager/identify"
BACKUP_URL: Final = "/api/plant_manager/backup/{backup_id}"
UPLOAD_URL: Final = "/api/plant_manager/upload/{kind}"
MAX_PHOTO_BYTES: Final = 20 * 1024 * 1024
MAX_UPLOAD_BYTES: Final = 512 * 1024 * 1024

SIGNAL_UPDATED: Final = f"{DOMAIN}_updated"

EVENT_WATERING_DUE: Final = f"{DOMAIN}_watering_due"
EVENT_CARE_LOGGED: Final = f"{DOMAIN}_care_logged"
EVENT_ALERT: Final = f"{DOMAIN}_alert"
EVENT_ALERT_CLEARED: Final = f"{DOMAIN}_alert_cleared"
EVENT_VACATION_STARTED: Final = f"{DOMAIN}_vacation_started"
EVENT_VACATION_ENDED: Final = f"{DOMAIN}_vacation_ended"

# Options
CONF_ID_PROVIDER: Final = "identification_provider"
CONF_PLANTNET_API_KEY: Final = "plantnet_api_key"
CONF_PLANTID_API_KEY: Final = "plantid_api_key"
CONF_AI_TASK_ENTITY: Final = "ai_task_entity"
CONF_OPB_CLIENT_ID: Final = "openplantbook_client_id"
CONF_OPB_CLIENT_SECRET: Final = "openplantbook_client_secret"
CONF_WEATHER_ENTITY: Final = "weather_entity"
CONF_NOTIFY_ALERTS: Final = "notify_alerts"
CONF_NOTIFY_SERVICE: Final = "notify_service"
CONF_REMINDER_TIME: Final = "reminder_time"

PROVIDER_NONE: Final = "none"
PROVIDER_PLANTNET: Final = "plantnet"
PROVIDER_PLANTID: Final = "plantid"
PROVIDER_AI_TASK: Final = "ai_task"
PROVIDERS: Final = [PROVIDER_NONE, PROVIDER_PLANTNET, PROVIDER_PLANTID, PROVIDER_AI_TASK]

DEFAULT_OPTIONS: Final = {
    CONF_ID_PROVIDER: PROVIDER_NONE,
    CONF_PLANTNET_API_KEY: "",
    CONF_PLANTID_API_KEY: "",
    CONF_AI_TASK_ENTITY: "",
    CONF_OPB_CLIENT_ID: "",
    CONF_OPB_CLIENT_SECRET: "",
    CONF_WEATHER_ENTITY: "",
    CONF_NOTIFY_ALERTS: True,
    CONF_NOTIFY_SERVICE: "",
    CONF_REMINDER_TIME: "09:00:00",
}

UNDO_WINDOW_MINUTES: Final = 15

# Plant fields
POT_MATERIALS: Final = [
    "plastic",
    "terracotta",
    "ceramic",
    "fabric",
    "self_watering",
    "no_drainage",
]
LIGHT_LEVELS: Final = ["low", "medium", "bright_indirect", "direct"]
PLACEMENTS: Final = ["indoor", "outdoor_covered", "outdoor"]
SENSOR_FIELDS: Final = {
    "temperature_sensor": "temperature",
    "humidity_sensor": "humidity",
    "moisture_sensor": "moisture",
    "illuminance_sensor": "illuminance",
}

# Care profile keys
P_BASE_INTERVAL: Final = "base_interval_days"
P_WINTER_DORMANCY: Final = "winter_dormancy"
P_FERTILIZE_INTERVAL: Final = "fertilize_interval_days"
P_MIN_TEMP: Final = "min_temp"
P_MAX_TEMP: Final = "max_temp"
P_MIN_HUMIDITY: Final = "min_humidity"
P_MAX_HUMIDITY: Final = "max_humidity"
P_MIN_MOISTURE: Final = "min_soil_moisture"
P_MAX_MOISTURE: Final = "max_soil_moisture"
P_MIN_LUX: Final = "min_light_lux"
P_MAX_LUX: Final = "max_light_lux"
P_LIGHT_PREFERENCE: Final = "light_preference"
P_TOXIC_TO_PETS: Final = "toxic_to_pets"
P_NOTES: Final = "notes"

# Watering status
STATUS_OK: Final = "ok"
STATUS_WATER_SOON: Final = "water_soon"
STATUS_NEEDS_WATER: Final = "needs_water"
STATUS_OVERDUE: Final = "overdue"
STATUSES: Final = [STATUS_OK, STATUS_WATER_SOON, STATUS_NEEDS_WATER, STATUS_OVERDUE]

# Care log
KIND_WATER: Final = "water"
KIND_FERTILIZE: Final = "fertilize"
KIND_SNOOZE: Final = "snooze"
CARE_KINDS: Final = [KIND_WATER, KIND_FERTILIZE, KIND_SNOOZE, "repot", "prune", "mist", "note"]

FEEDBACK_TOO_DRY: Final = "too_dry"
FEEDBACK_JUST_RIGHT: Final = "just_right"
FEEDBACK_TOO_WET: Final = "too_wet"
FEEDBACK: Final = [FEEDBACK_TOO_DRY, FEEDBACK_JUST_RIGHT, FEEDBACK_TOO_WET]
