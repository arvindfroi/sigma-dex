#!/usr/bin/env python3
"""Keep a backup of everything outside GitHub and the website's database, that only ever grows.

    python scripts/backup.py D:\\SigmaBackup

Runs every night on the Legion (Windows task "Sigma dex backup"). Three parts, none of which ever deletes anything:
- git/sigma-dex.git: a mirror of the GitHub repository. Every change of a branch is written to its reflog and the
  reflog never expires, so even a force-push or a deleted branch on GitHub cannot take old commits away from it.
- db/<date>/<table>.json.gz: a full copy of every table of the website's database (the edit log, pictures,
  request board, sprite studio jobs and tries) for that day. Old days are kept.
- files/<path>: every picture the database points to in the "art" storage (uploads, Lost and found, studio tries).
  A picture is downloaded once; nothing here is overwritten or removed.
A summary of each run is appended to backup.log. Restoring: docs/BACKUP.md.
"""
import datetime
import gzip
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import dexlib

REPO = "https://github.com/arvindfroi/sigma-dex.git"
TABLES = ["species_edits", "species_images", "species_image_moves", "sprite_jobs", "sprite_tries",
          "sprite_candidates", "sprite_comments", "sprite_worker"]
PICTURE = re.compile(r"^[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+)+\.(png|webp|jpe?g|gif)$", re.I)
PAGE = 1000


def get(url, key, headers=None):
    request = urllib.request.Request(url, headers=dict({"apikey": key, "Authorization": "Bearer " + key,
                                                         "User-Agent": "sigma-dex-backup"}, **(headers or {})))
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError:
            raise
        except OSError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def tables(base, key):
    """The tables the database shows (new ones are picked up by themselves), else the known list."""
    try:
        spec = json.loads(get(base + "/rest/v1/", key))
        found = sorted(p.strip("/") for p in spec.get("paths", {}) if p.count("/") == 1 and not p.startswith("/rpc"))
        return [t for t in found if t] or TABLES
    except Exception:
        return TABLES


def dump_table(base, key, table):
    rows, offset = [], 0
    while True:
        query = urllib.parse.urlencode({"select": "*", "limit": PAGE, "offset": offset})
        batch = json.loads(get("%s/rest/v1/%s?%s" % (base, table, query), key))
        rows += batch
        if len(batch) < PAGE:
            return rows
        offset += PAGE


def pictures(value, found):
    if isinstance(value, str):
        if PICTURE.match(value):
            found.add(value)
    elif isinstance(value, dict):
        for v in value.values():
            pictures(v, found)
    elif isinstance(value, list):
        for v in value:
            pictures(v, found)


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def backup_git(target):
    mirror = target / "git" / "sigma-dex.git"
    if not mirror.exists():
        mirror.parent.mkdir(parents=True, exist_ok=True)
        git("clone", "--mirror", REPO, str(mirror))
    for key, value in (("core.logAllRefUpdates", "always"), ("gc.reflogExpire", "never"),
                       ("gc.reflogExpireUnreachable", "never"), ("gc.pruneExpire", "never"), ("fetch.prune", "false")):
        git("config", key, value, cwd=mirror)
    git("fetch", "--no-prune", "origin", cwd=mirror)
    return git("rev-parse", "refs/heads/main", cwd=mirror).strip()[:7]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=True)
    settings = dexlib.load_config().get("web_edits") or {}
    base, key = settings["url"].rstrip("/"), settings["key"]
    day = datetime.date.today().isoformat()
    lines, problems = [], []

    try:
        lines.append("git main %s" % backup_git(target))
    except Exception as error:
        problems.append("git: %s" % getattr(error, "stderr", error))

    found = set()
    day_dir = target / "db" / day
    day_dir.mkdir(parents=True, exist_ok=True)
    for table in tables(base, key):
        try:
            rows = dump_table(base, key, table)
        except Exception as error:
            problems.append("table %s: %s" % (table, error))
            continue
        with gzip.open(day_dir / (table + ".json.gz"), "wt", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        pictures(rows, found)
        lines.append("%s %d rows" % (table, len(rows)))

    new = failed = 0
    for path in sorted(found):
        out = target / "files" / Path(*path.split("/"))
        if out.exists():
            continue
        try:
            data = get("%s/storage/v1/object/public/art/%s" % (base, urllib.parse.quote(path)), key)
        except urllib.error.HTTPError as error:
            if error.code not in (400, 404):            # 400/404: the picture is gone from the storage already
                failed += 1
            continue
        except OSError:
            failed += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        part = out.with_name(out.name + ".part")
        part.write_bytes(data)
        part.replace(out)
        new += 1
    lines.append("pictures: %d known, %d new, %d failed" % (len(found), new, failed))
    if failed:
        problems.append("%d pictures could not be downloaded (tried again tomorrow)" % failed)

    summary = "%s  %s%s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "; ".join(lines),
                            ("  PROBLEMS: " + "; ".join(problems)) if problems else "")
    with open(target / "backup.log", "a", encoding="utf-8") as log:
        log.write(summary + "\n")
    print(summary)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
