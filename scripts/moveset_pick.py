#!/usr/bin/env python3
"""Pick the 4 best moves for one Pokemon at one level, and say what its battle role is.

Reusable on purpose: scripts/moveset_fill.py uses it for each line's example set, and the story team
builder can use it per battle (a trainer's Pokemon at level 23 picks from the moves it knows by then).

    python scripts/moveset_pick.py leafaxer 50                 # level-up moves up to level 50
    python scripts/moveset_pick.py leafaxer 100 --all          # also TM, tutor and egg moves
    python scripts/moveset_pick.py leafaxer 40 --pool "Leaf Blade,Swords Dance,Iron Head,Earthquake,Rest"
    python scripts/moveset_pick.py leafaxer 50 --json          # machine-readable

From Python:
    import moveset_pick
    moveset_pick.pick(mon, level, pool)  ->  {"moves": [...], "role": ..., "why": {...}}
where mon = {"types": [...], "stats": {hp, attack, defense, sp_attack, sp_defense, speed}, "abilities": [...]}
and pool = move names (the moves it can know).

How it scores (the idea of Pokemon Showdown's random-battle sets, written small): every attacking move gets a
damage value (power x accuracy x same-type bonus x the right attacking stat x hits x what the ability adds,
minus for recharge, charging, self-KO, big stat drops); the 4 moves are chosen one by one, each time taking the
move that adds most: an attack adds the damage it brings against the 18 types beyond what the set already hits
(so a second Grass move adds little, Earthquake next to Leaf Blade adds a lot); a status move adds a share of the
set's best attack depending on the role (a setup move is worth a lot for a sweeper, recovery for a wall).
At most one setup move, one recovery move, one move that inflicts a status, one hazard; at least two attacks
(three for attackers).
"""
import argparse
import json
import sys

import moveset_data
from moveset_data import TYPES, effectiveness

STAT_KEYS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]

# Ability -> (test, multiplier) for attacks. test gets (move_name, move_data).
_SLICING = {"slicing"}
ABILITY_BOOSTS = {
    "Huge Power": (lambda n, m: m["category"] == "Physical", 2.0),
    "Pure Power": (lambda n, m: m["category"] == "Physical", 2.0),
    "Technician": (lambda n, m: 0 < m["power"] <= 60, 1.5),
    "Sharpness": (lambda n, m: "slicing" in m["flags"], 1.5),
    "Iron Fist": (lambda n, m: "punch" in m["flags"], 1.2),
    "Strong Jaw": (lambda n, m: "bite" in m["flags"], 1.5),
    "Tough Claws": (lambda n, m: "contact" in m["flags"], 1.3),
    "Mega Launcher": (lambda n, m: "pulse" in m["flags"], 1.5),
    "Punk Rock": (lambda n, m: "sound" in m["flags"], 1.3),
    "Reckless": (lambda n, m: m["recoil"], 1.2),
    "Sheer Force": (lambda n, m: m["secondary"], 1.3),
    "Gorilla Tactics": (lambda n, m: m["category"] == "Physical", 1.3),
    "Hustle": (lambda n, m: m["category"] == "Physical", 1.25),
    "Guts": (lambda n, m: m["category"] == "Physical", 1.1),
    "Steelworker": (lambda n, m: m["type"] == "Steel", 1.5),
    "Transistor": (lambda n, m: m["type"] == "Electric", 1.3),
    "Dragon's Maw": (lambda n, m: m["type"] == "Dragon", 1.5),
    "Rocky Payload": (lambda n, m: m["type"] == "Rock", 1.5),
    "Water Bubble": (lambda n, m: m["type"] == "Water", 2.0),
    "Solar Power": (lambda n, m: m["category"] == "Special", 1.2),
    "Analytic": (lambda n, m: True, 1.1),
    "Tinted Lens": (lambda n, m: True, 1.1),
    "Skill Link": (lambda n, m: bool(m["multihit"]), 1.0),   # handled in hits
    "Drought": (lambda n, m: m["type"] == "Fire", 1.5),
    "Drizzle": (lambda n, m: m["type"] == "Water", 1.5),
    "Primordial Sea": (lambda n, m: m["type"] == "Water", 1.5),
    "Sand Force": (lambda n, m: m["type"] in ("Rock", "Ground", "Steel"), 1.3),
    "Leaf Mane": (lambda n, m: m["category"] == "Physical", 1.25),
    "Cold-hearted": (lambda n, m: m["category"] == "Physical", 1.2),
    "Drunken Rage": (lambda n, m: m["category"] == "Physical", 1.4),
}
SETUP_CHEAP = {"Growl", "Leer", "Tail Whip", "Sand Attack", "Smokescreen", "Kinesis", "Flash", "String Shot",
               "Double Team", "Minimize", "Harden", "Withdraw", "Defense Curl", "Focus Energy", "Sharpen",
               "Meditate", "Howl", "Work Up", "Growth", "Charge", "Stockpile", "Odor Sleuth", "Foresight",
               "Lock-On", "Mind Reader", "Laser Focus", "Baby-Doll Eyes", "Confide", "Screech", "Metal Sound",
               "Fake Tears", "Scary Face", "Cotton Spore", "Feather Dance", "Captivate", "Charm", "Tickle",
               "Play Nice", "Noble Roar", "Swagger", "Flatter", "Attract", "Teeter Dance", "Supersonic",
               "Sweet Scent", "Camouflage", "Conversion", "Conversion 2", "Mimic", "Splash", "Celebrate",
               "Hold Hands", "Happy Hour", "Helping Hand", "Snatch", "Embargo", "Recycle", "Natural Gift",
               "Psych Up", "Secret Power", "Captivate", "Lucky Chant", "Magnet Rise", "Telekinesis", "Gravity",
               "Bide", "Endure", "Follow Me", "Rage Powder", "Ally Switch", "Safeguard", "Mist", "Rototiller",
               "Flower Shield", "Magnetic Flux", "Gear Up", "Aromatic Mist", "Tearful Look", "Venom Drench"}
# Moves that are only good with a partner move (score near zero alone).
NEEDS = {"Dream Eater": {"Spore", "Sleep Powder", "Hypnosis", "Yawn", "Sing", "Lovely Kiss", "Grass Whistle",
                         "Dark Void"},
         "Nightmare": {"Spore", "Sleep Powder", "Hypnosis", "Sing", "Lovely Kiss", "Grass Whistle"},
         "Sleep Talk": {"Rest"}, "Snore": {"Rest"}, "Stored Power": set(), "Last Resort": set(),
         "Focus Punch": {"Substitute"}, "Spit Up": {"Stockpile"}, "Swallow": {"Stockpile"}}
VARIABLE_POWER = {"Low Kick": 70, "Grass Knot": 70, "Heavy Slam": 70, "Heat Crash": 70, "Gyro Ball": 60,
                  "Electro Ball": 60, "Seismic Toss": 75, "Night Shade": 75, "Super Fang": 55, "Endeavor": 40,
                  "Psywave": 50, "Return": 102, "Frustration": 102, "Flail": 50, "Reversal": 50, "Punishment": 60,
                  "Crush Grip": 80, "Wring Out": 80, "Hidden Power": 60, "Natural Gift": 60, "Present": 40,
                  "Magnitude": 70, "Beat Up": 40, "Trump Card": 50, "Fling": 40, "Spit Up": 60, "Stored Power": 40,
                  "Final Gambit": 60, "Counter": 50, "Mirror Coat": 50, "Metal Burst": 50, "Bide": 30,
                  "Sonic Boom": 25, "Dragon Rage": 45, "Nature Power": 80, "Weather Ball": 75,
                  "Ruination": 70, "Super Fang ": 55}
RECOVERY = {"Recover", "Roost", "Soft-Boiled", "Slack Off", "Milk Drink", "Synthesis", "Moonlight", "Morning Sun",
            "Shore Up", "Heal Order", "Strength Sap", "Wish", "Lunar Blessing", "Life Dew", "Jungle Healing"}
HAZARDS = {"Stealth Rock", "Spikes", "Toxic Spikes", "Sticky Web"}
STATUS_INFLICT = {"Toxic", "Will-O-Wisp", "Thunder Wave", "Spore", "Sleep Powder", "Hypnosis", "Yawn", "Glare",
                  "Stun Spore", "Poison Powder", "Sing", "Lovely Kiss", "Grass Whistle", "Dark Void", "Nuzzle",
                  "Toxic Thread", "Poison Gas"}
PIVOT_STATUS = {"Parting Shot", "Teleport", "Baton Pass", "Shed Tail", "Chilly Reception"}
UTILITY = {"Taunt": .4, "Encore": .45, "Haze": .3, "Roar": .3, "Whirlwind": .3, "Heal Bell": .35, "Aromatherapy": .35,
           "Leech Seed": .5, "Pain Split": .45, "Destiny Bond": .35, "Trick": .3, "Switcheroo": .3, "Defog": .35,
           "Rapid Spin": .3, "Protect": .35, "Detect": .35, "Substitute": .35, "King's Shield": .5, "Spiky Shield": .45,
           "Baneful Bunker": .45, "Light Screen": .35, "Reflect": .35, "Aurora Veil": .45, "Trick Room": .3,
           "Tailwind": .35, "Memento": .25, "Healing Wish": .3, "Lunar Dance": .3, "Clear Smog": .3,
           "Knock Off": .2, "Fake Out": .25, "Curse": .0, "Belly Drum": .0, "Court Change": .2, "Disable": .2,
           "Magic Coat": .15, "Imprison": .1, "Torment": .1, "Skill Swap": .15, "Wide Guard": .1, "Quick Guard": .1,
           "Psych Up": .05, "Rest": .0, "Sleep Talk": .0}


def _num(value):
    return value if isinstance(value, (int, float)) else 0


def mon_from_species(data):
    """Profile from a species file's dict (types, stats, abilities)."""
    stats = data.get("base_stats") or {}
    ab = data.get("abilities") or {}
    return {"name": data.get("name"), "types": [t for t in (data.get("types") or []) if t],
            "stats": {k: _num(stats.get(k)) or 70 for k in STAT_KEYS},
            "abilities": [a for a in (ab.get("primary"), ab.get("secondary"), ab.get("hidden")) if a]}


# --------------------------------------------------------------------------------------------- role

ROLE_WORDS = [
    ("trick room", "Trick Room attacker"), ("mixed", "Mixed attacker"), ("tank", "Bulky attacker"),
    ("wall", "Wall"), ("bulky", "Bulky attacker"), ("support", "Support"), ("pivot", "Pivot"),
    ("sweeper", "Fast attacker"), ("frail", "Fast attacker"), ("fast", "Fast attacker"), ("weak", "Fast support"),
]


def detect_role(mon, wishes=""):
    """A short role name and the numbers behind it. Words in the designers' notes win."""
    s = mon["stats"]
    bst = sum(s.values()) or 1
    avg = bst / 6
    off_phys, off_spec = s["attack"], s["sp_attack"]
    if set(mon.get("abilities") or []) & {"Huge Power", "Pure Power"}:
        off_phys *= 2
    off = max(off_phys, off_spec)
    bulk = (s["hp"] * (s["defense"] + s["sp_defense"]) / 2) / (avg * avg)
    fast = s["speed"] >= 95 or (s["speed"] >= 80 and s["speed"] >= 1.25 * avg)
    slow = s["speed"] <= 45 or s["speed"] <= 0.6 * avg
    if abs(off_phys - off_spec) <= 15 and min(off_phys, off_spec) >= max(80, 1.05 * avg):
        side = "mixed"
    else:
        side = "physical" if off_phys > off_spec else "special"
    high_off = off >= max(90, 1.12 * avg)
    text = (wishes or "").lower()
    role = None
    for word, name in ROLE_WORDS:
        if word in text:
            role = name
            break
    if role is None:
        if slow and high_off and bulk < 1.25:
            role = "Trick Room attacker"
        elif high_off and fast:
            role = "Fast attacker"
        elif high_off and bulk >= 1.1:
            role = "Bulky attacker"
        elif high_off:
            role = "Wallbreaker"
        elif bulk >= 1.25:
            role = "Wall"
        elif fast:
            role = "Fast support"
        else:
            role = "Support"
    if role == "Wall":
        role = "Physical wall" if s["defense"] >= s["sp_defense"] + 15 else (
            "Special wall" if s["sp_defense"] >= s["defense"] + 15 else "Mixed wall")
    if role in ("Fast attacker", "Bulky attacker", "Wallbreaker", "Trick Room attacker"):
        role = "%s %s" % ("Mixed" if side == "mixed" else side.capitalize(), role[0].lower() + role[1:])
    return {"role": role, "side": side, "fast": fast, "slow": slow, "bulk": round(bulk, 2), "high_off": high_off}


def _role_kind(role):
    r = role.lower()
    if "wallbreaker" in r:
        return "attacker"
    if "wall" in r:
        return "wall"
    if "support" in r or "pivot" in r:
        return "support"
    if "trick room" in r:
        return "tr"
    if "bulky" in r:
        return "bulky"
    return "attacker"


# --------------------------------------------------------------------------------------------- scoring

def attack_value(mon, name, M):
    m = M.get(name)
    if not m or m["category"] == "Status":
        return 0.0
    power = VARIABLE_POWER.get(name, m["power"]) if (m["variable_power"] or name in VARIABLE_POWER) else m["power"]
    if power <= 1:
        return 0.0
    s, ab = mon["stats"], set(mon["abilities"])
    acc = 1.0 if m["accuracy"] > 100 else m["accuracy"] / 100
    if "No Guard" in ab:
        acc = 1.0
    mtype = m["type"]
    if "Toxic Voice" in ab and "sound" in m["flags"]:
        mtype = "Poison"
    stab = 1.0
    if mtype in mon["types"] or ("Toxic Voice" in ab and "sound" in m["flags"]):
        stab = 2.0 if "Adaptability" in ab else 1.5
    hits = 1.0
    if m["multihit"]:
        mh = m["multihit"]
        hits = mh if isinstance(mh, (int, float)) else (5.0 if "Skill Link" in ab else 3.1 if mh[1] == 5 else mh[0])
    if name == "Body Press":
        stat = s["defense"]
    elif name == "Foul Play":
        stat = 85
    else:
        stat = s["attack"] if m["category"] == "Physical" else s["sp_attack"]
    mult = 1.0
    for a in ab:
        rule = ABILITY_BOOSTS.get(a)
        if rule and rule[0](name, m):
            mult = max(mult, rule[1]) if a not in ("Analytic", "Tinted Lens") else mult * rule[1]
    pen = 1.0
    if m["recharge"]:
        pen *= .5
    if m["charge"] and not (name in ("Solar Beam", "Solar Blade") and ab & {"Drought", "Chlorophyll"}):
        pen *= .5
    if m["self_ko"]:
        pen *= .25
    if m["ohko"]:
        pen *= .3
    if m["recoil"]:
        pen *= .92 if "Rock Head" not in ab else 1.0
    sb = m.get("self_boosts") or {}
    drop = -sum(v for v in sb.values() if v < 0)
    if drop:
        pen *= 1.25 if "Contrary" in ab else (.72 if drop >= 2 and set(sb) & {"atk", "spa"} else .92)
    if name in ("Focus Punch", "Future Sight", "Doom Desire"):
        pen *= .55
    if name in NEEDS and not NEEDS[name]:
        pen *= .3
    if name in ("Fake Out", "First Impression"):
        pen *= .4
    if name in ("Explosion", "Self-Destruct", "Misty Explosion", "Memento", "Final Gambit"):
        pen *= .6
    if name in ("Belch", "Last Resort", "Synchronoise", "Steel Roller", "Burn Up", "Dream Eater"):
        pen *= .5
    if name in ("Hidden Power", "Natural Gift", "Secret Power", "Frustration"):
        pen *= .7
    return power * acc * stab * hits * mult * pen * stat / 100.0


def _coverage(values_by_type):
    return sum(values_by_type) / len(values_by_type)


def _eff(mtype, t):
    e = effectiveness(mtype, [t])
    return 2.0 if e > 2 else e


DOUBLES_UTILITY = {"Fake Out": .45, "Protect": .55, "Detect": .55, "Helping Hand": .4, "Follow Me": .5,
                   "Rage Powder": .5, "Wide Guard": .35, "Quick Guard": .25, "Tailwind": .5, "Trick Room": .45,
                   "Icy Wind": .3, "Snarl": .3, "Electroweb": .3, "Ally Switch": .3}


def pick(mon, level=100, pool=(), M=None, role=None, wishes="", n=4, battle="single"):
    """battle="double": moves that hit both foes count more, moves that also hit the partner a bit less,
    and doubles support (Fake Out, Protect, Follow Me, Tailwind ...) counts more."""
    """The n best moves out of pool for this mon. Returns {"moves": [...], "role": ..., "why": {...}}."""
    if M is None:
        M = moveset_data.load()["moves"]
    info = detect_role(mon, wishes) if role is None else {"role": role}
    kind = _role_kind(info["role"])
    pool = [p for p in dict.fromkeys(pool) if p in M]
    if not pool:
        return {"moves": [], "role": info["role"], "why": {}}
    vals = {p: attack_value(mon, p, M) for p in pool}
    if battle == "double":
        for p in pool:
            t = M[p].get("target")
            if vals[p] and t == "allAdjacentFoes":
                vals[p] *= 1.35          # 0.75 damage to each of two foes
            elif vals[p] and t == "allAdjacent":
                vals[p] *= 1.1           # also hits the partner
    for p, partners in NEEDS.items():          # Dream Eater without a sleep move etc. is close to useless
        if p in vals and partners and not partners & set(pool):
            vals[p] *= .1
    best_attack = max(vals.values()) or 1.0
    A = best_attack
    s = mon["stats"]
    ab = set(mon["abilities"])
    side_cat = "Physical" if s["attack"] * (2 if ab & {"Huge Power", "Pure Power"} else 1) >= s["sp_attack"] \
        else "Special"
    has_cat = {c: any(vals[p] > 0 and M[p]["category"] == c for p in pool) for c in ("Physical", "Special")}

    def status_value(p, chosen):
        m = M[p]
        if p in NEEDS and NEEDS[p] and not NEEDS[p] & set(chosen):
            return 0.02 * A
        boosts = m.get("boosts") or {}
        if boosts and m["target"] in ("self", "adjacentAllyOrSelf", "allies") and p not in SETUP_CHEAP:
            pos = {k: v for k, v in boosts.items() if v > 0}
            if not pos:
                return .05 * A
            useful = 0.0
            chosen_cats = {M[c]["category"] for c in chosen if vals[c] > 0}

            def fit(cat, stat_ok):
                if cat in chosen_cats:
                    return 1.0
                return (.5 if stat_ok else .1) if not chosen_cats or cat == side_cat else .1
            if "atk" in pos and has_cat["Physical"]:
                useful += pos["atk"] * fit("Physical", side_cat == "Physical" or s["attack"] >= 0.9 * s["sp_attack"])
            if "spa" in pos and has_cat["Special"]:
                useful += pos["spa"] * fit("Special", side_cat == "Special" or s["sp_attack"] >= 0.9 * s["attack"])
            if "spe" in pos and kind != "tr":
                useful += pos["spe"] * (.6 if s["speed"] < 100 else .3)
            if "def" in pos or "spd" in pos:
                useful += .35 * (pos.get("def", 0) + pos.get("spd", 0)) * (1.6 if kind in ("wall", "bulky") else .7)
                if "Body Press" in pool and "def" in pos:
                    useful += pos["def"] * .5
            mult = {"attacker": .55, "bulky": .45, "tr": .4, "wall": .3, "support": .2}[kind]
            if p == "Belly Drum":
                useful = 2.2 if side_cat == "Physical" else 0
            if p == "Curse" and "Ghost" in mon["types"]:
                useful = .3
            return min(useful * mult, 1.1) * A
        if p in RECOVERY or (m["heal"] and p != "Rest"):
            return A * {"wall": .85, "support": .7, "bulky": .6, "tr": .35, "attacker": .3}[kind]
        if p == "Rest":
            sleepy = "Sleep Talk" in pool or "Snore" in pool
            base = {"wall": .45, "bulky": .35, "support": .3}.get(kind, .12)
            if ab & {"Sloth Combat", "Early Bird", "Shed Skin", "Natural Cure", "Comatose"}:
                base += .25
            return A * min(base + (.12 if sleepy else 0), .8)
        if p in ("Sleep Talk", "Snore"):
            return A * (.5 if "Rest" in chosen else .02)
        if p in HAZARDS:
            return A * ({"support": .75, "wall": .65, "bulky": .5}.get(kind, .3) * (1.0 if p != "Toxic Spikes" else .7))
        if p in STATUS_INFLICT:
            acc = 1.0 if m["accuracy"] > 100 else m["accuracy"] / 100
            base = {"wall": .6, "support": .65, "bulky": .45, "tr": .4}.get(kind, .25)
            if p in ("Spore", "Sleep Powder", "Hypnosis", "Sing", "Lovely Kiss", "Grass Whistle", "Dark Void"):
                base += .15
            if p == "Yawn":
                base -= .1
            return A * base * acc
        if p in PIVOT_STATUS:
            return A * (.55 if kind in ("support", "wall") else .3)
        if p == "Trick Room":
            return A * (.5 if kind == "tr" else .12)
        if battle == "double" and p in DOUBLES_UTILITY:
            return A * DOUBLES_UTILITY[p]
        if p in UTILITY:
            u = UTILITY[p]
            if p in ("Protect", "Detect") and ab & {"Speed Boost", "Poison Heal", "Moody"}:
                u = .7
            if kind in ("wall", "support"):
                u *= 1.3
            elif kind in ("attacker", "tr"):
                u *= .6
            return A * u
        if p in SETUP_CHEAP:
            return A * (.12 if level < 20 else .05)
        return A * .08

    chosen, flags = [], {"setup": 0, "recovery": 0, "status": 0, "hazard": 0}
    min_attacks = {"attacker": 3, "tr": 3, "bulky": 2, "wall": 2, "support": 1}[kind]
    why = {}
    cur = [0.0] * len(TYPES)
    for slot in range(min(n, len(pool))):
        n_att = sum(1 for c in chosen if vals[c] > 0)
        slots_left = n - len(chosen)
        need_attack = (min_attacks - n_att) >= slots_left
        best, best_gain, best_note = None, -1.0, ""
        for p in pool:
            if p in chosen:
                continue
            m = M[p]
            if vals[p] > 0:
                mtype = "Poison" if ("Toxic Voice" in ab and "sound" in m["flags"]) else m["type"]
                new = [max(c, vals[p] * _eff(mtype, t)) for c, t in zip(cur, TYPES)]
                gain = _coverage(new) - _coverage(cur)
                if n_att:
                    gain *= 2.5       # covering what the set cannot hit well matters more than its average
                util = (DOUBLES_UTILITY.get(p, 0) if battle == "double" else UTILITY.get(p, 0)) * A * .6
                if m["priority"] > 0 and p not in ("Fake Out", "First Impression"):
                    util += .2 * vals[p] + (.1 * A if s["speed"] < 90 else 0)
                    if any(M[c]["priority"] > 0 and vals[c] > 0 for c in chosen):
                        util *= .2
                if m["switch"]:
                    util += (.3 if kind in ("support", "wall") else .15) * A
                if m["drain"] and kind in ("wall", "bulky", "support"):
                    util += .1 * vals[p]
                if any(M[c]["type"] == m["type"] and M[c]["category"] == m["category"] for c in chosen):
                    util *= .3
                gain += util
                if mtype in mon["types"] and not any(vals[c] > 0 and M[c]["type"] == mtype for c in chosen):
                    gain += .3 * vals[p] * (1 if m["priority"] <= 0 else .3)   # one strong move of each own type
                if p in NEEDS and NEEDS[p] and not NEEDS[p] & set(chosen):
                    gain *= .15
                note = "attack"
            else:
                if need_attack:
                    continue
                cls = ("setup" if (m.get("boosts") and m["target"] in ("self", "adjacentAllyOrSelf", "allies")
                                   and p not in SETUP_CHEAP and any(v > 0 for v in m["boosts"].values()))
                       else "recovery" if (p in RECOVERY or m["heal"] or p == "Rest")
                       else "status" if p in STATUS_INFLICT else "hazard" if p in HAZARDS else None)
                if cls and flags[cls]:
                    continue
                if cls == "setup" and n_att == 0 and slots_left <= 2:
                    continue
                gain = status_value(p, chosen)
                note = cls or "utility"
            if gain > best_gain:
                best, best_gain, best_note = p, gain, note
        if best is None:
            break
        chosen.append(best)
        why[best] = best_note
        if best_note in flags:
            flags[best_note] += 1
        if vals[best] > 0:
            mtype = "Poison" if ("Toxic Voice" in ab and "sound" in M[best]["flags"]) else M[best]["type"]
            cur = [max(c, vals[best] * _eff(mtype, t)) for c, t in zip(cur, TYPES)]
    return {"moves": chosen, "role": info["role"], "why": why,
            "coverage": round(_coverage(cur), 1)}


def learnable(data, level, include=("level_up",)):
    ls = data.get("learnset") or {}
    pool = []
    if "level_up" in include:
        pool += [e["move"] for e in (ls.get("level_up") or []) if isinstance(e, dict)
                 and isinstance(e.get("level"), int) and e["level"] <= level]
    for key in ("tm_hm", "tutor", "egg"):
        if key in include:
            pool += list(ls.get(key) or [])
    return pool


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("species", help="species file name, e.g. leafaxer")
    ap.add_argument("level", type=int)
    ap.add_argument("--all", action="store_true", help="also TM/HM, tutor and egg moves")
    ap.add_argument("--pool", help="comma-separated move list instead of the species' own moves")
    ap.add_argument("--proposal", action="store_true", help="use the moveset proposal instead of the file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--doubles", action="store_true", help="pick for a double battle")
    args = ap.parse_args()
    import yaml
    from dexlib import SPECIES_DIR
    path = SPECIES_DIR / (args.species + ".yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if args.proposal:
        from dexlib import ROOT
        prop = json.loads((ROOT / "proposals" / "movesets.json").read_text(encoding="utf-8"))["species"][args.species]
        data = dict(data, learnset=prop["learnset"])
    mon = mon_from_species(data)
    if args.pool:
        pool = [p.strip() for p in args.pool.split(",") if p.strip()]
    else:
        pool = learnable(data, args.level, ("level_up", "tm_hm", "tutor", "egg") if args.all else ("level_up",))
    result = pick(mon, args.level, pool, wishes=(data.get("design") or {}).get("wishes") or "",
                  battle="double" if args.doubles else "single")
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print("%s at level %d (%s): %s" % (data.get("name"), args.level, result["role"], ", ".join(result["moves"])))


if __name__ == "__main__":
    sys.exit(main())
