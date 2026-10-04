-- Migration "reorder" (2026-10-04): the website can move Pokemon to other dex numbers and add
-- empty slots between two Pokemon. A move is saved as ONE row of kind 'reorder', so it is applied
-- completely or not at all by scripts/import_web.py.
--
-- NOT applied yet. Run it once in the Supabase SQL editor (project "sigma-dex").
-- It only widens the allowed kinds; submit_edit (key check, 300 edits per hour limit) is unchanged
-- and already inserts whatever kind it is given, so a reorder counts as one edit in the limit
-- and shows up in the history like any other row.
--
-- Row layout: kind = 'reorder', species_id = 'reorder',
--   data = {"ops": [ {"op":"move","id":"<species id>","to":12}, {"op":"insert","at":30}, {"op":"close","at":40} ]}
-- The steps are applied in order (rules: dexlib.change_layout). They refer to Pokemon by id and
-- are checked again by the import (numbers inside the dex, last slot free for an insert, ...).

alter table public.species_edits drop constraint species_edits_kind_check;
alter table public.species_edits
  add constraint species_edits_kind_check check (kind in ('species', 'move', 'ability', 'reorder'));

-- A reorder must look like one: fixed id, 1-50 steps. (Existing rows are unaffected.)
alter table public.species_edits
  add constraint species_edits_reorder_check check (
    kind <> 'reorder'
    or (species_id = 'reorder'
        and jsonb_typeof(data -> 'ops') = 'array'
        and jsonb_array_length(data -> 'ops') between 1 and 50)
  );
