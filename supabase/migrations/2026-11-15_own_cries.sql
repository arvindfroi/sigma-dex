-- Migration "own cries" (2026-11-15): the CRY tab can save someone's own sound (an upload or a recording) with the
-- recipe, as data.audio = base64 of mono 16-bit PCM at 13379 Hz, at most 2 seconds (71 356 characters). Such a row may
-- be up to 100 000 bytes; every other row keeps the old limits (20 000 bytes, a cry without a sound 6000).
-- scripts/import_web.py writes the sound to assets/cries/<pokemon>.wav. submit_edit is unchanged.

alter table public.species_edits drop constraint species_edits_data_check;
alter table public.species_edits
  add constraint species_edits_data_check check (
    jsonb_typeof(data) = 'object'
    and (pg_column_size(data) < 20000
         or (kind = 'cry' and jsonb_typeof(data -> 'audio') = 'string' and pg_column_size(data) < 100000))
  );

alter table public.species_edits drop constraint species_edits_cry_check;
alter table public.species_edits
  add constraint species_edits_cry_check check (
    kind <> 'cry'
    or coalesce((data ->> 'deleted')::boolean, false)
    or (jsonb_typeof(data -> 'layers') = 'array'
        and jsonb_array_length(data -> 'layers') between 1 and 3
        and (pg_column_size(data) < 6000
             or (jsonb_typeof(data -> 'audio') = 'string' and char_length(data ->> 'audio') <= 72000 and pg_column_size(data) < 100000)))
  );
