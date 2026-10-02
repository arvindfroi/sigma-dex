# Getting everything out of the Discord channel

The concept art and a lot of decisions only exist in Discord. `scripts/discord_export.py`
downloads every message and every attachment from a channel in one go.

It uses Discord's official bot API. That is the only way that is allowed: tools that log in
with your personal account ("self-bots", or DiscordChatExporter with a user token) break
Discord's terms of service and can get the account banned.

## One-time setup (about 5 minutes)

Someone with the **Manage Server** permission on the server has to do steps 3-4.

1. Go to <https://discord.com/developers/applications>, click **New Application**, name it
   (e.g. "Sigma Dex Export").
2. Open **Bot** in the left menu. Turn on **Message Content Intent**. Click **Reset Token**
   and copy the token. Treat it like a password - never paste it into Discord, a file in
   this repo, or a chat.
3. Open **OAuth2 > URL Generator**. Tick **bot**, then the permissions **View Channels** and
   **Read Message History**. Open the generated URL and add the bot to the server.
4. If the channel is private, add the bot to it (channel settings > Permissions).
5. In Discord: **Settings > Advanced > Developer Mode** on, then right-click the channel >
   **Copy Channel ID**.

## Run it

```bash
export DISCORD_BOT_TOKEN=paste-the-token-here
```

Or save the token as the only line of a file named `.discord-token` in this folder (git
ignores it).

```bash
python3 scripts/discord_export.py CHANNEL_ID
```

The result lands in `discord-export/<channel id>/`:

- `messages.md` - the whole conversation, readable, oldest first
- `messages.json` - the same with all details
- `attachments/` - every image and file, prefixed with the message ID

That folder is ignored by git on purpose: it holds everyone's private messages. Go through
it, copy the art that belongs to a Pokemon into `assets/concept-art/<species>.png`, and
move the decisions into the species files. Running the script again later only downloads
new attachments.

When you are done, remove the bot from the server or reset its token.
