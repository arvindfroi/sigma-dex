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
   - **Raw pictures of unpicked studio tries live only here** (since 2026-11-13). After downloading, the backup sends
     the raws it holds with their sizes to the `sprite-worker` function (`prune_raws`, worker key from
     `SIGMA_WORKER_KEY_FILE`, default `D:\LocalAI\sigma-worker\worker.key`), which removes from the website storage
     every raw whose tries are all unpicked, have no follow-up try, were used by no job and finished more than a day
     ago (`RAW_DAYS`, rule in `raw_prune_candidates`), and only if the backup holds it at the same size. The path
     stays in `sprite_tries.raw`. Why: Supabase's free plan holds 1.1 GB, the bucket had reached 2.19 GB, 1.9 GB of
     it raws (a front's raw ~1.4 MB, its sprite 2 KB), and the website never shows a raw. Picked raws stay on the
     website. This is the only thing the backup ever deletes, and it never deletes here.
   - `backup.log`: one line per night with the free space left; a line with PROBLEMS means something was not copied
     or that less than 3 GB is free. Below 1.5 GB free no new pictures are downloaded, so the disk never fills up.

## Restoring

- A species file or picture: `git log -- data/species/<id>.yaml` in any clone (or in the mirror) and check out the old
  version. A Pokemon removed on the website comes back by taking its file from history and deleting its line from
  `data/removed_species.json`.
- The whole repository: `git clone D:\SigmaBackup\git\sigma-dex.git` gives every branch; `git reflog show main` in the
  mirror lists every state `main` has had.
- A database table: unzip `db\<date>\<table>.json.gz`; each file is a JSON list of rows, ready to insert again.
- Pictures: `files\<path>` is the same path as in the "art" storage. A pruned raw goes back by uploading
  `files\<path>` to the same path in the "art" bucket.

## The task script

`D:\SigmaBackup\run-backup.ps1` (only on the Legion) fetches the mirror, takes `scripts/` from `main` and runs
`backup.py`; its own output goes to `task-output.log`. Native commands (git, tar, python) run with
`$ErrorActionPreference = "Continue"` and are judged by their exit code: Windows PowerShell turns git's progress on
stderr ("From https://...") into an error, and with "Stop" that killed every night's run from 2026-11-12 (the task
showed result 1, nothing was logged) until it was fixed on 2026-11-13. A night without a new `backup.log` line
means the script itself stopped: look at `task-output.log` and the task's last result.
