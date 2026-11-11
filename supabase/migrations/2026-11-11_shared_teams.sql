-- Migration "shared teams" (2026-11-11): the team library on the website (TEAMS > Shared teams).
-- Arvind asked for a shared place where the group can share and comment on teams. Like the request
-- board it lives in the database only; scripts/import_web.py skips these rows.
--
-- Row layout:
--   kind = 'team',     species_id = 'team-<words>-<time>', data = {"name": "...", "text": "<Showdown export>",
--                      "by": "<name>", "deleted": true when taken down}. The newest row of a team wins.
--   kind = 'teamnote', species_id = the team's id,          data = {"text": "<comment>", "by": "<name>"}.
--                      Every row is one comment.
-- It only widens the allowed kinds and adds checks; submit_edit (key check, 300 edits per hour) is unchanged.

alter table public.species_edits drop constraint species_edits_kind_check;
alter table public.species_edits
  add constraint species_edits_kind_check check (kind in ('species', 'move', 'ability', 'reorder', 'request', 'team', 'teamnote'));

alter table public.species_edits
  add constraint species_edits_team_check check (
    kind not in ('team', 'teamnote')
    or (species_id ~ '^team-[a-z0-9-]{1,35}$'
        and (kind <> 'team' or (jsonb_typeof(data -> 'name') = 'string'
                                and char_length(data ->> 'name') between 1 and 60
                                and coalesce(char_length(data ->> 'text'), 0) <= 8000))
        and (kind <> 'teamnote' or (jsonb_typeof(data -> 'text') = 'string'
                                    and char_length(data ->> 'text') between 1 and 1000)))
  );
