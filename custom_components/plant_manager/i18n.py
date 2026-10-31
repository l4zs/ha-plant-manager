"""Texts the integration writes itself: notifications, the sitter's plan, errors.

Texts are written in English and looked up in a table per language, like gettext:
``tr("de", "{name} needs water", name="Monty")``. Errors are raised in English and
translated where they leave the integration (``translate_message``).
"""

from __future__ import annotations

from datetime import date
from functools import cache
import re

DEFAULT = "en"
LANGUAGES = ("en", "de")

GERMAN: dict[str, str] = {
    # problems (care.PROBLEM_TEXT)
    "watering is overdue": "Gießen ist überfällig",
    "too cold": "zu kalt",
    "too hot": "zu warm",
    "air too dry": "Luft zu trocken",
    "air too humid": "Luft zu feucht",
    "soil too wet": "Erde zu nass",
    "too dark": "zu dunkel",
    "too much direct light": "zu viel direktes Licht",
    # alerts
    "{name} is overdue for water": "{name} hätte längst Wasser gebraucht",
    "{name} needs water": "{name} braucht Wasser",
    "{name} could use fertilizer": "{name} könnte Dünger gebrauchen",
    "💧 Water: {names}": "💧 Gießen: {names}",
    "🌱 Fertilize: {names}": "🌱 Düngen: {names}",
    "Needs water": "Braucht Wasser",
    "Fertilize": "Düngen",
    "[Open the plant]": "[Pflanze öffnen]",
    "[Open today's care]": "[Heutige Pflege öffnen]",
    # vacation tips (vacation.TIP_TEXT)
    "Move it out of direct sun, a few metres from the window": (
        "Aus der direkten Sonne nehmen, ein paar Meter vom Fenster weg"
    ),
    "Put the pot in a plastic or glazed cachepot so the walls don't dry it out": (
        "Den Topf in einen Übertopf aus Plastik oder glasierter Keramik stellen, "
        "damit die Wände ihn nicht austrocknen"
    ),
    "The soil moisture sensor shows when it really needs water": (
        "Der Bodenfeuchtesensor zeigt, wann sie wirklich Wasser braucht"
    ),
    # the sitter's plan
    "🪴 Plant care from {start} to {end}": "🪴 Pflanzenpflege vom {start} bis {end}",
    "Thank you, {sitter}!": "Danke, {sitter}!",
    "Please water on these days:": "Bitte an diesen Tagen gießen:",
    (
        "Water slowly until it runs out at the bottom, then empty the saucer after 15 minutes. "
        "If the soil is still moist 2 cm deep, skip it."
    ): (
        "Langsam gießen, bis unten Wasser herausläuft, und den Untersetzer nach 15 Minuten "
        "leeren. Ist die Erde in 2 cm Tiefe noch feucht, die Pflanze auslassen."
    ),
    "Nothing to water, all plants last until we are back.": (
        "Nichts zu gießen, alle Pflanzen halten durch, bis wir zurück sind."
    ),
    # reminders
    "Plant care": "Pflanzenpflege",
    "The plant sitter": "Der Pflanzensitter",
    "💧 Water right before you leave: {names}": "💧 Direkt vor der Abreise gießen: {names}",
    "🧑‍🌾 The plant sitter needs to come 1 time, first on {day}": (
        "🧑‍🌾 Der Pflanzensitter muss einmal kommen, am {day}"
    ),
    "🧑‍🌾 The plant sitter needs to come {n} times, first on {day}": (
        "🧑‍🌾 Der Pflanzensitter muss {n}-mal kommen, zuerst am {day}"
    ),
    "All plants last until you are back 🌿": "Alle Pflanzen halten durch, bis du zurück bist 🌿",
    "[Open the vacation plan]": "[Urlaubsplan öffnen]",
    "Before you leave": "Vor der Abreise",
    "🧳 {sitter} waters today: {names}": "🧳 {sitter} gießt heute: {names}",
    "🪴 Please water today: {names}": "🪴 Bitte heute gießen: {names}",
    "Nothing to water today 🌿": "Heute gibt es nichts zu gießen 🌿",
    "🧳 Leaving tomorrow:": "🧳 Morgen geht es los:",
    "All plants are happy 🌿": "Alle Pflanzen sind zufrieden 🌿",
    "🌿 Plant Manager notifications work on this phone.": (
        "🌿 Benachrichtigungen von Plant Manager kommen auf diesem Handy an."
    ),
    # calendar and to-do list
    "💧 Water": "💧 Gießen",
    "🌱 Fertilize": "🌱 Düngen",
    "🧳 Water before leaving:": "🧳 Vor der Abreise gießen:",
    "🧑‍🌾 Plant sitter waters": "🧑‍🌾 Pflanzensitter gießt",
    "🧳 Vacation": "🧳 Urlaub",
    "💧 Water {name}": "💧 {name} gießen",
    "🌱 Fertilize {name}": "🌱 {name} düngen",
    # care tips of the built-in species (species_db)
    "Let the top 3-5 cm of soil dry out between waterings.": (
        "Die oberen 3-5 cm der Erde zwischen dem Gießen antrocknen lassen."
    ),
    "Stores water in its rhizomes; err on the side of underwatering.": (
        "Speichert Wasser in den Rhizomen; im Zweifel lieber zu wenig gießen."
    ),
    "Droops visibly when thirsty.": "Lässt sichtbar die Blätter hängen, wenn sie Durst hat.",
    "May go dormant and drop leaves in winter; water less then.": (
        "Kann im Winter ruhen und Blätter abwerfen; dann weniger gießen."
    ),
    "Water only when the soil is completely dry.": "Nur gießen, wenn die Erde ganz trocken ist.",
    "Dislikes being moved and cold drafts.": (
        "Mag es nicht, umgestellt zu werden, und keine kalte Zugluft."
    ),
    "Prefers filtered or rain water; sensitive to dry air.": (
        "Mag gefiltertes Wasser oder Regenwasser; empfindlich gegen trockene Luft."
    ),
    "Water from below; avoid wetting the leaves.": (
        "Von unten gießen; die Blätter nicht nass machen."
    ),
    "Never let the soil dry out completely.": "Die Erde nie ganz austrocknen lassen.",
    "Water when the roots turn silvery; never leave standing in water.": (
        "Gießen, wenn die Wurzeln silbrig werden; nie im Wasser stehen lassen."
    ),
    "Barely water in winter (every 4-6 weeks).": "Im Winter kaum gießen (alle 4-6 Wochen).",
    "Water deeply and consistently to avoid blossom end rot.": (
        "Gründlich und gleichmäßig gießen, um Blütenendfäule zu vermeiden."
    ),
    # errors
    "Plant Manager is not loaded": "Plant Manager ist nicht geladen",
    "Not loaded": "Nicht geladen",
    "Plant not found": "Pflanze nicht gefunden",
    "Plant {id} not found": "Pflanze {id} nicht gefunden",
    "Care event {id} not found": "Pflegeeintrag {id} nicht gefunden",
    "Photo {id} not found": "Foto {id} nicht gefunden",
    "Vacation {id} not found": "Urlaub {id} nicht gefunden",
    "File too large": "Datei zu groß",
    "Missing file": "Keine Datei",
    "Unknown upload": "Unbekannter Upload",
    "Only administrators can restore": "Nur Administratoren können wiederherstellen",
    "This trip is already over": "Diese Reise ist schon vorbei",
    "The notify action {service} does not exist": (
        "Die Benachrichtigungsaktion {service} gibt es nicht"
    ),
    "No vacation is planned": "Es ist kein Urlaub geplant",
    "Set a notify action for the plant sitter first": (
        "Lege zuerst eine Benachrichtigungsaktion für den Pflanzensitter fest"
    ),
    "Invalid time {time}": "Ungültige Uhrzeit {time}",
    "Invalid date {value}": "Ungültiges Datum {value}",
    "Unsupported image format": "Dieses Bildformat wird nicht unterstützt",
    "The photo is no longer available, take it again": (
        "Das Foto ist nicht mehr verfügbar, bitte nimm es neu auf"
    ),
    "This is not a Plant Manager backup": "Das ist keine Plant-Manager-Sicherung",
    "The backup's database is damaged": "Die Datenbank der Sicherung ist beschädigt",
    "The backup is from a newer version of Plant Manager": (
        "Die Sicherung stammt von einer neueren Version von Plant Manager"
    ),
    "This is not a zip file": "Das ist keine ZIP-Datei",
    "The day you are back must be after the day you leave": (
        "Der Tag der Rückkehr muss nach dem Tag der Abreise liegen"
    ),
    "A vacation can be at most {days} days long": "Ein Urlaub darf höchstens {days} Tage dauern",
    "{field} must be higher than the minimum": "{field} muss größer als das Minimum sein",
    # CSV import
    "{key} must be one of {choices}": "{key} muss einer von diesen Werten sein: {choices}",
    "area {area} not found, imported without an area": (
        "Bereich {area} nicht gefunden, ohne Bereich importiert"
    ),
    "last_watered {value} is not a date": "last_watered {value} ist kein Datum",
    "{column} must be yes or no": "{column} muss yes oder no sein",
    "needs a species or a base_interval_days": "braucht eine species oder base_interval_days",
}

# German common names of the built-in species, by species key.
COMMON_NAMES_DE: dict[str, str] = {
    "monstera deliciosa": "Monstera",
    "monstera adansonii": "Monstera adansonii",
    "epipremnum aureum": "Efeutute",
    "scindapsus pictus": "Silberne Efeutute",
    "philodendron hederaceum": "Kletter-Philodendron",
    "philodendron": "Philodendron",
    "thaumatophyllum bipinnatifidum": "Baumfreund",
    "zamioculcas zamiifolia": "Zamioculcas",
    "spathiphyllum": "Einblatt",
    "anthurium andraeanum": "Flamingoblume",
    "alocasia": "Pfeilblatt",
    "aglaonema": "Kolbenfaden",
    "dieffenbachia": "Dieffenbachie",
    "syngonium podophyllum": "Purpurtute",
    "dracaena trifasciata": "Bogenhanf",
    "dracaena marginata": "Drachenbaum",
    "dracaena fragrans": "Duftender Drachenbaum",
    "dracaena": "Drachenbaum",
    "yucca": "Yucca-Palme",
    "beaucarnea recurvata": "Elefantenfuß",
    "ficus lyrata": "Geigenfeige",
    "ficus elastica": "Gummibaum",
    "ficus benjamina": "Birkenfeige",
    "ficus": "Feige",
    "goeppertia": "Korbmarante",
    "maranta leuconeura": "Pfeilwurz",
    "ctenanthe": "Ctenanthe",
    "chamaedorea elegans": "Bergpalme",
    "dypsis lutescens": "Goldfruchtpalme",
    "howea forsteriana": "Kentiapalme",
    "strelitzia nicolai": "Baumstrelitzie",
    "strelitzia reginae": "Paradiesvogelblume",
    "chlorophytum comosum": "Grünlilie",
    "hoya carnosa": "Wachsblume",
    "hoya": "Wachsblume",
    "peperomia obtusifolia": "Fleischiger Zwergpfeffer",
    "peperomia": "Zwergpfeffer",
    "pilea peperomioides": "Ufopflanze",
    "tradescantia zebrina": "Zebra-Ampelkraut",
    "tradescantia": "Dreimasterblume",
    "hedera helix": "Efeu",
    "ceropegia woodii": "Leuchterblume",
    "curio rowleyanus": "Erbsenpflanze",
    "schefflera arboricola": "Strahlenaralie",
    "begonia": "Begonie",
    "saintpaulia": "Usambaraveilchen",
    "nephrolepis exaltata": "Schwertfarn",
    "adiantum": "Frauenhaarfarn",
    "asplenium nidus": "Nestfarn",
    "phalaenopsis": "Schmetterlingsorchidee",
    "guzmania": "Guzmanie",
    "aloe vera": "Aloe vera",
    "aloe": "Aloe",
    "echeveria": "Echeverie",
    "crassula ovata": "Geldbaum",
    "haworthiopsis": "Zebra-Haworthie",
    "kalanchoe blossfeldiana": "Flammendes Käthchen",
    "euphorbia milii": "Christusdorn",
    "schlumbergera": "Weihnachtskaktus",
    "cactaceae": "Kaktus",
    "ocimum basilicum": "Basilikum",
    "mentha": "Minze",
    "petroselinum crispum": "Petersilie",
    "salvia rosmarinus": "Rosmarin",
    "thymus vulgaris": "Thymian",
    "lavandula angustifolia": "Lavendel",
    "solanum lycopersicum": "Tomate",
    "capsicum annuum": "Paprika / Chili",
    "fragaria x ananassa": "Erdbeere",
    "citrus": "Zitruspflanze",
    "olea europaea": "Olivenbaum",
}

_TABLES = {"de": GERMAN}

_WEEKDAYS = {
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    "de": ("Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So."),
}
_MONTHS = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "de": (
        "Jan.",
        "Feb.",
        "März",
        "Apr.",
        "Mai",
        "Juni",
        "Juli",
        "Aug.",
        "Sep.",
        "Okt.",
        "Nov.",
        "Dez.",
    ),
}


def language(code: str | None) -> str:
    """The supported language for a language code such as "de-CH"; English otherwise."""
    base = (code or "").replace("_", "-").split("-")[0].lower()
    return base if base in LANGUAGES else DEFAULT


def tr(lang: str | None, text: str, **values: object) -> str:
    """Translate an English text and fill in its ``{placeholders}``."""
    template = _TABLES.get(language(lang), {}).get(text, text)
    return template.format(**values) if values else template


def tr_lower(lang: str | None, text: str) -> str:
    """Translate a sentence that follows a colon: lower case in English, German keeps nouns."""
    result = tr(lang, text)
    return result[:1].lower() + result[1:] if language(lang) == DEFAULT else result


def format_day(day: date, lang: str | None) -> str:
    """A short date: "Sat 2 Nov" or "Sa. 2. Nov."."""
    lang = language(lang)
    weekday, month = _WEEKDAYS[lang][day.weekday()], _MONTHS[lang][day.month - 1]
    if lang == "de":
        return f"{weekday} {day.day}. {month}"
    return f"{weekday} {day.day} {month}"


@cache
def _patterns(lang: str) -> list[tuple[re.Pattern[str], str]]:
    """Templates with placeholders as regular expressions, to translate formatted texts."""
    patterns = []
    for english, translated in _TABLES.get(lang, {}).items():
        if "{" not in english:
            continue
        regex = re.sub(r"\\\{(\w+)\\\}", lambda m: f"(?P<{m.group(1)}>.+?)", re.escape(english))
        patterns.append((re.compile(f"^{regex}$", re.DOTALL), translated))
    return patterns


def translate_message(lang: str | None, message: str) -> str:
    """Translate a text that was formatted in English, e.g. an error message."""
    lang = language(lang)
    table = _TABLES.get(lang)
    if not table:
        return message
    if message in table:
        return table[message]
    for pattern, translated in _patterns(lang):
        if match := pattern.match(message):
            return translated.format(**match.groupdict())
    return message
