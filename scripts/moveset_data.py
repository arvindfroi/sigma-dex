"""Game facts for the moveset tools: Origin HeartGold's moves, TMs, tutors and the official Pokemon's learnsets.

Used by scripts/moveset_pick.py (pick 4 moves for a level) and scripts/moveset_fill.py (propose whole learnsets).

Where the facts come from (nothing of this is stored in the repo):
- Origin HeartGold's player docs in ~/sigma-origin/docs (generated from the game's own data by the English
  patch team: species, learnsets, move table, TM list, tutors). Another folder can be given with the
  environment variable SIGMA_ORIGIN_DOCS.
- Pokemon Showdown's moves.json (MIT licence, https://github.com/smogon/pokemon-showdown) for what a move
  does (boosts, healing, priority, flags such as punch/sound/slicing). Origin's own type/power/accuracy win.

The parsed result is cached in .cache/movesets/ (gitignored) and rebuilt when a source file changes.
"""
import json
import os
import re
import urllib.request
from pathlib import Path

from dexlib import ROOT, norm

DOCS = Path(os.environ.get("SIGMA_ORIGIN_DOCS", Path.home() / "sigma-origin" / "docs"))
CACHE = ROOT / ".cache" / "movesets"
SHOWDOWN_URL = "https://play.pokemonshowdown.com/data/moves.json"
CACHE_VERSION = 4

TYPES = ["Normal", "Fire", "Water", "Grass", "Electric", "Ice", "Fighting", "Poison", "Ground", "Flying",
         "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"]

# Type chart (generation 6 and later, as in Origin): attacking type -> {defending type: multiplier}, 1 left out.
_CHART = {
    "Normal": {"Rock": .5, "Ghost": 0, "Steel": .5},
    "Fire": {"Fire": .5, "Water": .5, "Grass": 2, "Ice": 2, "Bug": 2, "Rock": .5, "Dragon": .5, "Steel": 2},
    "Water": {"Fire": 2, "Water": .5, "Grass": .5, "Ground": 2, "Rock": 2, "Dragon": .5},
    "Grass": {"Fire": .5, "Water": 2, "Grass": .5, "Poison": .5, "Ground": 2, "Flying": .5, "Bug": .5, "Rock": 2,
              "Dragon": .5, "Steel": .5},
    "Electric": {"Water": 2, "Grass": .5, "Electric": .5, "Ground": 0, "Flying": 2, "Dragon": .5},
    "Ice": {"Fire": .5, "Water": .5, "Grass": 2, "Ice": .5, "Ground": 2, "Flying": 2, "Dragon": 2, "Steel": .5},
    "Fighting": {"Normal": 2, "Ice": 2, "Poison": .5, "Flying": .5, "Psychic": .5, "Bug": .5, "Rock": 2, "Ghost": 0,
                 "Dark": 2, "Steel": 2, "Fairy": .5},
    "Poison": {"Grass": 2, "Poison": .5, "Ground": .5, "Rock": .5, "Ghost": .5, "Steel": 0, "Fairy": 2},
    "Ground": {"Fire": 2, "Grass": .5, "Electric": 2, "Poison": 2, "Flying": 0, "Bug": .5, "Rock": 2, "Steel": 2},
    "Flying": {"Grass": 2, "Electric": .5, "Fighting": 2, "Bug": 2, "Rock": .5, "Steel": .5},
    "Psychic": {"Fighting": 2, "Poison": 2, "Psychic": .5, "Dark": 0, "Steel": .5},
    "Bug": {"Fire": .5, "Grass": 2, "Fighting": .5, "Poison": .5, "Flying": .5, "Psychic": 2, "Ghost": .5, "Dark": 2,
            "Steel": .5, "Fairy": .5},
    "Rock": {"Fire": 2, "Ice": 2, "Fighting": .5, "Ground": .5, "Flying": 2, "Bug": 2, "Steel": .5},
    "Ghost": {"Normal": 0, "Psychic": 2, "Ghost": 2, "Dark": .5},
    "Dragon": {"Dragon": 2, "Steel": .5, "Fairy": 0},
    "Dark": {"Fighting": .5, "Psychic": 2, "Ghost": 2, "Dark": .5, "Fairy": .5},
    "Steel": {"Fire": .5, "Water": .5, "Electric": .5, "Ice": 2, "Rock": 2, "Steel": .5, "Fairy": 2},
    "Fairy": {"Fire": .5, "Fighting": 2, "Poison": .5, "Dragon": 2, "Dark": 2, "Steel": .5},
}


def effectiveness(attack_type, defend_types):
    value = 1.0
    for t in defend_types:
        value *= _CHART.get(attack_type, {}).get(t, 1.0)
    return value


# --------------------------------------------------------------------------------------------- parsing

def _subsequence(short, long):
    it = iter(long)
    return all(ch in it for ch in short)


def _num(text):
    text = text.strip()
    return int(text) if text.isdigit() else None


def _parse_moves(showdown):
    """Origin's move table (moves.md), with full names and Showdown's effect data matched to each move."""
    text = (DOCS / "moves.md").read_text(encoding="utf-8")
    sd_by_norm = {}
    for key, entry in showdown.items():
        if entry.get("isZ") or entry.get("isMax") or (entry.get("num") or 0) <= 0:
            continue
        sd_by_norm[norm(entry["name"])] = entry
    moves, abbr_to_name, unmatched = {}, {}, []
    tm_section = text.split("## TM and HM list")
    for line in tm_section[0].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8 or not cells[0].isdigit():
            continue
        mid, abbr, mtype, cat, power, acc, pp, tm = cells[:8]
        if abbr.startswith("move #"):
            continue
        key = norm(abbr)
        entry = sd_by_norm.get(key)
        if entry is None:
            cands = [e for k, e in sd_by_norm.items() if k[:1] == key[:1] and _subsequence(key, k)]
            cands.sort(key=lambda e: (e["type"] != mtype, abs(e["num"] - int(mid)), len(e["name"])))
            entry = cands[0] if cands else None
        if entry is None:
            unmatched.append(abbr)
            name = abbr
            entry = {}
        else:
            name = entry["name"]
        if name in moves:            # two rows matched the same move: keep the first
            continue
        moves[name] = {
            "id": int(mid), "abbr": abbr, "type": mtype, "category": cat,
            "power": _num(power) or (1 if power == "var." else 0), "variable_power": power == "var.",
            "accuracy": _num(acc) or (101 if acc == "—" else 100), "pp": _num(pp) or 0,
            "tm": tm or None,
            "priority": entry.get("priority", 0),
            "flags": sorted(k for k, v in (entry.get("flags") or {}).items() if v),
            "boosts": entry.get("boosts") if entry.get("target") in ("self", "adjacentAllyOrSelf", "allies") else None,
            "foe_boosts": entry.get("boosts") if entry.get("target") not in ("self", "adjacentAllyOrSelf", "allies") else None,
            "self_boosts": (entry.get("self") or {}).get("boosts"),
            "heal": bool(entry.get("heal")) or entry.get("id") in ("rest", "roost", "synthesis", "moonlight",
                                                                   "morningsun", "shoreup", "strengthsap"),
            "drain": bool(entry.get("drain")),
            "recoil": bool(entry.get("recoil") or entry.get("mindBlownRecoil") or entry.get("hasCrashDamage")),
            "status": entry.get("status"),
            "volatile": entry.get("volatileStatus"),
            "secondary": bool(entry.get("secondary") or entry.get("secondaries")),
            "switch": bool(entry.get("selfSwitch")),
            "side": entry.get("sideCondition"),
            "weather": entry.get("weather"),
            "terrain": entry.get("terrain"),
            "pseudo": entry.get("pseudoWeather"),
            "multihit": entry.get("multihit"),
            "self_ko": bool(entry.get("selfdestruct")),
            "recharge": "recharge" in (entry.get("flags") or {}),
            "charge": "charge" in (entry.get("flags") or {}),
            "ohko": bool(entry.get("ohko")),
            "target": entry.get("target"),
        }
        abbr_to_name[abbr] = name
    tms = []
    if len(tm_section) > 1:
        for line in tm_section[1].splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and re.match(r"^(TM|HM)\d+$", cells[0]):
                tms.append({"tm": cells[0], "move": abbr_to_name.get(cells[1], cells[1])})
    return moves, abbr_to_name, tms, unmatched


_HEAD = re.compile(r"^### #(\d+) (.+)$")


def _split_list(text, abbr_to_name, strip_tm=False):
    out = []
    for part in text.split(","):
        part = part.strip().rstrip(".")
        if not part:
            continue
        if strip_tm:
            part = re.sub(r"^(TM|HM)\d+\s+", "", part)
        out.append(abbr_to_name.get(part, part))
    return out


def _parse_species(abbr_to_name):
    species = {}
    for path in sorted(DOCS.glob("pokemon_*.md")):
        if "1026" in path.name:       # alternate forms (megas, regional forms): not used as models
            continue
        block = None
        section = None
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            m = _HEAD.match(line)
            if m:
                block = {"num": int(m.group(1)), "name": m.group(2).strip(), "level_up": [], "tm_hm": [],
                         "tutor": [], "egg": [], "evolves_from": None, "evolves_into": []}
                species[block["name"]] = block
                section = None
                continue
            if block is None:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else None
            if cells and len(cells) == 10 and cells[3].isdigit():
                block["types"] = [t.strip() for t in cells[0].split("/")]
                block["abilities"] = [a.strip() for a in cells[1].split("/") if a.strip()]
                block["hidden"] = cells[2]
                keys = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
                block["stats"] = {k: int(cells[3 + i]) for i, k in enumerate(keys)}
                continue
            if line.startswith("Catch rate"):
                m2 = re.match(r"Catch rate (\d+)", line)
                block["catch_rate"] = int(m2.group(1)) if m2 else None
                m2 = re.search(r"egg groups ([^·]+)", line)
                block["egg_groups"] = [g.strip() for g in m2.group(1).split("/")] if m2 else []
                block["genderless"] = "genderless" in line
                continue
            if line.startswith("Evolves from:"):
                m2 = re.match(r"Evolves from: (.+?) \((.+)\)", line.strip())
                if m2:
                    lv = re.match(r"Lv (\d+)", m2.group(2))
                    block["evolves_from"] = {"name": m2.group(1).strip(), "level": int(lv.group(1)) if lv else None,
                                             "how": m2.group(2)}
                continue
            if line.startswith("Evolves into:"):
                for part in re.findall(r"([^,(]+?) \(([^)]*)\)", line[len("Evolves into:"):]):
                    lv = re.match(r"Lv (\d+)", part[1])
                    block["evolves_into"].append({"name": part[0].strip(), "level": int(lv.group(1)) if lv else None,
                                                  "how": part[1]})
                continue
            if line.startswith("How to get it:"):
                block["obtainable"] = "no source found" not in line
                continue
            if line.startswith("**Level-up moves**"):
                section = "level_up"
                continue
            if section == "level_up" and cells and len(cells) >= 2 and (cells[0].isdigit() or cells[0] == "Evo"):
                lv = 0 if cells[0] == "Evo" else int(cells[0])
                block["level_up"].append([lv, abbr_to_name.get(cells[1], cells[1])])
                continue
            for label, key, strip in (("**TM/HM:**", "tm_hm", True), ("**Move tutors:**", "tutor", False),
                                      ("**Egg moves:**", "egg", False)):
                if line.startswith(label):
                    block[key] = _split_list(line[len(label):], abbr_to_name, strip)
                    section = None
    return species


def _parse_tutors(abbr_to_name):
    """Where each tutor move is taught, and for what. {move: [{"where":..., "payment":..., "species": n}]}"""
    text = (DOCS / "trades_tutors.md").read_text(encoding="utf-8")
    part = text.split("## Move tutors", 1)[1].split("**Moves set by events", 1)[0]
    tutors = {}
    for line in part.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0] in ("Where", "---"):
            continue
        where, move, mtype, payment, who = cells
        move = re.sub(r"\s*\*\*.*?\*\*", "", move).strip()
        name = abbr_to_name.get(move, move)
        m = re.match(r"(\d+) species", who)
        tutors.setdefault(name, []).append({
            "where": where, "payment": payment if payment not in ("—", "") else "free",
            "species": int(m.group(1)) if m else (len(who.split(",")) if "species:" not in who and ":" not in who else None),
            "restricted": "specific Pokémon only" in who,
        })
    return tutors


def _showdown_moves():
    path = CACHE / "showdown_moves.json"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(SHOWDOWN_URL, headers={"User-Agent": "sigma-dex"})
        with urllib.request.urlopen(req, timeout=60) as response:
            path.write_bytes(response.read())
    return json.loads(path.read_text(encoding="utf-8"))


def _annotate(species):
    """Stage in line, line length and whether the species is a legendary-like one."""
    def root_of(name, seen=()):
        sp = species.get(name)
        if not sp or not sp.get("evolves_from") or name in seen:
            return name
        return root_of(sp["evolves_from"]["name"], seen + (name,))

    def depth(name, seen=()):
        sp = species.get(name)
        if not sp or name in seen:
            return 0
        kids = [e["name"] for e in sp["evolves_into"] if e["name"] in species]
        return 1 + max((depth(k, seen + (name,)) for k in kids), default=0)

    for name, sp in species.items():
        stage, cur = 0, sp
        while cur.get("evolves_from") and cur["evolves_from"]["name"] in species and stage < 3:
            stage += 1
            cur = species[cur["evolves_from"]["name"]]
        root = root_of(name)
        sp["stage"] = stage
        sp["line_length"] = depth(root)
        sp["root"] = root
        sp["final"] = not [e for e in sp["evolves_into"] if e["name"] in species]
        sp["bst"] = sum(sp.get("stats", {}).values()) if sp.get("stats") else 0
        legend = (sp.get("catch_rate") or 255) <= 10 and "Undiscovered" in sp.get("egg_groups", []) and sp["line_length"] <= 1
        sp["legendary"] = bool(legend or (sp["bst"] >= 570 and sp["line_length"] <= 1))
        sp["baby"] = "Undiscovered" in sp.get("egg_groups", []) and not sp["final"]


SHOWDOWN = {"pokedex": "https://play.pokemonshowdown.com/data/pokedex.json",
            "learnsets": "https://play.pokemonshowdown.com/data/learnsets.json"}
STAT_MAP = {"hp": "hp", "atk": "attack", "def": "defense", "spa": "sp_attack", "spd": "sp_defense", "spe": "speed"}


def _fetch_json(name, url):
    path = CACHE / ("showdown_%s.json" % name)
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "sigma-dex"})
        with urllib.request.urlopen(req, timeout=120) as response:
            path.write_bytes(response.read())
    return json.loads(path.read_text(encoding="utf-8"))


def _move_entry(entry, changes):
    flags = entry.get("flags") or {}
    m = {
        "id": entry.get("num"), "abbr": entry["name"], "type": entry["type"], "category": entry["category"],
        "power": entry.get("basePower") or 0, "variable_power": False,
        "accuracy": 101 if entry.get("accuracy") is True else (entry.get("accuracy") or 100), "pp": entry.get("pp") or 0,
        "tm": None, "priority": entry.get("priority", 0), "flags": sorted(k for k, v in flags.items() if v),
        "boosts": entry.get("boosts") if entry.get("target") in ("self", "adjacentAllyOrSelf", "allies") else None,
        "foe_boosts": entry.get("boosts") if entry.get("target") not in ("self", "adjacentAllyOrSelf", "allies") else None,
        "self_boosts": (entry.get("self") or {}).get("boosts"),
        "heal": bool(entry.get("heal")) or entry.get("id") in ("rest", "roost", "synthesis", "moonlight", "morningsun",
                                                               "shoreup", "strengthsap"),
        "drain": bool(entry.get("drain")),
        "recoil": bool(entry.get("recoil") or entry.get("mindBlownRecoil") or entry.get("hasCrashDamage")),
        "status": entry.get("status"), "volatile": entry.get("volatileStatus"),
        "secondary": bool(entry.get("secondary") or entry.get("secondaries")), "switch": bool(entry.get("selfSwitch")),
        "side": entry.get("sideCondition"), "weather": entry.get("weather"), "terrain": entry.get("terrain"),
        "pseudo": entry.get("pseudoWeather"), "multihit": entry.get("multihit"), "self_ko": bool(entry.get("selfdestruct")),
        "recharge": "recharge" in flags, "charge": "charge" in flags, "ohko": bool(entry.get("ohko")),
        "target": entry.get("target"),
    }
    if entry.get("category") != "Status" and not entry.get("basePower"):
        m["variable_power"], m["power"] = True, 1
    for key, value in (changes.get(entry["name"]) or {}).items():      # Origin HeartGold's own numbers
        m[key] = value
    return m


def _load_showdown(origin):
    """The official games' data from Pokemon Showdown (MIT) + Origin's TMs, tutors and changed moves."""
    showdown = _showdown_moves()
    changes = origin.get("move_changes") or {}
    moves = {}
    for key, e in showdown.items():
        if e.get("isZ") or e.get("isMax") or not (0 < (e.get("num") or 0) < 1000) or \
                e.get("isNonstandard") in ("CAP", "LGPE", "Custom"):
            continue
        moves[e["name"]] = _move_entry(e, changes)
    tm_names = [m for m in origin["tms"]] + [m for m in origin["hms"]]
    tms = [{"tm": ("TM%02d" % (i + 1)) if i < len(origin["tms"]) else ("HM%02d" % (i - len(origin["tms"]) + 1)),
            "move": m} for i, m in enumerate(tm_names)]
    for t in tms:
        if t["move"] in moves:
            moves[t["move"]]["tm"] = t["tm"]
    tutors = {}
    for t in origin.get("tutors") or []:
        tutors.setdefault(t["move"], []).append({"where": t["where"], "payment": t["payment"],
                                                 "species": t.get("species"), "restricted": bool(t.get("only_some"))})
    dex = _fetch_json("pokedex", SHOWDOWN["pokedex"])
    learn = _fetch_json("learnsets", SHOWDOWN["learnsets"])
    id_to_name = {k: v["name"] for k, v in showdown.items()}
    species = {}
    for key, e in dex.items():
        if e.get("forme") or e.get("baseSpecies") or not (0 < e.get("num", 0) <= 1025):
            continue
        ls = (learn.get(key) or {}).get("learnset") or {}
        gens = [int(src[0]) for srcs in ls.values() for src in srcs if src[1:2] == "L"]
        latest = str(max(gens)) if gens else None
        level_up, tm, tutor, egg = [], set(), set(), set()
        for mid, srcs in ls.items():
            name = id_to_name.get(mid)
            if not name or name not in moves:
                continue
            for src in srcs:
                if latest and src.startswith(latest + "L"):
                    level_up.append([int(src[2:]), name])
                elif src[1:2] == "M":
                    tm.add(name)
                elif src[1:2] == "T":
                    tutor.add(name)
                elif src[1:2] == "E":
                    egg.add(name)
        level_up.sort()
        ab = e.get("abilities") or {}
        tags = e.get("tags") or []
        evos = []
        for ev in e.get("evos") or []:
            target = dex.get(re.sub(r"[^a-z0-9]", "", ev.lower())) or {}
            evos.append({"name": ev, "level": target.get("evoLevel"), "how": target.get("evoType") or "level"})
        species[e["name"]] = {
            "num": e["num"], "name": e["name"], "types": e["types"],
            "abilities": [ab[k] for k in ("0", "1") if ab.get(k)], "hidden": ab.get("H") or "",
            "stats": {STAT_MAP[k]: v for k, v in e["baseStats"].items()},
            "catch_rate": 3 if any("Legendary" in t or "Mythical" in t for t in tags) else 45,
            "egg_groups": e.get("eggGroups") or [], "genderless": e.get("gender") == "N",
            "evolves_from": {"name": e["prevo"], "level": e.get("evoLevel"), "how": e.get("evoType") or "level"}
            if e.get("prevo") else None,
            "evolves_into": evos, "obtainable": True,
            "level_up": level_up, "tm_hm": sorted(tm), "tutor": sorted(tutor | {m for m in tm if m not in tm_names
                                                                                 and m in tutors}),
            "egg": sorted(egg), "legendary_tag": any("Legendary" in t or "Mythical" in t for t in tags),
        }
    return moves, tms, tutors, species


def load():
    """Everything as one dict: moves, tms, tutors, species. Fast after the first run (cached).

    The official Pokemon's data comes from Pokemon Showdown (works anywhere, also on GitHub); Origin HeartGold's
    TMs, tutors and changed moves from data/engine/origin.yaml. SIGMA_MOVESET_SOURCE=origin reads Origin's own
    player docs instead (only on a machine that has them)."""
    origin_file = ROOT / "data" / "engine" / "origin.yaml"
    if os.environ.get("SIGMA_MOVESET_SOURCE", "showdown") != "origin" and origin_file.exists():
        import yaml
        stamp = [CACHE_VERSION, "showdown", int(origin_file.stat().st_mtime)]
        cache_file = CACHE / "showdown_reference.json"
        if cache_file.exists():
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached.get("stamp") == stamp:
                return cached
        origin = yaml.safe_load(origin_file.read_text(encoding="utf-8"))
        moves, tms, tutors, species = _load_showdown(origin)
        _annotate(species)
        for sp in species.values():
            sp["legendary"] = bool(sp.pop("legendary_tag") or sp["legendary"])
        data = {"stamp": stamp, "moves": moves, "abbr": {}, "tms": tms, "tutors": tutors, "species": species,
                "unmatched": [], "source": "showdown"}
        CACHE.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
    if not (DOCS / "moves.md").exists():
        raise SystemExit("Origin HeartGold docs not found in %s (set SIGMA_ORIGIN_DOCS)" % DOCS)
    sources = [DOCS / "moves.md", DOCS / "trades_tutors.md"] + sorted(DOCS.glob("pokemon_*.md"))
    stamp = [CACHE_VERSION] + [int(p.stat().st_mtime) for p in sources]
    cache_file = CACHE / "origin_reference.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if cached.get("stamp") == stamp:
            return cached
    showdown = _showdown_moves()
    moves, abbr_to_name, tms, unmatched = _parse_moves(showdown)
    species = _parse_species(abbr_to_name)
    _annotate(species)
    tutors = _parse_tutors(abbr_to_name)
    data = {"stamp": stamp, "moves": moves, "abbr": abbr_to_name, "tms": tms, "tutors": tutors,
            "species": species, "unmatched": unmatched}
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


if __name__ == "__main__":
    d = load()
    print("%d moves, %d TMs/HMs, %d tutor moves, %d species" % (len(d["moves"]), len(d["tms"]), len(d["tutors"]),
                                                               len(d["species"])))
    if d["unmatched"]:
        print("Moves without a Showdown match (kept with Origin's short name):", ", ".join(d["unmatched"]))
