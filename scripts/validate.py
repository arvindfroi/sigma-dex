#!/usr/bin/env python3
"""Check every species file for mistakes.

Errors (broken data) make the check fail. Warnings are things to look at but do not fail.
Missing information is not an error - see TODO.md for what is still to be filled in.
"""
import os
import sys

import dexlib
from dexlib import ROOT, section, listing


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_species(sid, data, ids, engine, errors, warnings):
    def err(msg):
        errors.append(msg)

    def warn(msg):
        warnings.append(msg)

    for field in dexlib.unknown_fields(data):
        err("unknown field '%s' - probably a typo (all fields: docs/FIELDS.md)" % field)

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        err("name is missing (if the name is a word like Yes/No/On, put it in quotes)")
    elif len(name) > dexlib.NAME_LIMIT:
        warn("name '%s' is %d characters, the game fits at most %d" % (name, len(name), dexlib.NAME_LIMIT))

    category = data.get("category")
    if category is not None and len(str(category)) > dexlib.CATEGORY_LIMIT:
        warn("category '%s' is %d characters, the game fits at most %d" % (category, len(str(category)), dexlib.CATEGORY_LIMIT))
    description = data.get("description")
    if description is not None:
        if not isinstance(description, str):
            err("description must be text")
        else:
            lines = description.strip().split("\n")
            if len(lines) > dexlib.DESCRIPTION_LINES:
                warn("description has %d lines, the Pokedex page fits %d" % (len(lines), dexlib.DESCRIPTION_LINES))
            if len(description.strip()) > dexlib.DESCRIPTION_LINES * dexlib.DESCRIPTION_LINE_LENGTH:
                warn("description is %d characters, the Pokedex page fits about %d"
                     % (len(description.strip()), dexlib.DESCRIPTION_LINES * dexlib.DESCRIPTION_LINE_LENGTH))

    abilities = data.get("abilities")
    if abilities is not None and not isinstance(abilities, dict):
        err("abilities must have primary / secondary / hidden")
    for slot, ability in section(data, "abilities").items():
        if slot in ("primary", "secondary", "hidden") and ability is not None and dexlib.norm(ability) not in engine["abilities"]:
            warn("ability '%s' does not exist in the game yet - check the spelling; if it is a new ability it has to be programmed" % ability)

    types = data.get("types")
    if types is not None and not isinstance(types, list):
        err("types must be a list like [Grass, Steel]")
    else:
        types = listing(types)
        if len(types) > 2:
            err("a Pokemon has at most 2 types, found %d" % len(types))
        if len(set(types)) != len(types):
            err("the same type is listed twice")
        for t in types:
            if t not in dexlib.TYPES:
                warn("type '%s' is not a real type (valid: %s)" % (t, ", ".join(dexlib.TYPES)))

    stats = section(data, "base_stats")
    for stat, value in stats.items():
        if stat in dexlib.STATS and value is not None and (not isinstance(value, int) or not 1 <= value <= 255):
            err("base_stats.%s must be a whole number 1-255, found %r" % (stat, value))
    total = dexlib.bst(data)
    if total is not None and total > 720:
        warn("base stat total is %d, higher than any official Pokemon" % total)

    ev = data.get("ev_yield")
    if ev is not None:
        if not isinstance(ev, dict):
            err("ev_yield must look like {speed: 1}")
        else:
            for stat, value in ev.items():
                if stat not in dexlib.STATS:
                    err("ev_yield has unknown stat '%s'" % stat)
                elif not isinstance(value, int) or not 0 <= value <= 3:
                    err("ev_yield.%s must be 0-3, found %r" % (stat, value))
            if sum(v for v in ev.values() if isinstance(v, int)) > 3:
                err("ev_yield gives more than 3 points in total")

    for key, low, high in (("catch_rate", 1, 255), ("base_exp", 1, 700), ("base_friendship", 0, 255), ("egg_cycles", 1, 120)):
        value = data.get(key)
        if value is not None and (not isinstance(value, int) or not low <= value <= high):
            err("%s must be a whole number %d-%d, found %r" % (key, low, high, value))

    for key in ("height_m", "weight_kg"):
        value = data.get(key)
        if value is not None and (not is_number(value) or value <= 0):
            err("%s must be a positive number, found %r" % (key, value))

    for key, valid in (("growth_rate", dexlib.GROWTH_RATES), ("body_color", dexlib.BODY_COLORS), ("gender", dexlib.GENDER_VALUES)):
        value = data.get(key)
        if value is not None and value not in valid:
            err("%s is %r, must be one of: %s" % (key, value, ", ".join(str(v) for v in valid)))

    egg_groups = data.get("egg_groups")
    if egg_groups is not None and not isinstance(egg_groups, list):
        err("egg_groups must be a list like [field, grass]")
    else:
        egg_groups = listing(egg_groups)
        if len(egg_groups) > 2:
            err("at most 2 egg groups, found %d" % len(egg_groups))
        for group in egg_groups:
            if group not in dexlib.EGG_GROUPS:
                err("egg group %r is not valid (valid: %s)" % (group, ", ".join(dexlib.EGG_GROUPS)))

    evolutions = data.get("evolutions")
    if evolutions is not None and not isinstance(evolutions, list):
        err("evolutions must be a list")
    if len(listing(evolutions)) > dexlib.MAX_EVOLUTIONS:
        err("a Pokemon can have at most %d evolutions" % dexlib.MAX_EVOLUTIONS)
    for evo in listing(evolutions):
        if not isinstance(evo, dict):
            err("each evolution must have 'into' and 'method'")
            continue
        target = evo.get("into")
        if target == sid:
            err("evolves into itself")
        elif target not in ids:
            err("evolves into '%s' but there is no data/species/%s.yaml" % (target, target))
        method = evo.get("method")
        if method not in dexlib.EVOLUTION_METHODS:
            err("evolution method %r must be one of: %s" % (method, ", ".join(dexlib.EVOLUTION_METHODS)))
        level = evo.get("level")
        if method in dexlib.LEVEL_METHODS and (not isinstance(level, int) or not 1 <= level <= 100):
            err("evolution method '%s' needs a level 1-100, found %r" % (method, level))
        if method in dexlib.ITEM_METHODS and not evo.get("item"):
            err("evolution method '%s' needs an item" % method)
        if method == "other" and not evo.get("note"):
            err("evolution method 'other' needs a note explaining how it evolves")

    learnset = data.get("learnset")
    if learnset is not None and not isinstance(learnset, dict):
        err("learnset must have level_up / tm_hm / tutor / egg lists")
    learnset = section(data, "learnset")
    for key in learnset:
        if learnset[key] is not None and not isinstance(learnset[key], list):
            err("learnset.%s must be a list" % key)
    for entry in listing(learnset.get("level_up")):
        if (not isinstance(entry, dict) or not isinstance(entry.get("level"), int)
                or not 0 <= entry["level"] <= 100 or not isinstance(entry.get("move"), str)):
            err("level_up entry %r must look like {level: 7, move: Vine Whip} (level 0 = learned when evolving)" % (entry,))
        elif dexlib.norm(entry["move"]) not in engine["moves"]:
            warn("move '%s' does not exist in the game yet - check the spelling; if it is a new move it has to be programmed" % entry["move"])
    for key in ("tm_hm", "tutor", "egg"):
        for move in listing(learnset.get(key)):
            if not isinstance(move, str):
                err("learnset.%s entry %r must be a move name" % (key, move))
            elif key == "tm_hm" and dexlib.norm(move) not in engine["tm_hm"]:
                warn("'%s' is not one of the game's TMs/HMs (list: data/engine/expansion.yaml)" % move)
            elif key != "tm_hm" and dexlib.norm(move) not in engine["moves"]:
                warn("%s move '%s' does not exist in the game yet - check the spelling; if it is a new move it has to be programmed" % (key, move))

    encounters = data.get("encounters")
    if encounters is not None and not isinstance(encounters, list):
        err("encounters must be a list")
    for entry in listing(encounters):
        if not isinstance(entry, dict) or not entry.get("location"):
            err("encounter %r needs at least a location" % (entry,))

    details = section(data, "engine")
    for key, low, high in (("elevation", 0, 64), ("front_y_offset", 0, 64), ("back_y_offset", 0, 64),
                           ("icon_palette", 0, 5), ("safari_flee_rate", 0, 255)):
        value = details.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high):
            err("engine.%s must be a whole number %d-%d, found %r" % (key, low, high, value))
    if details.get("no_flip") not in (None, True, False):
        err("engine.no_flip must be true or false")

    for key, value in section(data, "assets").items():
        if value is not None and not (isinstance(value, str) and (ROOT / value).is_file()):
            err("assets.%s points to '%s' which does not exist in the repo" % (key, value))
    folder = ROOT / "assets" / "sprites" / sid
    if folder.is_dir():
        import sprites                      # needs Pillow; only loaded when there are sprites to check
        for problem in sprites.check_folder(folder):
            err("sprites: " + problem)


def main():
    config = dexlib.load_config()
    dex_size = config.get("dex_size", 151)
    species, problems = dexlib.load_species()
    engine = dexlib.load_engine()
    ids = {sid for sid, _, _ in species}
    results = [(path, [msg], []) for path, msg in problems]

    for kind in ("moves", "abilities"):
        existing = {dexlib.norm(name) for name in engine["engine_names"][kind]}
        found = ["%s: %s" % (entry.get("name"), problem) for entry in engine["custom"][kind]
                 for problem in dexlib.check_custom(kind, entry, existing)]
        if found:
            results.append((ROOT / "data" / ("custom_%s.yaml" % kind), [], found))

    seen_dex, seen_names = {}, {}
    for sid, path, data in species:
        errors, warnings = [], []
        dex = data.get("dex")
        if not isinstance(dex, int) or isinstance(dex, bool) or not 1 <= dex <= dex_size:
            errors.append("dex must be a number 1-%d, found %r" % (dex_size, dex))
        elif dex in seen_dex:
            errors.append("dex number %d is already used by %s" % (dex, seen_dex[dex]))
        else:
            seen_dex[dex] = path.name
        key = str(data.get("name", "")).strip().lower()
        if key and key in seen_names:
            errors.append("name '%s' is already used by %s" % (data.get("name"), seen_names[key]))
        elif key:
            seen_names[key] = path.name
        check_species(sid, data, ids, engine, errors, warnings)
        results.append((path, errors, warnings))

    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    n_errors = n_warnings = 0
    for path, errors, warnings in results:
        rel = path.relative_to(ROOT)
        for level, messages in (("error", errors), ("warning", warnings)):
            for msg in messages:
                print("%-7s %s: %s" % (level.upper(), rel, msg))
                if in_actions:
                    print("::%s file=%s::%s" % (level, rel, msg))
        n_errors += len(errors)
        n_warnings += len(warnings)

    print("\n%d species files checked: %d errors, %d warnings" % (len(species) + len(problems), n_errors, n_warnings))
    return 1 if n_errors else 0


if __name__ == "__main__":
    sys.exit(main())
