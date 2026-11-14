#!/usr/bin/env python3
"""Copy what people saved on the website into the species files.

    python scripts/import_web.py              # reads the database named in data/config.yaml
    python scripts/import_web.py rows.json    # or a file with the same rows (for testing)

Every save on the website is one row in the database: a complete copy of that Pokemon.
A row of kind "reorder" is different: it holds steps that move Pokemon to other dex numbers
(see dexlib.change_layout) and changes only the `dex` numbers.
Rows newer than data/web_edits_cursor.txt are applied in order, so the newest save wins.
Rows of kind "shiny" and "cry" (the SHINY and CRY tabs) are written to assets/shiny/<pokemon>.json and
assets/cries/<pokemon>.json, and the species file's assets.shiny_palette / assets.cry point at them. A cry made from
someone's own sound also gets assets/cries/<pokemon>.wav (mono, 16-bit, 13379 Hz).
A row that would break a species file is skipped and reported in export/web_problems.json
(shown on the website). Art paths and sprite details cannot be edited on the website and
are always kept from the species file.
"""
import base64
import copy
import json
import re
import wave
import sys
import urllib.request

import dexlib
import validate
from dexlib import ROOT, norm

REPORT = ROOT / "export" / "web_problems.json"
CURSOR = ROOT / "data" / "web_edits_cursor.txt"
KEPT_FROM_FILE = ("assets", "engine")
HEX = re.compile(r"#[0-9a-f]{6}")
SAVED = {"shiny": ("shiny", "shiny_palette"), "cry": ("cries", "cry")}     # kind -> (folder under assets/, asset field)
CRY_RATE = 13379                    # an own sound: mono 16-bit PCM at HeartGold's cry rate (scripts/cry_engine.js)
OWN_SAMPLES = round(2.0 * CRY_RATE)  # at most 2 seconds (cry_engine.js OWN_LEN)


def number(value, low, high, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ValueError("%s must be a number %s to %s" % (what, low, high))
    return round(float(value), 3)


def clean_shiny(data):
    """normal colour -> shiny colour, for the front and back (map) and the walking sprite (follower)."""
    out = {}
    for key in ("map", "follower"):
        pairs = data.get(key) or {}
        if not isinstance(pairs, dict) or len(pairs) > 40:
            raise ValueError("%s must be at most 40 colours" % key)
        for a, b in pairs.items():
            if not (HEX.fullmatch(str(a)) and HEX.fullmatch(str(b))):
                raise ValueError("%s: '%s' -> '%s' is not a colour like #a0b8f8" % (key, a, b))
        out[key] = dict(sorted(pairs.items()))
    if not out["map"]:
        raise ValueError("the shiny has no colours")
    sliders = data.get("sliders") or []
    out["sliders"] = sliders if isinstance(sliders, list) and len(sliders) <= 20 else []
    out["why"] = str(data.get("why") or "")[:300]
    out["front"] = str(data.get("front") or "")[:300]       # the sprite it was made for
    return out


def clean_cry(data):
    """A cry recipe (scripts/cry_engine.js): which official cries it starts from and how they are bent."""
    layers = data.get("layers")
    if not isinstance(layers, list) or not 1 <= len(layers) <= 3:
        raise ValueError("a cry has 1 to 3 layers")
    out = {"v": int(data.get("v") or 1), "seed": int(data.get("seed") or 0), "layers": []}
    for layer in layers:
        if not isinstance(layer, dict):
            raise ValueError("a layer must be an object")
        bend = {"semi": number(layer.get("semi", 0), -12, 7, "semi"), "gain": number(layer.get("gain", 1), 0, 1.5, "gain"),
                "at": number(layer.get("at", 0), 0, 0.5, "at"), "rev": bool(layer.get("rev"))}
        if layer.get("own") is True:            # the Pokemon's own sound (uploaded or recorded on the website)
            if not isinstance(data.get("audio"), str):
                raise ValueError("a layer uses the own sound, but the cry has none")
            out["layers"].append(dict({"own": True}, **bend))
            continue
        dex = layer.get("dex")
        if isinstance(dex, bool) or not isinstance(dex, int) or not 1 <= dex <= 493:
            raise ValueError("a layer must name an official Pokemon 1-493")
        out["layers"].append(dict({"dex": dex}, **bend))
    out["stretch"] = number(data.get("stretch") or 1, 0.7, 1.4, "stretch")
    out["sweep"] = number(data.get("sweep") or 0, -6, 6, "sweep")
    out["tone"] = number(data.get("tone") or 0, -1, 1, "tone")
    out["drive"] = number(data.get("drive") or 0, 0, 1, "drive")
    out["len"] = number(data.get("len") or 1.6, 0.3, 1.6, "len")
    for key, fields in (("vib", (("rate", 0, 12), ("depth", 0, 1))), ("ring", (("hz", 10, 400), ("mix", 0, 0.6))), ("echo", (("ms", 20, 300), ("gain", 0, 0.6)))):
        part = data.get(key)
        out[key] = {name: number(part.get(name), low, high, key + "." + name) for name, low, high in fields} if isinstance(part, dict) else None
    out["reasons"] = [str(r)[:200] for r in (data.get("reasons") or [])[:8]]
    return out


def own_sound(text):
    """An own sound from the website: base64 of mono 16-bit little-endian PCM at 13379 Hz, at most 2 seconds."""
    try:
        pcm = base64.b64decode(text, validate=True)
    except ValueError:
        raise ValueError("the own sound is not readable")
    if len(pcm) % 2 or not 200 <= len(pcm) <= 2 * OWN_SAMPLES:
        raise ValueError("the own sound must be 0.01 to 2 seconds")
    return pcm


def save_extra(kind, sid, row, files):
    """A shiny or a cry saved on the website: its own file, and the species file points at it. Returns 1 if changed."""
    if sid not in files:
        raise ValueError("there is no Pokemon called '%s'" % sid)
    folder, field = SAVED[kind]
    target = ROOT / "assets" / folder / (sid + ".json")
    sound = target.with_suffix(".wav")       # a cry's own sound, next to its recipe
    data = row.get("data") or {}
    path, species = files[sid]
    assets = dict(species.get("assets") or {})
    if data.get("deleted"):
        if target.exists():
            target.unlink()
        if kind == "cry" and sound.exists():
            sound.unlink()
        assets[field] = None
    else:
        entry = clean_shiny(data) if kind == "shiny" else clean_cry(data)
        pcm = own_sound(data["audio"]) if kind == "cry" and any(layer.get("own") for layer in entry["layers"]) else None
        entry["by"] = row.get("editor") or ""
        entry["at"] = str(data.get("at") or "")[:40]
        target.parent.mkdir(parents=True, exist_ok=True)
        if pcm:
            with wave.open(str(sound), "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(CRY_RATE)
                out.writeframes(pcm)
            entry["audio"] = sound.relative_to(ROOT).as_posix()
        elif kind == "cry" and sound.exists():
            sound.unlink()
        target.write_text(json.dumps(entry, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        assets[field] = target.relative_to(ROOT).as_posix()
    if assets == (species.get("assets") or {}):
        return 1
    species = dict(species, assets=assets)
    dexlib.write_species(path, species)
    files[sid] = (path, species)
    return 1


def read_cursor():
    return int(CURSOR.read_text().strip() or 0) if CURSOR.exists() else 0


def fetch_rows(settings, cursor):
    rows = []
    while True:
        url = "%s/rest/v1/species_edits?select=id,kind,species_id,data,editor,created_at&id=gt.%d&order=id.asc&limit=1000" % (
            settings["url"].rstrip("/"), rows[-1]["id"] if rows else cursor)
        request = urllib.request.Request(url, headers={"apikey": settings["key"], "User-Agent": "sigma-dex"})
        with urllib.request.urlopen(request) as response:
            page = json.load(response)
        rows.extend(page)
        if len(page) < 1000:
            return rows


def empty(value):
    return value in (None, "", [], {})


def changed(new, old):
    return not (empty(new) and empty(old)) and new != old


def merge_edit(current, new, base):
    """Apply only what the editor actually changed (new versus the `base` they started from) onto the file.

    The website sends the whole Pokemon. If the page was opened before somebody else's change
    landed, saving everything would undo that change; this keeps it.
    """
    merged = copy.deepcopy(current)
    for key, parts in dexlib.FIELDS.items():
        if key in KEPT_FROM_FILE or key == "dex":
            continue
        if parts and isinstance(new.get(key) or {}, dict) and isinstance(base.get(key) or {}, dict):
            for part in parts:
                value, before = (new.get(key) or {}).get(part), (base.get(key) or {}).get(part)
                if changed(value, before):
                    if not isinstance(merged.get(key), dict):
                        merged[key] = {}
                    merged[key][part] = copy.deepcopy(value)
        elif changed(new.get(key), base.get(key)):
            merged[key] = copy.deepcopy(new.get(key))
    return merged


def known_fields_only(data):
    """Keep only fields a species file can hold, so stray input never reaches a file."""
    cleaned = {}
    for key, value in data.items():
        if key not in dexlib.FIELDS:
            continue
        if dexlib.FIELDS[key] and isinstance(value, dict):
            value = {sub: v for sub, v in value.items() if sub in dexlib.FIELDS[key]}
        cleaned[key] = value
    return cleaned


def delete_species(sid, files, config):
    """Remove a Pokemon from the dex (asked for on the website). Its species file, its sprite folders
    and its sprite pictures go; evolutions of other Pokemon into it are dropped. Its concept art was
    already moved to the lost-and-found pile by the website. Everything stays in git history and in
    the database's edit log, so it can be brought back. Returns the number of files changed."""
    if sid not in files:
        return 0                                         # already gone (or never imported)
    if sid in (config.get("starters") or []):
        raise ValueError("it is one of the starters (data/config.yaml) - choose another starter first")
    path, data = files.pop(sid)
    path.unlink()
    removed = dexlib.load_removed()
    removed[sid] = data.get("name") or sid
    dexlib.write_removed(removed)
    changed = 1
    for folder in (ROOT / "assets" / "sprites" / sid, ROOT / "assets" / "sprites-ds" / sid, ROOT / "assets" / "concept-art" / sid):
        if folder.is_dir():
            for f in folder.iterdir():
                f.unlink()
            folder.rmdir()
    manifest_path = ROOT / "data" / "images.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        kept = [e for e in manifest if e["species"] != sid]
        if len(kept) != len(manifest):
            manifest_path.write_text(json.dumps(kept, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for other, (other_path, data) in list(files.items()):
        evolutions = [e for e in dexlib.listing(data.get("evolutions")) if not (isinstance(e, dict) and e.get("into") == sid)]
        if len(evolutions) != len(dexlib.listing(data.get("evolutions"))):
            data = dict(data, evolutions=evolutions)
            dexlib.write_species(other_path, data)
            files[other] = (other_path, data)
            changed += 1
    return changed


def main():
    config = dexlib.load_config()
    cursor = read_cursor()
    if len(sys.argv) > 1:
        rows = [r for r in json.load(open(sys.argv[1], encoding="utf-8")) if r["id"] > cursor]
    else:
        settings = config.get("web_edits") or {}
        if not settings.get("url") or not settings.get("key"):
            print("No website database configured (web_edits in data/config.yaml) - nothing to import.")
            return 0
        try:
            rows = fetch_rows(settings, cursor)
        except OSError as error:
            print("WARNING: the website database could not be read (%s). Nothing imported." % error)
            return 0

    species, problems = dexlib.load_species()
    if problems:
        sys.exit("Fix the species files first (run scripts/validate.py).")
    engine = dexlib.load_engine()
    files = {sid: (path, data) for sid, path, data in species}
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else []
    changed = 0

    custom = {kind: dexlib.load_custom(kind) for kind in ("moves", "abilities")}
    custom_changed = set()

    for row in rows:
        sid, editor = str(row.get("species_id")), row.get("editor") or "someone"
        label = "%s (saved by %s)" % (sid, editor)
        if row.get("kind") in ("move", "ability"):
            kind = "moves" if row["kind"] == "move" else "abilities"
            label = "new %s %s" % (row["kind"], label)
            try:
                data = row.get("data")
                if not isinstance(data, dict) or dexlib.slugify(sid) != sid or not sid:
                    raise ValueError("the saved data is not a %s" % row["kind"])
                old = next((e for e in custom[kind] if e["id"] == sid), None)
                if data.get("deleted"):
                    custom[kind] = [e for e in custom[kind] if e["id"] != sid]
                else:
                    entry = {k: data.get(k) for k in dexlib.CUSTOM_FIELDS[kind] if k not in ("id", "implemented")}
                    entry["id"] = sid
                    if old and old.get("implemented"):
                        entry["implemented"] = old["implemented"]   # only set by whoever programs it
                    existing = {norm(name) for name in engine["engine_names"][kind]}
                    taken = {norm(e["name"]) for e in custom[kind] if e["id"] != sid}
                    found = dexlib.check_custom(kind, entry, existing)
                    if norm(entry.get("name") or "") in taken:
                        found.append("another new %s already has that name" % row["kind"])
                    if found:
                        raise ValueError("; ".join(found))
                    custom[kind] = [e for e in custom[kind] if e["id"] != sid] + [entry]
                custom_changed.add(kind)
                report = [entry for entry in report if entry.get("species") != row["kind"] + ":" + sid]
            except Exception as error:
                report.append({"id": row.get("id"), "species": row["kind"] + ":" + sid, "row": label, "problem": str(error)})
            continue
        if row.get("kind") in ("request", "team", "teamnote", "claim"):
            continue   # a card on the website's request board: it lives in the database only
        if row.get("kind") in SAVED:
            try:
                if not isinstance(row.get("data"), dict):
                    raise ValueError("the saved %s is empty" % row["kind"])
                changed += save_extra(row["kind"], sid, row, files)
                report = [entry for entry in report if entry.get("species") != row["kind"] + ":" + sid]
            except Exception as error:
                report.append({"id": row.get("id"), "species": row["kind"] + ":" + sid, "row": "%s of %s" % (row["kind"], label), "problem": str(error)})
            continue
        if row.get("kind") == "reorder":
            # Several dex numbers change at once: all of it is applied, or none of it.
            label = "reorder (saved by %s)" % editor
            try:
                size = config.get("dex_size", 151)
                layout = [None] * size
                for other, (_, data) in files.items():
                    if isinstance(data.get("dex"), int) and 1 <= data["dex"] <= size:
                        layout[data["dex"] - 1] = other
                new = dexlib.change_layout(layout, (row.get("data") or {}).get("ops"))
                for number, other in enumerate(new, 1):
                    if other and files[other][1].get("dex") != number:
                        path, data = files[other]
                        data = dict(data, dex=number)
                        dexlib.write_species(path, data)
                        files[other] = (path, data)
                        changed += 1
                report = [entry for entry in report if entry.get("species") != "reorder"]
            except Exception as error:
                report.append({"id": row.get("id"), "species": "reorder", "row": label, "problem": str(error)})
            continue
        if isinstance(row.get("data"), dict) and row["data"].get("deleted"):
            try:
                changed += delete_species(sid, files, config)
                report = [entry for entry in report if entry.get("species") != sid]
            except Exception as error:
                report.append({"id": row.get("id"), "species": sid, "row": "removal of " + label, "problem": str(error)})
            continue
        try:
            if not isinstance(row.get("data"), dict) or dexlib.slugify(sid) != sid or not sid:
                raise ValueError("the saved data is not a Pokemon")
            updated = known_fields_only(row["data"])
            base = row["data"].get("_base")
            if sid in files and isinstance(base, dict):
                updated = merge_edit(files[sid][1], updated, known_fields_only(base))
            if sid in files:
                path, current = files[sid]
                updated["dex"] = current.get("dex")
                for key in KEPT_FROM_FILE:
                    updated.pop(key, None)
                    if key in current:
                        updated[key] = copy.deepcopy(current[key])
            else:
                path, current = dexlib.SPECIES_DIR / (sid + ".yaml"), None
                for key in KEPT_FROM_FILE:
                    updated.pop(key, None)
                dex = updated.get("dex")
                if not isinstance(dex, int) or isinstance(dex, bool) or not 1 <= dex <= config.get("dex_size", 151):
                    raise ValueError("a new Pokemon needs a dex slot inside the dex")
                if any(data.get("dex") == dex for _, data in files.values()):
                    raise ValueError("dex slot %d is already taken" % dex)
            others = {norm(data.get("name")) for other, (_, data) in files.items() if other != sid}
            if norm(updated.get("name")) in others:
                raise ValueError("the name '%s' is already used by another Pokemon" % updated.get("name"))
            errors = []
            validate.check_species(sid, updated, set(files) | {sid}, engine, errors, [])
            if errors:
                raise ValueError("; ".join(errors))
            if current is None or dexlib.prune(updated) != dexlib.prune(current):
                dexlib.write_species(path, updated)
                changed += 1
            if current is None:                      # added again on the website: the sheet and doc may use it again
                removed = dexlib.load_removed()
                if sid in removed or dexlib.removed_name(updated.get("name"), removed):
                    removed = {k: v for k, v in removed.items() if k != sid and norm(v) != norm(updated.get("name"))}
                    dexlib.write_removed(removed)
            files[sid] = (path, updated)
            report = [entry for entry in report if entry.get("species") != sid]
        except Exception as error:  # one bad save must never stop the others
            report.append({"id": row.get("id"), "species": sid, "row": label, "problem": str(error)})

    for kind in sorted(custom_changed):
        dexlib.write_custom(kind, custom[kind])
        changed += 1
    if rows:
        CURSOR.write_text("%d\n" % rows[-1]["id"])
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report[-50:], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for entry in report:
        print("NOT USED %s: %s" % (entry["row"], entry["problem"]))
    print("Website import: %d saves read, %d files changed, %d problems listed" % (len(rows), changed, len(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
