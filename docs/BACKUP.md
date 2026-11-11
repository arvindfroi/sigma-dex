# Backup

Everything is kept in three places:

1. **GitHub** (`arvindfroi/sigma-dex`): the full history of every species file, picture and sprite. There is no
   rule against force-pushes on GitHub (Arvind, 2026-11-11: not needed); the Legion's mirror below keeps every old
   commit anyway.
2. **The website's database** (Supabase): the edit log, uploaded pictures, the request board and the sprite studio.
3. **The Legion, `D:\SigmaBackup`**, written every night at 04:17 by `scripts/backup.py` (Windows task
   "Sigma dex backup"). It only ever adds, and on a night when nothing changed it writes nothing but the log line:
   - `git\sigma-dex.git`: a mirror of GitHub whose reflogs never expire, so old commits survive even a force-push.
   - `db\<date>\<table>.json.gz`: every table of the database, one folder per day on which something changed
     (`state.json` remembers what the last run saw).
   - `files\...`: every picture the database points to (uploads, Lost and found, studio tries), downloaded once.
   - `backup.log`: one line per night; a line with PROBLEMS means something was not copied.

## Restoring

- A species file or picture: `git log -- data/species/<id>.yaml` in any clone (or in the mirror) and check out the old
  version. A Pokemon removed on the website comes back by taking its file from history and deleting its line from
  `data/removed_species.json`.
- The whole repository: `git clone D:\SigmaBackup\git\sigma-dex.git` gives every branch; `git reflog show main` in the
  mirror lists every state `main` has had.
- A database table: unzip `db\<date>\<table>.json.gz`; each file is a JSON list of rows, ready to insert again.
- Pictures: `files\<path>` is the same path as in the "art" storage.
