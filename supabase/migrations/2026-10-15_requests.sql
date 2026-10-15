-- Migration "requests" (2026-10-15): the request board on the website (REQUESTS). A card is saved
-- as a row of kind 'request'; the newest row of a card (species_id) is what the board shows, so
-- moving a card to another column is one more row. scripts/import_web.py skips these rows: the
-- board lives in the database only (cards written by the team are in data/requests.yaml).
--
-- NOT applied yet (needs Arvind's yes). submit_edit (key check, 300 edits per hour) is unchanged
-- and inserts whatever kind it is given.
--
-- Row layout: kind = 'request', species_id = 'req-<words>-<time>',
--   data = {"title": "...", "text": "...", "area": "pokemon|sprites|website|other",
--           "status": "idea|needed|doing|done", "by": "<name>"}

alter table public.species_edits drop constraint species_edits_kind_check;
alter table public.species_edits
  add constraint species_edits_kind_check check (kind in ('species', 'move', 'ability', 'reorder', 'request'));

alter table public.species_edits
  add constraint species_edits_request_check check (
    kind <> 'request'
    or (species_id ~ '^req-[a-z0-9-]{1,70}$'
        and jsonb_typeof(data -> 'title') = 'string'
        and char_length(data ->> 'title') between 3 and 120
        and coalesce(char_length(data ->> 'text'), 0) <= 1000
        and coalesce(data ->> 'status', 'idea') in ('idea', 'needed', 'doing', 'done')
        and coalesce(data ->> 'area', 'other') in ('pokemon', 'sprites', 'website', 'other'))
  );
