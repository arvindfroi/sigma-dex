-- Migration "character claims" (2026-11-11): MORE > Characters on the website, where each person in the group claims a
-- character of the game (gym leader, Elite Four, villain ...) to be replaced by themselves. The roles are listed without
-- names in data/characters.yaml (no spoilers). A claim is a row of kind 'claim': species_id = 'claim-<role id>',
-- data = {"by": "<name>" or "" when released, "role": "<role id>"}; the newest row of a role wins.
-- scripts/import_web.py skips these rows. submit_edit (key check, 300 edits per hour) is unchanged.

alter table public.species_edits drop constraint species_edits_kind_check;
alter table public.species_edits
  add constraint species_edits_kind_check check (kind in ('species', 'move', 'ability', 'reorder', 'request', 'team', 'teamnote', 'claim'));

alter table public.species_edits
  add constraint species_edits_claim_check check (
    kind <> 'claim'
    or (species_id ~ '^claim-[a-z0-9-]{1,34}$'
        and coalesce(char_length(data ->> 'by'), 0) <= 40
        and coalesce(char_length(data ->> 'note'), 0) <= 300)
  );
