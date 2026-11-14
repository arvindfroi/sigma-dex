-- Migration "shiny and cry" (2026-11-14): a Pokemon's SHINY and CRY tabs on the website save rows of kind 'shiny' and
-- 'cry'. species_id = the Pokemon (its file name). shiny data = {"map": {"#rrggbb": "#rrggbb", ...}, "follower": {...},
-- "sliders": [...], ...}; cry data = a recipe from scripts/cry_engine.js {"layers": [{"dex": 1-493, ...}], ...}.
-- {"deleted": true} removes one. The newest row of a Pokemon wins. scripts/import_web.py writes them to
-- assets/shiny/<pokemon>.json and assets/cries/<pokemon>.json. submit_edit (key check, 300 edits per hour) is unchanged.

alter table public.species_edits drop constraint species_edits_kind_check;
alter table public.species_edits
  add constraint species_edits_kind_check check (kind in ('species', 'move', 'ability', 'reorder', 'request', 'team', 'teamnote', 'claim', 'shiny', 'cry'));

alter table public.species_edits
  add constraint species_edits_shiny_check check (
    kind <> 'shiny'
    or coalesce((data ->> 'deleted')::boolean, false)
    or (jsonb_typeof(data -> 'map') = 'object' and pg_column_size(data) < 12000)
  );

alter table public.species_edits
  add constraint species_edits_cry_check check (
    kind <> 'cry'
    or coalesce((data ->> 'deleted')::boolean, false)
    or (jsonb_typeof(data -> 'layers') = 'array'
        and jsonb_array_length(data -> 'layers') between 1 and 3
        and pg_column_size(data) < 6000)
  );
