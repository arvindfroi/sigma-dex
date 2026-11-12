#!/usr/bin/env python3
"""Fill in the numbers nobody wants to think about, the way Game Freak would: body color, EV yield, catch rate,
base exp, growth rate, base friendship, gender, egg groups and egg cycles.

    python scripts/species_fill.py propose            # -> proposals/species_fill.json (what it would fill, and why)
    python scripts/species_fill.py show leafaxer      # one species
    python scripts/species_fill.py apply --all        # fill the EMPTY fields in the species files
    python scripts/species_fill.py suggest            # -> site/species_suggestions.json for the website's button

Only empty fields are ever filled; a value a person wrote is never changed. Species without base stats wait.
Where it is found (encounters) is not filled: that depends on the game's maps and the story plan.

How it decides (docs/SPECIES_FILL.md): each species is compared with every official Pokemon (the same weighted
"inspired by" list as the moveset tool: stats, types, stage, line length, evolution levels, look words, designer
wishes ...). Each value is the weighted choice of those Pokemon, plus Game Freak's fixed habits:
- EV yield: 1 point for a first stage, 2 for a middle stage, 2-3 for a final or single one (as its models), 3 for a
  legendary; on its highest stat (split when two stats are close).
- Catch rate and egg cycles snap to the values the games use; starters 45 / 20, legendaries 3 / 120.
- Base exp scales with the base stat total like its models (exp per stat point).
- Growth rate, gender, egg groups and egg cycles are the same for the whole line (as in the games); starters are
  Medium Slow and 87.5 % male, legendaries Slow and Undiscovered, pseudo-legendary lines Slow.
- Body color comes from the colour words in its look text (the colour of its body), else from its models.
The official numbers come from PokeAPI's public data (fetched when it runs; nothing of it is stored in the repo).
"""
import argparse
import csv
import datetime
import io
import json
import re
import statistics
import sys
import urllib.request
from collections import Counter, defaultdict

import yaml

import dexlib
import moveset_data
import moveset_fill as mf
from dexlib import ROOT, STATS

OUT = ROOT / "proposals" / "species_fill.json"
SUGGEST = ROOT / "site" / "species_suggestions.json"
POKEAPI = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/%s.csv"
FIELDS = ["body_color", "ev_yield", "catch_rate", "base_exp", "growth_rate", "base_friendship", "gender",
          "egg_groups", "egg_cycles"]
LABELS = {"body_color": "body color", "ev_yield": "EV yield", "catch_rate": "catch rate", "base_exp": "base exp",
          "growth_rate": "growth rate", "base_friendship": "base friendship", "gender": "gender",
          "egg_groups": "egg groups", "egg_cycles": "egg cycles"}
CATCH_VALUES = [3, 25, 30, 45, 60, 75, 90, 100, 120, 127, 140, 150, 170, 180, 190, 200, 225, 235, 255]
CYCLE_VALUES = [5, 10, 15, 20, 25, 30, 35, 40, 80, 120]
EGG_MAP = {"monster": "monster", "water1": "water_1", "bug": "bug", "flying": "flying", "ground": "field",
           "fairy": "fairy", "plant": "grass", "humanshape": "human_like", "water3": "water_3", "mineral": "mineral",
           "indeterminate": "amorphous", "water2": "water_2", "ditto": "ditto", "dragon": "dragon",
           "no-eggs": "undiscovered"}
GROWTH_MAP = {"slow": "slow", "medium": "medium_fast", "fast": "fast", "medium-slow": "medium_slow",
              "slow-then-very-fast": "erratic", "fast-then-very-slow": "fluctuating"}
GENDER_MAP = {-1: "genderless", 0: 100, 1: 87.5, 2: 75, 4: 50, 6: 25, 8: 0}
COLOR_WORDS = [
    ("brown", r"tan|brown|beige|bronze|chestnut|wooden|wood|copper|khaki|caramel|chocolate|rust"),
    ("red", r"red|crimson|scarlet|maroon|orange|vermilion|ruby"),
    ("yellow", r"yellow|gold|golden|blond|amber|lemon"),
    ("green", r"green|lime|olive|mossy|emerald|leafy"),
    ("blue", r"blue|cyan|navy|teal|turquoise|azure|aqua"),
    ("purple", r"purple|violet|lilac|lavender|plum|indigo|mauve"),
    ("pink", r"pink|magenta|rose|salmon|peach"),
    ("gray", r"gr[ae]y|silver|steel|metal|metallic|ashen|slate|stone-colou?red"),
    ("white", r"white|cream|ivory|pale|snowy|bone-white"),
    ("black", r"black|dark|ebony|charcoal|shadowy|jet"),
]
EGG_HINTS = [   # words in the look/concept/body/archetype -> the egg group Game Freak gives such a creature
    ("monster", r"turtle|tortoise|dinosaur|reptile|lizard|kaiju|monster|crocodile|alligator"),
    ("field", r"cow|bull|dog|cat|fox|wolf|rodent|mouse|rat|coati|raccoon|bear|deer|moose|horse|pig|boar|sheep|goat|"
              r"rabbit|monkey|ape|gorilla|sloth|lion|tiger|mammal|weasel|otter|hound|walrus|hippo|elephant"),
    ("flying", r"bird|gull|owl|crow|raven|eagle|hawk|parrot|pelican|feathered|wings? of a bird|bat\b"),
    ("bug", r"bug|insect|spider|beetle|moth|butterfly|mosquito|scorpion|centipede|ant\b|bee\b|wasp|mantis"),
    ("water_1", r"frog|toad|tadpole|octopus|squid|seal|whale|jellyfish|sea creature|amphibian|newt|penguin"),
    ("water_2", r"fish|eel|shark|piranha|carp"),
    ("water_3", r"crab|shrimp|lobster|clam|pearl|coral|shell creature|starfish"),
    ("dragon", r"dragon|serpent|wyrm|wyvern"),
    ("human_like", r"humanoid|human-like|ninja|knight|boxer|wrestler|monk|wizard|witch|pirate|gangster|"
                   r"upright body on two legs with arms"),
    ("amorphous", r"ghost|blob|slime|smoke|gas|cloud|spirit|candle|flame body|shadow"),
    ("grass", r"plant|flower|mushroom|tree|sapling|leafy|bulb plant|seed|sprout|vine|cactus"),
    ("mineral", r"rock|stone|boulder|golem|robot|machine|metal|crystal|statue|tower|barrel|tank\b|armou?r"),
    ("fairy", r"fairy|cute|sprite|pixie|angel"),
]
TYPE_COLOR = {"Fire": "red", "Water": "blue", "Grass": "green", "Electric": "yellow", "Ice": "blue",
              "Fighting": "brown", "Poison": "purple", "Ground": "brown", "Flying": "white", "Psychic": "pink",
              "Bug": "green", "Rock": "brown", "Ghost": "purple", "Dragon": "blue", "Dark": "black",
              "Steel": "gray", "Fairy": "pink", "Normal": "brown"}


def _csv(name):
    path = moveset_data.CACHE / ("pokeapi_%s.csv" % name)
    if not path.exists():
        moveset_data.CACHE.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(POKEAPI % name, headers={"User-Agent": "sigma-dex"})
        with urllib.request.urlopen(req, timeout=120) as response:
            path.write_bytes(response.read())
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def official_facts():
    """{national dex number: catch rate, friendship, egg cycles, gender, growth, color, egg groups, base exp, EVs}"""
    colors = {r["id"]: r["identifier"] for r in _csv("pokemon_colors")}
    growth = {r["id"]: GROWTH_MAP.get(r["identifier"]) for r in _csv("growth_rates")}
    groups = {r["id"]: EGG_MAP.get(r["identifier"]) for r in _csv("egg_groups")}
    out = {}
    for r in _csv("pokemon_species"):
        n = int(r["id"])
        out[n] = {"catch_rate": int(r["capture_rate"] or 0), "base_friendship": int(r["base_happiness"] or 0)
                  if r["base_happiness"] != "" else None, "egg_cycles": int(r["hatch_counter"] or 0),
                  "gender": GENDER_MAP.get(int(r["gender_rate"])), "growth_rate": growth.get(r["growth_rate_id"]),
                  "body_color": colors.get(r["color_id"]), "baby": r["is_baby"] == "1",
                  "legendary": r["is_legendary"] == "1" or r["is_mythical"] == "1", "egg_groups": [], "ev": {}}
    for r in _csv("pokemon_egg_groups"):
        n = int(r["species_id"])
        if n in out and groups.get(r["egg_group_id"]):
            out[n]["egg_groups"].append(groups[r["egg_group_id"]])
    default = {}
    for r in _csv("pokemon"):
        if r["is_default"] == "1":
            default[r["id"]] = int(r["species_id"])
            if int(r["species_id"]) in out and r["base_experience"]:
                out[int(r["species_id"])]["base_exp"] = int(r["base_experience"])
    for r in _csv("pokemon_stats"):
        n = default.get(r["pokemon_id"])
        if n in out and int(r["effort"]):
            out[n]["ev"][STATS[int(r["stat_id"]) - 1]] = int(r["effort"])
    return out


def snap(value, allowed):
    return min(allowed, key=lambda a: (abs(a - value), -a))


def wmedian(pairs):
    pairs = sorted((v, w) for v, w in pairs if v is not None)
    if not pairs:
        return None
    half, acc = sum(w for v, w in pairs) / 2, 0.0
    for v, w in pairs:
        acc += w
        if acc >= half:
            return v
    return pairs[-1][0]


def wmode(pairs):
    c = Counter()
    for v, w in pairs:
        if v is not None:
            c[json.dumps(v) if isinstance(v, list) else v] += w
    if not c:
        return None, 0.0
    v, w = c.most_common(1)[0]
    total = sum(c.values())
    return (json.loads(v) if isinstance(v, str) and v.startswith("[") else v), w / total


class Filler:
    def __init__(self):
        self.ref = mf.Reference(moveset_data.load())
        self.ours = mf.load_ours()
        self.lines = mf.build_lines(self.ours)
        self.prop = mf.Proposer(self.ours, self.lines, self.ref)
        self.facts = official_facts()

    def donors(self, sid):
        out = []
        for w, name in self.prop.weighted_donors(sid):
            f = self.facts.get(self.ref.all[name]["num"])
            if f:
                out.append((w, name, f))
        return out

    def members(self, sid):
        root = self.ours[sid]["root"]
        return [x for x in dict.fromkeys(x for p in self.lines.get(root, [[sid]]) for x in p)]

    def line_donors(self, sid):
        """Weighted donors of the whole line (first stage counts most): for what a line shares."""
        pairs = []
        for x in self.members(sid):
            if not self.ours[x]["stats"] or not self.ours[x]["types"]:
                continue
            k = 1.0 if self.ours[x]["stage"] == 0 else 0.7
            pairs += [(w * k, n, f) for w, n, f in self.donors(x)]
        return pairs

    def flags(self, sid):
        sp = self.ours[sid]
        text = " ".join(self.ours[x]["text"].lower() for x in self.members(sid))
        stats = self.prop.profile(sid)["stats"]
        bst = sum(stats.values())
        finals = [x for x in self.members(sid) if self.ours[x]["final"] and self.ours[x]["stats"]]
        top = max((sum(self.ours[x]["stats"].values()) for x in finals), default=bst)
        legendary = self.prop.legendary(dict(sp, stats=stats))
        line_legendary = legendary or any(self.ours[x]["stats"] and self.prop.legendary(
            dict(self.ours[x], stats=self.prop.profile(x)["stats"])) for x in self.members(sid))
        return {"starter": "starter" in text, "legendary": legendary, "line_legendary": line_legendary, "bst": bst,
                "pseudo": not line_legendary and sp["line_length"] >= 3 and top >= 590}

    # ------------------------------------------------------------------ fields
    def ev_yield(self, sid, fl):
        sp = self.ours[sid]
        st = self.prop.profile(sid)["stats"]
        if fl["legendary"]:
            total, why = 3, "legendaries give 3"
        elif sp["stage"] == 0 and not sp["final"]:
            total, why = 1, "a first stage gives 1"
        elif not sp["final"]:
            total, why = 2, "a middle stage gives 2"
        else:
            same = [(sum(f["ev"].values()), w) for w, n, f in self.donors(sid) if self.ref.all[n]["final"]]
            total = int(min(3, max(2 if sp["line_length"] >= 2 else 1, wmedian(same) or 2)))
            if sp["line_length"] >= 3:
                total = 3
            why = "a final stage gives %d like its models" % total
        order = sorted(STATS, key=lambda k: -st[k])
        a, b = order[0], order[1]
        if total == 1:
            ev = {a: 1}
        elif total == 2:
            ev = {a: 1, b: 1} if st[a] - st[b] <= 3 else {a: 2}
        else:
            ev = {a: 2, b: 1} if st[a] - st[b] <= 8 else {a: 3}
        return ev, why + ", on its highest stat%s" % ("s" if len(ev) > 1 else "")

    def catch_rate(self, sid, fl):
        sp = self.ours[sid]
        if fl["legendary"]:
            return 3, "legendary"
        if fl["line_legendary"]:
            return 45, "an earlier stage of a legendary line (like Cosmog or Poipole)"
        if fl["starter"]:
            return 45, "starters are 45"
        if fl["pseudo"]:
            return 45, "a strong three-stage line (like Dratini or Larvitar)"
        v = wmedian([(f["catch_rate"], w) for w, n, f in self.donors(sid) if not f["legendary"]])
        return snap(v or 45, CATCH_VALUES), "like its models (%s)" % self.top_names(sid)

    def base_exp(self, sid, fl):
        bst = fl["bst"]
        ratio = wmedian([(f.get("base_exp", 0) / max(1, self.ref.all[n]["bst"]), w) for w, n, f in self.donors(sid)
                         if f.get("base_exp")])
        v = round(bst * (ratio or 0.35))
        return v, "%d exp per 100 stat points like its models, for a total of %d" % (round((ratio or 0.35) * 100), bst)

    def growth_rate(self, sid, fl):
        if fl["line_legendary"] or fl["pseudo"]:
            return "slow", "legendaries and strong three-stage lines grow Slow"
        if fl["starter"]:
            return "medium_slow", "starters grow Medium Slow"
        v, share = wmode([(f["growth_rate"], w) for w, n, f in self.line_donors(sid)])
        return v or "medium_fast", "the whole line, like its models (%d %%)" % round(share * 100)

    def base_friendship(self, sid, fl):
        v, share = wmode([(70 if f["base_friendship"] == 50 else f["base_friendship"], w)
                          for w, n, f in self.donors(sid)
                          if f["base_friendship"] is not None and f["legendary"] == fl["legendary"]])
        if v is None:
            v = 0 if fl["legendary"] else 70
        return int(v), ("the usual 70" if v == 70 else "like its models (%d %%)" % round(share * 100))

    def gender(self, sid, fl):
        text = " ".join(self.ours[x]["text"].lower() for x in self.members(sid))
        if re.search(r"\b(only|all|always) (female|girls?|women)\b|female[- ]only", text):
            return 0, "the design says it is always female"
        if re.search(r"\b(only|all|always) (male|boys?|men)\b|male[- ]only", text):
            return 100, "the design says it is always male"
        if fl["starter"]:
            return 87.5, "starters are 87.5 % male"
        if fl["line_legendary"]:
            v, share = wmode([(f["gender"], w) for w, n, f in self.line_donors(sid) if f["legendary"]])
            return v if v is not None else "genderless", "a legendary line, like legendaries"
        v, share = wmode([(f["gender"], w) for w, n, f in self.line_donors(sid)])
        if v is None:
            v = 50
        return v, "the whole line, like its models (%d %%)" % round(share * 100)

    def egg_groups(self, sid, fl):
        sp = self.ours[sid]
        if fl["line_legendary"]:
            return ["undiscovered"], "legendaries (and their whole line) cannot breed"
        pairs = [(f["egg_groups"], w) for w, n, f in self.line_donors(sid)
                 if f["egg_groups"] and "undiscovered" not in f["egg_groups"]]
        votes = Counter()
        two = 0.0
        total = sum(w for g, w in pairs) or 1
        for groups, w in pairs:
            for g in groups:
                votes[g] += w / len(groups)
            if len(groups) == 2:
                two += w
        text = " ".join(str(self.ours[x]["design"].get(k) or "") for x in self.members(sid)
                        for k in ("look", "concept", "body_shape")).lower() + " " + " ".join(
            str((self.prop.arch(x) or {}).get("archetype") or "") for x in self.members(sid)).lower()
        for group, pattern in EGG_HINTS:
            if re.search(r"\b(%s)" % pattern, text):
                votes[group] += 0.35 * total            # what it is counts as much as a third of its models
        if not votes:
            return ["field"], "default"
        (g1, w1), *rest = votes.most_common()
        out = [g1]
        if rest and two / total >= 0.4 and rest[0][1] >= 0.45 * w1:
            out.append(rest[0][0])
        return out, "the whole line, like its models (%s)" % ", ".join(
            "%s %d %%" % (g, round(votes[g] / sum(votes.values()) * 100)) for g in out)

    def egg_cycles(self, sid, fl):
        if fl["line_legendary"]:
            return 120, "legendaries take 120"
        if fl["starter"]:
            return 20, "starters take 20"
        if fl["pseudo"]:
            return 40, "strong three-stage lines take 40"
        v = wmedian([(f["egg_cycles"], w) for w, n, f in self.line_donors(sid) if not f["legendary"]])
        return snap(v or 20, CYCLE_VALUES), "the whole line, like its models"

    BODY_WORDS = r"\b(body|skin|fur|feathers?|scales?|shell|coat|hide|plumage|torso|bark|carapace|hood|cloak|robe|mantle)\b"
    PART_WORDS = (r"\b(eyes?|ears?|snout|nose|spots?|tips?|claws?|hooves|mouth|cheeks?|pupils?|tuft|belt|helmet|"
                  r"marks?|markings|stripes?|tongue|teeth|fangs?|beak|feet|hands|lips?|bulb|lamp|cape|sash|bow|"
                  r"collar|crest|horns?|mask|gem|jewel|button|outline|ring)\b")

    def body_color(self, sid, fl):
        """Game Freak's body colour is the colour of most of its body: colours that describe the body count most,
        colours of small parts (eyes, snout, spots, claws, a helmet) count little."""
        sp = self.ours[sid]
        try:      # Claude looked at the sprites where text and picture disagreed (proposals/body_color_visual.json)
            visual = json.loads((ROOT / "proposals" / "body_color_visual.json").read_text(encoding="utf-8"))
        except Exception:
            visual = {}
        if sid in visual:
            return visual[sid], "the colour of most of its body in its sprite"
        look = str(sp["design"].get("look") or "")
        def first_color(text):
            found = []
            for color, pattern in COLOR_WORDS:
                for m in re.finditer(r"\b(%s)(ish)?\b" % pattern, text):
                    if m.group(1) in ("dark", "pale") and re.match(r"[\s-]*(%s)" % "|".join(
                            p for c, p in COLOR_WORDS if c != "black"), text[m.end():]):
                        continue          # "dark red" is red, "pale blue" is blue
                    found.append((m.start(), color))
            return min(found)[1] if found else None
        if look:
            low = look.lower()
            # 1. "It is a small tan turtle ..." / "It is a long, green dragon-like lizard ..." (before "with")
            head = re.split(r"\bwith\b|;|\.", low.split(". ")[0])[0]
            c = first_color(head)
            if c:
                return c, "its body colour in the look text (%s)" % head.strip()[:60]
            # 2. the first colour next to a body word: "deep blue fur", "a white hood", "its body is blue-purple"
            for clause in re.split(r"\bwith\b|,|;|\.", low):
                if re.search(self.BODY_WORDS, clause):
                    c = first_color(clause)
                    if c:
                        return c, "its body colour in the look text (%s)" % clause.strip()[:60]
            score = Counter()
            sentences = re.split(r"(?<=\.)\s", look.lower())
            for si, sentence in enumerate(sentences):
                for ci, clause in enumerate(re.split(r";|\bwith\b|, and\b|\band (?=(?:a|an|its|two|four)\b)",
                                                     sentence)):
                    weight = 1.0
                    if si == 0 and ci == 0:
                        weight = 4.0                      # "It is a small tan turtle" / "... creature with white fur"
                    if re.search(self.BODY_WORDS, clause):
                        weight = max(weight, 3.0)
                    if re.search(self.PART_WORDS, clause) and not re.search(self.BODY_WORDS, clause):
                        weight = 0.3
                    found = []
                    for color, pattern in COLOR_WORDS:
                        for m in re.finditer(r"\b(%s)(ish)?\b" % pattern, clause):
                            found.append((m.start(), color, m))
                    found.sort(key=lambda x: x[0])
                    seen_colors = 0
                    for pos, color, m in found:
                        if True:
                            if m.group(1) == "dark" and re.match(r"[\s-]*(red|green|blue|purple|brown|gr[ae]y|pink|"
                                                                   r"ringed)", clause[m.end():]):
                                continue      # "dark green" is green; "dark-ringed eye" is no colour
                            if m.group(1) == "pale" and re.match(r"\s*\w", clause[m.end():]) and \
                                    re.match(r"\s*(%s)" % "|".join(p for c, p in COLOR_WORDS), clause[m.end():]):
                                continue      # "pale blue" is blue
                            w = weight * (0.65 ** seen_colors)      # the first colour named counts most
                            if re.match(r"[\s-]*(\w+[\s-])?%s" % self.PART_WORDS[2:], clause[m.end():]):
                                w = min(w, 0.3)                    # "black spots", "black-tipped ears"
                            seen_colors += 1
                            score[color] += w
            if score:
                return score.most_common(1)[0][0], "the colour of most of its body in its look text"
        v, share = wmode([(f["body_color"], w) for w, n, f in self.donors(sid)])
        if v:
            return v, "like its models (no look text yet)"
        return TYPE_COLOR.get((sp["types"] or ["Normal"])[0], "brown"), "from its type"

    def top_names(self, sid):
        return ", ".join(n for w, n, f in self.donors(sid)[:3])

    def propose(self, sid):
        sp = self.ours[sid]
        if not sp["types"]:
            return {"skipped": "has no types yet"}
        if not sp["stats"]:
            return {"skipped": "waits for its base stats"}
        fl = self.flags(sid)
        out = {}
        for field in FIELDS:
            value, why = getattr(self, field)(sid, fl)
            out[field] = {"value": value, "why": why}
        out["_inspired"] = [(n, round(w * 100)) for w, n, f in self.donors(sid)[:6]]
        return out


def is_empty(data, field):
    v = data.get(field)
    if field == "ev_yield":
        return not (isinstance(v, dict) and any(v.values()))
    if field == "egg_groups":
        return not v
    return v is None or v == ""


def cmd_propose(args):
    mf.use_data_dir(args.data)
    f = Filler()
    res = {sid: f.propose(sid) for sid in sorted(f.ours)}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"generated": datetime.date.today().isoformat(), "species": res}, ensure_ascii=False,
                              indent=1) + "\n", encoding="utf-8")
    empty = sum(1 for sid, r in res.items() if "skipped" not in r for fld in FIELDS
                if is_empty(f.ours[sid]["data"], fld))
    print("%d species, %d empty fields would be filled -> %s" % (len(res), empty, OUT.relative_to(ROOT)))


def cmd_show(args):
    res = json.loads(OUT.read_text(encoding="utf-8"))["species"]
    for sid in args.species:
        print(sid, json.dumps(res.get(sid), ensure_ascii=False, indent=1))


def cmd_apply(args):
    mf.use_data_dir(args.data)
    res = json.loads(OUT.read_text(encoding="utf-8"))["species"]
    targets = list(res) if args.all else [s.strip() for s in (args.only or "").split(",") if s.strip()]
    if not targets:
        raise SystemExit("Say which: --only a,b or --all")
    changed = []
    for sid in targets:
        r = res.get(sid) or {}
        if "skipped" in r or not r:
            continue
        path = dexlib.SPECIES_DIR / (sid + ".yaml")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        filled = []
        for field in FIELDS:
            if field in r and is_empty(data, field):
                data[field] = r[field]["value"]
                filled.append(LABELS[field])
        if filled:
            design = data.setdefault("design", {})
            fb = list(design.get("filled_by_claude") or [])
            design["filled_by_claude"] = fb + [x for x in filled if x not in fb]
            dexlib.write_species(path, data)
            changed.append(sid)
    print("filled empty fields in %d species: %s" % (len(changed), ", ".join(changed)))


def cmd_suggest(args):
    mf.use_data_dir(args.data)
    f = Filler()
    species = {}
    for sid in sorted(f.ours):
        r = f.propose(sid)
        species[sid] = r if "skipped" in r else {k: [v["value"], v["why"]] for k, v in r.items() if k in FIELDS}
    old = None
    if SUGGEST.exists():
        try:
            old = json.loads(SUGGEST.read_text(encoding="utf-8"))
        except Exception:
            old = None
    if old and old.get("species") == json.loads(json.dumps(species, ensure_ascii=False)):
        print("species suggestions unchanged")
        return
    SUGGEST.write_text(json.dumps({"generated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                                   "species": species}, ensure_ascii=False, separators=(",", ":")) + "\n",
                       encoding="utf-8")
    print("species suggestions for %d species -> %s" % (len(species), SUGGEST.relative_to(ROOT)))


def main():
    import os
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(sys.executable, [sys.executable] + sys.argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, func in (("propose", cmd_propose), ("suggest", cmd_suggest)):
        p = sub.add_parser(name)
        p.add_argument("--data")
        p.set_defaults(func=func)
    p = sub.add_parser("show")
    p.add_argument("species", nargs="+")
    p.set_defaults(func=cmd_show)
    p = sub.add_parser("apply")
    p.add_argument("--only")
    p.add_argument("--all", action="store_true")
    p.add_argument("--data")
    p.set_defaults(func=cmd_apply)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
