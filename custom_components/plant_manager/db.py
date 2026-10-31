"""SQLite storage for Plant Manager.

Everything here is synchronous and must run in the executor.
"""

from __future__ import annotations

from collections.abc import Iterable
import json
import sqlite3
import threading
from typing import Any
import uuid

from .const import KIND_FERTILIZE, KIND_WATER

# Each entry migrates the schema from version N to N + 1.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE plants (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        species TEXT,
        common_name TEXT,
        family TEXT,
        area_id TEXT,
        placement TEXT NOT NULL DEFAULT 'indoor',
        light TEXT NOT NULL DEFAULT 'medium',
        pot_diameter_cm REAL NOT NULL DEFAULT 15,
        pot_material TEXT NOT NULL DEFAULT 'plastic',
        temperature_sensor TEXT,
        humidity_sensor TEXT,
        moisture_sensor TEXT,
        illuminance_sensor TEXT,
        profile TEXT NOT NULL DEFAULT '{}',
        profile_sources TEXT NOT NULL DEFAULT '[]',
        notes TEXT,
        acquired_date TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        -- watering model state, written by the manager on every tick
        dryness REAL,
        last_tick TEXT,
        learned_factor REAL NOT NULL DEFAULT 1,
        temp_ema REAL,
        humidity_ema REAL,
        last_moisture REAL,
        lux_day TEXT,
        lux_max_today REAL,
        lux_max_yesterday REAL
    );
    CREATE TABLE photos (
        id TEXT PRIMARY KEY,
        plant_id TEXT NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
        filename TEXT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0,
        source TEXT,
        created_at TEXT NOT NULL
    );
    CREATE INDEX photos_plant ON photos(plant_id);
    CREATE TABLE care_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plant_id TEXT NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
        kind TEXT NOT NULL,
        at TEXT NOT NULL,
        feedback TEXT,
        notes TEXT,
        source TEXT,
        created_at TEXT NOT NULL,
        -- model state before the event, for undo
        prev_dryness REAL,
        prev_learned_factor REAL
    );
    CREATE INDEX care_events_plant ON care_events(plant_id, at);
    """,
    """
    CREATE TABLE vacations (
        id TEXT PRIMARY KEY,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        sitter TEXT,
        sitter_notify TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        ended_at TEXT
    );
    """,
]

JSON_FIELDS = ("profile", "profile_sources")

# Fields a caller may set through create/update.
PLANT_FIELDS = (
    "name",
    "species",
    "common_name",
    "family",
    "area_id",
    "placement",
    "light",
    "pot_diameter_cm",
    "pot_material",
    "temperature_sensor",
    "humidity_sensor",
    "moisture_sensor",
    "illuminance_sensor",
    "profile",
    "profile_sources",
    "notes",
    "acquired_date",
)

# Fields the manager writes on every tick.
STATE_FIELDS = (
    "dryness",
    "last_tick",
    "learned_factor",
    "temp_ema",
    "humidity_ema",
    "last_moisture",
    "lux_day",
    "lux_max_today",
    "lux_max_yesterday",
)

VACATION_FIELDS = ("start_date", "end_date", "sitter", "sitter_notify", "notes")

WATERING_HISTORY = 12


class NotFoundError(Exception):
    """Raised when a record does not exist."""


def _plant_from_row(row: sqlite3.Row) -> dict[str, Any]:
    plant = dict(row)
    for field in JSON_FIELDS:
        plant[field] = json.loads(plant[field]) if plant[field] else None
    return plant


def _encode(field: str, value: Any) -> Any:
    if field in JSON_FIELDS:
        return json.dumps(value if value is not None else ({} if field == "profile" else []))
    return value


class PlantDatabase:
    """Thread-safe wrapper around one SQLite connection."""

    def __init__(self, path: str) -> None:
        """Initialize the database wrapper."""
        self._path = path
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None

    # -- lifecycle ---------------------------------------------------------

    def open(self) -> None:
        """Open the connection and migrate the schema."""
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        self._conn = conn
        self._migrate()

    def close(self) -> None:
        """Close the connection."""
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the open connection."""
        if self._conn is None:
            raise RuntimeError("Database is not open")
        return self._conn

    @property
    def schema_version(self) -> int:
        """Return the current schema version."""
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    def _migrate(self) -> None:
        with self._lock:
            version = self.schema_version
            for index in range(version, len(MIGRATIONS)):
                with self.conn:
                    self.conn.executescript(
                        "BEGIN;" + MIGRATIONS[index] + f"PRAGMA user_version = {index + 1};"
                    )

    # -- plants ------------------------------------------------------------

    def list_plants(self) -> list[dict[str, Any]]:
        """Return all plants with their photos and last care."""
        with self._lock:
            rows = self.conn.execute("SELECT * FROM plants ORDER BY name COLLATE NOCASE").fetchall()
            plants = [_plant_from_row(row) for row in rows]
            self._attach(plants)
            return plants

    def get_plant(self, plant_id: str) -> dict[str, Any]:
        """Return a single plant with photos and last care."""
        with self._lock:
            row = self.conn.execute("SELECT * FROM plants WHERE id = ?", (plant_id,)).fetchone()
            if row is None:
                raise NotFoundError(f"Plant {plant_id} not found")
            plant = _plant_from_row(row)
            self._attach([plant])
            return plant

    def _attach(self, plants: list[dict[str, Any]]) -> None:
        by_id = {plant["id"]: plant for plant in plants}
        for plant in plants:
            plant["photos"] = []
            plant["last_watered"] = None
            plant["last_fertilized"] = None
            plant["watering_dates"] = []
        if not by_id:
            return
        for row in self.conn.execute("SELECT * FROM photos ORDER BY position, created_at"):
            if (plant := by_id.get(row["plant_id"])) is not None:
                plant["photos"].append({"id": row["id"], "source": row["source"]})
        for row in self.conn.execute(
            "SELECT plant_id, kind, MAX(at) AS at FROM care_events "
            "WHERE kind IN (?, ?) GROUP BY plant_id, kind",
            (KIND_WATER, KIND_FERTILIZE),
        ):
            if (plant := by_id.get(row["plant_id"])) is not None:
                key = "last_watered" if row["kind"] == KIND_WATER else "last_fertilized"
                plant[key] = row["at"]
        for row in self.conn.execute(
            "SELECT plant_id, at FROM ("
            "  SELECT plant_id, at, ROW_NUMBER() OVER "
            "    (PARTITION BY plant_id ORDER BY at DESC) AS n "
            "  FROM care_events WHERE kind = ?"
            ") WHERE n <= ? ORDER BY at",
            (KIND_WATER, WATERING_HISTORY),
        ):
            if (plant := by_id.get(row["plant_id"])) is not None:
                plant["watering_dates"].append(row["at"])

    def create_plant(self, data: dict[str, Any], now: str) -> dict[str, Any]:
        """Create a plant and return it."""
        plant_id = uuid.uuid4().hex
        fields = {key: _encode(key, data.get(key)) for key in PLANT_FIELDS if key in data}
        fields.update(id=plant_id, created_at=now, updated_at=now)
        for key in JSON_FIELDS:
            fields.setdefault(key, _encode(key, None))
        columns = ", ".join(fields)
        placeholders = ", ".join("?" for _ in fields)
        with self._lock, self.conn:
            self.conn.execute(
                f"INSERT INTO plants ({columns}) VALUES ({placeholders})",
                tuple(fields.values()),
            )
        return self.get_plant(plant_id)

    def update_plant(self, plant_id: str, changes: dict[str, Any], now: str) -> dict[str, Any]:
        """Update plant fields and return the plant."""
        fields = {key: _encode(key, value) for key, value in changes.items() if key in PLANT_FIELDS}
        with self._lock:
            self.get_plant(plant_id)
            if fields:
                fields["updated_at"] = now
                assignments = ", ".join(f"{key} = ?" for key in fields)
                with self.conn:
                    self.conn.execute(
                        f"UPDATE plants SET {assignments} WHERE id = ?",
                        (*fields.values(), plant_id),
                    )
            return self.get_plant(plant_id)

    def delete_plant(self, plant_id: str) -> list[str]:
        """Delete a plant. Returns the photo filenames that should be removed."""
        with self._lock, self.conn:
            self.get_plant(plant_id)
            filenames = [
                row["filename"]
                for row in self.conn.execute(
                    "SELECT filename FROM photos WHERE plant_id = ?", (plant_id,)
                )
            ]
            self.conn.execute("DELETE FROM plants WHERE id = ?", (plant_id,))
            return filenames

    def save_states(self, states: dict[str, dict[str, Any]]) -> None:
        """Write the watering model state of several plants (the fields each state has)."""
        if not states:
            return
        keys = [key for key in STATE_FIELDS if key in next(iter(states.values()))]
        assignments = ", ".join(f"{key} = ?" for key in keys)
        with self._lock, self.conn:
            self.conn.executemany(
                f"UPDATE plants SET {assignments} WHERE id = ?",
                [(*(state[key] for key in keys), plant_id) for plant_id, state in states.items()],
            )

    # -- care log ----------------------------------------------------------

    def add_event(
        self,
        plant_id: str,
        kind: str,
        at: str,
        now: str,
        *,
        feedback: str | None = None,
        notes: str | None = None,
        source: str | None = None,
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Log a care event. ``state`` updates the model state in the same transaction."""
        with self._lock, self.conn:
            plant = self.get_plant(plant_id)
            cursor = self.conn.execute(
                "INSERT INTO care_events (plant_id, kind, at, feedback, notes, source, created_at, "
                "prev_dryness, prev_learned_factor) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    plant_id,
                    kind,
                    at,
                    feedback,
                    notes,
                    source,
                    now,
                    plant["dryness"],
                    plant["learned_factor"],
                ),
            )
            if state:
                fields = {key: value for key, value in state.items() if key in STATE_FIELDS}
                assignments = ", ".join(f"{key} = ?" for key in fields)
                self.conn.execute(
                    f"UPDATE plants SET {assignments} WHERE id = ?", (*fields.values(), plant_id)
                )
            return self.get_event(cursor.lastrowid)

    def get_event(self, event_id: int) -> dict[str, Any]:
        """Return a care event."""
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM care_events WHERE id = ?", (event_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"Care event {event_id} not found")
        return dict(row)

    def delete_event(self, event_id: int, *, restore_state: bool) -> dict[str, Any]:
        """Delete a care event, optionally restoring the model state from before it."""
        with self._lock, self.conn:
            event = self.get_event(event_id)
            self.conn.execute("DELETE FROM care_events WHERE id = ?", (event_id,))
            if restore_state:
                self.conn.execute(
                    "UPDATE plants SET dryness = ?, learned_factor = ?, last_tick = NULL "
                    "WHERE id = ?",
                    (
                        event["prev_dryness"],
                        event["prev_learned_factor"] or 1.0,
                        event["plant_id"],
                    ),
                )
            return event

    def events(self, plant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Care log of a plant, newest first."""
        with self._lock:
            rows = self.conn.execute(
                "SELECT id, kind, at, feedback, notes, source FROM care_events "
                "WHERE plant_id = ? ORDER BY at DESC, id DESC LIMIT ?",
                (plant_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def last_event(self, plant_id: str) -> dict[str, Any] | None:
        """The most recently logged event of a plant."""
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM care_events WHERE plant_id = ? ORDER BY id DESC LIMIT 1",
                (plant_id,),
            ).fetchone()
        return dict(row) if row else None

    # -- photos ------------------------------------------------------------

    def add_photo(self, plant_id: str, filename: str, source: str, now: str) -> dict[str, Any]:
        """Register a stored photo file for a plant."""
        photo_id = uuid.uuid4().hex
        with self._lock, self.conn:
            self.get_plant(plant_id)
            position = self.conn.execute(
                "SELECT COALESCE(MAX(position) + 1, 0) FROM photos WHERE plant_id = ?",
                (plant_id,),
            ).fetchone()[0]
            self.conn.execute(
                "INSERT INTO photos (id, plant_id, filename, position, source, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (photo_id, plant_id, filename, position, source, now),
            )
        return {"id": photo_id, "plant_id": plant_id, "filename": filename, "source": source}

    def get_photo(self, photo_id: str) -> dict[str, Any]:
        """Return a photo record."""
        with self._lock:
            row = self.conn.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Photo {photo_id} not found")
        return dict(row)

    def delete_photo(self, photo_id: str) -> str:
        """Delete a photo record and return its filename."""
        with self._lock, self.conn:
            photo = self.get_photo(photo_id)
            self.conn.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        return photo["filename"]

    def reorder_photos(self, plant_id: str, photo_ids: Iterable[str]) -> None:
        """Set the photo order of a plant."""
        with self._lock, self.conn:
            for position, photo_id in enumerate(photo_ids):
                self.conn.execute(
                    "UPDATE photos SET position = ? WHERE id = ? AND plant_id = ?",
                    (position, photo_id, plant_id),
                )

    # -- vacations ---------------------------------------------------------

    def current_vacation(self, today: str) -> dict[str, Any] | None:
        """The vacation that is planned or going on (not ended, not over before today)."""
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM vacations WHERE ended_at IS NULL AND end_date >= ? "
                "ORDER BY start_date LIMIT 1",
                (today,),
            ).fetchone()
        return dict(row) if row else None

    def save_vacation(
        self, vacation_id: str | None, data: dict[str, Any], now: str
    ) -> dict[str, Any]:
        """Create or update a vacation and return it."""
        fields = {key: data.get(key) for key in VACATION_FIELDS}
        with self._lock, self.conn:
            if vacation_id is None:
                vacation_id = uuid.uuid4().hex
                fields.update(id=vacation_id, created_at=now, updated_at=now)
                self.conn.execute(
                    f"INSERT INTO vacations ({', '.join(fields)}) "
                    f"VALUES ({', '.join('?' for _ in fields)})",
                    tuple(fields.values()),
                )
            else:
                fields["updated_at"] = now
                cursor = self.conn.execute(
                    f"UPDATE vacations SET {', '.join(f'{key} = ?' for key in fields)} "
                    "WHERE id = ?",
                    (*fields.values(), vacation_id),
                )
                if not cursor.rowcount:
                    raise NotFoundError(f"Vacation {vacation_id} not found")
            row = self.conn.execute(
                "SELECT * FROM vacations WHERE id = ?", (vacation_id,)
            ).fetchone()
        return dict(row)

    def end_vacation(self, vacation_id: str, now: str, *, started: bool) -> None:
        """End a vacation early. One that hasn't started yet is removed."""
        with self._lock, self.conn:
            if started:
                self.conn.execute(
                    "UPDATE vacations SET ended_at = ?, updated_at = ? WHERE id = ?",
                    (now, now, vacation_id),
                )
            else:
                self.conn.execute("DELETE FROM vacations WHERE id = ?", (vacation_id,))

    # -- export & backup ---------------------------------------------------

    EXPORT_TABLES = ("plants", "photos", "care_events", "vacations")

    def export_all(self) -> dict[str, list[dict[str, Any]]]:
        """Return every table's rows (JSON columns decoded)."""
        with self._lock:
            data: dict[str, list[dict[str, Any]]] = {}
            for table in self.EXPORT_TABLES:
                rows = [dict(row) for row in self.conn.execute(f"SELECT * FROM {table}")]
                for row in rows:
                    for field in JSON_FIELDS:
                        if isinstance(row.get(field), str):
                            row[field] = json.loads(row[field])
                data[table] = rows
            return data

    def backup_to(self, path: str) -> None:
        """Write a consistent copy of the database to a file."""
        with self._lock:
            target = sqlite3.connect(path)
            try:
                self.conn.backup(target)
            finally:
                target.close()
