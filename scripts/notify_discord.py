#!/usr/bin/env python3
"""Post in the group's Discord when a Pokemon reaches 100 % on the website.

    DISCORD_WEBHOOK_URL=... python scripts/notify_discord.py

Run by the Dex workflow after each sync. 100 % is the same as the website's "Done" (everything people fill in;
art is made in the sprite studio and not counted). data/discord_announced.json remembers who was announced,
so each Pokemon is posted once. Without a webhook nothing is posted, but the list is still kept up to date,
so turning the webhook on later does not post every finished Pokemon at once.
"""
import json
import os
import urllib.request

import dexlib
from dexlib import ROOT

STATE = ROOT / "data" / "discord_announced.json"
SITE = "https://arvindfroi.github.io/sigma-dex/"
FILLED = [(section, label, test) for section, label, test in dexlib.CHECKS if section != "Art"]


def done(data):
    return all(test(data) for _, _, test in FILLED)


def post(url, data, sid):
    designer = ((data.get("credits") or {}).get("designer") or "").strip()
    sprite = ROOT / "assets" / "sprites-ds" / sid / "front.png"
    embed = {"title": "%s er 100 %% ferdig!" % data.get("name", sid), "url": SITE + "#" + sid, "color": 0x6F55C4,
             "description": "#%03d %s%s" % (data.get("dex") or 0, " / ".join(data.get("types") or []),
                                             ("\nDesignet av " + designer) if designer else "")}
    if sprite.is_file():
        embed["thumbnail"] = {"url": SITE + "art/%s/ds-front.png" % sid}
    body = json.dumps({"username": "Sigma Dex", "embeds": [embed]}).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "sigma-dex"})
    urllib.request.urlopen(request, timeout=30).read()


def main():
    species, problems = dexlib.load_species()
    if problems:
        return 0
    announced = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None
    finished = {sid: data for sid, _, data in species if done(data)}
    if announced is None:                       # first run: remember who is done already, post nothing
        STATE.write_text(json.dumps(sorted(finished), indent=1) + "\n", encoding="utf-8")
        print("Discord: %d finished Pokemon remembered, nothing posted (first run)." % len(finished))
        return 0
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    new = [sid for sid in sorted(finished, key=lambda s: finished[s].get("dex") or 999) if sid not in announced]
    posted = []
    for sid in new:
        if url:
            try:
                post(url, finished[sid], sid)
            except OSError as error:
                print("Discord: could not post %s (%s); tried again next time." % (sid, error))
                continue
        posted.append(sid)
    if posted:
        STATE.write_text(json.dumps(sorted(set(announced) | set(posted)), indent=1) + "\n", encoding="utf-8")
    print("Discord: %d newly finished, %s." % (len(posted), "posted" if url else "no webhook set, only remembered"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
