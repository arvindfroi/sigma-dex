#!/usr/bin/env python3
"""Copy images that were attached on the website into the repository.

New images are downloaded into assets/concept-art/<pokemon>/ and listed in data/images.json;
removed ones are deleted again. The first image of a Pokemon becomes its `concept_art`.
"""
import json
import sys
import urllib.request

import dexlib
from dexlib import ROOT, section

MANIFEST = ROOT / "data" / "images.json"
ART = ROOT / "assets" / "concept-art"
MAX_BYTES = 3 * 1024 * 1024
SIGNATURES = {".png": b"\x89PNG", ".jpg": b"\xff\xd8\xff", ".gif": b"GIF8", ".webp": b"RIFF"}


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []


def fetch(url, key=None):
    headers = {"User-Agent": "sigma-dex"}
    if key:
        headers["apikey"] = key
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as response:
        return response.read(MAX_BYTES + 1)


def main():
    settings = dexlib.load_config().get("web_edits") or {}
    if not settings.get("url") or not settings.get("key"):
        print("No website database configured - no images to import.")
        return 0
    base = settings["url"].rstrip("/")
    try:
        rows = json.loads(fetch(base + "/rest/v1/species_images?select=id,species_id,path,caption,editor,removed&order=id.asc", settings["key"]))
    except OSError as error:
        print("WARNING: the image list could not be read (%s). Nothing imported." % error)
        return 0

    species, problems = dexlib.load_species()
    if problems:
        sys.exit("Fix the species files first (run scripts/validate.py).")
    files = {sid: (path, data) for sid, path, data in species}
    manifest = load_manifest()
    known = {entry["id"] for entry in manifest}
    added = removed = 0

    for row in rows:
        if row.get("removed"):
            for entry in [e for e in manifest if e["id"] == row["id"]]:
                (ROOT / entry["file"]).unlink(missing_ok=True)
                manifest.remove(entry)
                removed += 1
            continue
        sid, path = str(row.get("species_id")), str(row.get("path"))
        extension = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if row["id"] in known or sid not in files or extension not in SIGNATURES or dexlib.slugify(sid) != sid:
            continue  # an image for a Pokemon that is not in the repository yet waits until it is
        try:
            content = fetch("%s/storage/v1/object/public/art/%s" % (base, path))
        except OSError:
            continue
        if len(content) > MAX_BYTES or not content.startswith(SIGNATURES[extension]):
            continue
        target = ART / sid / ("%d%s" % (row["id"], extension))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        manifest.append({"id": row["id"], "species": sid, "file": str(target.relative_to(ROOT)),
                         "caption": row.get("caption"), "editor": row.get("editor")})
        added += 1

    manifest.sort(key=lambda entry: entry["id"])
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # A Pokemon's concept_art follows its first attached image (unless someone set another file by hand).
    managed = str(ART.relative_to(ROOT)) + "/"
    for sid, (path, data) in files.items():
        # Sprite pictures (captions like "[front] ...") are not concept art.
        first = next((entry["file"] for entry in manifest if entry["species"] == sid and not (entry.get("caption") or "").startswith("[")), None)
        current = section(data, "assets").get("concept_art")
        by_hand = current and not (current.startswith(managed + sid + "/") and current[len(managed + sid) + 1:].split(".")[0].isdigit())
        if by_hand or current == first:
            continue
        data.setdefault("assets", {})
        if not isinstance(data["assets"], dict):
            data["assets"] = {}
        data["assets"]["concept_art"] = first
        dexlib.write_species(path, data)

    print("Image import: %d added, %d removed, %d in the repository" % (added, removed, len(manifest)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
