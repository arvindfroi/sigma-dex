#!/usr/bin/env python3
"""Download every message and attachment (concept art!) from a Discord channel.

Uses Discord's official bot API, so it is allowed by Discord's rules - unlike "self-bot"
tools that log in with your personal account. Setup (docs/DISCORD.md has the full steps):

    export DISCORD_BOT_TOKEN=...          # never put the token in a file in this repo
    python3 scripts/discord_export.py CHANNEL_ID

Output goes to discord-export/<channel id>/ (ignored by git, because it contains
everybody's private chat messages): messages.json, messages.md and attachments/.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://discord.com/api/v10"
ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "DiscordBot (https://github.com/arvindfroi/sigma-dex, 1.0)"


def api_get(path, token):
    request = urllib.request.Request(API + path, headers={"Authorization": "Bot " + token, "User-Agent": USER_AGENT})
    while True:
        try:
            with urllib.request.urlopen(request) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429:  # rate limited: wait as long as Discord asks, then retry
                time.sleep(float(json.load(error).get("retry_after", 1)) + 0.1)
                continue
            hints = {401: "the bot token is wrong", 403: "the bot cannot see this channel (give it View Channel + Read Message History)",
                     404: "no such channel - check the channel ID"}
            sys.exit("Discord answered %d: %s" % (error.code, hints.get(error.code, error.reason)))


def main():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if len(sys.argv) != 2 or not sys.argv[1].isdigit() or not token:
        sys.exit(__doc__)
    channel = sys.argv[1]
    out = ROOT / "discord-export" / channel
    (out / "attachments").mkdir(parents=True, exist_ok=True)

    messages, before = [], None
    while True:
        batch = api_get("/channels/%s/messages?limit=100%s" % (channel, "&before=" + before if before else ""), token)
        if not batch:
            break
        messages.extend(batch)
        before = batch[-1]["id"]
        print("fetched %d messages..." % len(messages))
    messages.reverse()  # oldest first
    (out / "messages.json").write_text(json.dumps(messages, indent=2, ensure_ascii=False), encoding="utf-8")

    lines, downloaded = [], 0
    for message in messages:
        author = message.get("author", {}).get("global_name") or message.get("author", {}).get("username", "?")
        lines.append("**%s** (%s): %s" % (author, message.get("timestamp", "")[:16].replace("T", " "), message.get("content", "")))
        for attachment in message.get("attachments", []):
            name = "%s_%s" % (message["id"], re.sub(r"[^A-Za-z0-9._-]", "_", attachment.get("filename", "file")))
            target = out / "attachments" / name
            if not target.exists():
                request = urllib.request.Request(attachment["url"], headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request) as response:
                    target.write_bytes(response.read())
                downloaded += 1
            lines.append("  - attachment: attachments/%s" % name)
        if not message.get("content") and not message.get("attachments") and message.get("embeds"):
            lines.append("  - (embed only)")
    (out / "messages.md").write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    print("Done: %d messages, %d new attachments -> %s" % (len(messages), downloaded, out.relative_to(ROOT)))
    if messages and not any(m.get("content") for m in messages):
        print("All messages are empty: turn on 'Message Content Intent' for the bot in the Discord Developer Portal.")


if __name__ == "__main__":
    main()
