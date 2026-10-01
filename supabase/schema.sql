-- The database behind the website's edit form (Supabase project "sigma-dex").
-- Kept here for reference; it is already applied.

-- Every save on the website adds one row here. Rows are never changed or deleted,
-- so the table is also the full edit history. The repository imports new rows.
create table public.species_edits (
  id bigint generated always as identity primary key,
  species_id text not null check (species_id ~ '^[a-z0-9]+(-[a-z0-9]+)*$' and length(species_id) <= 40),
  data jsonb not null check (jsonb_typeof(data) = 'object' and pg_column_size(data) < 20000),
  editor text check (length(editor) <= 40),
  created_at timestamptz not null default now()
);

alter table public.species_edits enable row level security;

create policy "Anyone can read edits" on public.species_edits
  for select to anon, authenticated using (true);

-- Not reachable through the API: holds the hash of the edit key.
create schema if not exists private;
create table private.settings (
  key text primary key,
  value text not null
);

-- The only way to write: checks the edit key (when one is set) and a flood limit.
create function public.submit_species(p_key text, p_species_id text, p_data jsonb, p_editor text)
returns bigint
language plpgsql
security definer
set search_path = ''
as $$
declare
  expected text;
  new_id bigint;
begin
  select value into expected from private.settings where key = 'edit_key_sha256';
  if expected is not null
     and encode(sha256(convert_to(coalesce(p_key, ''), 'UTF8')), 'hex') <> expected then
    raise exception 'Wrong edit key' using errcode = '28000';
  end if;
  if (select count(*) from public.species_edits where created_at > now() - interval '1 hour') >= 300 then
    raise exception 'Too many edits in the last hour, try again later' using errcode = '54000';
  end if;
  insert into public.species_edits (species_id, data, editor)
  values (p_species_id, p_data, nullif(trim(p_editor), ''))
  returning id into new_id;
  return new_id;
end;
$$;

revoke all on function public.submit_species(text, text, jsonb, text) from public;
grant execute on function public.submit_species(text, text, jsonb, text) to anon, authenticated;

create index species_edits_created_at_idx on public.species_edits (created_at);

-- Set or change the edit key (run in the Supabase SQL editor, with your own key):
--   insert into private.settings (key, value)
--   values ('edit_key_sha256', encode(sha256(convert_to('YOUR NEW KEY', 'UTF8')), 'hex'))
--   on conflict (key) do update set value = excluded.value;
-- Remove the key so anyone can save:
--   delete from private.settings where key = 'edit_key_sha256';
