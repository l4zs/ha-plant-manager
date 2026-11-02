import {installGardenPanel} from './garden-panel.js?v=20261102-1';
import {plantName} from './garden-common.js?v=20261102-1';
// Plant Manager sidebar panel. Plain web component, no build step.

const DOMAIN = "plant_manager";
const VIEWS = ["plants", "today", "schedule", "vacation"];
const VIEW_LABELS = { plants: "Plants", today: "Today", schedule: "Schedule", vacation: "Vacation" };

// -- translations --------------------------------------------------------
// Texts are written in English and looked up here, with {placeholders}.

const GERMAN = {
  // shell
  Plants: "Pflanzen",
  Today: "Heute",
  Schedule: "Plan",
  Vacation: "Urlaub",
  " (away)": " (weg)",
  Menu: "Menü",
  "My notifications": "Meine Benachrichtigungen",
  "Loading…": "Lädt…",
  "Plant Manager is not available: {error}": "Plant Manager ist nicht verfügbar: {error}",
  never: "nie",
  "Overdue by {n} day": "Seit {n} Tag überfällig",
  "Overdue by {n} days": "Seit {n} Tagen überfällig",
  "Needs water now": "Braucht jetzt Wasser",
  "Water {when}": "Gießen {when}",
  "Estimated water left: {n} %": "Geschätzter Wasservorrat: {n} %",
  // labels
  OK: "OK",
  "Water soon": "Bald gießen",
  "Needs water": "Braucht Wasser",
  Overdue: "Überfällig",
  "Low (far from a window)": "Wenig (weit weg vom Fenster)",
  "Medium (a few metres from a window)": "Mittel (ein paar Meter vom Fenster)",
  "Bright, indirect": "Hell, indirekt",
  "Direct sun": "Direkte Sonne",
  Indoor: "Drinnen",
  "Outdoor, sheltered from rain": "Draußen, vor Regen geschützt",
  "Outdoor, gets rain": "Draußen, bekommt Regen",
  Plastic: "Plastik",
  "Terracotta / unglazed clay": "Terrakotta / unglasierter Ton",
  "Glazed ceramic": "Glasierte Keramik",
  "Fabric grow bag": "Pflanzsack aus Stoff",
  "Self-watering pot": "Selbstbewässerungstopf",
  "No drainage hole": "Ohne Abflussloch",
  Watered: "Jetzt gegossen",
  Fertilized: "Gedüngt",
  "Soil still moist": "Erde noch feucht",
  Repotted: "Umgetopft",
  Pruned: "Geschnitten",
  Misted: "Besprüht",
  Note: "Notiz",
  "soil was too dry": "Erde war zu trocken",
  "just right": "genau richtig",
  "soil was still wet": "Erde war noch nass",
  Water: "Gießen",
  Fertilize: "Düngen",
  "Water before you leave": "Vor der Abreise gießen",
  "Plant sitter waters": "Pflanzensitter gießt",
  "Pot size": "Topfgröße",
  "Pot type": "Topfart",
  Light: "Licht",
  "Room climate": "Raumklima",
  Season: "Jahreszeit",
  Placement: "Standort",
  "Learned from you": "Von dir gelernt",
  "Temperature sensor": "Temperatursensor",
  "Humidity sensor": "Luftfeuchtigkeitssensor",
  "Soil moisture sensor": "Bodenfeuchtesensor",
  "Illuminance sensor": "Helligkeitssensor",
  "Reference watering interval (days)": "Referenz-Gießintervall (Tage)",
  "Fertilize every (days, 0 = never)": "Düngen alle (Tage, 0 = nie)",
  "Min. temperature (°C)": "Min. Temperatur (°C)",
  "Max. temperature (°C)": "Max. Temperatur (°C)",
  "Min. humidity (%)": "Min. Luftfeuchtigkeit (%)",
  "Max. humidity (%)": "Max. Luftfeuchtigkeit (%)",
  "Water below soil moisture (%)": "Gießen unter Bodenfeuchte (%)",
  "Too wet above soil moisture (%)": "Zu nass über Bodenfeuchte (%)",
  "Min. daily peak light (lx)": "Min. Tageshöchstwert Licht (lx)",
  "Max. daily peak light (lx)": "Max. Tageshöchstwert Licht (lx)",
  AI: "KI",
  // plants
  "Search name, species, area…": "Name, Art, Bereich suchen…",
  "All areas": "Alle Bereiche",
  "Any status": "Jeder Status",
  "Needs attention": "Braucht Aufmerksamkeit",
  "+ Add plant": "+ Pflanze hinzufügen",
  "⇅ Import / export": "⇅ Import / Export",
  "No plants match the filters.": "Keine Pflanze passt zu den Filtern.",
  "No plants yet. Add your first plant, take a photo and it is identified for you.":
    "Noch keine Pflanzen. Füge deine erste Pflanze hinzu, mach ein Foto und sie wird für dich erkannt.",
  "Import & export": "Import & Export",
  "Export CSV": "CSV exportieren",
  "Export JSON": "JSON exportieren",
  "Import CSV": "CSV importieren",
  "Download backup": "Sicherung herunterladen",
  "Restore backup…": "Sicherung wiederherstellen…",
  "The CSV has one row per plant and uses the same columns for export and import, so an export is a template for adding many plants from a spreadsheet. Only <b>name</b> and <b>species</b> are needed; the care profile is looked up for the species, and profile columns you fill in win. A backup contains the database and all photos; Home Assistant's own backups include them too.":
    "Die CSV hat eine Zeile pro Pflanze und dieselben Spalten für Export und Import, ein Export ist also eine Vorlage, um viele Pflanzen aus einer Tabelle hinzuzufügen. Nur <b>name</b> und <b>species</b> (Art) sind nötig; das Pflegeprofil wird für die Art nachgeschlagen, und ausgefüllte Profilspalten haben Vorrang. Eine Sicherung enthält die Datenbank und alle Fotos; die Sicherungen von Home Assistant enthalten sie auch.",
  // today
  "💧 Watered": "💧 Jetzt gegossen",
  "Watered; it was too dry, remind me earlier": "Gegossen; es war zu trocken, früher erinnern",
  "Was too dry": "War zu trocken",
  "Not yet; remind me a bit later": "Noch nicht; etwas später erinnern",
  "Still moist": "Noch feucht",
  Problems: "Probleme",
  "Last fertilized {when}": "Zuletzt gedüngt {when}",
  "🌱 Fertilized": "🌱 Gedüngt",
  "Need water": "Brauchen Wasser",
  "All plants are happy. Nothing to do today.": "Alle Pflanzen sind zufrieden. Heute gibt es nichts zu tun.",
  "Add plants to get reminders here.": "Füge Pflanzen hinzu, um hier Erinnerungen zu bekommen.",
  // vacation banner and schedule
  "Away until {date}": "Weg bis {date}",
  "Away {start} – {end}": "Weg {start} – {end}",
  "The plant sitter": "Der Pflanzensitter",
  "{sitter} waters {n} time": "{sitter} gießt {n}-mal",
  "{sitter} waters {n} times": "{sitter} gießt {n}-mal",
  "No one needs to water": "Niemand muss gießen",
  Plan: "Plan",
  "Nothing planned for the next four weeks.": "Für die nächsten vier Wochen ist nichts geplant.",
  "Projected from the current conditions; the schedule adapts to the room climate, the season and your feedback.":
    "Aus den aktuellen Bedingungen berechnet; der Plan passt sich an Raumklima, Jahreszeit und deine Rückmeldungen an.",
  // vacation
  "Add plants first, then plan who waters what while you are away.":
    "Füge zuerst Pflanzen hinzu und plane dann, wer was gießt, während du weg bist.",
  "You're away, back {when}": "Du bist weg, zurück {when}",
  "Leaving {when}": "Abreise {when}",
  " · {sitter} waters": " · {sitter} gießt",
  Change: "Ändern",
  "I'm back": "Ich bin zurück",
  "Cancel vacation": "Urlaub absagen",
  "Change the vacation": "Urlaub ändern",
  "Plan a vacation": "Urlaub planen",
  "Plant Manager works out which plants to water right before you leave, what to move out of the sun, and on which days someone has to come by.":
    "Plant Manager rechnet aus, welche Pflanzen du direkt vor der Abreise gießt, was aus der Sonne muss und an welchen Tagen jemand vorbeikommen muss.",
  "Leaving (in the morning)": "Abreise (morgens)",
  "Back (in the evening)": "Zurück (abends)",
  "Plant sitter": "Pflanzensitter",
  "Name (optional)": "Name (optional)",
  "Sitter's notify action": "Benachrichtigungsaktion des Sitters",
  "Notes for the sitter": "Notizen für den Sitter",
  "Where the key and the watering can are, …": "Wo der Schlüssel und die Gießkanne sind, …",
  "With a notify action, the sitter gets a reminder on the morning of each day they need to come.":
    "Mit einer Benachrichtigungsaktion bekommt der Sitter an jedem Tag, an dem er kommen muss, morgens eine Erinnerung.",
  Save: "Speichern",
  "Save vacation": "Urlaub speichern",
  Cancel: "Abbrechen",
  Plant: "Pflanze",
  "Before you leave": "Vor der Abreise",
  "Water thoroughly the day before or the morning you leave": "Am Tag vorher oder am Morgen der Abreise gründlich gießen",
  "Last watered {when}": "Zuletzt gegossen {when}",
  "Never watered": "Noch nie gegossen",
  "So they dry out more slowly": "Damit sie langsamer austrocknen",
  "(lasts {with} instead of {without} days)": "(hält {with} statt {without} Tage)",
  "{sitter} waters on {n} day": "{sitter} gießt an {n} Tag",
  "{sitter} waters on {n} days": "{sitter} gießt an {n} Tagen",
  "🎉 No one needs to come: every plant lasts until you are back.":
    "🎉 Niemand muss kommen: jede Pflanze hält durch, bis du zurück bist.",
  "🎉 No one needs to come: every plant lasts until you are back if you water the ones above before leaving.":
    "🎉 Niemand muss kommen: jede Pflanze hält durch, bis du zurück bist, wenn du die oben genannten vor der Abreise gießt.",
  "Send to {sitter}": "An {sitter} senden",
  "the sitter": "den Sitter",
  "Copy plan": "Plan kopieren",
  "Print plan": "Plan drucken",
  Lasts: "Hält durch",
  "Lasts after watering": "Hält nach dem Gießen durch",
  "Lasts if moved": "Hält, wenn umgestellt",
  "Sitter: {n}×": "Sitter: {n}×",
  "All plants": "Alle Pflanzen",
  "Water lasts": "Wasser reicht",
  "While away": "Während du weg bist",
  "{n} d": "{n} T",
  "Projected for {days} days away with today's room climate and the season mid-trip. Turning the heating down or the air conditioning off changes how fast the soil dries. Nobody to water? A wick from a jug of water, a self-watering spike, or a bathtub with a few centimetres of water on a towel keeps most potted plants going for one or two weeks.":
    "Berechnet für {days} Tage mit dem heutigen Raumklima und der Jahreszeit zur Reisemitte. Wenn du die Heizung herunter- oder die Klimaanlage ausschaltest, trocknet die Erde anders schnell. Niemand zum Gießen? Ein Docht aus einem Wasserkrug, ein Bewässerungskegel oder eine Badewanne mit ein paar Zentimetern Wasser auf einem Handtuch versorgen die meisten Topfpflanzen ein bis zwei Wochen.",
  "Thank you, {sitter}!": "Danke, {sitter}!",
  "Plant care": "Pflanzenpflege",
  "How to water": "So wird gegossen",
  "Water slowly until it runs out at the bottom, then empty the saucer after 15 minutes. If the soil is still moist 2 cm deep, skip it.":
    "Langsam gießen, bis unten Wasser herausläuft, und den Untersetzer nach 15 Minuten leeren. Ist die Erde in 2 cm Tiefe noch feucht, die Pflanze auslassen.",
  Notes: "Notizen",
  "Allow pop-ups to print the plan": "Erlaube Pop-ups, um den Plan zu drucken",
  // notifications
  "Send to": "Senden an",
  "(someone else's)": "(von jemand anderem)",
  "No phones yet. Install the Home Assistant app on your phone and log in to this Home Assistant; the phone then shows up here.":
    "Noch keine Handys. Installiere die Home-Assistant-App auf deinem Handy und melde dich bei diesem Home Assistant an; dann erscheint das Handy hier.",
  What: "Was",
  "Daily summary: what to water and fertilize": "Tägliche Übersicht: was gegossen und gedüngt werden muss",
  At: "Um",
  "Problems right away (too cold, too dark, soil too wet, …)": "Probleme sofort (zu kalt, zu dunkel, Erde zu nass, …)",
  "The summary is only sent on days with something to do; while you are on vacation it says what the plant sitter waters. These settings are only for you{user}; everyone can choose their own.":
    "Die Übersicht kommt nur an Tagen, an denen etwas zu tun ist; während du im Urlaub bist, sagt sie, was der Pflanzensitter gießt. Diese Einstellungen gelten nur für dich{user}; alle können ihre eigenen wählen.",
  "Save and send a test": "Speichern und Test senden",
  // editor
  "Could not load plant: {error}": "Pflanze konnte nicht geladen werden: {error}",
  "New plant": "Neue Pflanze",
  "Saving…": "Speichert…",
  "Take a photo of the plant (leaves in view) and {provider} suggests what it is.":
    "Mach ein Foto der Pflanze (mit Blättern im Bild) und {provider} schlägt vor, was es ist.",
  "Add a photo. To identify plants from photos, choose a service under <b>Settings → Devices & services → Plant Manager → Configure</b>.":
    "Füge ein Foto hinzu. Um Pflanzen auf Fotos zu erkennen, wähle einen Dienst unter <b>Einstellungen → Geräte & Dienste → Plant Manager → Konfigurieren</b>.",
  "Identifying…": "Erkenne…",
  "{n} % match": "{n} % Übereinstimmung",
  "Pick the right one, or type the species below if none fits.": "Wähle die richtige aus, oder gib unten die Art ein, wenn keine passt.",
  "The plant could not be identified. Try a closer photo of the leaves, or enter the species below.":
    "Die Pflanze konnte nicht erkannt werden. Versuch ein näheres Foto der Blätter, oder gib unten die Art ein.",
  "The identification service rejected the API key.": "Der Erkennungsdienst hat den API-Schlüssel abgelehnt.",
  "The identification service's daily quota is used up.": "Das Tageskontingent des Erkennungsdienstes ist aufgebraucht.",
  "Could not reach the identification service.": "Der Erkennungsdienst ist nicht erreichbar.",
  "No plant was recognised in this photo.": "Auf diesem Foto wurde keine Pflanze erkannt.",
  "Identification failed. Check the logs.": "Die Erkennung ist fehlgeschlagen. Sieh im Protokoll nach.",
  "Identify again": "Neu erkennen",
  Identify: "Erkennen",
  "📷 Take photo": "📷 Foto aufnehmen",
  "⬆ Upload": "⬆ Hochladen",
  "waters less often": "seltener gießen",
  "waters more often": "öfter gießen",
  Care: "Pflege",
  "Next watering": "Nächstes Gießen",
  Every: "Alle",
  "{n} days": "{n} Tage",
  "Water left": "Wasservorrat",
  "Last watered": "Zuletzt gegossen",
  "Soil before watering": "Erde vor dem Gießen",
  "Soil before watering…": "Erde vor dem Gießen…",
  "Why every {n} days": "Warum alle {n} Tage",
  "Reference interval for the species": "Referenzintervall der Art",
  "{n} % humidity": "{n} % Luftfeuchtigkeit",
  "soil {n} %": "Erde {n} %",
  "fertilizing rests in winter": "Düngen pausiert im Winter",
  "fertilize {when}": "düngen {when}",
  "no fertilizing": "kein Dünger",
  Cover: "Titelbild",
  "Make cover": "Als Titelbild",
  Delete: "Löschen",
  "On save": "Beim Speichern",
  Remove: "Entfernen",
  Photos: "Fotos",
  "No photos yet.": "Noch keine Fotos.",
  Details: "Details",
  Name: "Name",
  "e.g. Monty": "z. B. Monty",
  Species: "Art",
  "e.g. Monstera deliciosa": "z. B. Monstera deliciosa",
  "Common name": "Trivialname",
  Area: "Bereich",
  None: "Keiner",
  "No areas set up": "Keine Bereiche eingerichtet",
  Location: "Standort",
  "Light at its spot": "Licht an ihrem Platz",
  "Pot diameter (cm)": "Topfdurchmesser (cm)",
  "Got it on": "Bekommen am",
  Sensors: "Sensoren",
  "Room temperature and humidity tune the watering interval (warm, dry air dries the soil faster). A soil moisture sensor replaces the estimate and detects waterings by itself. Light is used to warn when the spot is too dark or too bright.":
    "Raumtemperatur und Luftfeuchtigkeit passen das Gießintervall an (warme, trockene Luft trocknet die Erde schneller). Ein Bodenfeuchtesensor ersetzt die Schätzung und erkennt das Gießen selbst. Mit dem Licht wird gewarnt, wenn der Platz zu dunkel oder zu hell ist.",
  "Care profile": "Pflegeprofil",
  "Looking up care for {species}…": "Schlage die Pflege für {species} nach…",
  "From {sources}.": "Aus {sources}.",
  "Prefers {light} light.": "Mag Licht: {light}.",
  "⚠ Toxic to pets.": "⚠ Giftig für Haustiere.",
  "Safe for pets.": "Ungiftig für Haustiere.",
  "Rests in winter (waters much less, no fertilizer)": "Ruht im Winter (viel weniger gießen, kein Dünger)",
  "The reference interval is for a 15 cm plastic pot, medium light, 21 °C and 50 % humidity in summer. Pot, light, room climate and season are applied on top.":
    "Das Referenzintervall gilt für einen 15-cm-Plastiktopf, mittleres Licht, 21 °C und 50 % Luftfeuchtigkeit im Sommer. Topf, Licht, Raumklima und Jahreszeit kommen dazu.",
  "Look up care for the species again": "Pflege für die Art neu nachschlagen",
  "Care log": "Pflegeprotokoll",
  "Notes (optional)": "Notizen (optional)",
  Add: "Hinzufügen",
  "(detected by the moisture sensor)": "(vom Feuchtesensor erkannt)",
  "Nothing logged yet.": "Noch nichts eingetragen.",
  "Delete plant": "Pflanze löschen",
  "Please enter a name": "Bitte gib einen Namen ein",
  "Please enter the species, or take a photo to identify it": "Bitte gib die Art ein oder mach ein Foto, um sie zu erkennen",
  "Saved, but {n} photo(s) failed: {error}": "Gespeichert, aber {n} Foto(s) fehlgeschlagen: {error}",
  "Saved {name}": "{name} gespeichert",
  "Could not save: {error}": "Speichern fehlgeschlagen: {error}",
  "Upload failed: {error}": "Hochladen fehlgeschlagen: {error}",
  "Could not look up the care profile: {error}": "Das Pflegeprofil konnte nicht nachgeschlagen werden: {error}",
  // toasts
  "Too late to undo": "Zu spät zum Rückgängigmachen",
  Undone: "Rückgängig gemacht",
  Undo: "Rückgängig",
  "{name} watered": "{name} gegossen",
  "OK, {name} is reminded a bit later": "OK, an {name} wird etwas später erinnert",
  Logged: "Eingetragen",
  Removed: "Entfernt",
  "Photo deleted": "Foto gelöscht",
  "Notifications saved": "Benachrichtigungen gespeichert",
  "Test sent to {n} phone": "Test an {n} Handy gesendet",
  "Test sent to {n} phones": "Test an {n} Handys gesendet",
  "Vacation saved. Have a good trip!": "Urlaub gespeichert. Gute Reise!",
  "End the vacation now? Reminders go back to you.": "Urlaub jetzt beenden? Die Erinnerungen gehen wieder an dich.",
  "Cancel the planned vacation?": "Den geplanten Urlaub absagen?",
  "Welcome back! 🌿": "Willkommen zurück! 🌿",
  "Vacation cancelled": "Urlaub abgesagt",
  "Sent to {sitter}": "An {sitter} gesendet",
  "Plan copied": "Plan kopiert",
  "Copying is not allowed here; use Print plan instead": "Kopieren ist hier nicht erlaubt; nutze stattdessen Plan drucken",
  "Delete {name} with its photos and care log?": "{name} mit Fotos und Pflegeprotokoll löschen?",
  "Deleted {name}": "{name} gelöscht",
  skipped: "übersprungen",
  "Imported {n} plant(s).": "{n} Pflanze(n) importiert.",
  "Imported {n} plant(s)": "{n} Pflanze(n) importiert",
  "⚠ Row {row} {name}: {error}": "⚠ Zeile {row} {name}: {error}",
  "Import failed: {error}": "Import fehlgeschlagen: {error}",
  "Replace ALL plants, photos and care logs with this backup? The current data is kept as *.before-restore.":
    "ALLE Pflanzen, Fotos und Pflegeprotokolle durch diese Sicherung ersetzen? Die aktuellen Daten bleiben als *.before-restore erhalten.",
  "Restored {plants} plant(s) and {photos} photo(s)": "{plants} Pflanze(n) und {photos} Foto(s) wiederhergestellt",
  "Restore failed: {error}": "Wiederherstellen fehlgeschlagen: {error}",
  // where a care profile came from (stored in English)
  "built-in database": "eingebaute Datenbank",
  "AI estimate": "KI-Schätzung",
  "generic defaults": "allgemeine Standardwerte",
  "CSV import": "CSV-Import",
};

const TRANSLATIONS = { de: GERMAN };
let LANG = "en";
let LOCALE = "en"; // for numbers: "5,3" in German

// The user's language from their Home Assistant profile ("de", "de-CH", ...).
const languageOf = () => "de";

const t = (text, values = {}) =>
  (TRANSLATIONS[LANG]?.[text] ?? text).replace(/\{(\w+)\}/g, (match, key) =>
    key in values ? String(values[key]) : match
  );

// Singular or plural, with the count as {n}.
const tn = (n, one, other, values = {}) => t(n === 1 ? one : other, { n, ...values });

// A number with a fixed count of decimals, in the user's locale.
const num = (value, digits = 1) =>
  new Intl.NumberFormat(LOCALE, { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);

const SOURCE_PREFIXES = ["built-in database", "AI estimate", "generic defaults", "CSV import"];
const sourceLabel = (source) => {
  const prefix = SOURCE_PREFIXES.find((p) => source.startsWith(p));
  return prefix ? t(prefix) + source.slice(prefix.length) : source;
};

const LABELS = {
  // statuses
  ok: "OK",
  water_soon: "Water soon",
  needs_water: "Needs water",
  overdue: "Overdue",
  // light
  low: "Low (far from a window)",
  medium: "Medium (a few metres from a window)",
  bright_indirect: "Bright, indirect",
  direct: "Direct sun",
  // placement
  indoor: "Indoor",
  outdoor_covered: "Outdoor, sheltered from rain",
  outdoor: "Outdoor, gets rain",
  // pots
  terracotta: "Terracotta / unglazed clay",
  ceramic: "Glazed ceramic",
  fabric: "Fabric grow bag",
  self_watering: "Self-watering pot",
  no_drainage: "No drainage hole",
  // care log
  water: "Watered",
  fertilize: "Fertilized",
  snooze: "Soil still moist",
  repot: "Repotted",
  prune: "Pruned",
  mist: "Misted",
  note: "Note",
  // feedback
  too_dry: "soil was too dry",
  just_right: "just right",
  too_wet: "soil was still wet",
};

const KIND_ICONS = {
  water: "💧",
  fertilize: "🌱",
  snooze: "😴",
  repot: "🪴",
  prune: "✂️",
  mist: "💦",
  note: "📝",
  prepare: "🧳",
  sitter: "🧑‍🌾",
};

const SCHEDULE_LABELS = {
  water: "Water",
  fertilize: "Fertilize",
  prepare: "Water before you leave",
  sitter: "Plant sitter waters",
};

const FACTOR_LABELS = {
  pot_size: "Pot size",
  pot_material: "Pot type",
  light: "Light",
  climate: "Room climate",
  season: "Season",
  placement: "Placement",
  learned: "Learned from you",
};

const SENSOR_LABELS = {
  temperature_sensor: "Temperature sensor",
  humidity_sensor: "Humidity sensor",
  moisture_sensor: "Soil moisture sensor",
  illuminance_sensor: "Illuminance sensor",
};

const PROFILE_FIELDS = [
  ["base_interval_days", "Reference watering interval (days)", 0.5],
  ["fertilize_interval_days", "Fertilize every (days, 0 = never)", 1],
  ["min_temp", "Min. temperature (°C)", 0.5],
  ["max_temp", "Max. temperature (°C)", 0.5],
  ["min_humidity", "Min. humidity (%)", 1],
  ["max_humidity", "Max. humidity (%)", 1],
  ["min_soil_moisture", "Water below soil moisture (%)", 1],
  ["max_soil_moisture", "Too wet above soil moisture (%)", 1],
  ["min_light_lux", "Min. daily peak light (lx)", 100],
  ["max_light_lux", "Max. daily peak light (lx)", 100],
];

const PROVIDER_LABELS = { plantnet: "Pl@ntNet", plantid: "Plant.id", ai_task: "AI" };

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );

const human = (key) =>
  t(LABELS[key] ?? (key ? key.charAt(0).toUpperCase() + key.slice(1).replaceAll("_", " ") : ""));

const isoDate = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

const addDays = (d, days) => {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + days);
  return copy;
};

// A plain YYYY-MM-DD date at noon, so time zones don't shift the day.
const localDay = (day) => new Date(`${day}T12:00:00`);

function startOfDay(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

// "today", "in 3 days", "2 weeks ago"
function relativeDay(iso, lang) {
  if (!iso) return t("never");
  const days = Math.round((startOfDay(iso) - startOfDay(Date.now())) / 86400000);
  const format = new Intl.RelativeTimeFormat(lang || "en", { numeric: "auto" });
  if (Math.abs(days) < 14) return format.format(days, "day");
  if (Math.abs(days) < 60) return format.format(Math.round(days / 7), "week");
  if (Math.abs(days) < 550) return format.format(Math.round(days / 30), "month");
  return format.format(Math.round(days / 365), "year");
}

function dueText(care, lang) {
  if (!care) return "";
  if (care.needs_water) {
    const late = Math.round((care.dryness - 1) * care.interval_days);
    return late >= 1 ? tn(late, "Overdue by {n} day", "Overdue by {n} days") : t("Needs water now");
  }
  return t("Water {when}", { when: relativeDay(care.next_watering, lang) });
}

const reserveColor = (care) =>
  !care
    ? "var(--pm-divider)"
    : care.needs_water
      ? "var(--error-color, #db4437)"
      : care.status === "water_soon"
        ? "var(--warning-color, #ef8f00)"
        : "var(--pm-water)";

async function resizeImage(file, max = 1600) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
}

// -- styles --------------------------------------------------------------

const STYLES = `
  :host {
    display: block;
    min-height: 100vh;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    --pm-radius: var(--ha-card-border-radius, 12px);
    --pm-card: var(--card-background-color, #fff);
    --pm-muted: var(--secondary-text-color);
    --pm-divider: var(--divider-color, rgba(0,0,0,.12));
    --pm-accent: var(--primary-color);
    --pm-leaf: #43a047;
    --pm-water: #039be5;
  }
  * { box-sizing: border-box; }
  .toolbar {
    position: sticky; top: 0; z-index: 2;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 8px 16px; min-height: 56px;
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, #fff);
  }
  .toolbar h1 { font-size: 20px; font-weight: 400; margin: 0 16px 0 0; }
  .tabs { display: flex; gap: 4px; overflow-x: auto; }
  .tab {
    background: none; border: none; color: inherit; opacity: .75; cursor: pointer;
    padding: 8px 12px; border-radius: 18px; font: inherit; white-space: nowrap;
  }
  .tab.active { opacity: 1; font-weight: 500; box-shadow: inset 0 -2px 0 currentColor; border-radius: 0; }
  .badge {
    display: inline-block; min-width: 18px; padding: 0 5px; margin-left: 4px;
    border-radius: 9px; background: var(--error-color, #db4437); color: #fff;
    font-size: 12px; line-height: 18px; text-align: center;
  }
  .menu { background: none; border: none; color: inherit; cursor: pointer; padding: 8px; }
  main { padding: 16px; max-width: 1400px; margin: 0 auto; }
  .filters { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; align-items: center; }
  .filters input[type=search] { flex: 1 1 200px; }
  input, select, textarea {
    font: inherit; color: var(--primary-text-color);
    background: var(--input-fill-color, var(--secondary-background-color));
    border: 1px solid var(--pm-divider); border-radius: 8px; padding: 8px 10px;
    min-width: 0;
  }
  textarea { width: 100%; min-height: 70px; resize: vertical; }
  .btn {
    display: inline-flex; align-items: center; gap: 4px;
    font: inherit; cursor: pointer; border-radius: 18px; padding: 8px 16px;
    border: 1px solid var(--pm-divider); background: var(--pm-card); color: var(--primary-text-color);
  }
  .btn.primary { background: var(--pm-accent); color: var(--text-primary-color, #fff); border-color: transparent; }
  .btn.water { background: var(--pm-water); color: #fff; border-color: transparent; }
  .btn.small { padding: 4px 12px; font-size: 13px; }
  .btn.danger { color: var(--error-color, #db4437); }
  .btn:disabled { opacity: .5; cursor: default; }
  button.link { background: none; border: none; color: var(--pm-accent); cursor: pointer; font: inherit; padding: 4px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; }
  .plant-card {
    display: flex; flex-direction: column; text-align: left; padding: 0; cursor: pointer;
    background: var(--pm-card); border: 1px solid var(--pm-divider); border-radius: var(--pm-radius);
    overflow: hidden; color: inherit; font: inherit;
  }
  .narrow .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .narrow main { padding: 12px; }
  .plant-card.needs { border-color: var(--error-color, #db4437); }
  .thumb {
    aspect-ratio: 1; width: 100%; display: flex; align-items: center; justify-content: center;
    background: linear-gradient(160deg, rgba(67,160,71,.18), rgba(67,160,71,.06)); position: relative;
    font-size: 42px;
  }
  .thumb img { width: 100%; height: 100%; object-fit: cover; }
  .thumb .quick { position: absolute; right: 8px; bottom: 8px; }
  .plant-card .info { padding: 8px 10px 10px; display: flex; flex-direction: column; gap: 4px; }
  .name { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .species { font-style: italic; }
  .meta, .muted { color: var(--pm-muted); font-size: 13px; }
  .chip {
    display: inline-block; font-size: 12px; padding: 1px 8px; border-radius: 10px;
    background: var(--secondary-background-color); color: var(--primary-text-color);
  }
  .chip.ok { background: rgba(67,160,71,.2); }
  .chip.water_soon { background: rgba(255,152,0,.22); }
  .chip.needs_water, .chip.overdue, .chip.problem { background: rgba(219,68,55,.2); }
  .reserve { height: 6px; border-radius: 3px; background: var(--secondary-background-color); overflow: hidden; }
  .reserve > div { height: 100%; border-radius: 3px; }
  .row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .section {
    background: var(--pm-card); border: 1px solid var(--pm-divider); border-radius: var(--pm-radius);
    padding: 16px; margin-bottom: 16px;
  }
  .section.alerts { border-color: var(--warning-color, #ef8f00); }
  .section h2 { font-size: 16px; font-weight: 500; margin: 0 0 12px; }
  .section h3 { font-size: 14px; font-weight: 500; margin: 12px 0 4px; color: var(--pm-muted); }
  .list { display: flex; flex-direction: column; }
  .list-row {
    display: flex; align-items: center; gap: 12px; padding: 8px 0;
    border-bottom: 1px solid var(--pm-divider);
  }
  .list-row:last-child { border-bottom: none; }
  .list-row .grow { flex: 1; min-width: 0; }
  .mini { width: 48px; height: 48px; border-radius: 8px; overflow: hidden; flex: none; }
  .mini .thumb { aspect-ratio: auto; height: 100%; font-size: 24px; }
  .empty { color: var(--pm-muted); padding: 24px; text-align: center; }
  .hero { font-size: 40px; margin-bottom: 8px; }
  code { font-size: 12px; word-break: break-all; }
  .day-head { font-weight: 500; margin: 16px 0 4px; }
  .day-head:first-child { margin-top: 0; }
  .warning { font-size: 14px; margin: 4px 0; }
  .warning.high { color: var(--error-color, #db4437); }
  .warning.medium { color: var(--warning-color, #ef8f00); }
  .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .tile { background: var(--pm-card); border: 1px solid var(--pm-divider); border-radius: var(--pm-radius); padding: 14px 16px; }
  .tile .value { font-size: 28px; font-weight: 500; margin-top: 2px; }
  table { border-collapse: collapse; width: 100%; font-size: 14px; }
  td, th { padding: 6px 8px; border-bottom: 1px solid var(--pm-divider); text-align: left; }
  th { font-weight: 500; color: var(--pm-muted); }
  .num { text-align: right; font-variant-numeric: tabular-nums; }

  /* editor */
  .overlay {
    position: fixed; inset: 0; z-index: 10; background: rgba(0,0,0,.45);
    display: flex; align-items: flex-start; justify-content: center; overflow-y: auto; padding: 24px 12px;
  }
  .dialog {
    width: 100%; max-width: 820px; background: var(--primary-background-color);
    border-radius: var(--pm-radius); overflow: hidden;
  }
  .narrow .overlay { padding: 0; }
  .narrow .dialog { border-radius: 0; min-height: 100vh; }
  .dialog-head {
    position: sticky; top: 0; z-index: 1; display: flex; align-items: center; gap: 8px;
    padding: 10px 16px; background: var(--pm-card); border-bottom: 1px solid var(--pm-divider);
  }
  .dialog-head h2 { flex: 1; margin: 0; font-size: 18px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dialog-body { padding: 16px; }
  .form { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
  .field { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: var(--pm-muted); }
  .field.wide { grid-column: 1 / -1; }
  .field.check { flex-direction: row; align-items: center; gap: 8px; color: var(--primary-text-color); font-size: 15px; }
  .field > input, .field > select, .field > textarea { color: var(--primary-text-color); font-size: 15px; }
  .photos { display: flex; gap: 10px; flex-wrap: wrap; }
  .photo { width: 120px; display: flex; flex-direction: column; gap: 4px; }
  .photo .thumb { border-radius: 8px; overflow: hidden; }
  .photo.pending .thumb { outline: 2px dashed var(--pm-accent); }
  .photo .actions { display: flex; justify-content: space-between; }
  .cover-badge {
    position: absolute; top: 4px; left: 4px; background: var(--pm-accent); color: #fff;
    font-size: 11px; padding: 1px 6px; border-radius: 8px;
  }
  .candidates { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px; margin-top: 12px; }
  .candidate {
    display: flex; flex-direction: column; gap: 4px; text-align: left; cursor: pointer; font: inherit; color: inherit;
    border: 1px solid var(--pm-divider); border-radius: var(--pm-radius); padding: 10px 12px; background: var(--pm-card);
  }
  .candidate.chosen { border-color: var(--pm-leaf); box-shadow: inset 0 0 0 1px var(--pm-leaf); }
  .score { height: 4px; border-radius: 2px; background: var(--secondary-background-color); overflow: hidden; }
  .score > div { height: 100%; background: var(--pm-leaf); }
  .hint { font-size: 13px; color: var(--pm-muted); margin: 6px 0 0; }
  .facts { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 12px; }
  .fact .value { font-size: 20px; }
  .toast {
    position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%); z-index: 20;
    background: #323232; color: #fff; padding: 12px 16px; border-radius: 8px;
    display: flex; gap: 12px; align-items: center; max-width: calc(100vw - 32px);
    box-shadow: 0 3px 12px rgba(0,0,0,.3);
  }
  .toast button { background: none; border: none; color: var(--pm-accent); cursor: pointer; font: inherit; font-weight: 500; }
  .actions-bar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .banner {
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 16px;
    padding: 12px 16px; border-radius: var(--pm-radius); background: rgba(3,155,229,.12);
    border: 1px solid rgba(3,155,229,.35);
  }
  .banner .grow { flex: 1; min-width: 200px; }
  .chip.measures { background: rgba(255,152,0,.22); }
  .chip.sitter { background: rgba(3,155,229,.2); }
  .tip { font-size: 14px; margin: 2px 0; }
`;

// -- panel ---------------------------------------------------------------

class PlantManagerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._view = "plants";
    this._filter = { q: "", area: "", status: "" };
    this._plants = [];
    this._alerts = [];
    this._schedule = [];
    this._trip = { vacation: null, plan: null, text: null };
    this._tripDraft = null; // the vacation form while planning or editing
    this._tripPreview = null;
    this._showData = false;
    this._importReport = "";
    this._editor = null;
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener("input", (ev) => this._onInput(ev));
    this.shadowRoot.addEventListener("change", (ev) => this._onChange(ev));
  }

  set hass(hass) {
    const first = !this._hass;
    const language = languageOf(hass);
    const changed = language !== LANG;
    LANG = language;
    LOCALE = "de-DE";
    this._hass = hass;
    if (first) this._init();
    else if (changed && this._config) this._reloadLanguage();
  }

  // Texts from the backend (species, problems, the sitter's plan) come in the new language.
  async _reloadLanguage() {
    try {
      await this._load();
    } catch (err) {
      // keep what is shown
    }
    this._renderShell();
    if (this._notify) this._renderNotify();
  }

  get hass() {
    return this._hass;
  }

  set narrow(narrow) {
    const changed = this._narrow !== narrow;
    this._narrow = narrow;
    if (changed && this._config) this._renderShell();
  }

  set route(route) {
    this._route = route;
    if (this._config) this._gardenOpenFromLocation?.();
    const view = (route?.path || "").replace(/^\//, "").split("/")[0];
    if (VIEWS.includes(view) && view !== this._view) {
      this._view = view;
      if (this._config) this._renderShell();
    }
  }

  set panel(panel) {
    this._panel = panel;
  }

  connectedCallback() {
    if (this._hass && this._config && !this._unsub) this._subscribe();
  }

  disconnectedCallback() {
    if (this._unsub) this._unsub.then((unsub) => unsub()).catch(() => {});
    this._unsub = null;
  }

  // -- data --------------------------------------------------------------

  _ws(command, data = {}) {
    return this._hass.callWS({ type: `${DOMAIN}/${command}`, language: LANG, ...data });
  }

  async _init() {
    this.shadowRoot.innerHTML = `<style>${STYLES}</style><main><div class="empty">${t("Loading…")}</div></main>`;
    try {
      await this._load();
    } catch (err) {
      this.shadowRoot.innerHTML = `<style>${STYLES}</style><main><div class="empty">${esc(t("Plant Manager is not available: {error}", { error: err.message }))}</div></main>`;
      return;
    }
    this._renderShell();
    this._subscribe();
  }

  async _load() {
    const [config, plants, alerts, schedule, trip] = await Promise.all([
      this._ws("config"),
      this._ws("plants/list"),
      this._ws("alerts"),
      this._ws("schedule", { days: 28 }),
      this._ws("vacation/get"),
    ]);
    this._config = config;
    this._plants = plants;
    this._alerts = alerts;
    this._schedule = schedule;
    this._trip = trip;
    this._plantsById = Object.fromEntries(plants.map((plant) => [plant.id, plant]));
  }

  _subscribe() {
    this._unsub = this._hass.connection.subscribeMessage(
      (message) => this._onEvent(message),
      { type: `${DOMAIN}/subscribe` }
    );
  }

  _onEvent(message) {
    if (message.type !== "updated") return;
    clearTimeout(this._reloadTimer);
    this._reloadTimer = setTimeout(async () => {
      await this._load();
      this._renderTabs();
      this._renderMain();
      if (this._editor?.id && !this._editor.busy) this._refreshEditorPlant();
    }, 250);
  }

  _areas() {
    return Object.values(this._hass.areas || {}).sort((a, b) => a.name.localeCompare(b.name));
  }

  _areaName(areaId) {
    return this._hass.areas?.[areaId]?.name || "";
  }

  // -- rendering ---------------------------------------------------------

  _renderShell() {
    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <div class="${this._narrow ? "narrow" : ""}">
        <div class="toolbar">
          ${this._narrow ? `<button class="menu" data-action="menu" title="${t("Menu")}">☰</button>` : ""}
          <h1>${t("Plants")}</h1>
          <div class="tabs" id="tabs"></div>
          <button class="menu" data-action="open-notify" title="${t("My notifications")}" style="margin-left:auto">🔔</button>
        </div>
        <main id="main"></main>
        <div id="editor"></div>
        <div id="notify"></div>
        <div id="toast"></div>
      </div>`;
    this._renderTabs();
    this._renderMain();
    if (this._editor) this._renderEditor();
  }

  _renderTabs() {
    const tabs = this.shadowRoot.getElementById("tabs");
    if (!tabs) return;
    const needs = this._plants.filter((p) => p.care?.needs_water).length;
    const badges = { today: needs + this._alerts.filter((a) => a.kind === "problem").length };
    const away = this._trip?.plan?.active;
    tabs.innerHTML = VIEWS.map(
      (view) => `
        <button class="tab ${view === this._view ? "active" : ""}" data-action="view" data-view="${view}">
          ${view === "vacation" && this._trip?.vacation ? "🧳 " : ""}${t(VIEW_LABELS[view])}${
            view === "vacation" && away ? t(" (away)") : ""
          }${badges[view] ? `<span class="badge">${badges[view]}</span>` : ""}
        </button>`
    ).join("");
  }

  _renderMain() {
    const main = this.shadowRoot.getElementById("main");
    if (!main) return;
    const render = {
      plants: () => this._renderPlants(),
      today: () => this._renderToday(),
      schedule: () => this._renderSchedule(),
      vacation: () => this._renderVacation(),
    }[this._view];
    const focused = this.shadowRoot.activeElement;
    const key = focused?.dataset?.filter ? "filter" : focused?.dataset?.trip ? "trip" : null;
    const value = key && focused.dataset[key];
    const caret = focused?.selectionStart;
    main.innerHTML = render();
    if (key) {
      const input = main.querySelector(`[data-${key}="${value}"]`);
      input?.focus();
      if (caret != null && input?.setSelectionRange && input.type !== "date") {
        input.setSelectionRange(caret, caret);
      }
    }
    if (this._view === "vacation" && !this._trip?.vacation && !this._tripDraft) this._startTripDraft();
  }

  _thumb(plant, mini = false) {
    const photo = plant?.photos?.[0];
    const inner = photo ? `<img src="${esc(photo.url)}" alt="" loading="lazy">` : "🪴";
    const thumb = `<div class="thumb">${inner}</div>`;
    return mini ? `<div class="mini">${thumb}</div>` : thumb;
  }

  _options(values, selected, { empty, label = human } = {}) {
    const options = empty !== undefined ? [`<option value="">${esc(empty)}</option>`] : [];
    for (const value of values) {
      options.push(
        `<option value="${esc(value)}" ${String(value) === String(selected ?? "") ? "selected" : ""}>${esc(label(value))}</option>`
      );
    }
    return options.join("");
  }

  _filteredPlants() {
    const { q, area, status } = this._filter;
    const query = q.trim().toLowerCase();
    return this._plants
      .filter((plant) => {
        if (area && plant.area_id !== area) return false;
        if (status === "attention") {
          if (!plant.care?.needs_water && !plant.care?.problems?.length) return false;
        } else if (status && plant.care?.status !== status) return false;
        if (!query) return true;
        return [plantName(plant), plant.name, plant.species, plant.common_name, this._areaName(plant.area_id)]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(query));
      })
      .sort((a, b) => (a.care?.next_watering || "").localeCompare(b.care?.next_watering || ""));
  }

  _reserveBar(care) {
    const share = Math.max(0, Math.min(100, care?.water_reserve ?? 0));
    return `<div class="reserve" title="${t("Estimated water left: {n} %", { n: Math.round(share) })}"><div style="width:${share}%;background:${reserveColor(care)}"></div></div>`;
  }

  _renderPlants() {
    const { q, area, status } = this._filter;
    const plants = this._filteredPlants();
    const lang = "de-DE";
    const areas = this._areas();
    return `
      <div class="filters">
        <input type="search" placeholder="${esc(t("Search name, species, area…"))}" value="${esc(q)}" data-filter="q">
        ${areas.length ? `<select data-filter="area">${this._options(areas.map((a) => a.area_id), area, { empty: t("All areas"), label: (id) => this._areaName(id) })}</select>` : ""}
        <select data-filter="status">
          <option value="" ${status === "" ? "selected" : ""}>${t("Any status")}</option>
          <option value="attention" ${status === "attention" ? "selected" : ""}>${t("Needs attention")}</option>
          ${this._options(this._config.statuses, status)}
        </select>
        <button class="btn primary" data-action="new-plant">${t("+ Add plant")}</button>
        <button class="btn" data-action="toggle-data" aria-expanded="${this._showData}">${t("⇅ Import / export")}</button>
      </div>
      ${this._showData ? this._dataSection() : ""}
      ${
        plants.length
          ? `<div class="grid">${plants
              .map((plant) => {
                const care = plant.care;
                const problems = (care?.problems || []).filter((p) => p !== "watering_overdue");
                return `
            <div class="plant-card ${care?.needs_water ? "needs" : ""}" role="button" tabindex="0" data-action="open-plant" data-id="${plant.id}">
              <div class="thumb">${plant.photos?.[0] ? `<img src="${esc(plant.photos[0].url)}" alt="" loading="lazy">` : "🪴"}
                <button class="btn small water quick" data-action="water" data-id="${plant.id}" title="${t("Watered")}">💧</button>
              </div>
              <div class="info">
                <div class="name">${esc(plantName(plant))}</div>
                <div class="meta species">${esc(plant.species || plant.common_name || "")}</div>
                ${this._reserveBar(care)}
                <div class="row">
                  <span class="chip ${care?.status || ""}">${esc(dueText(care, lang))}</span>
                  ${problems.length ? `<span class="chip problem" title="${esc(problems.map((p) => this._config.problems[p]).join(", "))}">⚠ ${problems.length}</span>` : ""}
                </div>
                ${plant.area_id ? `<div class="muted">${esc(this._areaName(plant.area_id))}</div>` : ""}
              </div>
            </div>`;
              })
              .join("")}</div>`
          : `<div class="empty">${
              this._plants.length
                ? t("No plants match the filters.")
                : `<div class="hero">🌱</div>${t("No plants yet. Add your first plant, take a photo and it is identified for you.")}`
            }</div>`
      }`;
  }

  _dataSection() {
    const admin = this._hass.user?.is_admin;
    return `
      <div class="section">
        <h2>${t("Import & export")}</h2>
        <div class="actions-bar">
          <button class="btn" data-action="export-csv">${t("Export CSV")}</button>
          <button class="btn" data-action="export-json">${t("Export JSON")}</button>
          <label class="btn">${t("Import CSV")}<input type="file" accept=".csv,text/csv" data-import-csv hidden></label>
          ${
            admin
              ? `<button class="btn" data-action="backup">${t("Download backup")}</button>
                 <label class="btn danger">${t("Restore backup…")}<input type="file" accept=".zip" data-restore hidden></label>`
              : ""
          }
        </div>
        <p class="hint">${t("The CSV has one row per plant and uses the same columns for export and import, so an export is a template for adding many plants from a spreadsheet. Only <b>name</b> and <b>species</b> are needed; the care profile is looked up for the species, and profile columns you fill in win. A backup contains the database and all photos; Home Assistant's own backups include them too.")}</p>
        ${this._importReport}
      </div>`;
  }

  _download(name, content, type) {
    const blob = new Blob([content], { type });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 10000);
  }

  _plantRow(plant, meta, actions) {
    return `
      <div class="list-row">
        ${this._thumb(plant, true)}
        <div class="grow">
          <button class="link" data-action="open-plant" data-id="${plant.id}" style="padding:0">${esc(plantName(plant))}</button>
          <div class="meta">${meta}</div>
        </div>
        <div class="actions-bar">${actions}</div>
      </div>`;
  }

  _renderToday() {
    const lang = "de-DE";
    const needs = this._plants.filter((p) => p.care?.needs_water);
    const soon = this._plants.filter(
      (p) => !p.care?.needs_water && p.care && p.care.days_until_watering < 2
    );
    const fertilize = this._plants.filter((p) => p.care?.fertilize_due);
    const problems = this._alerts.filter((a) => a.kind === "problem");
    const waterActions = (plant) => `
      <button class="btn small water" data-action="water" data-id="${plant.id}">${t("💧 Watered")}</button>
      <button class="btn small" data-action="water" data-feedback="too_dry" data-id="${plant.id}" title="${t("Watered; it was too dry, remind me earlier")}">${t("Was too dry")}</button>
      <button class="btn small" data-action="snooze" data-id="${plant.id}" title="${t("Not yet; remind me a bit later")}">${t("Still moist")}</button>`;
    const sections = [];
    if (problems.length) {
      sections.push(`
        <div class="section alerts"><h2>${t("Problems")}</h2>
          ${problems
            .map(
              (a) => `<div class="warning ${a.severity}">⚠ <button class="link" data-action="open-plant" data-id="${a.plant_id}" style="padding:0">${esc(a.message)}</button></div>`
            )
            .join("")}
        </div>`);
    }
    if (needs.length) {
      sections.push(`
        <div class="section"><h2>${t("Needs water")}</h2><div class="list">
          ${needs.map((p) => this._plantRow(p, esc(dueText(p.care, lang)), waterActions(p))).join("")}
        </div></div>`);
    }
    if (soon.length) {
      sections.push(`
        <div class="section"><h2>${t("Water soon")}</h2><div class="list">
          ${soon.map((p) => this._plantRow(p, esc(dueText(p.care, lang)), waterActions(p))).join("")}
        </div></div>`);
    }
    if (fertilize.length) {
      sections.push(`
        <div class="section"><h2>${t("Fertilize")}</h2><div class="list">
          ${fertilize
            .map((p) =>
              this._plantRow(
                p,
                esc(t("Last fertilized {when}", { when: relativeDay(p.last_fertilized, lang) })),
                `<button class="btn small" data-action="log" data-kind="fertilize" data-id="${p.id}">${t("🌱 Fertilized")}</button>`
              )
            )
            .join("")}
        </div></div>`);
    }
    const counts = {
      total: this._plants.length,
      needs: needs.length,
      problems: problems.length,
    };
    return `
      ${this._trip?.plan?.active ? this._tripBanner() : ""}
      <div class="tiles">
        <div class="tile"><div class="muted">${t("Plants")}</div><div class="value">${counts.total}</div></div>
        <div class="tile"><div class="muted">${t("Need water")}</div><div class="value">${counts.needs}</div></div>
        <div class="tile"><div class="muted">${t("Problems")}</div><div class="value">${counts.problems}</div></div>
      </div>
      ${
        sections.join("") ||
        `<div class="empty"><div class="hero">🌿</div>${this._plants.length ? t("All plants are happy. Nothing to do today.") : t("Add plants to get reminders here.")}</div>`
      }`;
  }

  _tripBanner() {
    const { vacation, plan } = this._trip || {};
    if (!vacation || !plan) return "";
    const lang = "de-DE";
    const format = new Intl.DateTimeFormat(lang || "en", { weekday: "short", day: "numeric", month: "short" });
    const when = plan.active
      ? t("Away until {date}", { date: format.format(new Date(plan.back)) })
      : t("Away {start} – {end}", { start: format.format(new Date(plan.leave)), end: format.format(new Date(plan.back)) });
    const visits = plan.visits.length;
    return `
      <div class="banner">
        <span style="font-size:28px">🧳</span>
        <div class="grow"><b>${esc(when)}</b>
          <div class="meta">${esc(visits ? tn(visits, "{sitter} waters {n} time", "{sitter} waters {n} times", { sitter: vacation.sitter || t("The plant sitter") }) : t("No one needs to water"))}</div>
        </div>
        ${this._view !== "vacation" ? `<button class="btn small" data-action="view" data-view="vacation">${t("Plan")}</button>` : ""}
      </div>`;
  }

  _renderSchedule() {
    const lang = "de-DE";
    const schedule = this._schedule.filter((event) => event.kind !== "vacation");
    if (!schedule.length) {
      return `${this._tripBanner()}<div class="empty">${t("Nothing planned for the next four weeks.")}</div>`;
    }
    const days = new Map();
    for (const event of schedule) {
      const key = isoDate(new Date(event.at));
      if (!days.has(key)) days.set(key, []);
      days.get(key).push(event);
    }
    const dayFormat = new Intl.DateTimeFormat(lang || "en", { weekday: "long", day: "numeric", month: "long" });
    return `${this._tripBanner()}<div class="section">${[...days.entries()]
      .map(([day, events]) => {
        const date = new Date(`${day}T12:00:00`);
        const rel = relativeDay(date, lang);
        return `
          <div class="day-head">${esc(dayFormat.format(date))} <span class="muted">· ${esc(rel)}</span></div>
          <div class="list">${events
            .map((event) => {
              const plant = this._plantsById[event.plant_id];
              return this._plantRow(
                plant || { id: event.plant_id, name: event.name },
                `${KIND_ICONS[event.kind]} ${esc(SCHEDULE_LABELS[event.kind] ? t(SCHEDULE_LABELS[event.kind]) : human(event.kind))}`,
                ""
              );
            })
            .join("")}</div>`;
      })
      .join("")}
      <p class="hint">${t("Projected from the current conditions; the schedule adapts to the room climate, the season and your feedback.")}</p>
    </div>`;
  }

  // -- vacation ----------------------------------------------------------

  _startTripDraft(vacation = null) {
    const tomorrow = addDays(new Date(), 1);
    this._tripDraft = {
      start_date: vacation?.start_date || isoDate(tomorrow),
      end_date: vacation?.end_date || isoDate(addDays(tomorrow, 7)),
      sitter: vacation?.sitter || "",
      sitter_notify: vacation?.sitter_notify || "",
      notes: vacation?.notes || "",
    };
    this._tripPreview = null;
    this._previewTrip();
  }

  async _previewTrip() {
    const draft = this._tripDraft;
    if (!draft?.start_date || !draft?.end_date) return;
    try {
      const preview = await this._ws("vacation/preview", {
        start_date: draft.start_date,
        end_date: draft.end_date,
      });
      if (this._tripDraft !== draft) return;
      this._tripPreview = preview;
      this._tripError = null;
    } catch (err) {
      this._tripPreview = null;
      this._tripError = err.message;
    }
    if (this._view === "vacation") this._renderMain();
  }

  _renderVacation() {
    const { vacation, plan } = this._trip || {};
    if (!this._plants.length) {
      return `<div class="empty"><div class="hero">🧳</div>${t("Add plants first, then plan who waters what while you are away.")}</div>`;
    }
    if (this._tripDraft || !vacation) {
      const preview = this._tripPreview;
      return `${this._tripForm(vacation)}${preview?.plan ? this._tripPlan(preview.plan, null) : ""}`;
    }
    const lang = "de-DE";
    const format = new Intl.DateTimeFormat(lang || "en", { weekday: "short", day: "numeric", month: "long" });
    const when = plan.active
      ? t("You're away, back {when}", { when: relativeDay(plan.back, lang) })
      : t("Leaving {when}", { when: relativeDay(plan.leave, lang) });
    return `
      <div class="section">
        <div class="row" style="justify-content:space-between">
          <div>
            <h2 style="margin-bottom:4px">🧳 ${esc(format.format(localDay(vacation.start_date)))} – ${esc(format.format(localDay(vacation.end_date)))}</h2>
            <div class="muted">${esc(when)}${vacation.sitter ? esc(t(" · {sitter} waters", { sitter: vacation.sitter })) : ""}</div>
          </div>
          <div class="actions-bar">
            <button class="btn" data-action="edit-trip">${t("Change")}</button>
            <button class="btn danger" data-action="end-trip">${plan.active ? t("I'm back") : t("Cancel vacation")}</button>
          </div>
        </div>
      </div>
      ${this._tripPlan(plan, vacation)}`;
  }

  _tripForm(vacation) {
    const d = this._tripDraft || {};
    const notify = Object.keys(this._hass.services?.notify || {}).map((name) => `notify.${name}`);
    return `
      <div class="section">
        <h2>${vacation ? t("Change the vacation") : t("Plan a vacation")}</h2>
        <p class="hint" style="margin-top:0">${t("Plant Manager works out which plants to water right before you leave, what to move out of the sun, and on which days someone has to come by.")}</p>
        <div class="form" style="margin-top:12px">
          ${this._field(t("Leaving (in the morning)"), `<input type="date" data-trip="start_date" value="${esc(d.start_date)}">`)}
          ${this._field(t("Back (in the evening)"), `<input type="date" data-trip="end_date" value="${esc(d.end_date)}">`)}
          ${this._field(t("Plant sitter"), `<input data-trip="sitter" value="${esc(d.sitter)}" placeholder="${esc(t("Name (optional)"))}">`)}
          ${this._field(
            t("Sitter's notify action"),
            `<input data-trip="sitter_notify" list="notify-list" value="${esc(d.sitter_notify)}" placeholder="notify.mobile_app_…">
             <datalist id="notify-list">${notify.map((n) => `<option value="${esc(n)}">`).join("")}</datalist>`
          )}
          ${this._field(t("Notes for the sitter"), `<textarea data-trip="notes" placeholder="${esc(t("Where the key and the watering can are, …"))}">${esc(d.notes)}</textarea>`, true)}
        </div>
        <p class="hint">${t("With a notify action, the sitter gets a reminder on the morning of each day they need to come.")}</p>
        ${this._tripError ? `<p class="warning medium">${esc(this._tripError)}</p>` : ""}
        <div class="actions-bar" style="margin-top:12px">
          <button class="btn primary" data-action="save-trip">${vacation ? t("Save") : t("Save vacation")}</button>
          ${vacation ? `<button class="btn" data-action="cancel-trip-edit">${t("Cancel")}</button>` : ""}
        </div>
      </div>`;
  }

  // `vacation` is null for a preview: no actions then.
  _tripPlan(plan, vacation) {
    const lang = "de-DE";
    const entries = plan.plants;
    const byId = Object.fromEntries(entries.map((e) => [e.plant_id, e]));
    const tips = this._config.vacation_tips || {};
    const dayFormat = new Intl.DateTimeFormat(lang || "en", { weekday: "long", day: "numeric", month: "long" });
    const plant = (id) => this._plantsById[id] || { id, name: byId[id]?.name || t("Plant") };
    const area = (id) => this._areaName(plant(id).area_id);
    // English tips follow a colon in lower case; German nouns keep their capital.
    const tipText = (tip) => {
      const text = tips[tip] || human(tip);
      return LANG === "en" ? text.charAt(0).toLowerCase() + text.slice(1) : text;
    };
    const sections = [];

    const prepare = plan.active ? [] : plan.prepare;
    const measured = entries.filter((e) => e.risk !== "ok" && e.tips.some((tip) => tip !== "sensor"));
    if (prepare.length || measured.length) {
      sections.push(`
        <div class="section"><h2>${t("Before you leave")}</h2>
          ${
            prepare.length
              ? `<h3>${t("Water thoroughly the day before or the morning you leave")}</h3><div class="list">${prepare
                  .map((id) =>
                    this._plantRow(
                      plant(id),
                      `${esc(area(id))}${area(id) ? " · " : ""}${esc(plant(id).last_watered ? t("Last watered {when}", { when: relativeDay(plant(id).last_watered, lang) }) : t("Never watered"))}`,
                      vacation ? `<button class="btn small water" data-action="water" data-id="${id}">${t("💧 Watered")}</button>` : ""
                    )
                  )
                  .join("")}</div>`
              : ""
          }
          ${
            measured.length
              ? `<h3>${t("So they dry out more slowly")}</h3>${measured
                  .map(
                    (e) => `<div class="tip">🌤 <b>${esc(e.name)}</b>: ${e.tips
                      .filter((tip) => tip !== "sensor")
                      .map((tip) => esc(tipText(tip)))
                      .join("; ")}${
                      e.lasts_with_measures_days > e.lasts_days
                        ? ` <span class="muted">${esc(t("(lasts {with} instead of {without} days)", { with: num(e.lasts_with_measures_days), without: num(e.lasts_days) }))}</span>`
                        : ""
                    }</div>`
                  )
                  .join("")}`
              : ""
          }
        </div>`);
    }

    const sitterName = vacation?.sitter || t("The plant sitter");
    const visits = plan.visits.length;
    sections.push(`
      <div class="section"><h2>${esc(visits ? tn(visits, "{sitter} waters on {n} day", "{sitter} waters on {n} days", { sitter: sitterName }) : t("Plant sitter"))}</h2>
        ${
          visits
            ? plan.visits
                .map(
                  (visit) => `
            <div class="day-head">${esc(dayFormat.format(localDay(visit.date)))} <span class="muted">· ${esc(relativeDay(localDay(visit.date), lang))}</span></div>
            <div class="list">${visit.plant_ids
              .map((id) => this._plantRow(plant(id), esc(area(id) || plant(id).species || ""), ""))
              .join("")}</div>`
                )
                .join("")
            : `<p class="muted" style="margin-top:0">${
                prepare.length
                  ? t("🎉 No one needs to come: every plant lasts until you are back if you water the ones above before leaving.")
                  : t("🎉 No one needs to come: every plant lasts until you are back.")
              }</p>`
        }
        ${
          vacation && visits
            ? `<div class="actions-bar" style="margin-top:12px">
                ${vacation.sitter_notify ? `<button class="btn primary" data-action="send-plan">${esc(t("Send to {sitter}", { sitter: vacation.sitter || t("the sitter") }))}</button>` : ""}
                <button class="btn" data-action="copy-plan">${t("Copy plan")}</button>
                <button class="btn" data-action="print-plan">${t("Print plan")}</button>
              </div>`
            : ""
        }
      </div>`);

    const verdict = (e) =>
      e.risk === "ok"
        ? `<span class="chip ok">${e.prepare ? t("Lasts after watering") : t("Lasts")}</span>`
        : e.risk === "measures"
          ? `<span class="chip measures">${t("Lasts if moved")}</span>`
          : `<span class="chip sitter">${t("Sitter: {n}×", { n: e.visits.length })}</span>`;
    sections.push(`
      <div class="section"><h2>${t("All plants")}</h2>
        <table>
          <tr><th>${t("Plant")}</th><th class="num">${t("Water lasts")}</th><th>${t("While away")}</th></tr>
          ${entries
            .map(
              (e) => `<tr>
                <td><button class="link" data-action="open-plant" data-id="${e.plant_id}" style="padding:0">${esc(e.name)}</button></td>
                <td class="num">${t("{n} d", { n: num(e.lasts_days) })}</td>
                <td>${verdict(e)}</td></tr>`
            )
            .join("")}
        </table>
        <p class="hint">${t("Projected for {days} days away with today's room climate and the season mid-trip. Turning the heating down or the air conditioning off changes how fast the soil dries. Nobody to water? A wick from a jug of water, a self-watering spike, or a bathtub with a few centimetres of water on a towel keeps most potted plants going for one or two weeks.", { days: num(plan.days) })}</p>
      </div>`);
    return sections.join("");
  }

  _printPlan() {
    const { vacation, plan, text } = this._trip || {};
    if (!plan) return;
    const lang = "de-DE";
    const dayFormat = new Intl.DateTimeFormat(lang || "en", { weekday: "long", day: "numeric", month: "long" });
    const plant = (id) => this._plantsById[id] || { name: id };
    const html = `<!doctype html><html lang="${LANG}"><head><meta charset="utf-8"><title>${esc(t("Plant care"))}</title>
      <style>body{font-family:system-ui,sans-serif;max-width:720px;margin:24px auto;padding:0 16px;color:#222}
      h1{font-size:22px} h2{font-size:17px;margin:20px 0 6px;border-bottom:1px solid #ccc;padding-bottom:4px}
      li{margin:6px 0;display:flex;gap:10px;align-items:center} img{width:48px;height:48px;object-fit:cover;border-radius:6px}
      ul{list-style:none;padding:0} .muted{color:#666;font-size:13px} .box{width:16px;height:16px;border:1px solid #444;flex:none}
      pre{white-space:pre-wrap;font:inherit}</style></head><body>
      <h1>🪴 ${esc(text.split("\n")[0].replace(/^🪴\s*/, ""))}</h1>
      ${vacation.sitter ? `<p>${esc(t("Thank you, {sitter}!", { sitter: vacation.sitter }))}</p>` : ""}
      ${plan.visits
        .map(
          (visit) => `<h2>${esc(dayFormat.format(localDay(visit.date)))}</h2><ul>${visit.plant_ids
            .map((id) => {
              const p = plant(id);
              return `<li><span class="box"></span>${p.photos?.[0] ? `<img src="${esc(p.photos[0].url)}">` : ""}<div><b>${esc(p.name)}</b>
                <div class="muted">${esc([this._areaName(p.area_id), p.species].filter(Boolean).join(" · "))}</div></div></li>`;
            })
            .join("")}</ul>`
        )
        .join("")}
      <h2>${t("How to water")}</h2>
      <p>${t("Water slowly until it runs out at the bottom, then empty the saucer after 15 minutes. If the soil is still moist 2 cm deep, skip it.")}</p>
      ${vacation.notes ? `<h2>${t("Notes")}</h2><pre>${esc(vacation.notes)}</pre>` : ""}
      <script>window.onload = () => setTimeout(() => window.print(), 300);<\/script></body></html>`;
    const win = window.open("", "_blank");
    if (!win) {
      this._toast(t("Allow pop-ups to print the plan"));
      return;
    }
    win.document.write(html);
    win.document.close();
  }

  // -- my notifications --------------------------------------------------

  async _openNotify() {
    try {
      const data = await this._ws("notifications/get");
      this._notify = { phones: data.phones, draft: { ...data.settings, targets: [...data.settings.targets] } };
    } catch (err) {
      this._toast(err.message);
      return;
    }
    this._renderNotify();
  }

  _closeNotify() {
    this._notify = null;
    const root = this.shadowRoot.getElementById("notify");
    if (root) root.innerHTML = "";
  }

  _renderNotify() {
    const root = this.shadowRoot.getElementById("notify");
    if (!root || !this._notify) return;
    const { phones, draft } = this._notify;
    // Phones that were picked but are gone (app removed) stay visible so they can be unticked.
    const known = new Set(phones.map((p) => p.service));
    const all = [...phones, ...draft.targets.filter((t) => !known.has(t)).map((t) => ({ service: t, name: t, mine: true }))];
    const user = this._hass.user?.name;
    root.innerHTML = `
      <div class="overlay" data-action="notify-overlay">
        <div class="dialog" style="max-width:560px">
          <div class="dialog-head">
            <button class="btn" data-action="close-notify">✕</button>
            <h2>${t("My notifications")}</h2>
            <button class="btn primary" data-action="save-notify">${t("Save")}</button>
          </div>
          <div class="dialog-body">
            <div class="section">
              <h2>${t("Send to")}</h2>
              ${
                all.length
                  ? all
                      .map(
                        (p) => `<label class="field check"><input type="checkbox" data-notify-target="${esc(p.service)}" ${draft.targets.includes(p.service) ? "checked" : ""}>
                          📱 ${esc(p.name)}${p.mine ? "" : ` <span class="muted">${t("(someone else's)")}</span>`}</label>`
                      )
                      .join("")
                  : `<p class="muted" style="margin-top:0">${t("No phones yet. Install the Home Assistant app on your phone and log in to this Home Assistant; the phone then shows up here.")}</p>`
              }
            </div>
            <div class="section">
              <h2>${t("What")}</h2>
              <label class="field check"><input type="checkbox" data-notify="daily" ${draft.daily ? "checked" : ""}> ${t("Daily summary: what to water and fertilize")}</label>
              <label class="field" style="max-width:220px;margin:4px 0 12px 28px">${t("At")} <input type="time" data-notify="time" value="${esc(draft.time.slice(0, 5))}"></label>
              <label class="field check"><input type="checkbox" data-notify="problems" ${draft.problems ? "checked" : ""}> ${t("Problems right away (too cold, too dark, soil too wet, …)")}</label>
              <p class="hint">${t("The summary is only sent on days with something to do; while you are on vacation it says what the plant sitter waters. These settings are only for you{user}; everyone can choose their own.", { user: user ? ` (${esc(user)})` : "" })}</p>
              <div class="actions-bar" style="margin-top:12px">
                <button class="btn" data-action="test-notify" ${draft.targets.length ? "" : "disabled"}>${t("Save and send a test")}</button>
              </div>
            </div>
          </div>
        </div>
      </div>`;
  }

  async _saveNotify() {
    const { draft } = this._notify;
    const saved = await this._ws("notifications/set", {
      targets: draft.targets,
      daily: draft.daily,
      time: draft.time,
      problems: draft.problems,
    });
    this._notify.draft = { ...saved, targets: [...saved.targets] };
    return saved;
  }

  // -- editor ------------------------------------------------------------

  _blankDraft() {
    return {
      name: "",
      species: "",
      common_name: "",
      family: "",
      area_id: "",
      placement: "indoor",
      light: "medium",
      pot_diameter_cm: 15,
      pot_material: "plastic",
      temperature_sensor: "",
      humidity_sensor: "",
      moisture_sensor: "",
      illuminance_sensor: "",
      profile: {},
      profile_sources: [],
      notes: "",
      acquired_date: "",
      last_watered: isoDate(new Date()),
    };
  }

  async _openEditor(plantId) {
    let plant = null;
    if (plantId) {
      try {
        plant = await this._ws("plants/get", { plant_id: plantId });
      } catch (err) {
        this._toast(t("Could not load plant: {error}", { error: err.message }));
        return;
      }
    }
    const draft = this._blankDraft();
    const touched = new Set();
    if (plant) {
      for (const key of Object.keys(draft)) {
        if (plant[key] !== undefined && plant[key] !== null) draft[key] = plant[key];
        if (draft[key]) touched.add(key);
      }
      touched.add("profile");
    }
    this._editor = {
      id: plant?.id || null,
      plant,
      draft,
      touched,
      staged: [], // { staged_id, preview }
      pendingFiles: [], // { blob, preview } for existing plants without staging
      candidates: null,
      chosen: null,
      identifying: false,
      identifyError: null,
      resolving: false,
      busy: false,
    };
    this._renderEditor();
  }

  _closeEditor() {
    for (const file of [...(this._editor?.staged || []), ...(this._editor?.pendingFiles || [])]) {
      URL.revokeObjectURL(file.preview);
    }
    this._editor = null;
    const root = this.shadowRoot.getElementById("editor");
    if (root) root.innerHTML = "";
  }

  async _refreshEditorPlant() {
    const editor = this._editor;
    if (!editor?.id) return;
    try {
      editor.plant = await this._ws("plants/get", { plant_id: editor.id });
    } catch (err) {
      return;
    }
    for (const part of ["photos", "status", "log"]) this._renderEditorPart(part);
  }

  _renderEditor() {
    const root = this.shadowRoot.getElementById("editor");
    const editor = this._editor;
    if (!root || !editor) return;
    root.innerHTML = `
      <div class="overlay" data-action="overlay">
        <div class="dialog">
          <div class="dialog-head">
            <button class="btn" data-action="close-editor">✕</button>
            <h2>${esc(editor.draft.name && editor.draft.name !== editor.plant?.name ? editor.draft.name : editor.plant ? plantName(editor.plant) : t("New plant"))}</h2>
            <button class="btn primary" data-action="save-plant" ${editor.busy ? "disabled" : ""}>${editor.busy ? t("Saving…") : t("Save")}</button>
          </div>
          <div class="dialog-body">
            <div class="section" id="ed-identify"></div>
            <div id="ed-status"></div>
            <div class="section" id="ed-photos"></div>
            <div class="section" id="ed-form"></div>
            <div class="section" id="ed-sensors"></div>
            <div class="section" id="ed-profile"></div>
            <div id="ed-log"></div>
          </div>
        </div>
      </div>`;
    for (const part of ["identify", "status", "photos", "form", "sensors", "profile", "log"]) {
      this._renderEditorPart(part);
    }
  }

  _renderEditorPart(part) {
    const editor = this._editor;
    const el = this.shadowRoot.getElementById(`ed-${part}`);
    if (!editor || !el) return;
    el.innerHTML = {
      identify: () => this._editorIdentify(),
      status: () => this._editorStatus(),
      photos: () => this._editorPhotos(),
      form: () => this._editorForm(),
      sensors: () => this._editorSensors(),
      profile: () => this._editorProfile(),
      log: () => this._editorLog(),
    }[part]();
  }

  _editorIdentify() {
    const editor = this._editor;
    const provider = PROVIDER_LABELS[this._config.provider];
    const intro = this._config.identification
      ? t("Take a photo of the plant (leaves in view) and {provider} suggests what it is.", { provider: esc(t(provider || "")) })
      : t("Add a photo. To identify plants from photos, choose a service under <b>Settings → Devices & services → Plant Manager → Configure</b>.");
    let body = "";
    if (editor.identifying) {
      body = `<p class="muted">${t("Identifying…")}</p>`;
    } else if (editor.candidates?.length) {
      body = `<div class="candidates">${editor.candidates
        .map(
          (c, index) => `
          <button class="candidate ${editor.chosen === index ? "chosen" : ""}" data-action="choose" data-index="${index}">
            <span class="species"><b>${esc(c.scientific_name)}</b></span>
            <span class="muted">${esc(c.common_names?.[0] || c.family || "")}</span>
            <div class="score"><div style="width:${Math.round(c.score * 100)}%"></div></div>
            <span class="muted">${t("{n} % match", { n: Math.round(c.score * 100) })}</span>
          </button>`
        )
        .join("")}</div>
        <p class="hint">${t("Pick the right one, or type the species below if none fits.")}</p>`;
    } else if (editor.identifyError && editor.identifyError !== "no_provider") {
      const messages = {
        no_match: "The plant could not be identified. Try a closer photo of the leaves, or enter the species below.",
        invalid_auth: "The identification service rejected the API key.",
        quota_exceeded: "The identification service's daily quota is used up.",
        cannot_connect: "Could not reach the identification service.",
        not_a_plant: "No plant was recognised in this photo.",
      };
      body = `<p class="warning medium">${esc(t(messages[editor.identifyError] || "Identification failed. Check the logs."))}</p>`;
    }
    return `
      <h2>${editor.id ? t("Identify again") : t("Identify")}</h2>
      <p class="hint" style="margin-top:0">${intro}</p>
      <div class="actions-bar" style="margin-top:12px">
        <label class="btn primary">${t("📷 Take photo")}<input type="file" accept="image/*" capture="environment" data-identify hidden></label>
        <label class="btn">${t("⬆ Upload")}<input type="file" accept="image/*" data-identify hidden></label>
      </div>
      ${body}`;
  }

  _editorStatus() {
    const editor = this._editor;
    const plant = editor.plant;
    if (!plant?.care) return "";
    const care = plant.care;
    const lang = "de-DE";
    const factors = Object.entries(care.factors || {})
      .filter(([, value]) => Math.abs(value - 1) > 0.005)
      .map(
        ([key, value]) =>
          `<tr><td>${esc(FACTOR_LABELS[key] ? t(FACTOR_LABELS[key]) : human(key))}</td><td class="num">× ${num(value, 2)}</td><td class="muted">${value > 1 ? t("waters less often") : t("waters more often")}</td></tr>`
      )
      .join("");
    const problems = (care.problems || []).map((p) => this._config.problems[p]).filter(Boolean);
    return `
      <div class="section">
        <h2>${t("Care")}</h2>
        <div class="facts">
          <div class="fact"><div class="muted">${t("Next watering")}</div><div class="value">${esc(dueText(care, lang))}</div></div>
          <div class="fact"><div class="muted">${t("Every")}</div><div class="value">${t("{n} days", { n: num(care.interval_days) })}</div></div>
          <div class="fact"><div class="muted">${t("Water left")}</div><div class="value">${Math.round(care.water_reserve)} %</div></div>
          <div class="fact"><div class="muted">${t("Last watered")}</div><div class="value">${esc(relativeDay(plant.last_watered, lang))}</div></div>
        </div>
        ${this._reserveBar(care)}
        ${problems.length ? `<p class="warning medium">⚠ ${esc(problems.join(", "))}</p>` : ""}
        <div class="actions-bar" style="margin-top:12px">
          <button class="btn water" data-action="water" data-id="${plant.id}">${t("💧 Watered")}</button>
          <select data-water-feedback aria-label="${t("Soil before watering")}">
            <option value="">${t("Soil before watering…")}</option>
            ${this._options(this._config.feedback, "", { label: (v) => human(v).replace(/^./, (c) => c.toUpperCase()) })}
          </select>
          <button class="btn" data-action="snooze" data-id="${plant.id}">${t("Still moist")}</button>
          <button class="btn" data-action="log" data-kind="fertilize" data-id="${plant.id}">${t("🌱 Fertilized")}</button>
        </div>
        ${
          factors
            ? `<h3>${t("Why every {n} days", { n: num(care.interval_days) })}</h3>
               <table><tr><td>${t("Reference interval for the species")}</td><td class="num">${esc(t("{n} d", { n: plant.profile?.base_interval_days ?? "" }))}</td><td></td></tr>${factors}</table>`
            : ""
        }
        <p class="hint">
          ${care.temperature != null ? `${num(care.temperature)} °C · ` : ""}${care.humidity != null ? `${t("{n} % humidity", { n: Math.round(care.humidity) })} · ` : ""}${care.moisture != null ? `${t("soil {n} %", { n: Math.round(care.moisture) })} · ` : ""}
          ${care.next_fertilization ? (care.fertilizing_paused ? t("fertilizing rests in winter") : esc(t("fertilize {when}", { when: relativeDay(care.next_fertilization, lang) }))) : t("no fertilizing")}
          · ID <code>${esc(plant.id)}</code>
        </p>
      </div>`;
  }

  _editorPhotos() {
    const editor = this._editor;
    const photos = editor.plant?.photos || [];
    const tiles = photos.map(
      (photo, index) => `
        <div class="photo">
          <div class="thumb"><img src="${esc(photo.url)}" alt="">${index === 0 ? `<span class="cover-badge">${t("Cover")}</span>` : ""}</div>
          <div class="actions">
            ${index ? `<button class="link" data-action="cover-photo" data-id="${photo.id}">${t("Make cover")}</button>` : "<span></span>"}
            <button class="link" data-action="delete-photo" data-id="${photo.id}">${t("Delete")}</button>
          </div>
        </div>`
    );
    for (const [list, action] of [
      [editor.staged, "drop-staged"],
      [editor.pendingFiles, "drop-pending"],
    ]) {
      list.forEach((file, index) =>
        tiles.push(`
          <div class="photo pending">
            <div class="thumb"><img src="${esc(file.preview)}" alt=""></div>
            <div class="actions"><span class="muted">${t("On save")}</span>
              <button class="link" data-action="${action}" data-index="${index}">${t("Remove")}</button></div>
          </div>`)
      );
    }
    return `
      <h2>${t("Photos")}</h2>
      ${tiles.length ? `<div class="photos">${tiles.join("")}</div>` : `<p class="muted" style="margin-top:0">${t("No photos yet.")}</p>`}
      <div class="actions-bar" style="margin-top:12px">
        <label class="btn">${t("📷 Take photo")}<input type="file" accept="image/*" capture="environment" data-upload hidden></label>
        <label class="btn">${t("⬆ Upload")}<input type="file" accept="image/*" multiple data-upload hidden></label>
      </div>`;
  }

  _field(label, input, wide = false) {
    return `<label class="field ${wide ? "wide" : ""}">${esc(label)}${input}</label>`;
  }

  _editorForm() {
    const d = this._editor.draft;
    const isNew = !this._editor.id;
    const areas = this._areas();
    return `
      <h2>${t("Details")}</h2>
      <div class="form">
        ${this._field(t("Name"), `<input data-field="name" value="${esc(d.name)}" placeholder="${esc(t("e.g. Monty"))}">`)}
        ${this._field(
          t("Species"),
          `<input data-field="species" list="species-list" value="${esc(d.species)}" placeholder="${esc(t("e.g. Monstera deliciosa"))}">
           <datalist id="species-list">${this._config.species.map((s) => `<option value="${esc(s.value)}">${esc(s.label)}</option>`).join("")}</datalist>`
        )}
        ${this._field(t("Common name"), `<input data-field="common_name" value="${esc(d.common_name)}">`)}
        ${this._field(
          t("Area"),
          areas.length
            ? `<select data-field="area_id">${this._options(areas.map((a) => a.area_id), d.area_id, { empty: t("None"), label: (id) => this._areaName(id) })}</select>`
            : `<select data-field="area_id" disabled><option>${t("No areas set up")}</option></select>`
        )}
        ${this._field(t("Location"), `<select data-field="placement">${this._options(this._config.placements, d.placement)}</select>`)}
        ${this._field(t("Light at its spot"), `<select data-field="light">${this._options(this._config.light_levels, d.light)}</select>`)}
        ${this._field(t("Pot diameter (cm)"), `<input type="number" min="2" max="300" step="1" data-field="pot_diameter_cm" data-kind="float" value="${esc(d.pot_diameter_cm)}">`)}
        ${this._field(t("Pot type"), `<select data-field="pot_material">${this._options(this._config.pot_materials, d.pot_material)}</select>`)}
        ${isNew ? this._field(t("Last watered"), `<input type="date" data-field="last_watered" value="${esc(d.last_watered)}">`) : ""}
        ${this._field(t("Got it on"), `<input type="date" data-field="acquired_date" value="${esc(d.acquired_date || "")}">`)}
        ${this._field(t("Notes"), `<textarea data-field="notes">${esc(d.notes || "")}</textarea>`, true)}
      </div>`;
  }

  _sensorOptions(deviceClass, selected) {
    const states = Object.values(this._hass.states).filter(
      (s) =>
        s.entity_id.startsWith("sensor.") &&
        (s.attributes.device_class === deviceClass || s.entity_id === selected)
    );
    states.sort((a, b) =>
      (a.attributes.friendly_name || a.entity_id).localeCompare(b.attributes.friendly_name || b.entity_id)
    );
    return this._options(
      states.map((s) => s.entity_id),
      selected,
      {
        empty: t("None"),
        label: (id) => {
          const state = this._hass.states[id];
          const value = state ? ` (${state.state}${state.attributes.unit_of_measurement ? ` ${state.attributes.unit_of_measurement}` : ""})` : "";
          return `${state?.attributes.friendly_name || id}${value}`;
        },
      }
    );
  }

  _editorSensors() {
    const d = this._editor.draft;
    return `
      <h2>${t("Sensors")}</h2>
      <div class="form">
        ${Object.entries(this._config.sensor_fields)
          .map(([field, deviceClass]) =>
            this._field(t(SENSOR_LABELS[field]), `<select data-field="${field}">${this._sensorOptions(deviceClass, d[field])}</select>`)
          )
          .join("")}
      </div>
      <p class="hint">${t("Room temperature and humidity tune the watering interval (warm, dry air dries the soil faster). A soil moisture sensor replaces the estimate and detects waterings by itself. Light is used to warn when the spot is too dark or too bright.")}</p>`;
  }

  _editorProfile() {
    const editor = this._editor;
    const profile = editor.draft.profile || {};
    const sources = editor.draft.profile_sources || [];
    const toxic = profile.toxic_to_pets;
    return `
      <h2>${t("Care profile")}</h2>
      ${editor.resolving ? `<p class="muted">${esc(t("Looking up care for {species}…", { species: editor.draft.species }))}</p>` : ""}
      ${profile.notes ? `<p style="margin-top:0">💡 ${esc(profile.notes)}</p>` : ""}
      <p class="hint" style="margin-top:0">
        ${sources.length ? `${esc(t("From {sources}.", { sources: sources.map(sourceLabel).join(", ") }))} ` : ""}
        ${profile.light_preference ? `${esc(t("Prefers {light} light.", { light: LANG === "en" ? human(profile.light_preference).toLowerCase() : human(profile.light_preference) }))} ` : ""}
        ${toxic === true ? `${t("⚠ Toxic to pets.")} ` : toxic === false ? `${t("Safe for pets.")} ` : ""}
      </p>
      <div class="form">
        ${PROFILE_FIELDS.map(([key, label, step]) =>
          this._field(t(label), `<input type="number" step="${step}" data-profile="${key}" value="${esc(profile[key] ?? "")}">`)
        ).join("")}
        <label class="field check"><input type="checkbox" data-profile="winter_dormancy" ${profile.winter_dormancy !== false ? "checked" : ""}> ${t("Rests in winter (waters much less, no fertilizer)")}</label>
      </div>
      <p class="hint">${t("The reference interval is for a 15 cm plastic pot, medium light, 21 °C and 50 % humidity in summer. Pot, light, room climate and season are applied on top.")}</p>
      <div class="actions-bar" style="margin-top:8px">
        <button class="btn" data-action="resolve-profile" ${editor.draft.species ? "" : "disabled"}>${t("Look up care for the species again")}</button>
      </div>`;
  }

  _editorLog() {
    const editor = this._editor;
    if (!editor.id) return "";
    const events = editor.plant?.events || [];
    const lang = "de-DE";
    const when = new Intl.DateTimeFormat(lang || "en", { dateStyle: "medium", timeStyle: "short" });
    return `
      <div class="section">
        <h2>${t("Care log")}</h2>
        <div class="actions-bar">
          <select data-log-kind>${this._options(this._config.care_kinds.filter((k) => !["water", "snooze"].includes(k)), "fertilize")}</select>
          <input data-log-notes placeholder="${esc(t("Notes (optional)"))}" style="flex:1 1 180px">
          <button class="btn" data-action="add-log">${t("Add")}</button>
        </div>
        ${
          events.length
            ? `<div class="list" style="margin-top:8px">${events
                .map(
                  (event) => `
              <div class="list-row">
                <span style="font-size:20px">${KIND_ICONS[event.kind] || "•"}</span>
                <div class="grow">
                  <div>${esc(human(event.kind))}${event.feedback ? ` <span class="muted">(${esc(human(event.feedback))})</span>` : ""}${event.source === "sensor" ? ` <span class="muted">${t("(detected by the moisture sensor)")}</span>` : ""}</div>
                  <div class="meta">${esc(when.format(new Date(event.at)))}${event.notes ? ` · ${esc(event.notes)}` : ""}</div>
                </div>
                <button class="link" data-action="delete-event" data-id="${event.id}">${t("Remove")}</button>
              </div>`
                )
                .join("")}</div>`
            : `<p class="muted">${t("Nothing logged yet.")}</p>`
        }
      </div>
      <div class="section">
        <button class="btn danger" data-action="delete-plant">${t("Delete plant")}</button>
      </div>`;
  }

  _payload() {
    const d = this._editor.draft;
    const payload = {
      name: (d.name || "").trim(),
      species: (d.species || "").trim() || null,
      common_name: (d.common_name || "").trim() || null,
      family: d.family || null,
      area_id: d.area_id || null,
      placement: d.placement,
      light: d.light,
      pot_diameter_cm: d.pot_diameter_cm || 15,
      pot_material: d.pot_material,
      notes: d.notes || null,
      acquired_date: d.acquired_date || null,
      profile: Object.fromEntries(
        Object.entries(d.profile || {}).filter(([, value]) => value !== null && value !== "")
      ),
      profile_sources: d.profile_sources || [],
    };
    for (const field of Object.keys(this._config.sensor_fields)) payload[field] = d[field] || null;
    if (!this._editor.id && d.last_watered) payload.last_watered = d.last_watered;
    return payload;
  }

  async _savePlant() {
    const editor = this._editor;
    const payload = this._payload();
    if (!payload.name) {
      this._toast(t("Please enter a name"));
      return;
    }
    if (!payload.species && !Object.keys(payload.profile).length) {
      this._toast(t("Please enter the species, or take a photo to identify it"));
      return;
    }
    editor.busy = true;
    this._renderEditor();
    try {
      const plant = editor.id
        ? await this._ws("plants/update", { plant_id: editor.id, changes: payload })
        : await this._ws("plants/create", { plant: payload });
      editor.id = plant.id;
      const failures = [];
      for (const staged of editor.staged) {
        try {
          await this._ws("photos/attach_staged", { plant_id: plant.id, staged_id: staged.staged_id });
        } catch (err) {
          failures.push(err.message);
        }
      }
      for (const file of editor.pendingFiles) {
        try {
          await this._upload(plant.id, file.blob);
        } catch (err) {
          failures.push(err.message);
        }
      }
      this._toast(
        failures.length
          ? t("Saved, but {n} photo(s) failed: {error}", { n: failures.length, error: failures[0] })
          : t("Saved {name}", { name: plant.name })
      );
      this._closeEditor();
    } catch (err) {
      editor.busy = false;
      this._renderEditor();
      this._toast(t("Could not save: {error}", { error: err.message }));
    }
  }

  _uploadFile(kind, file) {
    return this._post(`/api/${DOMAIN}/upload/${kind}`, file, file.name);
  }

  async _post(url, blob, filename = "photo.jpg") {
    const form = new FormData();
    form.append("file", blob, filename);
    const query = `${url.includes("?") ? "&" : "?"}language=${LANG}`;
    const response = await this._hass.fetchWithAuth(url + query, { method: "POST", body: form });
    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try {
        message = (await response.json()).message || message;
      } catch (err) {
        // keep the status text
      }
      throw new Error(message);
    }
    return response.json();
  }

  _upload(plantId, blob) {
    return this._post(`/api/${DOMAIN}/plants/${plantId}/photos`, blob);
  }

  async _prepare(file) {
    try {
      return await resizeImage(file);
    } catch (err) {
      return file; // Browser can't decode it (e.g. HEIC on desktop); send the original.
    }
  }

  async _identify(file) {
    const editor = this._editor;
    if (!editor) return;
    const blob = await this._prepare(file);
    editor.identifying = true;
    editor.candidates = null;
    editor.identifyError = null;
    this._renderEditorPart("identify");
    try {
      const result = await this._post(`/api/${DOMAIN}/identify`, blob);
      if (this._editor !== editor) return;
      editor.staged.push({ staged_id: result.staged_id, preview: URL.createObjectURL(blob) });
      editor.candidates = result.candidates;
      editor.identifyError = result.error;
      editor.chosen = null;
      if (result.candidates.length && !editor.touched.has("species")) await this._choose(0);
    } catch (err) {
      this._toast(t("Upload failed: {error}", { error: err.message }));
    }
    editor.identifying = false;
    this._renderEditorPart("identify");
    this._renderEditorPart("photos");
  }

  async _choose(index) {
    const editor = this._editor;
    const candidate = editor.candidates?.[index];
    if (!candidate) return;
    editor.chosen = index;
    const d = editor.draft;
    d.species = candidate.scientific_name;
    d.family = candidate.family || "";
    d.common_name = candidate.common_names?.[0] || "";
    if (!editor.touched.has("name")) d.name = d.common_name || d.species;
    this._renderEditorPart("identify");
    this._renderEditorPart("form");
    this._updateTitle();
    await this._resolveProfile(true);
  }

  async _resolveProfile(force) {
    const editor = this._editor;
    const d = editor.draft;
    if (!d.species || (!force && editor.touched.has("profile"))) return;
    editor.resolving = true;
    this._renderEditorPart("profile");
    try {
      const result = await this._ws("profile/resolve", { species: d.species, family: d.family || null });
      if (this._editor !== editor) return;
      d.profile = result.profile;
      d.profile_sources = result.sources;
      if (!d.common_name && result.common_name) {
        d.common_name = result.common_name;
        if (!editor.touched.has("name")) d.name = result.common_name;
        this._renderEditorPart("form");
        this._updateTitle();
      }
    } catch (err) {
      this._toast(t("Could not look up the care profile: {error}", { error: err.message }));
    }
    editor.resolving = false;
    this._renderEditorPart("profile");
  }

  _updateTitle() {
    const title = this.shadowRoot.querySelector(".dialog-head h2");
    if (title) title.textContent = this._editor?.draft.name || t("New plant");
  }

  async _handleFiles(files) {
    const editor = this._editor;
    if (!editor) return;
    for (const file of files) {
      const blob = await this._prepare(file);
      if (editor.id) {
        try {
          await this._upload(editor.id, blob);
        } catch (err) {
          this._toast(t("Upload failed: {error}", { error: err.message }));
        }
      } else {
        editor.pendingFiles.push({ blob, preview: URL.createObjectURL(blob) });
      }
    }
    if (editor.id) await this._refreshEditorPlant();
    else this._renderEditorPart("photos");
  }

  // -- events ------------------------------------------------------------

  _undoToast(message, undoId) {
    this._toast(message, t("Undo"), () =>
      this._run(
        this._ws("undo", { undo_id: undoId }).then((result) => {
          if (!result.undone) throw new Error(t("Too late to undo"));
        }),
        t("Undone")
      )
    );
  }

  _toast(message, actionLabel, action) {
    const root = this.shadowRoot.getElementById("toast");
    if (!root) return;
    clearTimeout(this._toastTimer);
    root.innerHTML = `<div class="toast"><span>${esc(message)}</span>${actionLabel ? `<button data-action="toast-action">${esc(actionLabel)}</button>` : ""}</div>`;
    this._toastAction = action;
    this._toastTimer = setTimeout(() => {
      root.innerHTML = "";
    }, actionLabel ? 8000 : 4000);
  }

  _navigate(view) {
    this._view = view;
    history.pushState(null, "", `/${this._route?.prefix?.replace(/^\//, "") || "plant-manager"}/${view}`);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    this._renderTabs();
    this._renderMain();
  }

  async _run(promise, success) {
    try {
      const result = await promise;
      if (success) this._toast(success);
      return result;
    } catch (err) {
      this._toast(err.message || String(err));
      return null;
    }
  }

  _plantName(id) {
    return this._plantsById?.[id] ? plantName(this._plantsById[id]) : this._editor?.draft.name || t("Plant");
  }

  async _onClick(ev) {
    const el = ev.target.closest("[data-action]");
    if (!el) return;
    const action = el.dataset.action;
    const editor = this._editor;
    switch (action) {
      case "menu":
        this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
        break;
      case "view":
        this._navigate(el.dataset.view);
        break;
      case "new-plant":
        this._openEditor(null);
        break;
      case "open-plant":
        this._openEditor(el.dataset.id);
        break;
      case "overlay":
        if (ev.target === el) this._closeEditor();
        break;
      case "close-editor":
        this._closeEditor();
        break;
      case "save-plant":
        this._savePlant();
        break;
      case "toast-action":
        this._toastAction?.();
        this.shadowRoot.getElementById("toast").innerHTML = "";
        break;
      case "water": {
        const select = this.shadowRoot.querySelector("[data-water-feedback]");
        const feedback = el.dataset.feedback || (editor && select?.value) || null;
        const result = await this._run(this._ws("plants/water", { plant_id: el.dataset.id, feedback }));
        if (result) this._undoToast(t("{name} watered", { name: this._plantName(el.dataset.id) }), result.undo_id);
        break;
      }
      case "snooze": {
        const result = await this._run(this._ws("plants/snooze", { plant_id: el.dataset.id }));
        if (result) this._undoToast(t("OK, {name} is reminded a bit later", { name: this._plantName(el.dataset.id) }), result.undo_id);
        break;
      }
      case "log": {
        const result = await this._run(this._ws("plants/log", { plant_id: el.dataset.id, kind: el.dataset.kind }));
        if (result) this._undoToast(`${this._plantName(el.dataset.id)}: ${LANG === "en" ? human(el.dataset.kind).toLowerCase() : human(el.dataset.kind)}`, result.undo_id);
        break;
      }
      case "add-log": {
        const kind = this.shadowRoot.querySelector("[data-log-kind]").value;
        const notes = this.shadowRoot.querySelector("[data-log-notes]").value.trim() || null;
        await this._run(this._ws("plants/log", { plant_id: editor.id, kind, notes }), t("Logged"));
        break;
      }
      case "delete-event":
        await this._run(this._ws("events/delete", { event_id: Number(el.dataset.id) }), t("Removed"));
        break;
      case "choose":
        this._choose(Number(el.dataset.index));
        break;
      case "resolve-profile":
        this._resolveProfile(true);
        break;
      case "drop-staged": {
        const [removed] = editor.staged.splice(Number(el.dataset.index), 1);
        if (removed) URL.revokeObjectURL(removed.preview);
        this._renderEditorPart("photos");
        break;
      }
      case "drop-pending": {
        const [removed] = editor.pendingFiles.splice(Number(el.dataset.index), 1);
        if (removed) URL.revokeObjectURL(removed.preview);
        this._renderEditorPart("photos");
        break;
      }
      case "delete-photo":
        await this._run(this._ws("photos/delete", { photo_id: el.dataset.id }), t("Photo deleted"));
        break;
      case "cover-photo": {
        const ids = editor.plant.photos.map((photo) => photo.id);
        const order = [el.dataset.id, ...ids.filter((id) => id !== el.dataset.id)];
        await this._run(this._ws("photos/reorder", { plant_id: editor.id, photo_ids: order }));
        break;
      }
      case "open-notify":
        this._openNotify();
        break;
      case "notify-overlay":
        if (ev.target === el) this._closeNotify();
        break;
      case "close-notify":
        this._closeNotify();
        break;
      case "save-notify":
        if (await this._run(this._saveNotify(), t("Notifications saved"))) this._closeNotify();
        break;
      case "test-notify": {
        const saved = await this._run(this._saveNotify());
        if (!saved) break;
        const result = await this._run(this._ws("notifications/test"));
        if (result) this._toast(tn(result.sent, "Test sent to {n} phone", "Test sent to {n} phones"));
        this._renderNotify();
        break;
      }
      case "toggle-data":
        this._showData = !this._showData;
        this._renderMain();
        break;
      case "export-csv": {
        const result = await this._run(this._ws("export/csv"));
        if (result) this._download("plants.csv", result.csv, "text/csv");
        break;
      }
      case "export-json": {
        const result = await this._run(this._ws("export/json"));
        if (result) this._download("plants.json", JSON.stringify(result, null, 2), "application/json");
        break;
      }
      case "backup": {
        const result = await this._run(this._ws("backup/create"));
        if (result) {
          const link = document.createElement("a");
          link.href = result.url;
          link.download = "plant-manager-backup.zip";
          document.body.appendChild(link);
          link.click();
          link.remove();
        }
        break;
      }
      case "edit-trip":
        this._startTripDraft(this._trip.vacation);
        this._renderMain();
        break;
      case "cancel-trip-edit":
        this._tripDraft = null;
        this._tripPreview = null;
        this._tripError = null;
        this._renderMain();
        break;
      case "save-trip": {
        const d = this._tripDraft;
        const vacation = {
          start_date: d.start_date,
          end_date: d.end_date,
          sitter: d.sitter.trim() || null,
          sitter_notify: d.sitter_notify.trim() || null,
          notes: d.notes.trim() || null,
        };
        try {
          this._trip = await this._ws("vacation/set", { vacation });
          this._tripDraft = null;
          this._tripPreview = null;
          this._tripError = null;
          this._toast(t("Vacation saved. Have a good trip!"));
          this._renderTabs();
          this._renderMain();
        } catch (err) {
          this._tripError = err.message;
          this._renderMain();
        }
        break;
      }
      case "end-trip": {
        const active = this._trip?.plan?.active;
        if (!confirm(active ? t("End the vacation now? Reminders go back to you.") : t("Cancel the planned vacation?"))) break;
        await this._run(this._ws("vacation/end"), active ? t("Welcome back! 🌿") : t("Vacation cancelled"));
        break;
      }
      case "send-plan":
        await this._run(
          this._ws("vacation/send_plan"),
          t("Sent to {sitter}", { sitter: this._trip.vacation.sitter || t("the sitter") })
        );
        break;
      case "copy-plan":
        try {
          await navigator.clipboard.writeText(this._trip.text);
          this._toast(t("Plan copied"));
        } catch (err) {
          this._toast(t("Copying is not allowed here; use Print plan instead"));
        }
        break;
      case "print-plan":
        this._printPlan();
        break;
      case "delete-plant":
        if (confirm(t("Delete {name} with its photos and care log?", { name: editor.plant.name }))) {
          const done = await this._run(
            this._ws("plants/delete", { plant_id: editor.id }),
            t("Deleted {name}", { name: editor.plant.name })
          );
          if (done !== null) this._closeEditor();
        }
        break;
      default:
        break;
    }
  }

  _readField(el) {
    if (el.dataset.kind === "float") return el.value === "" ? null : parseFloat(el.value);
    return el.value;
  }

  _onInput(ev) {
    const el = ev.target;
    if (el.dataset.filter === "q") {
      this._filter.q = el.value;
      this._renderMain();
    } else if (el.dataset.trip && this._tripDraft && el.type !== "date") {
      this._tripDraft[el.dataset.trip] = el.value;
    } else if (el.dataset.field && this._editor && el.tagName !== "SELECT") {
      this._editor.draft[el.dataset.field] = this._readField(el);
      this._editor.touched.add(el.dataset.field);
      if (el.dataset.field === "name") this._updateTitle();
    } else if (el.dataset.profile && this._editor && el.type !== "checkbox") {
      const profile = { ...this._editor.draft.profile };
      profile[el.dataset.profile] = el.value === "" ? null : parseFloat(el.value);
      this._editor.draft.profile = profile;
      this._editor.touched.add("profile");
    }
  }

  async _onChange(ev) {
    const el = ev.target;
    const editor = this._editor;
    if (el.dataset.filter && el.dataset.filter !== "q") {
      this._filter[el.dataset.filter] = el.value;
      this._renderMain();
    } else if (el.dataset.notifyTarget !== undefined && this._notify) {
      const targets = this._notify.draft.targets.filter((t) => t !== el.dataset.notifyTarget);
      if (el.checked) targets.push(el.dataset.notifyTarget);
      this._notify.draft.targets = targets;
      this._renderNotify();
    } else if (el.dataset.notify && this._notify) {
      this._notify.draft[el.dataset.notify] = el.type === "checkbox" ? el.checked : el.value;
    } else if (el.dataset.trip && this._tripDraft) {
      this._tripDraft[el.dataset.trip] = el.value;
      if (el.type === "date") {
        // Moving the departure moves the return with it.
        const d = this._tripDraft;
        if (el.dataset.trip === "start_date" && d.start_date && d.end_date <= d.start_date) {
          d.end_date = isoDate(addDays(localDay(d.start_date), 7));
        }
        this._previewTrip();
      }
    } else if (el.dataset.importCsv !== undefined) {
      const [file] = el.files;
      el.value = "";
      if (!file) return;
      try {
        const report = await this._uploadFile("csv", file);
        const problems = [
          ...report.errors.map((e) => ({ ...e, level: "medium", label: t("skipped") })),
          ...report.warnings.map((e) => ({ ...e, level: "", label: "" })),
        ];
        this._importReport = `<p class="meta">${esc(t("Imported {n} plant(s).", { n: report.created }))}</p>${
          problems.length
            ? `<div class="list">${problems
                .map((e) => `<div class="warning ${e.level}">${esc(t("⚠ Row {row} {name}: {error}", { row: e.row, name: e.name || "", error: e.error }))}${e.label ? ` (${esc(e.label)})` : ""}</div>`)
                .join("")}</div>`
            : ""
        }`;
        this._toast(t("Imported {n} plant(s)", { n: report.created }));
      } catch (err) {
        this._toast(t("Import failed: {error}", { error: err.message }));
      }
      this._renderMain();
    } else if (el.dataset.restore !== undefined) {
      const [file] = el.files;
      el.value = "";
      if (!file || !confirm(t("Replace ALL plants, photos and care logs with this backup? The current data is kept as *.before-restore."))) return;
      try {
        const result = await this._uploadFile("backup", file);
        this._toast(t("Restored {plants} plant(s) and {photos} photo(s)", { plants: result.plants, photos: result.photos }));
        this._importReport = "";
      } catch (err) {
        this._toast(t("Restore failed: {error}", { error: err.message }));
      }
    } else if (el.dataset.identify !== undefined && editor) {
      const [file] = el.files;
      el.value = "";
      if (file) this._identify(file);
    } else if (el.dataset.upload !== undefined && editor) {
      const files = [...el.files];
      el.value = "";
      this._handleFiles(files);
    } else if (el.dataset.profile === "winter_dormancy" && editor) {
      editor.draft.profile = { ...editor.draft.profile, winter_dormancy: el.checked };
      editor.touched.add("profile");
    } else if (el.dataset.field && editor) {
      editor.draft[el.dataset.field] = this._readField(el);
      editor.touched.add(el.dataset.field);
      if (el.dataset.field === "species") {
        // A new species brings its care profile, unless the user edited it.
        const known = this._config.species.find((s) => s.value.toLowerCase() === el.value.trim().toLowerCase());
        if (known && !editor.touched.has("common_name")) {
          editor.draft.common_name = known.label.replace(/\s*\(.*\)$/, "");
          if (!editor.touched.has("name")) editor.draft.name = editor.draft.common_name;
          this._renderEditorPart("form");
          this._updateTitle();
        }
        if (!editor.id) editor.touched.delete("profile");
        await this._resolveProfile(false);
      }
    }
  }
}

customElements.define("plant-manager-panel", PlantManagerPanel);

installGardenPanel(PlantManagerPanel);
