"""Built-in care profiles for common plants.

``base_interval_days`` is the watering interval under reference conditions:
15 cm plastic pot with drainage, medium indirect light, 21 °C, 50 % relative
humidity, during the growing season. The care model scales it from there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import (
    P_BASE_INTERVAL,
    P_FERTILIZE_INTERVAL,
    P_LIGHT_PREFERENCE,
    P_MAX_HUMIDITY,
    P_MAX_LUX,
    P_MAX_MOISTURE,
    P_MAX_TEMP,
    P_MIN_HUMIDITY,
    P_MIN_LUX,
    P_MIN_MOISTURE,
    P_MIN_TEMP,
    P_NOTES,
    P_TOXIC_TO_PETS,
    P_WINTER_DORMANCY,
)

DEFAULT_PROFILE: dict[str, Any] = {
    P_BASE_INTERVAL: 7.0,
    P_WINTER_DORMANCY: True,
    P_FERTILIZE_INTERVAL: 21,
    P_MIN_TEMP: 15.0,
    P_MAX_TEMP: 30.0,
    P_MIN_HUMIDITY: 40.0,
    P_MAX_HUMIDITY: 80.0,
    P_MIN_MOISTURE: 20.0,
    P_MAX_MOISTURE: 60.0,
    P_MIN_LUX: 1500.0,
    P_MAX_LUX: 30000.0,
    P_LIGHT_PREFERENCE: "bright_indirect",
    P_TOXIC_TO_PETS: None,
    P_NOTES: "",
}


@dataclass(frozen=True, slots=True)
class SpeciesEntry:
    """A built-in species or genus entry."""

    key: str
    common_name: str
    profile: dict[str, Any]
    aliases: tuple[str, ...] = ()


# Groups of shared climate requirements, merged under each entry.
_TROPICAL = {
    P_MIN_TEMP: 16.0,
    P_MAX_TEMP: 30.0,
    P_MIN_HUMIDITY: 50.0,
    P_MAX_HUMIDITY: 85.0,
    P_MIN_MOISTURE: 25.0,
    P_MAX_MOISTURE: 65.0,
    P_MIN_LUX: 1500.0,
    P_MAX_LUX: 25000.0,
    P_LIGHT_PREFERENCE: "bright_indirect",
}
_HUMIDITY_LOVER = {
    P_MIN_TEMP: 17.0,
    P_MAX_TEMP: 29.0,
    P_MIN_HUMIDITY: 60.0,
    P_MAX_HUMIDITY: 90.0,
    P_MIN_MOISTURE: 35.0,
    P_MAX_MOISTURE: 70.0,
    P_MIN_LUX: 1000.0,
    P_MAX_LUX: 15000.0,
    P_LIGHT_PREFERENCE: "medium",
}
_HARDY = {
    P_MIN_TEMP: 12.0,
    P_MAX_TEMP: 32.0,
    P_MIN_HUMIDITY: 30.0,
    P_MAX_HUMIDITY: 80.0,
    P_MIN_MOISTURE: 15.0,
    P_MAX_MOISTURE: 55.0,
    P_MIN_LUX: 500.0,
    P_MAX_LUX: 30000.0,
    P_LIGHT_PREFERENCE: "medium",
}
_SUCCULENT = {
    P_MIN_TEMP: 10.0,
    P_MAX_TEMP: 35.0,
    P_MIN_HUMIDITY: 20.0,
    P_MAX_HUMIDITY: 60.0,
    P_MIN_MOISTURE: 7.0,
    P_MAX_MOISTURE: 40.0,
    P_MIN_LUX: 5000.0,
    P_MAX_LUX: 80000.0,
    P_LIGHT_PREFERENCE: "direct",
    P_WINTER_DORMANCY: True,
}
_HERB = {
    P_MIN_TEMP: 10.0,
    P_MAX_TEMP: 32.0,
    P_MIN_HUMIDITY: 40.0,
    P_MAX_HUMIDITY: 80.0,
    P_MIN_MOISTURE: 30.0,
    P_MAX_MOISTURE: 70.0,
    P_MIN_LUX: 8000.0,
    P_MAX_LUX: 80000.0,
    P_LIGHT_PREFERENCE: "direct",
    P_WINTER_DORMANCY: False,
}
_MEDITERRANEAN = {
    P_MIN_TEMP: 5.0,
    P_MAX_TEMP: 35.0,
    P_MIN_HUMIDITY: 30.0,
    P_MAX_HUMIDITY: 70.0,
    P_MIN_MOISTURE: 15.0,
    P_MAX_MOISTURE: 50.0,
    P_MIN_LUX: 10000.0,
    P_MAX_LUX: 90000.0,
    P_LIGHT_PREFERENCE: "direct",
    P_WINTER_DORMANCY: True,
}


def _e(
    key: str,
    common: str,
    group: dict[str, Any],
    interval: float,
    fertilize: int,
    *,
    toxic: bool | None = None,
    dormancy: bool | None = None,
    notes: str = "",
    aliases: tuple[str, ...] = (),
    **overrides: Any,
) -> SpeciesEntry:
    profile = {
        **DEFAULT_PROFILE,
        **group,
        P_BASE_INTERVAL: interval,
        P_FERTILIZE_INTERVAL: fertilize,
    }
    if dormancy is not None:
        profile[P_WINTER_DORMANCY] = dormancy
    profile[P_TOXIC_TO_PETS] = toxic
    profile[P_NOTES] = notes
    profile.update(overrides)
    return SpeciesEntry(key, common, profile, aliases)


_ENTRIES: list[SpeciesEntry] = [
    # Aroids
    _e(
        "monstera deliciosa",
        "Swiss cheese plant",
        _TROPICAL,
        7,
        14,
        toxic=True,
        notes="Let the top 3-5 cm of soil dry out between waterings.",
    ),
    _e("monstera adansonii", "Monkey mask monstera", _TROPICAL, 6, 14, toxic=True),
    _e(
        "epipremnum aureum",
        "Golden pothos",
        _TROPICAL,
        8,
        21,
        toxic=True,
        aliases=("scindapsus aureus", "pothos"),
    ),
    _e("scindapsus pictus", "Satin pothos", _TROPICAL, 9, 21, toxic=True),
    _e("philodendron hederaceum", "Heartleaf philodendron", _TROPICAL, 7, 21, toxic=True),
    _e("philodendron", "Philodendron", _TROPICAL, 7, 21, toxic=True),
    _e(
        "thaumatophyllum bipinnatifidum",
        "Tree philodendron",
        _TROPICAL,
        7,
        21,
        toxic=True,
        aliases=("philodendron bipinnatifidum", "philodendron selloum"),
    ),
    _e(
        "zamioculcas zamiifolia",
        "ZZ plant",
        _HARDY,
        18,
        42,
        toxic=True,
        notes="Stores water in its rhizomes; err on the side of underwatering.",
    ),
    _e(
        "spathiphyllum",
        "Peace lily",
        _HUMIDITY_LOVER,
        5,
        21,
        toxic=True,
        aliases=("spathiphyllum wallisii",),
        notes="Droops visibly when thirsty.",
    ),
    _e(
        "anthurium andraeanum",
        "Flamingo flower",
        _HUMIDITY_LOVER,
        7,
        21,
        toxic=True,
        light_preference="bright_indirect",
    ),
    _e(
        "alocasia",
        "Elephant ear",
        _HUMIDITY_LOVER,
        6,
        14,
        toxic=True,
        notes="May go dormant and drop leaves in winter; water less then.",
    ),
    _e(
        "aglaonema",
        "Chinese evergreen",
        _TROPICAL,
        8,
        28,
        toxic=True,
        light_preference="medium",
        min_light_lux=700.0,
    ),
    _e("dieffenbachia", "Dumb cane", _TROPICAL, 7, 21, toxic=True),
    _e("syngonium podophyllum", "Arrowhead plant", _TROPICAL, 6, 21, toxic=True),
    # Dracaena & relatives
    _e(
        "dracaena trifasciata",
        "Snake plant",
        _HARDY,
        18,
        42,
        toxic=True,
        aliases=("sansevieria trifasciata", "sansevieria"),
        notes="Water only when the soil is completely dry.",
    ),
    _e("dracaena marginata", "Dragon tree", _HARDY, 10, 28, toxic=True),
    _e("dracaena fragrans", "Corn plant", _HARDY, 9, 28, toxic=True),
    _e("dracaena", "Dracaena", _HARDY, 10, 28, toxic=True),
    _e("yucca", "Yucca", _MEDITERRANEAN, 16, 30, toxic=True, aliases=("yucca elephantipes",)),
    _e("beaucarnea recurvata", "Ponytail palm", _SUCCULENT, 21, 42, toxic=False),
    # Ficus
    _e(
        "ficus lyrata",
        "Fiddle-leaf fig",
        _TROPICAL,
        8,
        21,
        toxic=True,
        notes="Dislikes being moved and cold drafts.",
    ),
    _e("ficus elastica", "Rubber plant", _TROPICAL, 9, 21, toxic=True, min_humidity=40.0),
    _e("ficus benjamina", "Weeping fig", _TROPICAL, 7, 21, toxic=True),
    _e("ficus", "Fig", _TROPICAL, 8, 21, toxic=True),
    # Prayer plants
    _e(
        "goeppertia",
        "Calathea",
        _HUMIDITY_LOVER,
        5,
        21,
        toxic=False,
        aliases=("calathea",),
        notes="Prefers filtered or rain water; sensitive to dry air.",
    ),
    _e("maranta leuconeura", "Prayer plant", _HUMIDITY_LOVER, 5, 21, toxic=False),
    _e("ctenanthe", "Never-never plant", _HUMIDITY_LOVER, 5, 21, toxic=False),
    # Palms
    _e(
        "chamaedorea elegans",
        "Parlour palm",
        _TROPICAL,
        6,
        28,
        toxic=False,
        light_preference="medium",
    ),
    _e("dypsis lutescens", "Areca palm", _TROPICAL, 6, 21, toxic=False),
    _e("howea forsteriana", "Kentia palm", _TROPICAL, 8, 28, toxic=False),
    _e("strelitzia nicolai", "Giant bird of paradise", _TROPICAL, 8, 14, toxic=True),
    _e(
        "strelitzia reginae",
        "Bird of paradise",
        _TROPICAL,
        8,
        14,
        toxic=True,
        light_preference="direct",
    ),
    # Trailing & small foliage
    _e("chlorophytum comosum", "Spider plant", _HARDY, 6, 21, toxic=False),
    _e("hoya carnosa", "Wax plant", _TROPICAL, 12, 28, toxic=False, min_humidity=40.0),
    _e("hoya", "Hoya", _TROPICAL, 12, 28, toxic=False, min_humidity=40.0),
    _e("peperomia obtusifolia", "Baby rubber plant", _TROPICAL, 10, 30, toxic=False),
    _e("peperomia", "Peperomia", _TROPICAL, 10, 30, toxic=False),
    _e(
        "pilea peperomioides",
        "Chinese money plant",
        _TROPICAL,
        7,
        21,
        toxic=False,
        min_humidity=40.0,
    ),
    _e("tradescantia zebrina", "Inch plant", _HARDY, 6, 21, toxic=True),
    _e("tradescantia", "Spiderwort", _HARDY, 6, 21, toxic=True),
    _e("hedera helix", "English ivy", _HARDY, 6, 21, toxic=True),
    _e(
        "ceropegia woodii",
        "String of hearts",
        _SUCCULENT,
        14,
        28,
        toxic=False,
        light_preference="bright_indirect",
    ),
    _e(
        "curio rowleyanus",
        "String of pearls",
        _SUCCULENT,
        14,
        28,
        toxic=True,
        aliases=("senecio rowleyanus",),
        light_preference="bright_indirect",
    ),
    _e(
        "schefflera arboricola",
        "Dwarf umbrella tree",
        _TROPICAL,
        8,
        21,
        toxic=True,
        aliases=("heptapleurum arboricola",),
    ),
    _e("begonia", "Begonia", _HUMIDITY_LOVER, 6, 14, toxic=True, dormancy=False),
    _e(
        "saintpaulia",
        "African violet",
        _HUMIDITY_LOVER,
        5,
        14,
        toxic=False,
        aliases=("streptocarpus ionanthus",),
        dormancy=False,
        notes="Water from below; avoid wetting the leaves.",
    ),
    # Ferns
    _e(
        "nephrolepis exaltata",
        "Boston fern",
        _HUMIDITY_LOVER,
        3,
        28,
        toxic=False,
        notes="Never let the soil dry out completely.",
    ),
    _e("adiantum", "Maidenhair fern", _HUMIDITY_LOVER, 3, 28, toxic=False),
    _e("asplenium nidus", "Bird's nest fern", _HUMIDITY_LOVER, 5, 28, toxic=False),
    # Orchids & bromeliads
    _e(
        "phalaenopsis",
        "Moth orchid",
        _TROPICAL,
        8,
        14,
        toxic=False,
        dormancy=False,
        min_soil_moisture=15.0,
        notes="Water when the roots turn silvery; never leave standing in water.",
    ),
    _e("guzmania", "Guzmania bromeliad", _HUMIDITY_LOVER, 7, 30, toxic=False),
    # Succulents & cacti
    _e("aloe vera", "Aloe vera", _SUCCULENT, 18, 42, toxic=True, aliases=("aloe barbadensis",)),
    _e("aloe", "Aloe", _SUCCULENT, 18, 42, toxic=True),
    _e("echeveria", "Echeveria", _SUCCULENT, 16, 42, toxic=False),
    _e("crassula ovata", "Jade plant", _SUCCULENT, 16, 42, toxic=True),
    _e(
        "haworthiopsis",
        "Zebra haworthia",
        _SUCCULENT,
        18,
        42,
        toxic=False,
        aliases=("haworthia", "haworthiopsis attenuata", "haworthiopsis fasciata"),
        light_preference="bright_indirect",
    ),
    _e("kalanchoe blossfeldiana", "Flaming Katy", _SUCCULENT, 12, 21, toxic=True),
    _e("euphorbia milii", "Crown of thorns", _SUCCULENT, 14, 28, toxic=True),
    _e(
        "schlumbergera",
        "Christmas cactus",
        _TROPICAL,
        9,
        21,
        toxic=False,
        dormancy=False,
        light_preference="bright_indirect",
    ),
    _e(
        "cactaceae",
        "Cactus",
        _SUCCULENT,
        25,
        42,
        toxic=False,
        notes="Barely water in winter (every 4-6 weeks).",
    ),
    # Herbs & edibles
    _e("ocimum basilicum", "Basil", _HERB, 2, 14, toxic=False, min_temp=15.0),
    _e("mentha", "Mint", _HERB, 2, 21, toxic=True),
    _e("petroselinum crispum", "Parsley", _HERB, 3, 21, toxic=False),
    _e(
        "salvia rosmarinus",
        "Rosemary",
        _MEDITERRANEAN,
        8,
        42,
        toxic=False,
        aliases=("rosmarinus officinalis",),
    ),
    _e("thymus vulgaris", "Thyme", _MEDITERRANEAN, 8, 42, toxic=False),
    _e(
        "lavandula angustifolia",
        "Lavender",
        _MEDITERRANEAN,
        9,
        42,
        toxic=True,
        aliases=("lavandula",),
    ),
    _e(
        "solanum lycopersicum",
        "Tomato",
        _HERB,
        2,
        10,
        toxic=True,
        notes="Water deeply and consistently to avoid blossom end rot.",
    ),
    _e("capsicum annuum", "Chili / bell pepper", _HERB, 3, 14, toxic=False),
    _e("fragaria x ananassa", "Strawberry", _HERB, 3, 14, toxic=False),
    _e("citrus", "Citrus", _MEDITERRANEAN, 6, 14, toxic=True, min_temp=8.0),
    _e("olea europaea", "Olive tree", _MEDITERRANEAN, 10, 30, toxic=False),
]


def _norm(name: str) -> str:
    return " ".join(name.lower().replace("×", "x").split())  # noqa: RUF001


_INDEX: dict[str, SpeciesEntry] = {}
for _entry in _ENTRIES:
    _INDEX[_entry.key] = _entry
    for _alias in _entry.aliases:
        _INDEX.setdefault(_norm(_alias), _entry)
    _INDEX.setdefault(_norm(_entry.common_name), _entry)


def lookup(name: str, family: str | None = None) -> SpeciesEntry | None:
    """Find the best matching entry for a species, genus, family or common name."""
    key = _norm(name)
    if not key:
        return None
    if key in _INDEX:
        return _INDEX[key]
    # Drop cultivar / variety suffixes: "Monstera deliciosa 'Thai Constellation'"
    words = key.replace("'", " ").replace('"', " ").split()
    if len(words) >= 2 and (match := _INDEX.get(" ".join(words[:2]))):
        return match
    if words and (match := _INDEX.get(words[0])):
        return match
    if family and (match := _INDEX.get(_norm(family))):
        return match
    return None


def species_options() -> list[dict[str, str]]:
    """Return select options for the manual species picker."""
    return [
        {
            "value": entry.key.capitalize(),
            "label": f"{entry.common_name} ({entry.key.capitalize()})",
        }
        for entry in _ENTRIES
    ]
