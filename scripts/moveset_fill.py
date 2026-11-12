#!/usr/bin/env python3
"""Propose learnsets (level-up, TM/HM, tutor, egg) for every evolution line, based on real Pokemon.

    python scripts/moveset_fill.py propose            # all lines -> proposals/movesets.json + proposals/MOVESETS.md
    python scripts/moveset_fill.py propose leafing    # only the lines of these species (faster to look at)
    python scripts/moveset_fill.py show leafaxer      # print one proposal
    python scripts/moveset_fill.py apply --only leafing,leafsteel   # write them into the species files
    python scripts/moveset_fill.py apply --all        # every proposal

Nothing is written into data/species/ except by `apply`, and `apply` only ADDS moves: what a species file
already has is never removed, moved or changed. Run apply only after the group (Arvind) said yes.

How it decides is written down in docs/MOVESETS.md. In short:
1. Lines come from the `evolutions` fields; species with no written evolution that sit next to each other in
   the dex, share a type and grow in stats are treated as a line too (shown as "guessed").
2. For each line the most similar official line is found in Origin HeartGold (stats shape, types, number of
   stages, evolution levels, words in the look/concept such as "turtle" or "bat", shared abilities).
3. Its level-up list is copied stage by stage at our evolution levels; its moves of a type we do not have are
   swapped for a move of our type at about the same power (same physical/special side as our stats).
4. TM/HM, tutor and egg moves are taken from what the most similar official species of the same stage and the
   official species of our types learn (Origin's own TM list and tutors; tutor places and prices are listed).
5. Moves named in design.wishes / design.notes are added. Existing moves are kept as they are.
6. A role is chosen from the stats and notes; missing role tools (a strong same-type move, a setup move for a
   sweeper, recovery for a wall) are added if similar official Pokemon have them; combos with no official
   precedent at that power (priority + setup on a strong attacker, Shell Smash, Spore ...) are not added.
"""
import argparse
import datetime
import difflib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict

import yaml

import dexlib
import moveset_data
import moveset_pick as mp
from dexlib import ROOT, STATS

OUT_DIR = ROOT / "proposals"
OUT_JSON = OUT_DIR / "movesets.json"
OUT_MD = OUT_DIR / "MOVESETS.md"
DESIGN_REVIEW = OUT_DIR / "design_review.json"   # judgment notes from reading each design (kept across reruns)
KEYS = ("level_up", "tm_hm", "tutor", "egg")
DATA_DIR = ROOT / "data"

# Official species that make bad models (special learnsets or none).
BAD_MODELS = {"Smeargle", "Ditto", "Unown", "Wobbuffet", "Wynaut", "Magikarp", "Shedinja", "Metapod", "Kakuna",
              "Silcoon", "Cascoon", "Spewpa", "Burmy", "Combee", "Tynamo", "Cosmog", "Cosmoem", "Kricketot",
              "Feebas", "Pyukumuku", "Arceus", "Silvally", "Type: Null", "Mew", "Kubfu", "Zygarde", "Rotom",
              "Castform", "Delibird", "Luvdisc", "Bidoof", "Bibarel"}
# Moves never added by this tool (too strong / too special to hand out): they stay if a designer wrote them.
NEVER_ADD = {"Spore", "Dark Void", "Shell Smash", "Geomancy", "Tail Glow", "Belly Drum", "Quiver Dance",
             "Victory Dance", "Clangorous Soul", "No Retreat", "Extreme Speed", "Baton Pass", "Shed Tail",
             "Fillet Away", "Last Respects", "Revival Blessing", "Sketch", "Transform", "Lovely Kiss",
             "Minimize", "Double Team", "Sheer Cold", "Fissure", "Horn Drill", "Guillotine", "Glare",
             "Wicked Blow", "Surging Strikes", "Population Bomb", "Boomburst", "Shift Gear", "Spin Out",
             "Destiny Bond", "Perish Song", "Mean Look", "Block", "Spider Web", "Swagger", "Flatter",
             "Return", "Frustration", "Hidden Power", "Natural Gift", "Secret Power", "Captivate", "Snatch",
             "Embargo", "Recycle", "Psych Up", "Fling", "Attract", "Struggle", "Water Spout", "Eruption",
             "Dragon Energy", "Dream Eater", "Nightmare", "Self-Destruct", "Explosion", "Memento",
             "Final Gambit", "Healing Wish", "Lunar Dance", "Misty Explosion"}
STRONG_SETUP = {"Swords Dance", "Dragon Dance", "Nasty Plot", "Shell Smash", "Quiver Dance", "Belly Drum",
                "Victory Dance", "Tail Glow", "Geomancy", "Shift Gear", "Coil", "Bulk Up", "Calm Mind",
                "Clangorous Soul", "No Retreat", "Tidy Up", "Agility", "Rock Polish", "Autotomize", "Curse",
                "Work Up", "Hone Claws", "Growth", "Iron Defense", "Cosmic Power", "Acid Armor", "Amnesia",
                "Cotton Guard", "Stockpile", "Bulk Up"}
SETUP_ATK = ["Swords Dance", "Dragon Dance", "Bulk Up", "Hone Claws", "Coil", "Howl", "Curse"]
SETUP_SPA = ["Nasty Plot", "Calm Mind", "Work Up", "Growth"]
SETUP_SPE = ["Agility", "Rock Polish", "Autotomize", "Flame Charge"]
STATUS_GROUP = {   # status moves of one type that do the same job, to swap a donor's status move for ours
    "sleep": {"Sleep Powder", "Hypnosis", "Sing", "Grass Whistle", "Yawn", "Spore", "Lovely Kiss"},
    "para": {"Stun Spore", "Thunder Wave", "Glare", "Nuzzle"},
    "poison": {"Poison Powder", "Toxic", "Poison Gas", "Toxic Spikes", "Toxic Thread"},
    "burn": {"Will-O-Wisp"},
    "confuse": {"Confuse Ray", "Supersonic", "Sweet Kiss", "Teeter Dance"},
    "heal": {"Synthesis", "Recover", "Roost", "Moonlight", "Morning Sun", "Slack Off", "Soft-Boiled", "Milk Drink",
             "Shore Up", "Aqua Ring", "Ingrain", "Wish", "Rest", "Heal Order", "Strength Sap"},
    "weather": {"Sunny Day", "Rain Dance", "Sandstorm", "Hail", "Snowscape"},
    "terrain": {"Grassy Terrain", "Electric Terrain", "Psychic Terrain", "Misty Terrain"},
    "hazard": {"Stealth Rock", "Spikes", "Toxic Spikes", "Sticky Web"},
    "drain": {"Leech Seed"},
}
TYPE_WEATHER = {"Fire": "Sunny Day", "Grass": "Sunny Day", "Water": "Rain Dance", "Rock": "Sandstorm",
                "Ground": "Sandstorm", "Ice": "Snowscape"}
TYPE_TERRAIN = {"Grass": "Grassy Terrain", "Electric": "Electric Terrain", "Psychic": "Psychic Terrain",
                "Fairy": "Misty Terrain"}
# Words in a design's look/concept/category/name -> official species it resembles (a nudge, not a must).
KEYWORDS = {
    "bat": ["Zubat", "Golbat", "Crobat", "Woobat", "Swoobat", "Noibat", "Noivern"],
    "turtle": ["Squirtle", "Wartortle", "Blastoise", "Turtwig", "Grotle", "Torterra", "Torkoal", "Tirtouga",
               "Carracosta", "Turtonator", "Shuckle"],
    "tortoise": ["Turtwig", "Grotle", "Torterra", "Torkoal"],
    "cow": ["Miltank", "Tauros"], "bull": ["Tauros", "Bouffalant"], "moose": ["Stantler", "Sawsbuck"],
    "deer": ["Stantler", "Deerling", "Sawsbuck", "Xerneas"],
    "frog": ["Froakie", "Frogadier", "Greninja", "Croagunk", "Toxicroak", "Tympole", "Palpitoad", "Seismitoad",
             "Poliwag", "Poliwhirl", "Politoed"],
    "toad": ["Croagunk", "Toxicroak", "Seismitoad", "Palpitoad"], "tadpole": ["Poliwag", "Tympole"],
    "koala": ["Komala"], "raccoon": ["Zigzagoon", "Linoone"], "coati": ["Zigzagoon", "Linoone", "Sentret", "Furret"],
    "rat": ["Rattata", "Raticate"], "mouse": ["Rattata", "Pikachu", "Dedenne"],
    "monkey": ["Mankey", "Primeape", "Aipom", "Ambipom", "Chimchar", "Monferno", "Infernape", "Pansage", "Passimian"],
    "eel": ["Tynamo", "Eelektrik", "Eelektross"], "snake": ["Ekans", "Arbok", "Seviper", "Serperior", "Silicobra",
                                                             "Sandaconda", "Dunsparce"],
    "spider": ["Spinarak", "Ariados", "Joltik", "Galvantula", "Dewpider", "Araquanid", "Tarountula", "Spidops"],
    "tarantula": ["Spinarak", "Ariados", "Tarountula", "Spidops"],
    "octopus": ["Octillery", "Grapploct", "Clobbopus"], "squid": ["Inkay", "Malamar"],
    "beetle": ["Heracross", "Pinsir", "Karrablast", "Escavalier", "Grubbin", "Charjabug", "Vikavolt", "Dwebble"],
    "dog": ["Growlithe", "Arcanine", "Houndour", "Houndoom", "Poochyena", "Mightyena", "Lillipup", "Stoutland",
            "Rockruff", "Lycanroc", "Yamper", "Boltund", "Maschiff", "Mabosstiff"],
    "hound": ["Houndour", "Houndoom", "Maschiff", "Mabosstiff"], "wolf": ["Poochyena", "Mightyena", "Lycanroc"],
    "cat": ["Meowth", "Persian", "Glameow", "Purugly", "Purrloin", "Liepard", "Litten", "Torracat", "Incineroar"],
    "lion": ["Litleo", "Pyroar", "Luxray"], "fox": ["Vulpix", "Ninetales", "Fennekin", "Zorua", "Zoroark"],
    "mushroom": ["Paras", "Parasect", "Shroomish", "Breloom", "Foongus", "Amoonguss", "Morelull", "Shiinotic"],
    "flower": ["Bellossom", "Flabébé", "Floette", "Florges", "Roselia", "Roserade", "Comfey"],
    "hippo": ["Hippopotas", "Hippowdon"], "elephant": ["Phanpy", "Donphan", "Cufant", "Copperajah"],
    "shark": ["Carvanha", "Sharpedo", "Gible", "Gabite", "Garchomp"], "whale": ["Wailmer", "Wailord"],
    "mole": ["Diglett", "Dugtrio", "Drilbur", "Excadrill"], "bee": ["Combee", "Vespiquen", "Beedrill"],
    "mantis": ["Scyther", "Scizor", "Kleavor", "Fomantis", "Lurantis"], "bear": ["Teddiursa", "Ursaring",
                                                                                 "Cubchoo", "Beartic"],
    "panda": ["Pancham", "Pangoro"], "sloth": ["Slakoth", "Vigoroth", "Slaking"],
    "rabbit": ["Buneary", "Lopunny", "Scorbunny", "Raboot", "Cinderace"], "owl": ["Hoothoot", "Noctowl", "Rowlet"],
    "crow": ["Murkrow", "Honchkrow", "Corvisquire", "Corviknight"], "raven": ["Murkrow", "Honchkrow", "Corviknight"],
    "eagle": ["Rufflet", "Braviary", "Staravia", "Staraptor"], "hawk": ["Fletchling", "Talonflame", "Staraptor"],
    "pelican": ["Pelipper", "Wingull"], "gull": ["Wingull", "Pelipper"], "parrot": ["Chatot"],
    "penguin": ["Piplup", "Prinplup", "Empoleon", "Eiscue"], "harpy": ["Pidgeot", "Staraptor"],
    "golem": ["Golett", "Golurk", "Geodude", "Graveler", "Golem"], "statue": ["Golett", "Golurk", "Bronzong"],
    "knight": ["Honedge", "Doublade", "Aegislash", "Gallade", "Bisharp"], "sword": ["Honedge", "Doublade",
                                                                                   "Aegislash", "Gallade"],
    "ninja": ["Greninja", "Ninjask", "Accelgor"], "snowman": ["Snorunt", "Glalie", "Vanillite"],
    "lamp": ["Chinchou", "Lanturn", "Litwick", "Lampent", "Chandelure"], "candle": ["Litwick", "Lampent"],
    "smoke": ["Koffing", "Weezing", "Litwick", "Torkoal"], "jellyfish": ["Tentacool", "Tentacruel", "Frillish"],
    "pearl": ["Clamperl", "Shellder", "Cloyster"], "clam": ["Shellder", "Cloyster", "Clamperl"],
    "starfish": ["Staryu", "Starmie"], "crab": ["Krabby", "Kingler", "Corphish", "Crawdaunt", "Crabrawler"],
    "seal": ["Seel", "Dewgong", "Spheal", "Popplio"], "otter": ["Oshawott", "Dewott", "Samurott"],
    "dragon": ["Dratini", "Dragonair", "Dragonite", "Bagon", "Shelgon", "Salamence"],
    "dinosaur": ["Tyrunt", "Tyrantrum", "Cranidos", "Rampardos", "Larvitar", "Pupitar", "Tyranitar"],
    "lizard": ["Charmander", "Salandit", "Salazzle", "Helioptile", "Heliolisk"], "komodo": ["Salazzle", "Heliolisk"],
    "iguana": ["Helioptile", "Heliolisk"], "worm": ["Wurmple", "Dunsparce"], "caterpillar": ["Caterpie", "Wurmple"],
    "moth": ["Venonat", "Venomoth", "Volcarona", "Dustox", "Frosmoth"], "butterfly": ["Butterfree", "Beautifly",
                                                                                     "Vivillon"],
    "centipede": ["Venipede", "Whirlipede", "Scolipede", "Sizzlipede", "Centiskorch"],
    "robot": ["Magnemite", "Magneton", "Klink", "Porygon"], "machine": ["Magnemite", "Klink", "Bronzor"],
    "ghost": ["Gastly", "Haunter", "Gengar", "Misdreavus"], "skull": ["Duskull", "Dusclops", "Cubone"],
    "horse": ["Ponyta", "Rapidash", "Blitzle", "Zebstrika", "Mudbray", "Mudsdale"], "unicorn": ["Ponyta",
                                                                                                "Rapidash"],
    "boar": ["Swinub", "Piloswine", "Tepig", "Pignite", "Emboar"], "pig": ["Tepig", "Pignite", "Spoink"],
    "sheep": ["Mareep", "Flaaffy", "Ampharos", "Wooloo"], "goat": ["Skiddo", "Gogoat"],
    "tree": ["Sudowoodo", "Trevenant", "Phantump"], "seed": ["Seedot", "Sewaddle"], "leaf": ["Leavanny", "Sewaddle"],
    "angel": ["Togekiss", "Togetic"], "wizard": ["Delphox", "Mismagius"], "fish": ["Goldeen", "Seaking",
                                                                                  "Basculin", "Finneon"],
    "tomato": ["Applin", "Flapple"], "onion": ["Applin"], "boxer": ["Hitmonchan", "Crabrawler", "Conkeldurr"],
    "fighter": ["Machop", "Machoke", "Machamp", "Timburr"], "monk": ["Meditite", "Medicham", "Mienfoo", "Mienshao"],
    "witch": ["Mismagius", "Misdreavus"], "plane": ["Togekiss", "Corviknight"], "helicopter": ["Corviknight"],
    "amber": ["Shuckle", "Dwebble"], "cockroach": ["Pheromosa"], "hedgehog": ["Cyndaquil", "Chespin"],
    "squirrel": ["Pachirisu", "Skwovet"], "kangaroo": ["Kangaskhan"], "gorilla": ["Grookey", "Rillaboom",
                                                                                 "Darmanitan"],
    "yeti": ["Abomasnow", "Snover", "Darmanitan"], "lantern": ["Litwick", "Lanturn"], "bulb": ["Chinchou", "Lanturn"],
    "ice cube": ["Eiscue", "Bergmite", "Avalugg"], "eiscue": ["Eiscue"], "sudowoodo": ["Sudowoodo", "Bonsly"],
    "komala": ["Komala"], "unown": ["Bronzong", "Beheeyem"],
}
# Abilities (official and our own) -> moves that make the ability work, best first, and how many to add at most.
ABILITY_SYNERGY = {
    "Strong Jaw": (["Crunch", "Psychic Fangs", "Fire Fang", "Ice Fang", "Thunder Fang", "Bite"], 3),
    "Iron Fist": (["Drain Punch", "Ice Punch", "Thunder Punch", "Fire Punch", "Mach Punch", "Bullet Punch"], 3),
    "Sharpness": (["Leaf Blade", "Night Slash", "X-Scissor", "Psycho Cut", "Air Slash", "Slash", "Aqua Cutter"], 3),
    "Technician": (["Bullet Seed", "Icicle Spear", "Rock Blast", "Mach Punch", "Bullet Punch", "Aqua Jet",
                    "Double Kick", "Arm Thrust", "Dual Wingbeat", "Double Hit", "Fury Swipes", "Quick Attack",
                    "Pin Missile", "Water Shuriken", "Shadow Sneak", "Ice Shard"], 2),
    "Skill Link": (["Bullet Seed", "Icicle Spear", "Rock Blast", "Pin Missile", "Arm Thrust", "Tail Slap"], 2),
    "Mega Launcher": (["Water Pulse", "Dark Pulse", "Dragon Pulse", "Aura Sphere"], 2),
    "Punk Rock": (["Hyper Voice", "Bug Buzz", "Snarl", "Disarming Voice", "Echoed Voice"], 2),
    "Liquid Voice": (["Hyper Voice", "Disarming Voice", "Echoed Voice"], 2),
    "Toxic Voice": (["Hyper Voice", "Bug Buzz", "Snarl", "Disarming Voice", "Echoed Voice", "Uproar"], 3),
    "Soundproof": ([], 0),
    "Reckless": (["Double-Edge", "Take Down", "Brave Bird", "Flare Blitz", "Wild Charge", "Head Smash"], 2),
    "Rock Head": (["Double-Edge", "Head Smash", "Take Down"], 1),
    "Sheer Force": ([], 0),
    "Drought": (["Sunny Day", "Solar Beam", "Weather Ball"], 2),
    "Chlorophyll": (["Sunny Day", "Growth", "Solar Beam"], 2),
    "Solar Power": (["Sunny Day", "Solar Beam"], 1),
    "Leaf Mane": (["Sunny Day", "Solar Blade", "Solar Beam"], 2),
    "Drizzle": (["Rain Dance", "Thunder", "Hurricane", "Weather Ball"], 2),
    "Swift Swim": (["Rain Dance"], 1),
    "Rain Dish": (["Rain Dance"], 1),
    "Primordial Sea": (["Thunder", "Hurricane"], 1),
    "Sand Stream": (["Sandstorm"], 1), "Sand Rush": (["Sandstorm"], 1), "Sand Force": (["Sandstorm"], 1),
    "Snow Warning": (["Blizzard", "Aurora Veil", "Hail"], 2), "Slush Rush": (["Hail"], 1),
    "Ice Body": (["Hail"], 1), "Cold-hearted": (["Hail", "Blizzard"], 1),
    "Weather Switch": (["Rain Dance", "Sunny Day", "Weather Ball"], 3),
    "Electric Surge": (["Electric Terrain", "Rising Voltage"], 1),
    "Grassy Surge": (["Grassy Terrain", "Grassy Glide"], 1),
    "Psychic Surge": (["Psychic Terrain", "Expanding Force"], 1),
    "Misty Surge": (["Misty Terrain"], 1),
    "Guts": (["Facade"], 1), "Toxic Boost": (["Facade"], 1), "Flare Boost": (["Facade"], 1),
    "Poison Heal": (["Protect", "Substitute"], 1), "Speed Boost": (["Protect"], 1),
    "Prankster": (["Thunder Wave", "Taunt", "Will-O-Wisp", "Encore", "Light Screen", "Reflect"], 2),
    "Sniper": (["Night Slash", "Stone Edge", "Slash", "Leaf Blade"], 1),
    "Super Luck": (["Night Slash", "Stone Edge", "Slash"], 1),
    "Heavy Metal": (["Heavy Slam"], 1),
    "Sloth Combat": (["Rest", "Sleep Talk", "Snore"], 3),
    "Lullaby": (["Yawn", "Rest", "Sleep Talk"], 2),
    "Shed Skin": (["Rest"], 1), "Early Bird": (["Rest", "Sleep Talk"], 1),
    "Unburden": (["Acrobatics"], 1),
    "Stamina": (["Body Press"], 1),
}
# Words in the look/concept/notes -> a move that shows it (added only if it fits the types).
FLAVOUR = [
    (r"\b(lamp|lantern|light ?bulb|bulb on|lights? up|blinds?|shines? a light|flashlight)\b", ["Flash"]),
    (r"\bsmok(e|es|ing|y)\b", ["Smokescreen"]),
    (r"\b(sings?|song|singing|screams?|screech)\b", ["Hyper Voice", "Round"]),
    (r"\bdrill\b", ["Drill Run"]),
    (r"\bhorns?\b", ["Horn Attack"]),
    (r"\bbeak\b", ["Peck", "Drill Peck"]),
    (r"\bwings?\b", ["Wing Attack"]),
    (r"\b(claw|claws)\b", ["Slash", "Metal Claw"]),
    (r"\b(spikes|spiky|spines|quills)\b", ["Pin Missile", "Spikes"]),
    (r"\b(venom|venomous|poisonous)\b", ["Poison Fang", "Poison Jab"]),
    (r"\b(bottles?|throws? (things|rocks|bottles))\b", ["Fling"]),
    (r"\b(sleepy|lazy|always asleep|sleeps)\b", ["Yawn"]),
    (r"\b(shell)\b", ["Withdraw"]),
]
FLAVOUR_ANY_TYPE = {"Flash", "Withdraw", "Fling", "Smokescreen"}

# Types the species files cannot hold yet. Arvind 2026-11-12: Rainbro is Stellar (no weaknesses or strengths).
# Stellar here = no same-type bonus, moves spread over many types (a rainbow); Origin has no such type yet.
TYPE_OVERRIDES = {"rainbro": ["Stellar"]}
RAINBOW = ["Fire", "Water", "Grass", "Electric", "Ice", "Psychic", "Fairy", "Dragon", "Fighting", "Flying",
           "Dark", "Ghost", "Rock", "Ground", "Steel", "Poison", "Bug"]
ARMLESS = ("serpentine", "fish", "finned", "head", "ball", "blob", "orb", "quadruped", "four legs", "no arms",
           "legless", "insect body with wings", "bug-like")


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


# --------------------------------------------------------------------------------------------- our species

def load_claude_moves():
    path = DATA_DIR / "claude_moves.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_ours(exclude_claude=False):
    """Our species. exclude_claude=True leaves out the moves Claude added earlier (data/claude_moves.json), so a
    new proposal can replace them while the designers' own moves stay."""
    species, problems = dexlib.load_species()
    claude = load_claude_moves() if exclude_claude else {}
    out = {}
    for sid, path, data in species:
        if sid in claude:
            data = json.loads(json.dumps(data))
            ls, cm = data.setdefault("learnset", {}), claude[sid]
            lu_moves = {m for lv, m in cm.get("level_up", [])}
            ls["level_up"] = [e for e in (ls.get("level_up") or []) if not (isinstance(e, dict) and e.get("move") in
                                                                         lu_moves)]
            for k in ("tm_hm", "tutor", "egg"):
                ls[k] = [m for m in (ls.get(k) or []) if m not in set(cm.get(k, []))]
        stats = data.get("base_stats") or {}
        st = {k: _num(stats.get(k)) for k in STATS}
        ab = data.get("abilities") or {}
        design = data.get("design") or {}
        ls = data.get("learnset") or {}
        out[sid] = {
            "id": sid, "path": path, "data": data, "name": data.get("name") or sid, "dex": data.get("dex"),
            "types": [t for t in (data.get("types") or []) if t] or TYPE_OVERRIDES.get(sid, []),
            "stats": st if all(st.values()) else None,
            "abilities": [a for a in (ab.get("primary"), ab.get("secondary"), ab.get("hidden")) if a],
            "evolutions": [e for e in (data.get("evolutions") or []) if isinstance(e, dict) and e.get("into")],
            "design": design,
            "text": " ".join(str(design.get(k) or "") for k in ("concept", "look", "notes", "wishes", "body_shape",
                                                                "movement")) + " " + str(data.get("category") or "")
                    + " " + str(data.get("description") or ""),
            "learnset": {k: list(ls.get(k) or []) for k in KEYS},
        }
    return out


def build_lines(ours):
    """Parent links (explicit and guessed), stage, line paths. Adds keys to each species dict."""
    parent, notes = {}, {}
    for sid, sp in ours.items():
        for e in sp["evolutions"]:
            if e["into"] in ours:
                parent.setdefault(e["into"], (sid, e))
    # "Evolves from Tomadernader" / "Evolved from CIGGITI" on a concept card
    def find(name):
        key = re.sub(r"[^a-z]", "", name.lower())
        for sid, sp in ours.items():
            for cand in (sid, sp["name"]):
                ck = re.sub(r"[^a-z]", "", str(cand).lower())
                if ck == key or (len(key) >= 6 and ck[:5] == key[:5] and abs(len(ck) - len(key)) <= 2):
                    return sid
        return None
    for sid, sp in ours.items():
        if sid in parent:
            continue
        m = re.search(r"[Ee]volve[sd]? from ([A-Za-z\-]+)", str(sp["design"].get("notes") or ""))
        src = find(m.group(1)) if m else None
        if src and src != sid:
            parent[sid] = (src, {"into": sid, "method": "card"})
            notes[sid] = "card"
    loose =[sp for sid, sp in ours.items() if sid not in parent and not [e for e in sp["evolutions"]
                                                                            if e["into"] in ours]]
    loose.sort(key=lambda s: (s["dex"] if isinstance(s["dex"], int) else 9999))
    bst = lambda s: sum(s["stats"].values()) if s["stats"] else None
    by_dex = {s["dex"]: s for s in loose if isinstance(s["dex"], int)}
    linked_child = set()

    def can_link(a, b):
        if not a["types"] or not b["types"] or not set(a["types"]) & set(b["types"]):
            return False
        ba, bb = bst(a), bst(b)
        if a["id"] in b["id"] and b["id"] != a["id"]:          # pipwi -> pipwi-utv, viridub -> viridub-utvikling
            return True
        if ba is None or bb is None:
            return (ba or 0) <= 430 and set(a["types"]) <= set(b["types"]) | set(a["types"])
        return ba <= 430 and bb >= ba + 50

    for s in loose:
        if s["id"] in linked_child or not isinstance(s["dex"], int):
            continue
        chain = [s]
        while len(chain) < 3:
            nxt = by_dex.get(chain[-1]["dex"] + 1)
            if not nxt or nxt["id"] in linked_child:
                break
            if can_link(chain[-1], nxt):
                chain.append(nxt)
                continue
            # branch: same parent, a sister of similar strength (Ciggiti -> Chuchar / Parahaunt)
            if len(chain) >= 2 and can_link(chain[-2], nxt) and bst(chain[-1]) and bst(nxt) and \
                    abs(bst(chain[-1]) - bst(nxt)) <= 60:
                parent[nxt["id"]] = (chain[-2]["id"], {"into": nxt["id"], "method": "guessed"})
                notes[nxt["id"]] = "guessed"
                linked_child.add(nxt["id"])
            break
        for a, b in zip(chain, chain[1:]):
            if b["id"] in parent:
                continue
            parent[b["id"]] = (a["id"], {"into": b["id"], "method": "guessed"})
            notes[b["id"]] = "guessed"
            linked_child.add(b["id"])
    children = defaultdict(list)
    for c, (p, e) in parent.items():
        children[p].append((c, e))
    for sid, sp in ours.items():
        stage, cur = 0, sid
        while cur in parent and stage < 4:
            cur = parent[cur][0]
            stage += 1
        sp["root"], sp["stage"] = cur, stage
        sp["parent"] = parent.get(sid, (None, None))[0]
        sp["evo_in"] = parent.get(sid, (None, None))[1]           # how it evolved INTO this one
        sp["children"] = [c for c, e in children.get(sid, [])]
        sp["guessed_parent"] = notes.get(sid) == "guessed"

    def depth(sid):
        return 1 + max((depth(c) for c in ours[sid]["children"]), default=0)

    def paths(sid):
        kids = ours[sid]["children"]
        if not kids:
            return [[sid]]
        return [[sid] + p for c in kids for p in paths(c)]

    lines = {}
    for sid, sp in ours.items():
        sp["line_length"] = depth(sp["root"]) if sp["root"] in ours else 1
        sp["final"] = not sp["children"]
        if sp["root"] == sid:
            lines[sid] = paths(sid)
    return lines


def evo_level(ours, child):
    e = ours[child]["evo_in"] or {}
    return e.get("level") if isinstance(e.get("level"), int) else None


# --------------------------------------------------------------------------------------------- reference

class Reference:
    """Official species from Origin plus statistics over their learnsets."""

    def __init__(self, data):
        self.M = data["moves"]
        self.tms = [t["move"] for t in data["tms"]]
        self.tm_label = {t["move"]: t["tm"] for t in data["tms"]}
        self.tutor_where = data["tutors"]
        self.all = data["species"]
        self.models = {n: s for n, s in data["species"].items() if s.get("stats") and n not in BAD_MODELS
                       and not s.get("baby") and len(s["level_up"]) >= 6}
        self.tutor_moves = sorted({m for s in self.all.values() for m in s["tutor"]})
        self.egg_group_moves = defaultdict(set)      # what partners of an egg group can pass on
        for s in self.all.values():
            for g in s.get("egg_groups") or []:
                self.egg_group_moves[g] |= {mv for lv, mv in s["level_up"]} | set(s["egg"])
        self._stats()

    def _stats(self):
        M = self.M
        lines_of = defaultdict(set)
        levels = defaultdict(list)
        for n, s in self.all.items():
            for lv, mv in s["level_up"]:
                lines_of[mv].add(s["root"])
                if lv > 1:
                    levels[mv].append(lv / max(1, (s["bst"] or 400)) * 500)
        self.line_count = {m: len(v) for m, v in lines_of.items()}
        self.typical_level = {m: statistics.median(v) for m, v in levels.items() if v}
        pool = defaultdict(lambda: defaultdict(Counter))      # type -> category -> move -> lines
        for n, s in self.models.items():
            for lv, mv in s["level_up"]:
                m = M.get(mv)
                if not m:
                    continue
                if m["type"] in s["types"]:
                    pool[m["type"]][m["category"]][mv] += 1
        self.type_pool = {t: {c: {mv: k for mv, k in cnt.items() if self.line_count.get(mv, 0) >= 3}
                              for c, cnt in cats.items()} for t, cats in pool.items()}
        # P(move | type, stage kind) for TM, tutor, egg
        self.freq = {}
        for key in ("tm_hm", "tutor", "egg", "level_up"):
            per = defaultdict(lambda: defaultdict(Counter))
            totals = defaultdict(Counter)
            for n, s in self.models.items():
                kind = "final" if s["final"] else ("base" if s["stage"] == 0 else "mid")
                if key == "egg" and s["stage"] != 0:
                    continue
                moves = set(mv for lv, mv in s["level_up"]) if key == "level_up" else set(s[key])
                for t in s["types"] + ["*"]:
                    totals[t][kind] += 1
                    for mv in moves:
                        per[t][kind][mv] += 1
            self.freq[key] = (per, totals)

    def p_type(self, key, move, types, kind):
        per, totals = self.freq[key]
        best = 0.0
        for t in types:
            k = kind if totals[t][kind] >= 5 else None
            if k is None:
                tot = sum(totals[t].values())
                cnt = sum(per[t][x][move] for x in per[t])
            else:
                tot, cnt = totals[t][k], per[t][k][move]
            if tot:
                best = max(best, cnt / tot)
        return best

    def p_all(self, key, move, kind):
        per, totals = self.freq[key]
        return per["*"][kind][move] / totals["*"][kind] if totals["*"][kind] else 0.0

    def is_signature(self, move):
        return self.line_count.get(move, 0) <= 2


def stat_shape(stats):
    v = [stats[k] for k in STATS]
    tot = sum(v) or 1
    v = [x / tot for x in v]
    mean = sum(v) / 6
    return [x - mean for x in v]


def cosine(a, b):
    na = math.sqrt(sum(x * x for x in a)) or 1
    nb = math.sqrt(sum(x * x for x in b)) or 1
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def keyword_models(sp, ref):
    text = (sp["text"] + " " + sp["name"]).lower()
    found = set()
    for word, names in KEYWORDS.items():
        if re.search(r"\b%s(s|es)?\b" % re.escape(word), text):
            for nm in names:
                if nm in ref.all:
                    found.add(ref.all[nm]["root"])
    return found


def similarity(sp, o, kw_roots, legendary, use_stats=True):
    score = 0.0
    if sp["stats"] and use_stats:
        score += 1.6 * cosine(stat_shape(sp["stats"]), stat_shape(o["stats"]))
        score += 0.8 * math.exp(-abs(sum(sp["stats"].values()) - o["bst"]) / 70)
    t = 0.0
    for i, ty in enumerate(sp["types"]):
        if ty in o["types"]:
            t += 1.0 + (0.25 if o["types"].index(ty) == i else 0)
    t -= 0.35 * len([ty for ty in o["types"] if ty not in sp["types"]])
    score += 1.3 * t / max(1, len(sp["types"]))
    if sp["stage"] == o["stage"] and sp["line_length"] == o["line_length"]:
        score += 0.9
    elif sp["final"] == o["final"]:
        score += 0.45
    if o["root"] in kw_roots:
        score += 0.8
    shared = len(set(sp["abilities"]) & set(o["abilities"] + [o.get("hidden")]))
    score += 0.25 * min(shared, 2)
    if legendary != o["legendary"]:
        score -= 1.5
    return score


# --------------------------------------------------------------------------------------------- the engine

class Proposer:
    def __init__(self, ours, lines, ref):
        self.ours, self.lines, self.ref, self.M = ours, lines, ref, ref.M
        self.custom_moves = self._custom_moves()
        self.official_paths = self._official_paths()
        self._evo_used = {}
        self._line_model = {}
        self._cur_level = 0
        self._skipped = {}
        try:
            self.ref_abilities = sorted(json.loads((ROOT / "data" / "engine" / "showdown.json").read_text(
                encoding="utf-8"))["abilities"])
        except Exception:
            self.ref_abilities = []

    def _custom_moves(self):
        try:
            entries = yaml.safe_load((DATA_DIR / "custom_moves.yaml").read_text(encoding="utf-8"))["moves"]
        except Exception:
            entries = []
        return {e["name"]: e for e in entries if e.get("name")}

    def _official_paths(self):
        paths = []
        for n, s in self.ref.models.items():
            if s["stage"] != 0:
                continue

            def walk(name, acc):
                sp = self.ref.all.get(name)
                if not sp or name in acc or len(acc) >= 3:
                    return
                acc = acc + [name]
                kids = [e["name"] for e in sp["evolves_into"] if e["name"] in self.ref.models and e["name"] not in acc]
                if not kids:
                    paths.append(acc)
                for k in kids:
                    walk(k, acc)
            walk(n, [])
        return paths

    # -------------------------------------------------------------- profiles
    def legendary(self, sp):
        bst = sum(sp["stats"].values()) if sp["stats"] else 0
        txt = sp["text"].lower()
        return (sp["line_length"] == 1 and (bst >= 570 or "legendar" in txt)) or ("legendary" in txt and bst >= 540)

    def profile(self, sid):
        sp = self.ours[sid]
        if sp.get("_profile"):
            return sp["_profile"]
        stats, estimated = sp["stats"], False
        if not stats:
            estimated = True
            target = {(1, 0): 470, (2, 0): 330, (2, 1): 495, (3, 0): 315, (3, 1): 410, (3, 2): 525}.get(
                (sp["line_length"], sp["stage"]), 450)
            mates = [self.ours[x] for p in self.lines.get(sp["root"], []) for x in p if self.ours[x]["stats"]]
            if mates:
                base = min(mates, key=lambda m: abs(m["stage"] - sp["stage"]))["stats"]
                tot = sum(base.values())
                stats = {k: max(10, round(v * target / tot)) for k, v in base.items()}
            else:
                cands = sorted(self.ref.models.values(),
                               key=lambda o: -similarity(sp, o, set(), False, use_stats=False))[:6]
                stats = {k: round(statistics.mean(o["stats"][k] * target / o["bst"] for o in cands)) for k in STATS}
        mon = {"name": sp["name"], "types": sp["types"], "stats": stats, "abilities": sp["abilities"]}
        role_text = " ".join(str(sp["design"].get(k) or "") for k in ("wishes", "notes", "concept"))
        info = mp.detect_role(mon, self._role_words(role_text))
        sp["_profile"] = dict(mon, estimated=estimated, info=info)
        return sp["_profile"]

    @staticmethod
    def _role_words(text):
        t = text.lower()
        m = re.search(r"role ([a-z ]+?)(?:[.;,]|$)", t)
        keep = [m.group(1)] if m else []
        for w in ("trick room", "mixed attacker", "tank", "wall", "bulky", "support", "pivot", "sweeper", "frail",
                  "weak but fast", "fast"):
            if w in t:
                keep.append(w)
        return " ".join(keep)

    # -------------------------------------------------------------- donors
    def donors_for(self, sid, n=8):
        sp = self.ours[sid]
        prof = self.profile(sid)
        tmp = dict(sp, stats=prof["stats"])
        kw = keyword_models(sp, self.ref)
        leg = self.legendary(tmp)
        scored = []
        for name, o in self.ref.models.items():
            if not leg and o["legendary"]:
                continue
            scored.append((similarity(tmp, o, kw, leg) + self.named_bonus(sid, o), name))
        scored.sort(reverse=True)
        same_kind = [x for x in scored if self.ref.models[x[1]]["final"] == sp["final"]]
        return (same_kind or scored)[:n], kw, leg

    def line_donor(self, path):
        """Best official path for our path (same length if possible)."""
        best = None
        kw = set()
        for x in path:
            kw |= keyword_models(self.ours[x], self.ref)
        leg = any(self.legendary(dict(self.ours[x], stats=self.profile(x)["stats"])) for x in path)
        for op in self.official_paths:
            if len(op) != len(path):
                continue
            os_ = [self.ref.all[n] for n in op]
            if not leg and any(o["legendary"] for o in os_):
                continue
            s, wsum = 0.0, 0.0
            for i, (x, o) in enumerate(zip(path, os_)):
                tmp = dict(self.ours[x], stats=self.profile(x)["stats"])
                w = 1.5 if i == len(path) - 1 else 1.0
                s += w * (similarity(tmp, o, kw, leg) + self.named_bonus(x, o))
                wsum += w
            s /= wsum
            for i in range(1, len(path)):
                ours_lv = evo_level(self.ours, path[i])
                theirs = (os_[i - 1]["evolves_into"] and [e["level"] for e in os_[i - 1]["evolves_into"]
                                                          if e["name"] == op[i]] or [None])[0]
                if ours_lv and theirs:
                    s += 0.15 * math.exp(-abs(ours_lv - theirs) / 10)
            if best is None or s > best[0]:
                best = (s, op)
        if best is None:              # no official line that long: align on the final stages
            n = len(path)
            cands = [op for op in self.official_paths if len(op) >= 1]
            best = max(((sum(similarity(dict(self.ours[x], stats=self.profile(x)["stats"]),
                                        self.ref.all[o], kw, leg)
                             for x, o in zip(path[::-1], op[::-1])) / n, op[-n:] if len(op) >= n else
                        [op[0]] * (n - len(op)) + op) for op in cands), key=lambda t: t[0])
        return best

    def preferred_types(self, sid):
        """Types the designers ask for: "mostly psychic and dark type moves", "mostly fighting moves"."""
        sp = self.ours[sid]
        text = " ".join(str(sp["design"].get(k) or "") for k in ("wishes", "concept")).lower()
        out = []
        for m in re.finditer(r"(?:mostly|mainly|lots of|many)\s+((?:[a-z]+(?:\s*(?:,|and|or)\s*)?){1,3})", text):
            for w in re.findall(r"[a-z]+", m.group(1)):
                t = w.capitalize()
                if t in moveset_data.TYPES and t not in out:
                    out.append(t)
        return out

    def named_models(self, sid):
        """Official Pokemon the designers name in wishes/notes/concept ("like Zigzagoon or Ratata")."""
        sp = self.ours[sid]
        if "_named" in sp:
            return sp["_named"]
        text = " ".join(str(sp["design"].get(k) or "") for k in ("wishes", "concept"))
        names = {re.sub(r"[^a-z]", "", n.lower()): n for n in self.ref.all}
        roots = set()
        for tok in re.findall(r"[A-Za-z][A-Za-z'\-]{3,}", text):
            key = re.sub(r"[^a-z]", "", tok.lower())
            if key in ("ghost", "fairy", "steel", "rock", "water", "dark", "fire", "grass", "ice", "bug"):
                continue
            hit = names.get(key) or (difflib.get_close_matches(key, list(names), n=1, cutoff=0.8) or [None])[0]
            if hit:
                hit = names.get(hit, hit)
                roots.add(self.ref.all[hit]["root"])
        sp["_named"] = roots
        return roots

    def _same_job(self, mv, own, level=None):
        """An own move of the same type, side and about the same power, learned at about the same level, with no
        special effect that makes it different (pivot, priority, drain, multi-hit ...); or the same status job."""
        m = self.M.get(mv)
        if not m:
            return None
        special = lambda x: (x["switch"], x["priority"] > 0, x["drain"], bool(x["multihit"]), x["self_ko"],
                             x["recharge"], x["charge"], bool(x.get("self_boosts")), x["variable_power"],
                             bool(x.get("volatile")),
                             x.get("target") in ("allAdjacentFoes", "allAdjacent", "all"))
        for e in own:
            o = self.M.get(e["move"])
            if not o or o is m:
                continue
            olv = e.get("level") if isinstance(e.get("level"), int) else None
            near = level is None or olv is None or level <= 1 or olv <= 1 or abs(olv - level) <= 6
            if m["category"] != "Status" and o["category"] == m["category"] and o["type"] == m["type"] \
                    and abs(o["power"] - m["power"]) <= 15 and special(o) == special(m) and near:
                return e["move"]
            if m["category"] == "Status":
                for group in STATUS_GROUP.values():
                    if mv in group and e["move"] in group:
                        return e["move"]
                if (m.get("boosts") or {}) and m.get("boosts") == o.get("boosts"):
                    return e["move"]
        return None

    def _fit_level(self, e, own, own_levels):
        """Keep the designers' power curve: nothing stronger of the same type before their move; no shared level."""
        lv = e["level"]
        m = self.M.get(e["move"])
        if lv <= 1 or not m:
            return lv
        if m["category"] != "Status":
            for o in own:
                om = self.M.get(o["move"])
                if om and om["type"] == m["type"] and om["category"] != "Status" and isinstance(o.get("level"), int) \
                        and o["level"] > 1 and m["power"] > om["power"] + 10 and lv < o["level"]:
                    lv = o["level"] + 3
        while lv in own_levels and lv < 100:
            lv += 1
        return lv

    def own_moves(self, sid):
        sp = self.ours[sid]
        return {e.get("move") if isinstance(e, dict) else e for k in KEYS for e in sp["learnset"][k]} & set(self.M)

    def named_bonus(self, sid, o):
        """Official Pokemon the designers name, and ones that can learn the moves the designers already chose."""
        bonus = 1.5 if o["root"] in self.named_models(sid) else 0.0
        own = self.own_moves(sid)
        if own:
            pool = o.get("_pool")
            if pool is None:
                pool = o["_pool"] = set(mv for lv, mv in o["level_up"]) | set(o["tm_hm"]) | set(o["tutor"]) | \
                    set(o["egg"])
            bonus += 1.0 * len(own & pool) / len(own)
        return bonus

    # -------------------------------------------------------------- helpers
    def armless(self, sid):
        sp = self.ours[sid]
        shape = str(sp["design"].get("body_shape") or "").lower() + " " + str(sp["design"].get("movement") or "").lower()
        if any(w in shape for w in ("arm", "hand", "humanoid", "bipedal", "upright")):
            return False
        return any(w in shape for w in ARMLESS)

    def body_ok(self, sid, move):
        m = self.M.get(move)
        if not m:
            return True
        if "punch" in m["flags"] and self.armless(sid):
            return False
        return True

    def wished_moves(self, sid):
        """Moves named by the designers (wishes, notes, concept). -> (known, new_wanted)"""
        sp = self.ours[sid]
        d = sp["design"]
        texts = [str(d.get("wishes") or ""), str(d.get("notes") or ""), str(d.get("concept") or "")]
        known, wanted = [], []
        names = sorted(set(self.M) | set(self.custom_moves), key=len, reverse=True)
        for i, text in enumerate(texts):
            if not text:
                continue
            segments = [text] if i == 0 else []
            segments += re.findall(r"(?:[Mm]oves?|learn\w*|gets?|[Ss]ignature moves?)\s*:?\s*([^.]*)", text)
            low_full = text.lower()
            for name in names:
                ln = name.lower()
                if " " in ln or "-" in ln:
                    hit = re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(ln), low_full)
                else:
                    hit = False
                    for seg in segments:
                        for mm in re.finditer(r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(name), seg, re.I):
                            before = seg[:mm.start()].rstrip().split(" ")[-1:] or [""]
                            after = seg[mm.end():].lstrip().split(" ")[:1] or [""]
                            # part of a longer name such as "Aqua Slash" or "Hex Burst": not this move
                            if (before[0][:1].isupper() and seg[:mm.start()].endswith(" ") and
                                    not before[0].endswith((":", ",", "."))) or after[0][:1].isupper() and \
                                    seg[mm.end():mm.end() + 1] == " ":
                                continue
                            hit = True
                            break
                        if hit:
                            break
                if hit and name not in known:
                    if not any(name in k and name != k for k in known):
                        known.append(name)
            for m in re.finditer(r"[Ss]ignature moves?:?\s*([^.;]*)", text):
                for piece in re.split(r",| and ", re.sub(r"\([^)]*(\)|$)", "", m.group(1))):
                    nm = re.sub(r"\(.*", "", piece).strip(" .:'\"")
                    if not nm or len(nm) > 24:
                        continue
                    match = self._custom_match(nm)
                    if match:
                        if match not in known:
                            known.append(match)
                    elif nm not in self.M and nm not in wanted and nm[0].isupper():
                        wanted.append(nm)
        known = [k for k in known if k not in ("Psychic",) or "psychic type" not in str(d.get("wishes") or "").lower()]
        return known, wanted

    def _custom_match(self, name):
        key = re.sub(r"[^a-z]", "", name.lower())
        best = (0.0, None)
        for c in self.custom_moves:
            ck = re.sub(r"[^a-z]", "", c.lower())
            r = difflib.SequenceMatcher(None, key, ck).ratio()
            if r > best[0]:
                best = (r, c)
        return best[1] if best[0] >= 0.72 else None

    # -------------------------------------------------------------- level-up
    def remap(self, lv, donor_evos, our_evos):
        if lv <= 1:
            return lv
        anchors = [(1, 1)]
        for e, f in zip(donor_evos, our_evos):
            if e and f and e > anchors[-1][0] and f > anchors[-1][1]:
                anchors.append((e, f))
        for (a0, b0), (a1, b1) in zip(anchors, anchors[1:]):
            if lv <= a1:
                return max(2, round(b0 + (lv - a0) * (b1 - b0) / (a1 - a0)))
        a, b = anchors[-1]
        return min(100, max(2, round(b + (lv - a))))

    def translate_attack(self, move, target_type, side, used, power=None):
        m = self.M[move]
        p = power if power is not None else m["power"]
        pool = self.ref.type_pool.get(target_type, {})
        cats = [side, "Physical" if side == "Special" else "Special"] if side in ("Physical", "Special") \
            else [m["category"], "Special" if m["category"] == "Physical" else "Physical"]
        cap = 45 + 2.2 * self._cur_level if self._cur_level else 999   # no 95-power move at level 12
        if m["power"] > cap:
            p = min(p, cap)
        for cat in cats:
            cands = [(abs(self.M[mv]["power"] - p) + (0 if cnt >= 6 else 8) + (6 if self.M[mv]["recharge"] or
                                                                                 self.M[mv]["charge"] else 0)
                      + (40 if self.M[mv]["power"] > cap else 0), -cnt, mv)
                     for mv, cnt in pool.get(cat, {}).items()
                     if mv not in used and self.M[mv]["power"] > 1 and mv not in NEVER_ADD
                     and not self.M[mv]["self_ko"]]
            if cands:
                cands.sort()
                if cands[0][0] <= 35:
                    return cands[0][2]
        return None

    def translate_status(self, move, our_types, used):
        group = next((g for g, s in STATUS_GROUP.items() if move in s), None)
        if group == "weather":
            for t in our_types:
                if TYPE_WEATHER.get(t) and TYPE_WEATHER[t] not in used:
                    return TYPE_WEATHER[t]
            return None
        if group == "terrain":
            for t in our_types:
                if TYPE_TERRAIN.get(t) and TYPE_TERRAIN[t] not in used:
                    return TYPE_TERRAIN[t]
            return None
        if group:
            for t in our_types:
                for cat in ("Status",):
                    cands = [(-c, mv) for mv, c in self.ref.type_pool.get(t, {}).get(cat, {}).items()
                             if mv in STATUS_GROUP[group] and mv not in used and mv not in NEVER_ADD]
                    if cands:
                        return sorted(cands)[0][1]
        return None

    def build_level_up(self, path, donor_path, memo, reasons):
        """Level-up lists for every stage of one path, from the donor path."""
        out = {}
        our_evos = [evo_level(self.ours, path[i]) for i in range(1, len(path))]
        donor_evos = []
        for i in range(1, len(donor_path)):
            prev = self.ref.all[donor_path[i - 1]]
            lv = [e["level"] for e in prev["evolves_into"] if e["name"] == donor_path[i]]
            donor_evos.append(lv[0] if lv and lv[0] else None)
        our_evos = [o if o else d for o, d in zip(our_evos, donor_evos)]
        donor_evos = [d if d else o for o, d in zip(our_evos, donor_evos)]
        line_types = []
        for x in path:
            for t in self.ours[x]["types"]:
                if t not in line_types:
                    line_types.append(t)
        type_count = Counter()
        for k, (sid, dname) in enumerate(zip(path, donor_path)):
            sp = self.ours[sid]
            if not sp["types"]:
                out[sid] = []
                continue
            prof = self.profile(sid)
            side = {"physical": "Physical", "special": "Special"}.get(prof["info"]["side"], "mixed")
            donor = self.ref.all[dname]
            entries = []
            used_here = set()
            evo_in = our_evos[k - 1] if k >= 1 else 0
            for lv, move in donor["level_up"]:
                if lv == 0 and sp["stage"] == 0:
                    continue
                m = self.M.get(move)
                if not m:
                    continue
                level = 0 if lv == 0 else self.remap(lv, donor_evos, our_evos)
                # a move of an earlier stage's type stays only if that stage learned it before evolving
                inherited = m["type"] not in sp["types"] and m["type"] in line_types and 0 < level <= (evo_in or 0)
                key = (move, tuple(sp["types"]), inherited)
                new = memo.get(key, "?")
                if new == "?":
                    self._cur_level = max(level, evo_in or 0) if level else (evo_in or 0)
                    new, why = self._translate_one(sid, move, donor, side, memo, type_count,
                                                   line_types if inherited else sp["types"])
                    if new is not None and new != move:
                        reasons.setdefault(new, why)
                    memo[key] = new
                if not new or new in used_here or not self.body_ok(sid, new) or new in NEVER_ADD:
                    continue
                used_here.add(new)
                entries.append({"level": level, "move": new})
                if new == move:
                    reasons.setdefault(new, "same move as %s" % dname)
            self._evo_used[sid] = evo_in
            entries.sort(key=lambda e: e["level"])
            self._ensure_types(sid, entries, side, memo, reasons, donor)
            out[sid] = entries
        return out

    ENSEMBLE_K = 60          # how many official Pokemon can contribute
    ENSEMBLE_T = 0.6         # how fast the influence falls off with less similarity (smaller = steeper)

    def weighted_donors(self, sid):
        """All official Pokemon, each with a weight from its similarity (a soft gradient, not one model)."""
        sp = self.ours[sid]
        if "_wdonors" in sp:
            return sp["_wdonors"]
        prof = self.profile(sid)
        tmp = dict(sp, stats=prof["stats"])
        kw = keyword_models(sp, self.ref)
        leg = self.legendary(tmp)
        scored = []
        for name, o in self.ref.models.items():
            if not leg and o["legendary"]:
                continue
            sc = similarity(tmp, o, kw, leg) + self.named_bonus(sid, o)
            if o["final"] == sp["final"]:
                sc += 0.4
            scored.append((sc, name))
        scored.sort(reverse=True)
        top = scored[:self.ENSEMBLE_K]
        best = top[0][0] if top else 0
        out = [(math.exp((sc - best) / self.ENSEMBLE_T), name) for sc, name in top]
        total = sum(w for w, n in out) or 1
        sp["_wdonors"] = [(w / total, n) for w, n in out]
        return sp["_wdonors"]

    def _anchors(self, sid):
        sp = self.ours[sid]
        enter = evo_level(self.ours, sid) if sp["parent"] else None
        leave = min([evo_level(self.ours, c) for c in sp["children"] if evo_level(self.ours, c)] or [None],
                    key=lambda x: x or 999)
        return enter, leave

    def build_level_up_ensemble(self, sid, reasons_line):
        sp = self.ours[sid]
        prof = self.profile(sid)
        side = {"physical": "Physical", "special": "Special"}.get(prof["info"]["side"], "mixed")
        o_enter, o_leave = self._anchors(sid)
        memo, type_count = {}, Counter()
        score, levels, why = Counter(), defaultdict(list), {}
        counts = []
        start = o_enter if (sp["parent"] and o_enter) else 1
        donor_bands, donor_n = Counter(), 0.0
        for w, name in self.weighted_donors(sid):
            o = self.ref.all[name]
            d_enter = (o.get("evolves_from") or {}).get("level")
            d_leave = min([e["level"] for e in o["evolves_into"] if e.get("level")] or [None], key=lambda x: x or 999)
            donor_a = [x for x in (d_enter, d_leave)]
            ours_a = [o_enter or d_enter, o_leave or d_leave]
            seen = set()
            n = 0
            for lv, move in o["level_up"]:
                if lv == 0 and not sp["parent"]:
                    continue
                m = self.M.get(move)
                if not m:
                    continue
                level = 0 if lv == 0 else self.remap(lv, [x for x in donor_a if x], [y for x, y in zip(donor_a, ours_a)
                                                                                    if x])
                key = (move, m["type"] in o["types"])
                new = memo.get(key, "?")
                if new == "?":
                    self._cur_level = max(level, o_enter or 0)
                    new, why_ = self._translate_one(sid, move, o, side, memo, type_count, sp["types"])
                    memo[key] = new
                    if new and new != move:
                        why.setdefault(new, why_)
                if not new or new in seen or new in NEVER_ADD or not self.body_ok(sid, new):
                    continue
                seen.add(new)
                n += 1
                score[new] += w
                levels[new].append((level, w))
                donor_bands[self._band(level, start)] += w
                donor_n += w
            counts.append((len(o["level_up"]), w))
        want = round(sum(c * w for c, w in counts))
        want = max(10, min(24, want))
        own = set(sp["types"]) | {"Normal"} | set(self.preferred_types(sid))

        def enough(mv, sc, band):  # moves outside its own types need more of the similar Pokemon to agree
            if band >= 2:          # late moves differ more between Pokemon, so each gets fewer votes
                return sc >= (0.02 if self.M[mv]["type"] in own else 0.10)
            return sc >= (0.04 if self.M[mv]["type"] in own else 0.15)

        def median_level(mv):
            pts = sorted(levels[mv])
            if sp["parent"] and pts and pts[0][0] <= 1:
                later = [(l, w) for l, w in pts if l > 1]
                if later and sum(w for l, w in pts if l <= 1) < sum(w for l, w in later):
                    pts = later
            half, acc = sum(w for l, w in pts) / 2, 0.0
            for l, w in pts:
                acc += w
                if acc >= half:
                    return l
            return pts[-1][0]
        # Spread the moves over the levels like the official ones do: start, before evolving, right after, middle, late
        own_lv1 = sum(1 for e in sp["learnset"]["level_up"] if isinstance(e, dict) and e.get("level") in (0, 1))
        quota = {b: round(donor_bands[b] / (donor_n or 1) * want) for b in range(5)}
        quota[0] = min(quota[0], max(1, (6 if sp["parent"] else 4) - own_lv1))
        by_band = defaultdict(list)
        lvl_of = {}
        for mv, sc in score.most_common():
            lvl_of[mv] = median_level(mv)
            band = self._band(lvl_of[mv], start)
            if enough(mv, sc, band):
                by_band[band].append(mv)
        chosen, spare = [], []
        for band in range(5):
            chosen += by_band[band][:quota[band]]
            spare += [(score[mv], mv) for mv in by_band[band][quota[band]:] if band > 0]
        for sc, mv in sorted(spare, reverse=True):
            if len(chosen) >= want:
                break
            chosen.append(mv)
        entries = []
        for mv in chosen:
            entries.append({"level": lvl_of[mv], "move": mv})
            if mv not in reasons_line:
                share = round(score[mv] * 100)
                reasons_line[mv] = why.get(mv) or "learned by similar official Pokemon (%d%% of the weight)" % share
                if why.get(mv):
                    reasons_line[mv] += " (%d%% of the weight)" % share
        entries.sort(key=lambda e: (e["level"], e["move"]))
        top = self.weighted_donors(sid)[0][1]
        self._ensure_types(sid, entries, side, memo, reasons_line, self.ref.all[top])
        inspired = [(n, round(w * 100)) for w, n in self.weighted_donors(sid)[:8]]
        return entries, inspired

    @staticmethod
    def _band(level, start):
        if level <= 1:
            return 0
        if level <= start:
            return 1
        if level <= start + 12:
            return 2
        if level <= start + 25:
            return 3
        return 4

    def _ensure_types(self, sid, entries, side, memo, reasons, donor):
        """Each of our types gets level-up attacks: swap coverage/Normal attacks for moves of a missing type."""
        sp = self.ours[sid]
        pref = self.preferred_types(sid)
        for t in sp["types"] + [t for t in pref if t not in sp["types"]]:
            want = (3 if sp["final"] else 2) + (2 if t in pref else 0)
            have = [e for e in entries if self.M.get(e["move"]) and self.M[e["move"]]["type"] == t
                    and self.M[e["move"]]["category"] != "Status"]
            if len(have) >= want:
                continue
            swappable = [e for e in entries if self.M.get(e["move"]) and e["level"] >= 5
                         and self.M[e["move"]]["category"] != "Status"
                         and self.M[e["move"]]["type"] not in sp["types"] + pref
                         and self.M[e["move"]]["power"] >= 40]
            swappable.sort(key=lambda e: (self.M[e["move"]]["type"] == "Normal", e["level"]))
            for e in swappable[:want - len(have)]:
                key = ("ensure", e["move"], t)
                new = memo.get(key) or self.translate_attack(e["move"], t, side, {x["move"] for x in entries} |
                                                             {v for v in memo.values() if isinstance(v, str)})
                if not new:
                    continue
                memo[key] = new
                reasons.setdefault(new, "%s (%s %d) in place of %s's %s, so its %s type has level-up moves" % (
                    new, t, self.M[new]["power"], donor["name"], e["move"], t))
                e["move"] = new

    def _translate_one(self, sid, move, donor, side, memo, type_count, line_types):
        sp = self.ours[sid]
        m = self.M[move]
        our = sp["types"]
        if "Stellar" in our:       # no own type: spread the attacks over the rainbow, keep plain status moves
            if m["category"] == "Status":
                return (move, "same move as %s" % donor["name"]) if not self.ref.is_signature(move) else (None, "")
            used = set(v for v in memo.values() if isinstance(v, str))
            for t in sorted(RAINBOW, key=lambda t: (type_count[t], RAINBOW.index(t))):
                new = self.translate_attack(move, t, side, used)
                if new:
                    type_count[t] += 1
                    return new, "%s (%s %d) in place of %s's %s: Stellar gets moves of many types" % (
                        new, t, self.M[new]["power"], donor["name"], move)
            return None, ""
        if self.ref.is_signature(move) and move not in self.ref.tms:
            if m["category"] == "Status":
                return None, ""
            t = m["type"] if m["type"] in our else our[0]
            new = self.translate_attack(move, t, side, set(v for v in memo.values() if isinstance(v, str)))
            if new:
                return new, "%s (%s %d) in place of %s's own move %s" % (new, t, self.M[new]["power"],
                                                                         donor["name"], move)
            return None, ""
        if m["type"] in our or m["type"] in line_types:
            if m["category"] != "Status" and side in ("Physical", "Special") and m["category"] != side \
                    and m["power"] >= 60:
                alt = self.translate_attack(move, m["type"], side, set(v for v in memo.values() if isinstance(v, str)))
                if alt and abs(self.M[alt]["power"] - m["power"]) <= 20:
                    return alt, "%s side of %s (instead of %s)" % (side.lower(), m["type"], move)
            return move, "same move as %s" % donor["name"]
        donor_stab = m["type"] in donor["types"]
        signature = self.ref.is_signature(move)
        if m["category"] != "Status" and (donor_stab or signature):
            weights = {t: (0.6 if i == 0 else 0.4) for i, t in enumerate(our)}
            target = min(our, key=lambda t: (type_count[t] + 0.01) / weights[t])
            new = self.translate_attack(move, target, side, set(v for v in memo.values() if isinstance(v, str)))
            if not new and len(our) > 1:
                other = [t for t in our if t != target][0]
                new = self.translate_attack(move, other, side, set(v for v in memo.values() if isinstance(v, str)))
                target = other
            if new:
                type_count[target] += 1
                return new, "%s (%s %d) in place of %s's %s" % (
                    new, self.M[new]["type"], self.M[new]["power"], donor["name"], move)
            return None, ""
        if m["category"] == "Status" and m["type"] in donor["types"] and m["type"] not in ("Normal",):
            new = self.translate_status(move, our, set(v for v in memo.values() if isinstance(v, str)))
            if new:
                return new, "%s in place of %s's %s" % (new, donor["name"], move)
            # keep widely learned status moves (Protect-like), drop type flavour
            if self.ref.line_count.get(move, 0) >= 40 and not any(move in s for s in STATUS_GROUP.values()):
                return move, "same move as %s" % donor["name"]
            return None, ""
        if signature:
            return None, ""
        return move, "same move as %s" % donor["name"]

    # -------------------------------------------------------------- TM / tutor / egg
    def score_list(self, sid, key, donors, candidates):
        sp = self.ours[sid]
        prof = self.profile(sid)
        kind = "final" if sp["final"] else ("base" if sp["stage"] == 0 else "mid")
        tot_w = 0.0
        p_donor = Counter()
        pop = self.weighted_donors(sid) if sp["stats"] else [(math.exp(sc - donors[0][0]), n) for sc, n in donors]
        if key == "egg":
            pop = [(w, n) for w, n in pop if self.ref.all[n]["stage"] == 0] or pop
        for w, name in pop:
            tot_w += w
            for mv in set(self.ref.all[name][key]):
                p_donor[mv] += w
        out = {}
        for mv in candidates:
            m = self.M.get(mv)
            if not m:
                continue
            pd = p_donor[mv] / tot_w if tot_w else 0
            pt = self.ref.p_type(key, mv, sp["types"], kind) if "Stellar" not in sp["types"] else \
                self.ref.p_all(key, mv, kind)
            pa = self.ref.p_all(key, mv, kind)
            score = 0.55 * pd + 0.45 * pt
            if m["type"] in sp["types"] and m["category"] != "Status":
                score += 0.15
            if m["type"] in self.preferred_types(sid) and m["category"] != "Status":
                score += 0.2
            if m["category"] != "Status" and m["type"] not in sp["types"] and m["type"] != "Normal" and pt < 0.08 \
                    and pd < 0.5:
                score -= 0.15
            out[mv] = (score, pd, pt, pa)
        return out

    def build_tm(self, sid, donors):
        sp = self.ours[sid]
        scores = self.score_list(sid, "tm_hm", donors, self.ref.tms)
        chosen = {}
        for mv, (score, pd, pt, pa) in scores.items():
            if not self.body_ok(sid, mv) or mv in NEVER_ADD and mv not in ("Return", "Frustration", "Hidden Power",
                                                                              "Secret Power", "Attract",
                                                                              "Double Team", "Swagger", "Captivate",
                                                                              "Natural Gift", "Snatch", "Embargo",
                                                                              "Recycle", "Psych Up", "Fling"):
                continue
            if mv == "Fly" and "Flying" not in sp["types"] and pd < 0.6:
                continue
            if pa >= 0.8 or score >= 0.45:
                chosen[mv] = "TM: %d%% of similar official Pokemon, %d%% of official %s types" % (
                    round(pd * 100), round(pt * 100), "/".join(sp["types"]))
        return chosen

    def build_tutor(self, sid, donors):
        sp = self.ours[sid]
        scores = self.score_list(sid, "tutor", donors, self.ref.tutor_moves)
        chosen = {}
        starter = "starter" in sp["text"].lower() or any("starter" in self.ours[x]["text"].lower()
                                                         for x in self._line_members(sid))
        for mv, (score, pd, pt, pa) in scores.items():
            places = self.ref.tutor_where.get(mv, [])
            if not places or not self.body_ok(sid, mv):
                continue
            restricted = all(p["restricted"] or (p["species"] or 99) <= 12 for p in places)
            m = self.M[mv]
            if mv in ("Headbutt", "Surf", "Charge"):      # single-species tutor scripts (Surf is HM03 anyway)
                continue
            if mv in ("Blast Burn", "Frenzy Plant", "Hydro Cannon"):
                if starter and sp["final"] and m["type"] in sp["types"]:
                    chosen[mv] = "tutor: the starters' strongest move (%s)" % self._where(mv)
                continue
            if restricted and not (pd >= 0.5 and m["type"] in sp["types"]):
                continue
            if mv in NEVER_ADD:
                continue
            if score >= 0.40:
                chosen[mv] = "tutor (%s): %d%% of similar official Pokemon" % (self._where(mv), round(pd * 100))
        return chosen

    def _where(self, mv):
        places = self.ref.tutor_where.get(mv, [])
        return "; ".join("%s, %s" % (p["where"], p["payment"]) for p in places[:2]) or "no tutor"

    def build_egg(self, sid, donors, line_moves):
        sp = self.ours[sid]
        if sp["stage"] != 0 or sp["line_length"] == 0:
            return {}
        if self.legendary(dict(sp, stats=self.profile(sid)["stats"])):
            return {}
        groups = self.egg_groups(sid)
        gender = sp["data"].get("gender")
        if "Undiscovered" in groups or (gender == "genderless" and "Ditto" not in groups):
            return {}
        partners = set()
        for g in groups:
            partners |= self.ref.egg_group_moves.get(g, set())
        cands = set()
        for s, name in donors:
            cands |= set(self.ref.all[name]["egg"])
        per, totals = self.ref.freq["egg"]
        for t in sp["types"]:
            cands |= {mv for mv, c in per[t]["base"].items() if c >= 3}
        scores = self.score_list(sid, "egg", donors, sorted(cands))
        counts = [len(self.ref.all[n]["egg"]) for s, n in donors if self.ref.all[n]["stage"] == 0]
        want = int(min(10, max(4, statistics.median(counts) if counts else 6)))
        if partners:      # breeding: an egg move must be one a partner of the same egg group learns
            scores = {mv: v for mv, v in scores.items() if mv in partners}
        ranked = sorted(((sc, mv) for mv, (sc, pd, pt, pa) in scores.items()
                         if mv not in line_moves and mv not in NEVER_ADD and self.body_ok(sid, mv)
                         and sc >= 0.2 and not (self.M[mv]["type"] not in sp["types"] + ["Normal"] and pt < 0.1)),
                        reverse=True)
        return {mv: "egg move: %d%% score from similar first stages and official %s first stages%s" % (
            round(sc * 100), "/".join(sp["types"]),
            ("; egg group %s (%s)" % ("/".join(groups), "its own" if sp["data"].get("egg_groups") else
                                       "guessed from its model")) if groups else "")
                for sc, mv in ranked[:want]}

    def egg_groups(self, sid):
        """Its own egg groups, or the line model's first stage's (Origin names, e.g. "Water 1")."""
        sp = self.ours[sid]
        own = [str(g).replace("_", " ").title().replace("Human Like", "Human-Like") for g in
               (sp["data"].get("egg_groups") or [])]
        if own:
            return own
        model = self._line_model.get(sp["root"])
        if model and model in self.ref.all:
            return list(self.ref.all[model].get("egg_groups") or [])
        return []

    def _line_members(self, sid):
        root = self.ours[sid]["root"]
        return sorted({x for p in self.lines.get(root, [[sid]]) for x in p})

    # -------------------------------------------------------------- role and balance
    def full_pool(self, sid, learnset):
        pool = [e["move"] for e in learnset["level_up"]] + learnset["tm_hm"] + learnset["tutor"]
        cur = sid
        while cur:
            pool += self._egg_of_line.get(cur, [])
            cur = self.ours[cur]["parent"]
        return pool

    def precedent(self, sid, predicate):
        prof = self.profile(sid)
        bst = sum(prof["stats"].values())
        leg = self.legendary(dict(self.ours[sid], stats=prof["stats"]))
        off = max(prof["stats"]["attack"], prof["stats"]["sp_attack"])
        hits = []
        for n, o in self.ref.models.items():
            if o["legendary"] and not leg:
                continue
            if abs(o["bst"] - bst) > 50 or abs(max(o["stats"]["attack"], o["stats"]["sp_attack"]) - off) > 20:
                continue
            pool = set(mv for lv, mv in o["level_up"]) | set(o["tm_hm"]) | set(o["tutor"]) | set(o["egg"])
            if predicate(o, pool):
                hits.append(n)
        return hits

    def priority_stab(self, types, pool):
        return [mv for mv in pool if self.M.get(mv) and self.M[mv]["priority"] > 0 and self.M[mv]["power"] >= 40
                and self.M[mv]["type"] in types and mv not in ("Fake Out", "First Impression")]

    def balance(self, sid, learnset, added, reasons, flags):
        """Remove ADDED moves that make a combo with no official precedent; flag existing ones."""
        prof = self.profile(sid)
        sp = self.ours[sid]
        st = prof["stats"]
        off = max(st["attack"], st["sp_attack"])
        abil = set(sp["abilities"])

        def drop(mv, why):
            for key in KEYS:
                if key == "level_up":
                    if any(e["move"] == mv for e in added[key]):
                        added[key] = [e for e in added[key] if e["move"] != mv]
                        learnset[key] = [e for e in learnset[key] if not (e["move"] == mv and e.get("_new"))]
                        flags.append("Not added: %s (%s)" % (mv, why))
                elif mv in added[key]:
                    added[key].remove(mv)
                    learnset[key] = [x for x in learnset[key] if x != mv]
                    flags.append("Not added: %s (%s)" % (mv, why))

        def is_added(mv):
            return any(e["move"] == mv for e in added["level_up"]) or any(mv in added[k] for k in KEYS[1:])

        checked = set()

        def rule(name, present, predicate, candidates, why):
            """present: the combo is in the pool now. Remove an added part, or flag it once."""
            if not present:
                return False
            if self.precedent(sid, predicate):
                return False
            victim = next((m for m in candidates if is_added(m)), None)
            if victim:
                drop(victim, why + ", no official Pokemon of about this strength has that")
                return True
            if name not in checked:
                checked.add(name)
                flags.append("Check (designers' own moves/abilities): %s - no official Pokemon of about this "
                             "strength has that" % why)
            return False

        for _ in range(6):
            pool = set(self.full_pool(sid, learnset))
            setups = [mv for mv in pool if mv in STRONG_SETUP and mv not in ("Iron Defense", "Cosmic Power",
                                                                              "Acid Armor", "Amnesia", "Cotton Guard",
                                                                              "Stockpile", "Curse")]
            prio = self.priority_stab(sp["types"], pool)
            abil_of = lambda o: set(o["abilities"] + [o.get("hidden")])
            def boosts_cat(mv):
                b = (self.M.get(mv) or {}).get("boosts") or {}
                return ({"Physical"} if b.get("atk", 0) > 0 else set()) | ({"Special"} if b.get("spa", 0) > 0 else set())
            prio_cats = {self.M[mv]["category"] for mv in prio}
            setups_p = [mv for mv in setups if boosts_cat(mv) & prio_cats]
            if rule("prio+setup", setups_p and prio and off >= 110,
                    lambda o, p: any(x in p for x in setups_p) and self.priority_stab(o["types"], p),
                    setups_p + prio, "same-type priority (%s) + setup (%s) on a strong attacker" % (
                        prio[0] if prio else "", setups[0] if setups else "")):
                continue
            if rule("speedboost", "Speed Boost" in abil and setups,
                    lambda o, p: "Speed Boost" in abil_of(o) and any(x in p for x in setups),
                    setups, "Speed Boost + a setup move (%s)" % (setups[0] if setups else "")):
                continue
            if rule("huge", abil & {"Huge Power", "Pure Power"} and prio,
                    lambda o, p: abil_of(o) & {"Huge Power", "Pure Power"} and self.priority_stab(o["types"], p),
                    prio, "Huge Power + same-type priority"):
                continue
            recov = [mv for mv in pool if mv in mp.RECOVERY]
            bulky_setup = [mv for mv in setups if mv in ("Calm Mind", "Bulk Up", "Coil", "Dragon Dance",
                                                         "Quiver Dance", "Swords Dance", "Nasty Plot")]
            if rule("recov+setup", recov and bulky_setup and prof["info"]["bulk"] >= 1.15,
                    lambda o, p: any(r in p for r in mp.RECOVERY) and any(b in p for b in bulky_setup),
                    bulky_setup + recov, "recovery (%s) + setup (%s) on a bulky Pokemon" % (
                        recov[0] if recov else "", bulky_setup[0] if bulky_setup else "")):
                continue
            rare = [mv for mv in pool if mv in ("Shell Smash", "Quiver Dance", "Belly Drum", "Geomancy",
                                                "Tail Glow", "Victory Dance", "Clangorous Soul", "No Retreat",
                                                "Spore", "Extreme Speed", "Dark Void", "Shift Gear")]
            for mv in rare:
                rule("rare:" + mv, True, lambda o, p, mv=mv: mv in p, [mv], "%s on a Pokemon this strong" % mv)
            if "Serene Grace" in abil:
                for mv in [m for m in pool if m in ("Air Slash", "Iron Head", "Headbutt", "Rock Slide",
                                                    "Zen Headbutt", "Bite", "Stomp", "Astonish")]:
                    if is_added(mv):
                        drop(mv, "Serene Grace + flinch move")
            if "Contrary" in abil:
                for mv in [m for m in pool if (self.M.get(m) or {}).get("self_boosts")]:
                    if is_added(mv):
                        drop(mv, "Contrary turns its stat drops into boosts")
            if "Simple" in abil:
                for mv in setups:
                    if is_added(mv):
                        drop(mv, "Simple doubles setup")
            break
        for a in abil & {"Moody", "Shadow Tag", "Arena Trap"}:
            flags.append("Check: %s is banned in most competitive rules" % a)
        if abil & {"Drizzle"} and abil & {"Swift Swim"} or abil & {"Drought"} and abil & {"Chlorophyll"}:
            flags.append("Check: weather setter + weather speed ability on one Pokemon (doubles its Speed alone)")

    def power_check(self, sid, sample):
        """Compare the example set's damage against official Pokemon of about the same total."""
        prof = self.profile(sid)
        bst = sum(prof["stats"].values())
        leg = self.legendary(dict(self.ours[sid], stats=prof["stats"]))
        mine = self._set_power(prof, sample)
        theirs = []
        for n, o in self.ref.models.items():
            if not o["final"] or o["legendary"] != leg or abs(o["bst"] - bst) > 40:
                continue
            omon = {"types": o["types"], "stats": o["stats"], "abilities": o["abilities"] + [o.get("hidden")]}
            pool = [mv for lv, mv in o["level_up"]] + o["tm_hm"] + o["tutor"] + o["egg"]
            osample = self._pick_cached(n, omon, pool)
            theirs.append(self._set_power(omon, osample))
        if len(theirs) < 5:
            return None
        theirs.sort()
        rank = sum(1 for t in theirs if t < mine) / len(theirs)
        return {"percentile": round(rank * 100), "compared_with": len(theirs), "max": round(theirs[-1]),
                "mine": round(mine)}

    _pick_memo = {}

    def _pick_cached(self, name, mon, pool):
        if name not in self._pick_memo:
            self._pick_memo[name] = mp.pick(mon, 100, pool, self.M)["moves"]
        return self._pick_memo[name]

    def _set_power(self, mon, moves):
        vals = sorted((mp.attack_value(mon, m, self.M) for m in moves), reverse=True)
        top = sum(vals[:2])
        boost = 1.0
        for m in moves:
            b = (self.M.get(m) or {}).get("boosts") or {}
            if (self.M.get(m) or {}).get("target") == "self" and (b.get("atk", 0) + b.get("spa", 0)) >= 2:
                boost = max(boost, 1.5)
            elif (self.M.get(m) or {}).get("target") == "self" and (b.get("atk", 0) + b.get("spa", 0)) >= 1:
                boost = max(boost, 1.3 if b.get("spe") else 1.2)
        return top * boost * (1 + max(0, mon["stats"]["speed"] - 80) / 250)

    def _fits(self, sid, mv, donors):
        """Could this Pokemon plausibly learn mv? Its type, Normal, a field/weather move, or similar ones learn it."""
        m = self.M.get(mv)
        sp = self.ours[sid]
        if not m or mv in NEVER_ADD or not self.body_ok(sid, mv):
            return False
        if m["type"] in sp["types"] + self.preferred_types(sid) or m["type"] == "Normal":
            return True
        if m["category"] == "Status" and (m.get("weather") or m.get("terrain") or mv in mp.UTILITY
                                          or mv in mp.STATUS_INFLICT or mv in ("Flash", "Smokescreen", "Haze")):
            return True
        kind = "final" if sp["final"] else ("base" if sp["stage"] == 0 else "mid")
        if any(self.ref.p_type(k, mv, sp["types"], kind) >= 0.1 for k in ("tm_hm", "tutor", "level_up")):
            return True
        return any(mv in self.ref.all[n]["tm_hm"] + self.ref.all[n]["tutor"] + [x for l, x in self.ref.all[n]["level_up"]]
                   for s, n in donors)

    def apply_design(self, sid, learnset, added, reasons, flags):
        """Changes from reading the design text (proposals/design_review.json): drop added moves that clash with
        the design, add moves the design asks for. Existing moves are never touched; names and lists are checked."""
        if not hasattr(self, "_design"):
            try:
                self._design = json.loads(DESIGN_REVIEW.read_text(encoding="utf-8"))
            except Exception:
                self._design = {}
        d = self._design.get(sid)
        if not d:
            return None
        why = d.get("why") or {}
        existing = self.ours[sid]["learnset"]
        have_existing = {e.get("move") if isinstance(e, dict) else e for k in KEYS for e in existing[k]}
        for mv in d.get("drop") or []:
            if mv in have_existing:
                continue
            hit = False
            if any(e["move"] == mv for e in added["level_up"]):
                added["level_up"] = [e for e in added["level_up"] if e["move"] != mv]
                learnset["level_up"] = [e for e in learnset["level_up"] if not (e["move"] == mv and e.get("_new"))]
                hit = True
            for k in KEYS[1:]:
                if mv in added[k]:
                    added[k].remove(mv)
                    learnset[k] = [x for x in learnset[k] if x != mv]
                    hit = True
            if hit:
                flags.append("Left out for the design: %s (%s)" % (mv, why.get(mv, "does not fit the design")))
        tms, tutors = set(self.ref.tms), set(self.ref.tutor_where)
        for k in KEYS:
            for item in (d.get("add") or {}).get(k) or []:
                mv = item["move"] if isinstance(item, dict) else item
                if mv not in self.M or mv in NEVER_ADD or mv in set(self.full_pool(sid, learnset)):
                    continue
                if (k == "tm_hm" and mv not in tms) or (k == "tutor" and mv not in tutors) or \
                        (k == "egg" and self.ours[sid]["stage"] != 0):
                    continue
                text = "design: %s" % why.get(mv, "fits the design")
                if k == "level_up":
                    lv = item.get("level") if isinstance(item, dict) and isinstance(item.get("level"), int) else None
                    self._add(sid, learnset, added, mv, reasons, text, level=lv if lv is not None else None)
                else:
                    learnset[k].append(mv)
                    added[k].append(mv)
                    reasons[mv] = text
        return d.get("note")

    def ability_tools(self, sid, learnset, added, reasons, donors):
        """Moves that make its abilities work (Strong Jaw -> bite moves, Drought -> Sunny Day/Solar Beam ...)."""
        sp = self.ours[sid]
        own = sp["types"] + ["Normal"] + self.preferred_types(sid)
        for ab in sp["abilities"]:
            moves, most = ABILITY_SYNERGY.get(ab, ([], 0))
            moves = sorted(moves, key=lambda mv: (self.M.get(mv, {}).get("type") not in own, moves.index(mv)))
            if ab in ("Technician", "Skill Link", "Reckless", "Sniper", "Super Luck"):
                moves = [mv for mv in moves if self.M.get(mv, {}).get("type") in own]
            pool = set(self.full_pool(sid, learnset))
            have = sum(1 for mv in moves if mv in pool)
            for mv in moves:
                if have >= most:
                    break
                if mv in pool:
                    continue
                strict = ab in ("Strong Jaw", "Iron Fist", "Sharpness", "Mega Launcher", "Prankster")
                if (strict and self.M.get(mv) and self.M[mv]["category"] != "Status") or self._fits(sid, mv, donors):
                    if self._add(sid, learnset, added, mv, reasons, "goes with its ability %s" % ab, prefer_tm=True):
                        have += 1

    def flavour_moves(self, sid, learnset, added, reasons, donors):
        """A move or two that shows what the design is (a glowing lamp -> Flash, a beak -> Peck ...)."""
        sp = self.ours[sid]
        d = sp["design"]
        text = " ".join(str(d.get(k) or "") for k in ("look", "concept", "notes", "wishes", "body_shape")) + " " + \
            str(sp["data"].get("description") or "")
        added_n = 0
        for pattern, moves in FLAVOUR:
            m = re.search(pattern, text, re.I)
            if not m or added_n >= 2:
                continue
            pool = set(self.full_pool(sid, learnset))
            if any(mv in pool for mv in moves):
                continue
            if moves == ["Flash"] and re.search(r"glowing (red |yellow |blue |white )?eyes", text, re.I) and \
                    not re.search(r"lamp|lantern|bulb|light", text, re.I):
                continue
            for mv in moves:
                m_ = self.M.get(mv)
                if not m_ or not (mv in FLAVOUR_ANY_TYPE or m_["type"] in sp["types"] + ["Normal"]
                                  + self.preferred_types(sid)) or not self.body_ok(sid, mv):
                    continue
                if self._add(
                        sid, learnset, added, mv, reasons, 'fits the design ("%s" in its look/notes)' % m.group(0),
                        prefer_tm=True):
                    added_n += 1
                    break

        w = sp["data"].get("weight_kg")
        if isinstance(w, (int, float)) and w >= 150 and "Heavy Slam" not in set(self.full_pool(sid, learnset)) \
                and ("Steel" in sp["types"] or self.profile(sid)["info"]["bulk"] >= 1.1):
            self._add(sid, learnset, added, "Heavy Slam", reasons, "it weighs %g kg (Heavy Slam hits harder the "
                      "heavier the user)" % w, prefer_tm=True)

    def role_tools(self, sid, learnset, added, reasons, donors):
        """Make sure the role has its tools (strong same-type moves, setup for sweepers, recovery for walls)."""
        sp = self.ours[sid]
        prof = self.profile(sid)
        info = prof["info"]
        role = info["role"].lower()
        huge = 2 if set(sp["abilities"]) & {"Huge Power", "Pure Power"} else 1
        side = "Physical" if prof["stats"]["attack"] * huge >= prof["stats"]["sp_attack"] else "Special"
        pool = set(self.full_pool(sid, learnset))
        notes = []
        for t in sp["types"]:
            strong = [mv for mv in pool if self.M.get(mv) and self.M[mv]["type"] == t and self.M[mv]["power"] >= 75
                      and self.M[mv]["category"] != "Status"]
            if strong:
                continue
            cats = [side] if info["side"] != "mixed" else ["Physical", "Special"]
            cands = []
            for cat in cats:
                for mv, cnt in self.ref.type_pool.get(t, {}).get(cat, {}).items():
                    m = self.M[mv]
                    if 75 <= m["power"] <= 100 and not m["recharge"] and not m["charge"] and mv not in NEVER_ADD \
                            and not m["self_ko"] and m["accuracy"] >= 85:
                        cands.append((cnt + (5 if mv in self.ref.tms else 0), mv))
            if cands:
                mv = max(cands)[1]
                self._add(sid, learnset, added, mv, reasons, "role: a strong %s move (it had none of 75+ power)" % t,
                          prefer_tm=True)
                notes.append(mv)
        donor_pools = []
        for s, n in donors:
            o = self.ref.all[n]
            donor_pools.append(set(mv for lv, mv in o["level_up"]) | set(o["tm_hm"]) | set(o["tutor"]))
        pool = set(self.full_pool(sid, learnset))
        if ("attacker" in role or "sweeper" in role) and "trick room" not in role:
            setups = SETUP_ATK if side == "Physical" else SETUP_SPA
            if info["side"] == "mixed":
                setups = ["Nasty Plot", "Swords Dance", "Work Up", "Calm Mind", "Bulk Up"]
            if not any(s in pool for s in setups + ["Dragon Dance", "Quiver Dance", "Shell Smash", "Coil",
                                                     "Shift Gear", "Bulk Up", "Calm Mind"]):
                c = Counter(s for p in donor_pools for s in setups if s in p)
                if c and c.most_common(1)[0][1] >= max(2, 0.35 * len(donor_pools)):
                    mv = c.most_common(1)[0][0]
                    self._add(sid, learnset, added, mv, reasons, "role: setup move for an attacker (%d of %d similar "
                              "official Pokemon have it)" % (c[mv], len(donor_pools)), prefer_tm=True)
        if "attacker" in role or "wallbreaker" in role:
            cover = {self.M[mv]["type"] for mv in pool if self.M.get(mv) and self.M[mv]["power"] >= 70
                     and self.M[mv]["category"] != "Status" and self.M[mv]["type"] not in sp["types"]}
            if len(cover) < 2:
                c = Counter()
                for p in donor_pools:
                    for mv in p:
                        m = self.M.get(mv)
                        if m and m["category"] == (side if info["side"] != "mixed" else m["category"]) \
                                and m["power"] >= 70 and m["type"] not in sp["types"] and m["type"] not in cover \
                                and mv not in NEVER_ADD and not m["recharge"] and not m["self_ko"] \
                                and (mv in self.ref.tms or mv in self.ref.tutor_where):
                            c[mv] += 1
                for mv, n in c.most_common():
                    if len(cover) >= 2:
                        break
                    if self.M[mv]["type"] in cover or n < 2:
                        continue
                    if self._add(sid, learnset, added, mv, reasons, "role: coverage for an attacker (%d of %d similar "
                                 "official Pokemon have it)" % (n, len(donor_pools)), prefer_tm=True):
                        cover.add(self.M[mv]["type"])
            pool = set(self.full_pool(sid, learnset))
        if "wall" in role or "support" in role:
            if not any(r in pool for r in mp.RECOVERY):
                c = Counter(r for p in donor_pools for r in mp.RECOVERY if r in p)
                if c and c.most_common(1)[0][1] >= max(2, 0.35 * len(donor_pools)):
                    mv = c.most_common(1)[0][0]
                    self._add(sid, learnset, added, mv, reasons, "role: recovery for a %s (%d of %d similar official "
                              "Pokemon have it)" % (info["role"].lower(), c[mv], len(donor_pools)))
        tr_share = sum(1 for p in donor_pools if "Trick Room" in p) / max(1, len(donor_pools))
        if "Trick Room" not in pool and ("trick room" in sp["text"].lower() or ("trick room" in role and
                                                                               tr_share >= 0.35)):
            self._add(sid, learnset, added, "Trick Room", reasons, "role: Trick Room attacker (%s)" % (
                "the designers' notes say so" if "trick room" in sp["text"].lower() else
                "%d%% of similar official Pokemon have it" % round(tr_share * 100)), prefer_tm=True)
        return notes

    def _add(self, sid, learnset, added, mv, reasons, why, prefer_tm=False, level=None):
        if mv in set(self.full_pool(sid, learnset)) or mv not in self.M and mv not in self.custom_moves:
            return False
        if prefer_tm and mv in self.ref.tms:
            learnset["tm_hm"].append(mv)
            added["tm_hm"].append(mv)
        elif prefer_tm and mv in self.ref.tutor_where and not mv in ("Blast Burn", "Frenzy Plant", "Hydro Cannon"):
            learnset["tutor"].append(mv)
            added["tutor"].append(mv)
        else:
            if level is None:
                tl = self.ref.typical_level.get(mv, 40)
                bst = sum(self.profile(sid)["stats"].values())
                level = int(min(75, max(10, tl * bst / 500)))
                pw = (self.M.get(mv) or {}).get("power") or 0
                if pw >= 80:
                    level = max(level, min(60, int(pw * 0.4)))     # strong moves come later
                parent_evo = evo_level(self.ours, sid) if self.ours[sid]["parent"] else None
                if parent_evo and level <= parent_evo:
                    level = parent_evo + 4
            e = {"level": level, "move": mv, "_new": True}
            learnset["level_up"].append(e)
            added["level_up"].append({"level": level, "move": mv})
            learnset["level_up"].sort(key=lambda x: x["level"])
        reasons[mv] = why
        return True

    # -------------------------------------------------------------- whole run
    def propose_line(self, root):
        paths = self.lines[root]
        results = {}
        memo = {}
        reasons_line = {}
        self._egg_of_line = getattr(self, "_egg_of_line", {})
        level_up = {}
        donor_info = {}
        for path in sorted(paths, key=len, reverse=True):
            score, dpath = self.line_donor(path)
            built = self.build_level_up(path, dpath, memo, reasons_line)
            for sid, entries in built.items():
                if sid not in level_up:
                    level_up[sid] = entries
                    donor_info[sid] = {"line_model": " > ".join(dpath), "line_score": round(score, 2),
                                       "stage_model": dpath[path.index(sid)]}
            self._line_model.setdefault(root, dpath[0])
        members = [x for p in sorted(paths, key=len, reverse=True) for x in p]
        members = list(dict.fromkeys(members))
        for sid in members:          # level-up from ALL similar official Pokemon, weighted by how similar
            if self.ours[sid]["types"] and self.ours[sid]["stats"]:
                entries, inspired = self.build_level_up_ensemble(sid, reasons_line)
                if entries:
                    level_up[sid] = entries
                    donor_info.setdefault(sid, {})["inspired"] = inspired
        tm_line, tutor_line = {}, {}
        for sid in sorted(members, key=lambda x: self.ours[x]["stage"]):
            sp = self.ours[sid]
            prof = self.profile(sid)
            donors, kw, leg = self.donors_for(sid)
            existing = {k: list(sp["learnset"][k]) for k in KEYS}
            reasons = {}
            added = {k: [] for k in KEYS}
            flags = []
            if not sp["types"]:
                results[sid] = self._skeleton(sid, "has no types yet: give it types first")
                continue
            if not sp["stats"]:
                results[sid] = self._skeleton(sid, "waits for its base stats (moves are proposed once they are in)")
                continue
            if "Stellar" in sp["types"]:
                flags.append("Stellar: no same-type bonus, so its moves are spread over many types. Origin HG has "
                             "no Stellar type yet (its old ??? type slot is used by Fairy): the game export needs new "
                             "code for it, and the website's type list does not have it")
            # level-up: existing first, then the model's list
            have = {e.get("move") for e in existing["level_up"] if isinstance(e, dict)}
            lu = [dict(e) for e in existing["level_up"] if isinstance(e, dict)]
            proposal = level_up.get(sid, [])
            cap = max(len(proposal) + 2, len(lu))
            own = [dict(e) for e in existing["level_up"] if isinstance(e, dict) and self.M.get(e.get("move"))]
            own_levels = {e["level"] for e in own if isinstance(e.get("level"), int) and e["level"] > 1}
            for e in proposal:
                if e["move"] in have:
                    continue
                if len(lu) >= cap:
                    break
                twin = self._same_job(e["move"], own, e["level"])
                if twin:
                    reasons_skip = "%s does the same job as your own %s" % (e["move"], twin)
                    self._skipped.setdefault(sid, []).append(reasons_skip)
                    continue
                e = dict(e)
                e["level"] = self._fit_level(e, own, own_levels)
                have.add(e["move"])
                lu.append(dict(e, _new=True))
                added["level_up"].append(dict(e))
                reasons[e["move"]] = reasons_line.get(e["move"], "from %s" % donor_info.get(sid, {}).get(
                    "stage_model", "the model"))
            # earlier stage moves an evolved form keeps (official games keep them)
            par = sp["parent"]
            if par and par in results:
                limit = evo_level(self.ours, sid) or self._evo_used.get(sid) or 1
                for e in results[par]["learnset"]["level_up"]:
                    if e["move"] in have or e["level"] == 0 or not isinstance(e.get("level"), int):
                        continue
                    later = e["level"] > limit
                    if later and self._same_job(e["move"], [x for x in lu if isinstance(x, dict)], e["level"]):
                        continue
                    have.add(e["move"])
                    lv = min(100, e["level"] + 3) if later else e["level"]   # learned a bit later after evolving
                    lu.append({"level": lv, "move": e["move"], "_new": True})
                    added["level_up"].append({"level": lv, "move": e["move"]})
                    reasons[e["move"]] = "learned by %s %s" % (self.ours[par]["name"], "too, a bit later" if later
                                                               else "before it evolves")
            lu.sort(key=lambda e: (e["level"], e["move"]))
            learnset = {"level_up": lu, "tm_hm": list(existing["tm_hm"]), "tutor": list(existing["tutor"]),
                        "egg": list(existing["egg"])}
            # TMs and tutors: the line keeps what earlier stages had
            tms = self.build_tm(sid, donors)
            for mv in tm_line.get(par, {}):
                tms.setdefault(mv, "TM: %s can learn it too" % self.ours[par]["name"])
            for mv, why in tms.items():
                if mv not in learnset["tm_hm"] and mv not in [e["move"] for e in lu if e["level"] <= 1 and False]:
                    learnset["tm_hm"].append(mv)
                    added["tm_hm"].append(mv)
                    reasons[mv] = why
            tm_line[sid] = tms
            tut = self.build_tutor(sid, donors)
            for mv in tutor_line.get(par, {}):
                tut.setdefault(mv, "tutor (%s): %s can learn it too" % (self._where(mv), self.ours[par]["name"]))
            for mv, why in tut.items():
                if mv not in learnset["tutor"] and mv not in learnset["tm_hm"]:
                    learnset["tutor"].append(mv)
                    added["tutor"].append(mv)
                    reasons[mv] = why
            tutor_line[sid] = tut
            line_moves = set(e["move"] for x in members for e in level_up.get(x, [])) | set(learnset["tm_hm"])
            egg = self.build_egg(sid, donors, line_moves | {e["move"] for e in lu})
            for mv, why in egg.items():
                if mv not in learnset["egg"]:
                    learnset["egg"].append(mv)
                    added["egg"].append(mv)
                    reasons[mv] = why
            self._egg_of_line[sid] = list(learnset["egg"])
            # designers' moves
            wished, wanted = self.wished_moves(sid)
            for mv in wished:
                if mv in set(self.full_pool(sid, learnset)):
                    continue
                if mv in self.custom_moves:
                    lvl = max([e["level"] for e in lu] + [30]) if sp["final"] else None
                    self._add(sid, learnset, added, mv, reasons, "designer's signature move (data/custom_moves.yaml)",
                              level=lvl)
                else:
                    self._add(sid, learnset, added, mv, reasons, "named by the designers (notes/wishes)",
                              prefer_tm=True)
            for later in self._later(sid):
                pass
            wish_text = str(sp["design"].get("wishes") or "")
            for ab in self.ref_abilities:
                if len(ab) > 3 and re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(ab.lower()), wish_text.lower()) \
                        and ab not in sp["abilities"]:
                    flags.append("The wishes name the ability %s, but it is not one of its abilities yet" % ab)
            if wanted:
                flags.append("New move(s) from the concept card not in the game yet: %s - describe them under "
                             "New moves on the website to add them" % ", ".join(wanted))
            self.ability_tools(sid, learnset, added, reasons, donors)
            self.flavour_moves(sid, learnset, added, reasons, donors)
            if sp["final"]:
                self.role_tools(sid, learnset, added, reasons, donors)
            for form in sp["data"].get("forms") or []:
                if isinstance(form, dict) and form.get("changes") == "battle":
                    flags.append("Has a battle form (%s): check that the moves also fit that form" % (
                        form.get("name") or "unnamed"))
            design_note = self.apply_design(sid, learnset, added, reasons, flags)
            self.balance(sid, learnset, added, reasons, flags)
            for key in ("tm_hm",):
                bad = [mv for mv in existing[key] if mv not in self.ref.tms]
                if bad:
                    flags.append("Already in the file but not a TM/HM in Origin HG: %s" % ", ".join(bad))
            bad = [mv for mv in existing["tutor"] if mv not in self.ref.tutor_where]
            if bad:
                flags.append("Already in the file but no Origin HG tutor teaches it: %s" % ", ".join(bad))
            unknown = [e.get("move") for e in existing["level_up"] if isinstance(e, dict)
                       and e.get("move") not in self.M and e.get("move") not in self.custom_moves]
            if unknown:
                flags.append("Not a move in the game (spelling?): %s" % ", ".join(map(str, unknown)))
            at1 = [e["move"] for e in existing["level_up"] if isinstance(e, dict) and e.get("level") == 1]
            if len(at1) >= 5:
                flags.append("%d of its own moves are all at level 1 (%s): fine as ideas, but you may want to "
                             "spread them over the levels" % (len(at1), ", ".join(at1)))
            if prof["estimated"]:
                flags.append("It has no base stats yet: the role and moves use guessed stats (%s)" %
                             "/".join(str(prof["stats"][k]) for k in STATS))
            if sp["guessed_parent"]:
                flags.append("Evolves from %s? Not written in the files; guessed from the dex order" %
                             self.ours[sp["parent"]]["name"])
            for e in learnset["level_up"]:
                e.pop("_new", None)
            levels = sorted({e["level"] for e in learnset["level_up"] if isinstance(e.get("level"), int)
                             and e["level"] > 1})
            enter = evo_level(self.ours, sid) if sp["parent"] else None
            if enter and not [lv for lv in levels if lv > enter]:
                flags.append("Learns no new level-up moves after it evolves (level %d)" % enter)
            gaps = [(b - a, a, b) for a, b in zip([1] + levels, levels) if a < 50]
            if gaps and max(gaps)[0] > 16:
                g = max(gaps)
                flags.append("Long gap with no new level-up moves: level %d to %d" % (g[1], g[2]))
            res = {
                "name": sp["name"], "dex": sp["dex"], "types": sp["types"], "stage": sp["stage"],
                "line": [self.ours[x]["name"] for x in members], "root": root,
                "final": sp["final"], "evolves_from": self.ours[par]["name"] if par else None,
                "evolves_at": evo_level(self.ours, sid),
                "stats": prof["stats"], "stats_estimated": prof["estimated"],
                "role": prof["info"]["role"], "role_info": prof["info"],
                "models": {"inspired": donor_info.get(sid, {}).get("inspired") or [],
                           "line": donor_info.get(sid, {}).get("line_model"),
                           "stage": donor_info.get(sid, {}).get("stage_model"),
                           "similar": [n for s, n in donors[:6]], "look_words": sorted(
                               self.ref.all[r]["name"] for r in kw)[:8]},
                "existing_counts": {k: len(existing[k]) for k in KEYS},
                "learnset": learnset, "added": added,
                "reasons": {mv: reasons[mv] for mv in reasons if self._in_added(added, mv)},
                "tutor_places": {mv: [{"where": p["where"], "payment": p["payment"]}
                                      for p in self.ref.tutor_where.get(mv, [])] for mv in learnset["tutor"]},
                "flags": flags, "claude_fill": bool(sp["design"].get("claude_fill")), "design_note": design_note,
                "skipped_for_own_moves": self._skipped.get(sid, []),
                "wishes": sp["design"].get("wishes"),
            }
            if sp["final"]:
                pool = self.full_pool(sid, learnset)
                sample = mp.pick(prof, 100, pool, self.M, role=prof["info"]["role"])
                res["example_set"] = sample["moves"]
                res["power"] = self.power_check(sid, sample["moves"])
                if res["power"] and res["power"]["percentile"] >= 97 and res["power"]["mine"] > res["power"]["max"]:
                    flags.append("Strong: its example set hits harder than every official Pokemon of about the same "
                                 "total (%s)" % res["power"])
                if res["power"] and res["power"]["percentile"] <= 10 and "attacker" in res["role"].lower():
                    flags.append("Weak for an attacker: its best set is in the bottom %d%% of official Pokemon of "
                                 "about the same total" % max(1, res["power"]["percentile"]))
            results[sid] = res
        return results

    def _later(self, sid):
        return self.ours[sid]["children"]

    @staticmethod
    def _in_added(added, mv):
        return any(e["move"] == mv for e in added["level_up"]) or any(mv in added[k] for k in KEYS[1:])

    def _skeleton(self, sid, why):
        sp = self.ours[sid]
        return {"name": sp["name"], "dex": sp["dex"], "types": sp["types"], "stage": sp["stage"], "line": [sp["name"]],
                "root": sp["root"], "final": sp["final"], "skipped": why, "learnset": sp["learnset"],
                "added": {k: [] for k in KEYS}, "reasons": {}, "flags": [why], "role": None,
                "claude_fill": bool(sp["design"].get("claude_fill"))}


# --------------------------------------------------------------------------------------------- output

def write_markdown(result):
    lines = ["# Moveset proposals", "",
             "Generated by `scripts/moveset_fill.py propose` on %s. Nothing here is in the species files yet: "
             "`apply` adds it after the group said yes. How it decides: [docs/MOVESETS.md](../docs/MOVESETS.md)." %
             result["generated"], ""]
    by_root = defaultdict(list)
    for sid, r in result["species"].items():
        by_root[r["root"]].append((r.get("stage", 0), r.get("dex") or 0, sid, r))
    for root in sorted(by_root, key=lambda x: min(t[1] for t in by_root[x])):
        members = sorted(by_root[root])
        lines.append("## " + " > ".join(r["name"] for s, d, sid, r in members))
        lines.append("")
        for s, d, sid, r in members:
            if r.get("skipped"):
                lines.append("### %s - skipped: %s" % (r["name"], r["skipped"]))
                continue
            head = "### %s (%s)%s" % (r["name"], "/".join(r["types"]), (" - role: **%s**" % r["role"]) if r["final"]
                                      else "")
            lines.append(head)
            m = r["models"]
            lines.append("Modelled on %s (line %s); similar: %s." % (m["stage"], m["line"], ", ".join(m["similar"])))
            for key, label in (("level_up", "Level-up"), ("tm_hm", "TM/HM"), ("tutor", "Tutor"), ("egg", "Egg")):
                add = r["added"][key]
                if key == "level_up":
                    txt = ", ".join("%s %s" % ("Evo" if e["level"] == 0 else "Lv%d" % e["level"], e["move"])
                                    for e in sorted(add, key=lambda e: e["level"]))
                else:
                    txt = ", ".join(add)
                lines.append("- %s: had %d, adds %d%s" % (label, r["existing_counts"][key], len(add),
                                                          (": " + txt) if txt else ""))
            if r.get("example_set"):
                lines.append("- Example set: %s" % " / ".join(r["example_set"]))
            for f in r["flags"]:
                lines.append("- Note: %s" % f)
            lines.append("")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def use_data_dir(path):
    """Read and write species from another checkout's data folder (e.g. a worktree of main)."""
    global DATA_DIR
    if path:
        from pathlib import Path
        DATA_DIR = Path(path).resolve()
        dexlib.SPECIES_DIR = DATA_DIR / "species"


def cmd_propose(args):
    use_data_dir(args.data)
    data = moveset_data.load()
    ref = Reference(data)
    ours = load_ours(exclude_claude=args.fresh)
    lines = build_lines(ours)
    prop = Proposer(ours, lines, ref)
    roots = list(lines)
    if args.species:
        roots = sorted({ours[s]["root"] for s in args.species})
    out = {"generated": datetime.date.today().isoformat(), "species": {}}
    if args.species and OUT_JSON.exists():
        out = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        out["generated"] = datetime.date.today().isoformat()
    import subprocess
    try:
        commit = subprocess.run(["git", "-C", str(DATA_DIR), "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True).stdout.strip()
    except Exception:
        commit = ""
    out["data_dir"], out["data_commit"] = str(DATA_DIR), commit
    out["fresh"] = bool(args.fresh)
    for root in roots:
        out["species"].update(prop.propose_line(root))
    OUT_DIR.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_markdown(out)
    n_add = sum(len(r["added"][k]) for r in out["species"].values() for k in KEYS)
    print("%d species in %d lines, %d moves proposed -> %s, %s" % (
        len(out["species"]), len({r["root"] for r in out["species"].values()}), n_add,
        OUT_JSON.relative_to(ROOT), OUT_MD.relative_to(ROOT)))


SUGGESTIONS = ROOT / "site" / "moveset_suggestions.json"


def cmd_suggest(args):
    """Fresh suggestions for every species, for the website's "Moveset suggestions" button (site/...json).
    "fill" = what the current moves lack; "fresh" = a new proposal for the part Claude added before (the
    designers' own moves stay). The file only changes when a suggestion changes."""
    use_data_dir(args.data)
    data = moveset_data.load()
    ref = Reference(data)

    def run(exclude):
        ours = load_ours(exclude_claude=exclude)
        lines = build_lines(ours)
        prop = Proposer(ours, lines, ref)
        res = {}
        for root in lines:
            res.update(prop.propose_line(root))
        return res, ours
    fill, ours = run(False)
    fresh, _ = run(True)
    claude = load_claude_moves()

    def compact(r):
        why = r.get("reasons") or {}
        a = r["added"]
        out = {"level_up": [[e["level"], e["move"], why.get(e["move"], "")] for e in
                            sorted(a["level_up"], key=lambda e: (e["level"], e["move"]))]}
        for k in KEYS[1:]:
            out[k] = [[m, why.get(m, "")] for m in a[k]]
        return out
    species = {}
    for sid, r in sorted(fill.items()):
        cur = ours[sid]["learnset"]
        have = {k: {(e.get("move") if isinstance(e, dict) else e) for e in cur[k]} for k in KEYS}
        cm = claude.get(sid, {})
        still = {"level_up": [m for lv, m in cm.get("level_up", []) if m in have["level_up"]]}
        for k in KEYS[1:]:
            still[k] = [m for m in cm.get(k, []) if m in have[k]]
        entry = {"name": r["name"], "skipped": r.get("skipped"), "role": r.get("role"),
                 "example": r.get("example_set") or [], "inspired": (r.get("models") or {}).get("inspired") or [],
                 "flags": r.get("flags") or [], "claude": still}
        if not r.get("skipped"):
            entry["fill"] = compact(r)
            fr = fresh.get(sid)
            if fr and not fr.get("skipped"):
                entry["fresh"] = compact(fr)
                entry["fresh_example"] = fr.get("example_set") or []
        species[sid] = entry
    body = {"species": species}
    old = None
    if SUGGESTIONS.exists():
        try:
            old = json.loads(SUGGESTIONS.read_text(encoding="utf-8"))
        except Exception:
            old = None
    if old and old.get("species") == json.loads(json.dumps(species, ensure_ascii=False)):
        print("moveset suggestions unchanged")
        return
    body["generated"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    SUGGESTIONS.write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print("moveset suggestions for %d species -> %s" % (len(species), SUGGESTIONS.relative_to(ROOT)))


def cmd_show(args):
    out = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    for sid in args.species:
        r = out["species"][sid]
        print(json.dumps({k: v for k, v in r.items() if k not in ("learnset",)}, ensure_ascii=False, indent=1))


def cmd_apply(args):
    use_data_dir(args.data)
    out = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    if out.get("data_dir") and out["data_dir"] != str(DATA_DIR):
        raise SystemExit("The proposals were made from %s; pass --data %s (or propose again from %s)" % (
            out["data_dir"], out["data_dir"], DATA_DIR))
    if args.all:
        targets = list(out["species"])
    elif args.only:
        targets = [s.strip() for s in args.only.split(",") if s.strip()]
    else:
        raise SystemExit("Say which: --only a,b or --all (only after the group approved them)")
    changed = []
    claude_moves = load_claude_moves()
    fresh = out.get("fresh")
    for sid in targets:
        r = out["species"].get(sid)
        if not r or r.get("skipped"):
            print("skip %s: no proposal" % sid)
            continue
        path = dexlib.SPECIES_DIR / (sid + ".yaml")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        ls = data.setdefault("learnset", {})
        if fresh:        # a new proposal replaces what Claude added before; the group's own moves stay
            cm = claude_moves.get(sid, {})
            lu_moves = {m for lv, m in cm.get("level_up", [])}
            ls["level_up"] = [e for e in (ls.get("level_up") or []) if not (isinstance(e, dict) and
                                                                             e.get("move") in lu_moves)]
            for k in KEYS[1:]:
                ls[k] = [m for m in (ls.get(k) or []) if m not in set(cm.get(k, []))]
            claude_moves[sid] = {}
        filled = []
        for key, label in (("level_up", "level-up moves"), ("tm_hm", "TM/HM moves"), ("tutor", "tutor moves"),
                           ("egg", "egg moves")):
            cur = list(ls.get(key) or [])
            if key == "level_up":
                have = {e.get("move") for e in cur if isinstance(e, dict)}
                new = [dict(e) for e in r["added"][key] if e["move"] not in have]
                if new:
                    cur = sorted(cur + new, key=lambda e: (e.get("level") if isinstance(e.get("level"), int) else 0))
            else:
                new = [mv for mv in r["added"][key] if mv not in cur]
                cur = cur + new
            if new:
                ls[key] = cur
                filled.append(label)
        if filled:
            design = data.setdefault("design", {})
            fb = list(design.get("filled_by_claude") or [])
            for f in filled:
                if f not in fb:
                    fb.append(f)
            design["filled_by_claude"] = fb
            dexlib.write_species(path, data)
            changed.append(sid)
            rec = claude_moves.setdefault(sid, {})
            for key in KEYS:
                for x in r["added"][key]:
                    item = [x["level"], x["move"]] if key == "level_up" else x
                    if item not in rec.setdefault(key, []):
                        rec[key].append(item)
    (DATA_DIR / "claude_moves.json").write_text(json.dumps(claude_moves, ensure_ascii=False, indent=1, sort_keys=True)
                                                + "\n", encoding="utf-8")
    print("updated %d species files: %s" % (len(changed), ", ".join(changed)))


def main():
    # Same input, same output: Python shuffles the order of sets between runs unless PYTHONHASHSEED is fixed.
    import os
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(sys.executable, [sys.executable] + sys.argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose")
    p.add_argument("species", nargs="*")
    p.add_argument("--data", help="data folder to read (default: this checkout's data/), e.g. a worktree of main")
    p.add_argument("--fresh", action="store_true", help="a new proposal for the part Claude added before "
                   "(data/claude_moves.json); apply then replaces that part")
    p.set_defaults(func=cmd_propose)
    p = sub.add_parser("suggest")
    p.add_argument("--data", help="data folder to read (default: this checkout's data/)")
    p.set_defaults(func=cmd_suggest)
    p = sub.add_parser("show")
    p.add_argument("species", nargs="+")
    p.set_defaults(func=cmd_show)
    p = sub.add_parser("apply")
    p.add_argument("--only")
    p.add_argument("--all", action="store_true")
    p.add_argument("--data", help="data folder to write (must be the one the proposals were made from)")
    p.set_defaults(func=cmd_apply)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
