#!/usr/bin/env python3
"""Fixed game rules for our Pokemon, and checks for abilities that do not fit the rest.

    python scripts/dex_rules.py fix      # apply the fixed rules to data/species/ (runs on every sync)
    python scripts/dex_rules.py check    # list abilities that do not fit its moves, type or stats

Which Pokemon are legendary: data/legendaries.yaml (legendary_status()).

Fixed rules (always applied, whatever is typed in):
- Wonder Guard: base HP is 1 (like Shedinja), also in forms that have Wonder Guard.

Moves that cannot work for a Pokemon (Rest, Substitute, recoil moves ... for a Wonder Guard Pokemon with 1 HP) are
never added by the moveset tools (moveset_fill.py, moveset_pick.py); `check` lists the ones that are there.
The checks only warn: a designer may have a reason. validate.py shows them as warnings.
"""
import sys

import dexlib
from dexlib import norm

HP_ONE = {"wonderguard"}

# With 1 HP these do nothing or knock it out itself.
ONE_HP_USELESS = {"Rest", "Substitute", "Belly Drum", "Pain Split", "Endure", "Wish", "Swallow", "Stockpile",
                  "Ingrain", "Aqua Ring", "Fillet Away", "Clangorous Soul", "Mind Blown", "Steel Beam", "Life Dew",
                  "Jungle Healing", "Lunar Blessing", "Healing Wish", "Lunar Dance", "Recover", "Roost", "Synthesis",
                  "Moonlight", "Morning Sun", "Slack Off", "Soft-Boiled", "Milk Drink", "Heal Order", "Shore Up",
                  "Strength Sap", "Shed Tail", "Final Gambit"}
# Wonder Guard cannot be swapped or copied away, so these fail.
WONDER_GUARD_FAILS = {"Skill Swap", "Role Play", "Entrainment", "Simple Beam", "Worry Seed", "Gastro Acid"}

# Abilities whose effect is a form change the game only has for the original Pokemon.
FORM_ABILITIES = {"Disguise": "Mimikyu", "Shields Down": "Minior", "Battle Bond": "Greninja", "Zen Mode": "Darmanitan",
                  "Schooling": "Wishiwashi", "Power Construct": "Zygarde", "Stance Change": "Aegislash",
                  "Gulp Missile": "Cramorant", "Ice Face": "Eiscue", "Hunger Switch": "Morpeko",
                  "Zero to Hero": "Palafin", "Forecast": "Castform", "Flower Gift": "Cherrim", "Multitype": "Arceus",
                  "RKS System": "Silvally", "Commander": "Tatsugiri"}
# Abilities so strong that official competitive play bans them.
BANNED_SINGLES = {"Moody", "Shadow Tag", "Arena Trap"}


_LEGENDARIES = None


def legendary_status(sid):
    """'legendary', 'mythical' or 'ordinary' from data/legendaries.yaml; None when the list does not say."""
    global _LEGENDARIES
    if _LEGENDARIES is None:
        import yaml
        path = dexlib.ROOT / "data" / "legendaries.yaml"
        _LEGENDARIES = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
    for key, status in (("legendary", "legendary"), ("mythical", "mythical"), ("undecided", "ordinary"),
                        ("ordinary", "ordinary")):
        if sid in (_LEGENDARIES.get(key) or []):
            return status
    return None


def abilities(data):
    ab = data.get("abilities") or {}
    return [a for a in (ab.get("primary"), ab.get("secondary"), ab.get("hidden")) if a]


def one_hp(ability_names):
    return any(norm(a) in HP_ONE for a in ability_names)


def useless_move(ability_names, move, m=None):
    """True if this move cannot work for a Pokemon with these abilities (m: the move's data, optional)."""
    if one_hp(ability_names):
        if move in ONE_HP_USELESS or move in WONDER_GUARD_FAILS:
            return True
        if m and (m.get("heal") or m.get("recoil")) and not m.get("drain"):
            return True
    return False


def fix(data):
    """Apply the fixed rules to one species. Returns a list of what changed."""
    changed = []
    if one_hp(abilities(data)):
        stats = data.get("base_stats") if isinstance(data.get("base_stats"), dict) else {}
        if stats.get("hp") != 1:
            changed.append("base HP %s -> 1 (Wonder Guard)" % stats.get("hp"))
            stats["hp"] = 1
            data["base_stats"] = stats
    for form in data.get("forms") or []:
        if isinstance(form, dict) and one_hp(abilities(form)):
            stats = form.get("base_stats") if isinstance(form.get("base_stats"), dict) else {}
            if stats.get("hp") != 1:
                changed.append("form '%s': base HP %s -> 1 (Wonder Guard)" % (form.get("name"), stats.get("hp")))
                stats["hp"] = 1
                form["base_stats"] = stats
    return changed


def _learnset_moves(data):
    learn = data.get("learnset") or {}
    out = [e.get("move") for e in learn.get("level_up") or [] if isinstance(e, dict) and e.get("move")]
    for key in ("tm_hm", "tutor", "egg"):
        out += [m for m in learn.get(key) or [] if m]
    return list(dict.fromkeys(out))


def check(data, moves=None):
    """Warnings for one species. moves: {name: move data} (moveset_data.load()["moves"]) for the move checks."""
    out = []
    abil = abilities(data)
    types = data.get("types") or []
    stats = data.get("base_stats") or {}
    if one_hp(abil):
        if stats.get("hp") not in (None, 1):
            out.append("has Wonder Guard, so its base HP must be 1 (it is %s)" % stats.get("hp"))
        try:
            import moveset_data
            weak = [t for t in dexlib.TYPES if moveset_data.effectiveness(t, types) > 1]
            if len(weak) < 4:
                out.append("has Wonder Guard but only %d weaknesses (%s): only those can hit it, Shedinja has 5"
                           % (len(weak), ", ".join(weak) or "none"))
        except Exception:
            pass
        by_norm = {norm(k): (k, v) for k, v in (moves or {}).items()}
        bad = [mv for mv in _learnset_moves(data)
               if useless_move(abil, by_norm.get(norm(mv), (mv, None))[0], by_norm.get(norm(mv), (mv, None))[1])]
        if bad:
            out.append("has Wonder Guard (1 HP), so these moves do nothing or knock it out: %s" % ", ".join(bad))
    for a in abil:
        if a in FORM_ABILITIES:
            out.append("%s changes %s's form in the game; for our Pokemon it needs its own form and new code, or "
                       "a different ability" % (a, FORM_ABILITIES[a]))
        if a in BANNED_SINGLES:
            out.append("%s is banned in official competitive play - check that it is not too strong here" % a)
    if stats.get("attack") and stats.get("sp_attack"):
        for a in abil:
            if a in ("Huge Power", "Pure Power", "Hustle", "Guts", "Gorilla Tactics") \
                    and stats["attack"] * (2 if a in ("Huge Power", "Pure Power") else 1) + 20 < stats["sp_attack"]:
                out.append("%s boosts physical attacks, but its Sp. Attack is higher" % a)
            if a in ("Solar Power", "Mega Launcher", "Punk Rock") and stats["sp_attack"] + 20 < stats["attack"]:
                out.append("%s boosts special attacks, but its Attack is higher" % a)
    return out


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    species, _ = dexlib.load_species()
    if cmd == "fix":
        n = 0
        for sid, path, data in species:
            changes = fix(data)
            if changes:
                dexlib.write_species(path, data)
                n += 1
                print("%s: %s" % (sid, "; ".join(changes)))
        print("%d species changed by the fixed rules" % n)
    elif cmd == "check":
        try:
            import moveset_data
            moves = moveset_data.load()["moves"]
        except Exception:
            moves = {}
        for sid, path, data in species:
            for w in check(data, moves):
                print("%s (%s): %s" % (data.get("name") or sid, sid, w))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
