"""Shared helpers for the Sigma Dex scripts: loading, constants, template, completeness."""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SPECIES_DIR = ROOT / "data" / "species"
CONFIG_PATH = ROOT / "data" / "config.yaml"

ENGINE_PATH = ROOT / "data" / "engine" / "expansion.yaml"

# The 18 types a Pokemon can have in pokeemerald-expansion.
TYPES = [
    "Normal", "Fire", "Water", "Grass", "Electric", "Ice", "Fighting", "Poison", "Ground",
    "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy",
]
STATS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
GROWTH_RATES = ["erratic", "fast", "medium_fast", "medium_slow", "slow", "fluctuating"]
EGG_GROUPS = [
    "monster", "water_1", "water_2", "water_3", "bug", "flying", "field", "fairy", "grass",
    "human_like", "mineral", "amorphous", "dragon", "ditto", "undiscovered",
]
BODY_COLORS = ["red", "blue", "yellow", "green", "black", "brown", "purple", "gray", "white", "pink"]
GENDER_VALUES = [0, 12.5, 25, 50, 75, 87.5, 100, "genderless"]
# Our method name -> the constant the game uses. "other" = needs custom code.
EVOLUTION_METHODS = {
    "level": "EVO_LEVEL",
    "item": "EVO_ITEM",
    "trade": "EVO_TRADE",
    "trade_item": "EVO_TRADE_ITEM",
    "friendship": "EVO_FRIENDSHIP",
    "friendship_day": "EVO_FRIENDSHIP_DAY",
    "friendship_night": "EVO_FRIENDSHIP_NIGHT",
    "level_attack_higher": "EVO_LEVEL_ATK_GT_DEF",
    "level_attack_equal": "EVO_LEVEL_ATK_EQ_DEF",
    "level_defense_higher": "EVO_LEVEL_ATK_LT_DEF",
    "beauty": "EVO_BEAUTY",
    "other": None,
}
LEVEL_METHODS = ("level", "level_attack_higher", "level_attack_equal", "level_defense_higher")
ITEM_METHODS = ("item", "trade_item")
MAX_EVOLUTIONS = 5           # EVOS_PER_MON

# Text limits in pokeemerald-expansion (include/constants/global.h, struct SpeciesInfo).
NAME_LIMIT = 12              # POKEMON_NAME_LENGTH
CATEGORY_LIMIT = 12          # categoryName[13]
MOVE_NAME_LIMIT = 16
ABILITY_NAME_LIMIT = 16
DESCRIPTION_LINES = 4
DESCRIPTION_LINE_LENGTH = 42

def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


def scalar(value):
    """One value as YAML text: plain when that is safe, quoted otherwise."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return "%g" % value
    text = str(value).strip()
    if re.match(r"^[A-Za-z][A-Za-z0-9 ._'\-]*$", text) and text.lower() not in (
        "yes", "no", "on", "off", "true", "false", "null", "y", "n",
    ):
        return text
    return json.dumps(text, ensure_ascii=False)


def flow_map(mapping, keys):
    parts = ["%s: %s" % (k, scalar(mapping[k])) for k in keys if mapping.get(k) is not None]
    parts += ["%s: %s" % (k, scalar(v)) for k, v in mapping.items() if k not in keys and v is not None]
    return "{" + ", ".join(parts) + "}"


def render_species(data):
    """The canonical text of a species file: every field, in a fixed order, with its hint."""
    lines = []

    def put(indent, key, text="", comment=None):
        line = "%s%s:%s" % ("  " * indent, key, " " + text if text != "" else "")
        lines.append(line.ljust(24) + " # " + comment if comment and len(line) <= 40 else line)

    def put_list(indent, key, values, comment):
        items = [scalar(v) for v in listing(values)]
        text = "[" + ", ".join(items) + "]"
        if len(text) <= 32:
            put(indent, key, text, comment)
            return
        lines.append("%s# %s" % ("  " * indent, comment))
        current = "%s%s: [" % ("  " * indent, key)
        pad = " " * len(current)
        for i, item in enumerate(items):
            piece = item + ("," if i < len(items) - 1 else "]")
            if len(current) + len(piece) > 92 and current.strip():
                lines.append(current.rstrip())
                current = pad
            current += piece + " "
        lines.append(current.rstrip())

    def put_block(indent, key, entries, keys, comment):
        entries = [e for e in listing(entries) if isinstance(e, dict)]
        if not entries:
            put(indent, key, "[]", comment)
            return
        lines.append("%s# %s" % ("  " * indent, comment))
        put(indent, key)
        lines.extend("%s  - %s" % ("  " * indent, flow_map(e, keys)) for e in entries)

    credits, abilities, stats = section(data, "credits"), section(data, "abilities"), section(data, "base_stats")
    items, learnset, design = section(data, "held_items"), section(data, "learnset"), section(data, "design")
    assets, engine = section(data, "assets"), section(data, "engine")
    sid = slugify(data.get("name") or "name")

    lines.append("# Sigma Dex species file. What every field means: docs/FIELDS.md")
    put(0, "dex", scalar(data.get("dex")))
    put(0, "name", scalar(data.get("name")))
    lines.append("")
    put(0, "credits")
    put(1, "designer", scalar(credits.get("designer")), "who came up with it (Discord name)")
    put(1, "artist", scalar(credits.get("artist")), "who drew the concept art")
    lines.append("")
    put_list(0, "types", data.get("types"), "1 or 2 types, e.g. [Grass, Steel]")
    lines += ["", "# --- Pokedex page ---"]
    put(0, "category", scalar(data.get("category")), 'e.g. Seed  (shown in game as "Seed Pokemon"), max 12 characters')
    description = data.get("description")
    if isinstance(description, str) and "\n" in description.strip():
        put(0, "description", "|", "the Pokedex entry text: max 4 lines of about 40 characters")
        lines.extend("  " + row.strip() for row in description.strip().split("\n"))
    else:
        put(0, "description", scalar(description), "the Pokedex entry text: max 4 lines of about 40 characters")
    put(0, "height_m", scalar(data.get("height_m")), "e.g. 0.7")
    put(0, "weight_kg", scalar(data.get("weight_kg")), "e.g. 6.9")
    put(0, "body_color", scalar(data.get("body_color")), "red blue yellow green black brown purple gray white pink")
    lines += ["", "# --- Battle data ---"]
    put(0, "abilities")
    put(1, "primary", scalar(abilities.get("primary")))
    put(1, "secondary", scalar(abilities.get("secondary")), "optional")
    put(1, "hidden", scalar(abilities.get("hidden")), "optional")
    lines.append("")
    put(0, "base_stats", "", "each 1-255")
    for stat in STATS:
        put(1, stat, scalar(stats.get(stat)))
    lines.append("")
    ev = data.get("ev_yield")
    ev = {k: v for k, v in ev.items() if v} if isinstance(ev, dict) else {}
    put(0, "ev_yield", flow_map(ev, STATS) if ev else "", "EVs given when defeated, 1-3 points total, e.g. {speed: 1}")
    put(0, "catch_rate", scalar(data.get("catch_rate")), "3 (legendary) to 255 (very easy)")
    put(0, "base_exp", scalar(data.get("base_exp")), "exp yield when defeated, e.g. 64")
    put(0, "growth_rate", scalar(data.get("growth_rate")), "erratic fast medium_fast medium_slow slow fluctuating")
    put(0, "base_friendship", scalar(data.get("base_friendship")), "70 is the standard value")
    lines += ["", "# --- Breeding ---"]
    put(0, "gender", scalar(data.get("gender")), "percent male: 0, 12.5, 25, 50, 75, 87.5, 100 - or genderless")
    put_list(0, "egg_groups", data.get("egg_groups"), "1 or 2, e.g. [field, grass]")
    put(0, "egg_cycles", scalar(data.get("egg_cycles")), "hatch time, 20 is typical")
    lines.append("")
    put(0, "held_items", "", "items wild ones can hold (optional)")
    put(1, "common", scalar(items.get("common")))
    put(1, "rare", scalar(items.get("rare")))
    lines += ["", "# --- Evolution: what THIS Pokemon evolves INTO ---"]
    evolutions = [e for e in listing(data.get("evolutions")) if isinstance(e, dict)]
    if evolutions:
        put(0, "evolutions")
        for evo in evolutions:
            keys = [k for k in ("into", "method", "level", "item", "note") if evo.get(k) is not None]
            keys += [k for k in evo if k not in keys and evo[k] is not None]
            for i, key in enumerate(keys):
                lines.append("  %s %s: %s" % ("-" if i == 0 else " ", key, scalar(evo[key])))
    else:
        lines += [
            "evolutions: []",
            "# evolutions:",
            "#   - into: leafsteel    # file name of the target, without .yaml",
            "#     method: level      # level | item | trade | friendship | ... full list in docs/FIELDS.md",
            "#     level: 16          # for method: level",
            "#     item:              # for method: item, e.g. Thunder Stone",
            "#     note:              # anything else worth knowing",
        ]
    lines += ["", "# --- Moves ---"]
    put(0, "learnset")
    put_block(1, "level_up", learnset.get("level_up"), ("level", "move"), "e.g. [{level: 1, move: Tackle}, {level: 7, move: Vine Whip}]")
    put_list(1, "tm_hm", learnset.get("tm_hm"), "e.g. [Cut, Solar Beam] - only the game's TMs and HMs")
    put_list(1, "tutor", learnset.get("tutor"), "moves a move tutor can teach it")
    put_list(1, "egg", learnset.get("egg"), "only needed for the first stage of an evolution line")
    lines += ["", "# --- Where it is found ---"]
    put_block(0, "encounters", data.get("encounters"), ("location", "method", "levels", "rate"),
              "e.g. [{location: Route 1, method: grass, levels: 2-4, rate: 20}]")
    lines += ["", "# --- Design ---"]
    put(0, "design")
    put(1, "concept", scalar(design.get("concept")), "what is it? one or two sentences")
    put(1, "name_origin", scalar(design.get("name_origin")))
    put(1, "notes", scalar(design.get("notes")))
    lines += ["", "# --- Assets (paths inside this repo, leave empty until the file exists) ---"]
    put(0, "assets")
    put(1, "concept_art", scalar(assets.get("concept_art")), "e.g. assets/concept-art/%s.png" % sid)
    put(1, "front_sprite", scalar(assets.get("front_sprite")), "front.png      64x64, 16 colors")
    put(1, "front_anim", scalar(assets.get("front_anim")), "anim_front.png 64x128, two frames stacked")
    put(1, "back_sprite", scalar(assets.get("back_sprite")), "back.png       64x64, same 16 colors as the front")
    put(1, "icon", scalar(assets.get("icon")), "icon.png       32x64, two frames stacked")
    put(1, "footprint", scalar(assets.get("footprint")), "footprint.png  16x16, black and white")
    put(1, "shiny_palette", scalar(assets.get("shiny_palette")), "shiny.pal      the 16 colors of the shiny version")
    put(1, "cry", scalar(assets.get("cry")), "sound file")
    lines += ["", "# --- Game engine details (only matter once sprites exist, see docs/ENGINE.md) ---"]
    put(0, "engine")
    put(1, "no_flip", scalar(bool(engine.get("no_flip"))), "true if the sprite must never be mirrored")
    put(1, "elevation", scalar(engine.get("elevation") or 0), "pixels it floats above the ground in battle")
    put(1, "front_y_offset", scalar(engine.get("front_y_offset")), "pixels the front sprite is moved down")
    put(1, "back_y_offset", scalar(engine.get("back_y_offset")), "pixels the back sprite is moved down")
    put(1, "icon_palette", scalar(engine.get("icon_palette")), "0, 1 or 2 - which shared icon palette fits best")
    put(1, "safari_flee_rate", scalar(engine.get("safari_flee_rate") or 0))
    return "\n".join(lines) + "\n"


def prune(value):
    """Drop everything empty, so two versions of a species can be compared by content."""
    if isinstance(value, dict):
        cleaned = {k: prune(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v not in (None, "", [], {}, False, 0) or (v == 0 and k in ("gender", "level"))}
    if isinstance(value, list):
        return [prune(v) for v in value]
    if isinstance(value, str):
        return "\n".join(row.strip() for row in value.strip().split("\n"))
    return value


def write_species(path, data):
    """Write a species file in canonical form. Refuses if anything would get lost."""
    text = render_species(data)
    if prune(yaml.safe_load(text)) != prune(data):
        raise ValueError("%s has content the file format cannot hold - check for misspelled field names" % path.name)
    path.write_text(text, encoding="utf-8")


def norm(text):
    """Compare names loosely: 'Solar Beam', 'SolarBeam' and 'SOLAR_BEAM' are the same."""
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def constant(text):
    """'Vine Whip' -> 'VINE_WHIP', the way the game's C constants are written."""
    return re.sub(r"[^A-Z0-9]+", "_", str(text).upper()).strip("_")


def load_engine():
    """Names the unmodified game knows, plus this project's custom moves and abilities."""
    with open(ENGINE_PATH, encoding="utf-8") as handle:
        engine = yaml.safe_load(handle)
    custom = {}
    for kind in ("moves", "abilities"):
        with open(ROOT / "data" / ("custom_%s.yaml" % kind), encoding="utf-8") as handle:
            entries = (yaml.safe_load(handle) or {}).get(kind) or []
        custom[kind] = [e for e in entries if isinstance(e, dict) and e.get("name")]
    return {
        "moves": {norm(m) for m in engine["moves"]} | {norm(e["name"]) for e in custom["moves"]},
        "abilities": {norm(a) for a in engine["abilities"]} | {norm(e["name"]) for e in custom["abilities"]},
        "tm_hm": {norm(m) for m in engine["tms"] + engine["hms"]},
        "tm_hm_order": engine["tms"] + engine["hms"],
        "constants": {norm(name): const for kind in ("moves", "abilities") for name, const in engine[kind].items()},
        "names": {
            "moves": sorted(list(engine["moves"]) + [e["name"] for e in custom["moves"]]),
            "abilities": sorted(list(engine["abilities"]) + [e["name"] for e in custom["abilities"]]),
        },
        "custom": custom,
    }


EVO_WORDS = {
    "level_attack_higher": "Attack > Defense", "level_attack_equal": "Attack = Defense",
    "level_defense_higher": "Attack < Defense",
}


def evolution_to_text(evo):
    """How an evolution is written in the spreadsheet: 'Lv 16', 'Thunder Stone', 'Trade', ..."""
    method = evo.get("method")
    if method == "level":
        return "Lv %s" % evo.get("level")
    if method in EVO_WORDS:
        return "Lv %s (%s)" % (evo.get("level"), EVO_WORDS[method])
    if method == "item":
        return str(evo.get("item"))
    if method == "trade":
        return "Trade"
    if method == "trade_item":
        return "Trade holding %s" % evo.get("item")
    if method == "friendship":
        return "Friendship"
    if method in ("friendship_day", "friendship_night"):
        return "Friendship (%s)" % method.split("_")[1]
    if method == "beauty":
        return "Beauty %s" % evo.get("level")
    return "Other: %s" % (evo.get("note") or "")


def text_to_evolution(text):
    """The reverse of evolution_to_text. Anything unrecognised is taken as an item name."""
    text = str(text).strip()
    low = text.lower()
    match = re.match(r"^(?:lv\.?|lvl\.?|level)?\s*(\d+)\s*(?:\((.*)\))?$", low)
    if match:
        extra = (match.group(2) or "").replace(" ", "")
        for method, words in EVO_WORDS.items():
            if extra == words.lower().replace(" ", ""):
                return {"method": method, "level": int(match.group(1))}
        return {"method": "level", "level": int(match.group(1))}
    if low == "trade":
        return {"method": "trade"}
    if low.startswith("trade holding "):
        return {"method": "trade_item", "item": text[len("trade holding "):].strip()}
    if low.startswith("friendship"):
        for time in ("day", "night"):
            if time in low:
                return {"method": "friendship_" + time}
        return {"method": "friendship"}
    match = re.match(r"^beauty\s*(\d+)$", low)
    if match:
        return {"method": "beauty", "level": int(match.group(1))}
    if low.startswith("other"):
        return {"method": "other", "note": text[5:].lstrip(": ").strip() or "not described yet"}
    return {"method": "item", "item": text}


# Every field a species file may contain. Anything else is a typo.
FIELDS = {
    "dex": None, "name": None, "types": None, "category": None, "description": None, "height_m": None,
    "weight_kg": None, "body_color": None, "ev_yield": None, "catch_rate": None, "base_exp": None,
    "growth_rate": None, "base_friendship": None, "gender": None, "egg_groups": None, "egg_cycles": None,
    "evolutions": None, "encounters": None,
    "credits": ("designer", "artist"),
    "abilities": ("primary", "secondary", "hidden"),
    "base_stats": tuple(STATS),
    "held_items": ("common", "rare"),
    "learnset": ("level_up", "tm_hm", "tutor", "egg"),
    "design": ("concept", "name_origin", "notes"),
    "assets": ("concept_art", "front_sprite", "front_anim", "back_sprite", "icon", "footprint", "shiny_palette", "cry"),
    "engine": ("no_flip", "elevation", "front_y_offset", "back_y_offset", "icon_palette", "safari_flee_rate"),
}


def unknown_fields(data):
    found = []
    for key, value in data.items():
        if key not in FIELDS:
            found.append(key)
        elif FIELDS[key] and isinstance(value, dict):
            found.extend("%s.%s" % (key, sub) for sub in value if sub not in FIELDS[key])
    return found


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_species():
    """Return ([(id, path, data)], [(path, message)]) sorted by dex number."""
    species, problems = [], []
    for path in sorted(SPECIES_DIR.glob("*.yaml")):
        try:
            with open(path, encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            problems.append((path, "not valid YAML: %s" % str(exc).replace("\n", " ")))
            continue
        if not isinstance(data, dict):
            problems.append((path, "file is empty or not a mapping"))
            continue
        species.append((path.stem, path, data))
    species.sort(key=lambda item: (item[2].get("dex") if isinstance(item[2].get("dex"), int) else 10**6, item[0]))
    return species, problems


def section(data, key):
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def listing(value):
    return value if isinstance(value, list) else []


def bst(data):
    stats = section(data, "base_stats")
    values = [stats.get(stat) for stat in STATS]
    if all(isinstance(v, int) for v in values):
        return sum(values)
    return None


def filled(value):
    return value is not None and value != "" and value != [] and value != {}


# (section, label, path) - everything a species needs before it can go into the game.
# The website uses the same list, so keep it as plain data.
CHECK_LIST = [
    ("Identity", "types", "types"),
    ("Identity", "designer credit", "credits.designer"),
    ("Dex page", "category", "category"),
    ("Dex page", "description", "description"),
    ("Dex page", "height", "height_m"),
    ("Dex page", "weight", "weight_kg"),
    ("Dex page", "body color", "body_color"),
    ("Stats", "base stats", "base_stats.*"),
    ("Stats", "ability", "abilities.primary"),
    ("Stats", "EV yield", "ev_yield"),
    ("Stats", "catch rate", "catch_rate"),
    ("Stats", "base exp", "base_exp"),
    ("Stats", "growth rate", "growth_rate"),
    ("Stats", "base friendship", "base_friendship"),
    ("Breeding", "gender", "gender"),
    ("Breeding", "egg groups", "egg_groups"),
    ("Breeding", "egg cycles", "egg_cycles"),
    ("Moves", "level-up moves", "learnset.level_up"),
    ("Moves", "TM/HM moves", "learnset.tm_hm"),
    ("Location", "encounters", "encounters"),
    ("Design", "concept", "design.concept"),
    ("Art", "concept art", "assets.concept_art"),
    ("Art", "front sprite", "assets.front_sprite"),
    ("Art", "front animation frame", "assets.front_anim"),
    ("Art", "back sprite", "assets.back_sprite"),
    ("Art", "icon", "assets.icon"),
    ("Art", "footprint", "assets.footprint"),
    ("Art", "shiny palette", "assets.shiny_palette"),
    ("Art", "cry", "assets.cry"),
]


def has(data, path):
    if path == "base_stats.*":
        return bst(data) is not None
    value = data
    for key in path.split("."):
        value = value.get(key) if isinstance(value, dict) else None
    return filled(value)


CHECKS = [(_section, _label, (lambda d, _path=_path: has(d, _path))) for _section, _label, _path in CHECK_LIST]
SECTIONS = []
for _section, _label, _test in CHECKS:
    if _section not in SECTIONS:
        SECTIONS.append(_section)


def missing(data):
    """List of (section, label) still missing for this species."""
    return [(sec, label) for sec, label, test in CHECKS if not test(data)]


def completeness(data):
    return round(100 * (len(CHECKS) - len(missing(data))) / len(CHECKS))
