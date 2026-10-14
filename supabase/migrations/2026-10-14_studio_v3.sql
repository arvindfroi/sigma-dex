-- Sprite studio v3 (2026-10-14): step by step, the people choose. Arvind: "the pickers miss every time; we need a picking page
-- in the sprite studio that is clear and easy to use, that shows how long pictures take so it does not just load, where the
-- users have real control and can keep working on the sprites they like best".
-- Every picture the worker draws is a TRY (one row, with its time); a job draws several tries of one STAGE:
--   art    the creature cut out of a chosen picture (base Qwen)          from: species pictures
--   front  the DS front (front LoRA)                                      from: an art try or a species picture
--   back   the DS back, on the front's colours (back LoRA)                from: a front try
--   icon   the menu icon (icon LoRA: the PC box recipe and canvas swap)   from: a front try
-- People can also mirror a try or draw on it (new details, a changed design): that is a new try of the same step, saved
-- by the sprite-draw function, and the next steps can be made from it.
-- People pick tries; picked front + back + icon are put together into a version (sprite_candidates), approved as before.
-- Nothing existing is removed: the old buttons (request_sprites, request_sprite_edit) keep working.

create table public.sprite_tries (
  id bigint generated always as identity primary key,
  job_id bigint references public.sprite_jobs (id) on delete cascade,   -- null for one drawn or mirrored on the website
  species_id text not null,
  stage text not null check (stage in ('art', 'front', 'back', 'icon')),
  recipe text check (length(recipe) <= 60),
  n int not null check (n between 1 and 16),
  seed bigint,
  status text not null default 'drawing' check (status in ('drawing', 'done', 'broken', 'failed')),
  image text,                                 -- the finished picture (art 640, front / back 80x80, icon 32x32)
  raw text,                                   -- what the model drew, before reading it as pixels
  note text check (length(note) <= 300),      -- why it is broken, or what it was asked
  expected_seconds real,
  seconds real,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  parent_try bigint references public.sprite_tries (id),
  editor text check (length(editor) <= 40),  -- who drew or mirrored it (website tries)
  picked boolean not null default false,
  picked_by text check (length(picked_by) <= 40),
  picked_at timestamptz,
  created_at timestamptz not null default now(),
  unique (job_id, n));
create index sprite_tries_species on public.sprite_tries (species_id, stage, id desc);
alter table public.sprite_tries enable row level security;
create policy "Anyone can see sprite tries" on public.sprite_tries for select to anon, authenticated using (true);

alter table public.sprite_jobs
  add column stage text check (stage in ('art', 'front', 'back', 'icon')),
  add column count int check (count between 1 and 16),
  add column from_try bigint references public.sprite_tries (id),
  add column prompt text check (length(prompt) <= 800),
  add column recipe text check (length(recipe) <= 60);
alter table public.sprite_jobs drop constraint sprite_jobs_mode_check;
alter table public.sprite_jobs add constraint sprite_jobs_mode_check check (mode in ('new', 'edit', 'tries'));

-- Seconds per try, measured by the worker (a recent average per stage), so the website can say how long things take.
alter table public.sprite_worker add column timings jsonb check (timings is null or pg_column_size(timings) < 2000);

-- Ask for tries of one stage.
create function public.request_tries(p_species_id text, p_stage text, p_count int, p_from_try bigint, p_refs bigint[],
                                     p_prompt text, p_recipe text, p_editor text)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; new_id bigint;
begin
  if p_stage not in ('art', 'front', 'back', 'icon') then raise exception 'Unknown step'; end if;
  if p_count is null or p_count < 1 or p_count > 16 then raise exception 'Ask for 1 to 16 pictures'; end if;
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running')) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour') >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  if exists (select 1 from unnest(coalesce(p_refs, '{}')) r
             where not exists (select 1 from public.species_images i where i.id = r and i.species_id = p_species_id and not i.removed)) then
    raise exception 'A reference picture does not belong to this Pokemon';
  end if;
  if p_from_try is not null then
    select * into t from public.sprite_tries where id = p_from_try;
    if not found or t.species_id <> p_species_id then raise exception 'That picture does not belong to this Pokemon'; end if;
    if t.status <> 'done' then raise exception 'That picture is not finished'; end if;
  end if;
  if p_stage = 'art' and coalesce(array_length(p_refs, 1), 0) = 0 then raise exception 'Choose a picture to cut the creature out of'; end if;
  if p_stage = 'front' and p_from_try is null and coalesce(array_length(p_refs, 1), 0) = 0 then raise exception 'Choose the art to draw from'; end if;
  if p_stage = 'front' and p_from_try is not null and t.stage not in ('art', 'front') then raise exception 'A front is drawn from art'; end if;
  if p_stage in ('back', 'icon') and (p_from_try is null or t.stage <> 'front') then raise exception 'Choose the front first'; end if;
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (p_species_id, p_species_id || ' sprite', nullif(trim(p_prompt), ''), coalesce(p_refs, '{}'), 1, nullif(trim(p_editor), ''),
          'three-quarter', 'ds', 'tries', p_stage, p_count, p_from_try, nullif(trim(p_prompt), ''), nullif(trim(p_recipe), ''))
  returning id into new_id;
  return new_id;
end $$;
revoke all on function public.request_tries(text, text, int, bigint, bigint[], text, text, text) from public;
grant execute on function public.request_tries(text, text, int, bigint, bigint[], text, text, text) to anon, authenticated;

-- Pick a try (or take the pick back). The picks are kept: who chose what, among which (the answer key for the pickers).
create function public.pick_try(p_try bigint, p_picked boolean, p_editor text)
returns boolean language plpgsql security definer set search_path = '' as $$
begin
  update public.sprite_tries set picked = coalesce(p_picked, true), picked_by = nullif(trim(p_editor), ''), picked_at = now()
   where id = p_try and status in ('done', 'broken');
  if not found then raise exception 'That picture does not exist'; end if;
  return coalesce(p_picked, true);
end $$;
revoke all on function public.pick_try(bigint, boolean, text) from public;
grant execute on function public.pick_try(bigint, boolean, text) to anon, authenticated;

-- Put a picked front, back and icon together into a version, which is then approved as before (review_sprite).
create function public.assemble_sprite(p_front bigint, p_back bigint, p_icon bigint, p_editor text)
returns bigint language plpgsql security definer set search_path = '' as $$
declare f public.sprite_tries; b public.sprite_tries; i public.sprite_tries; new_id bigint;
begin
  select * into f from public.sprite_tries where id = p_front and stage = 'front' and status = 'done';
  if not found then raise exception 'Choose a finished front'; end if;
  select * into b from public.sprite_tries where id = p_back and stage = 'back' and status = 'done' and species_id = f.species_id;
  if not found then raise exception 'Choose a finished back of the same Pokemon'; end if;
  if p_icon is not null then
    select * into i from public.sprite_tries where id = p_icon and stage = 'icon' and status = 'done' and species_id = f.species_id;
    if not found then raise exception 'Choose a finished icon of the same Pokemon'; end if;
  end if;
  insert into public.sprite_candidates (job_id, species_id, seed, prompt, style_version, raw_front, raw_back, front, back, icon, gen, kind, note, editor)
  values (f.job_id, f.species_id, f.seed,
          format('put together from tries: front #%s (%s), back #%s (%s), icon %s', f.id, f.recipe, b.id, b.recipe, coalesce('#' || i.id || ' (' || i.recipe || ')', 'none')),
          'studio-v3', f.raw, b.raw, f.image, b.image, i.image, 4, 'ai', null, nullif(trim(p_editor), ''))
  returning id into new_id;
  return new_id;
end $$;
revoke all on function public.assemble_sprite(bigint, bigint, bigint, text) from public;
grant execute on function public.assemble_sprite(bigint, bigint, bigint, text) to anon, authenticated;

-- The worker's claim: as before, plus the try fields; a job of tries may run long (8 fronts on a warm laptop GPU took up
-- to 23 minutes), so a job is put back in line only after 90 minutes instead of 30.
create or replace function public.claim_sprite_job()
returns jsonb language plpgsql security definer set search_path = '' as $$
declare j public.sprite_jobs;
begin
  insert into public.sprite_worker (id, seen_at, state) values (1, now(), 'idle')
  on conflict (id) do update set seen_at = now();
  update public.sprite_jobs set status = 'queued', started_at = null
   where status = 'running' and started_at < now() - interval '90 minutes';
  select * into j from public.sprite_jobs where status = 'queued' order by id limit 1 for update skip locked;
  if not found then
    update public.sprite_worker set state = 'idle' where id = 1;
    return null;
  end if;
  update public.sprite_jobs set status = 'running', started_at = now() where id = j.id;
  update public.sprite_worker set state = 'drawing ' || j.species_id where id = 1;
  delete from public.sprite_tries where job_id = j.id;              -- a job put back in line starts over
  return jsonb_build_object(
    'id', j.id, 'species_id', j.species_id, 'look', j.look, 'notes', j.notes, 'variations', j.variations,
    'pose', j.pose, 'style', j.style, 'mode', j.mode, 'view', j.view, 'area', j.area,
    'stage', j.stage, 'count', j.count, 'prompt', j.prompt, 'recipe', j.recipe,
    'refs', (select coalesce(jsonb_agg(i.path order by array_position(j.ref_image_ids, i.id)), '[]') from public.species_images i where i.id = any (j.ref_image_ids) and not i.removed),
    'parent', (select jsonb_build_object('id', c.id, 'raw_front', c.raw_front, 'raw_back', c.raw_back, 'seed', c.seed,
                                         'front', c.front, 'back', c.back, 'icon', c.icon, 'gen', c.gen)
                 from public.sprite_candidates c where c.id = j.parent_candidate),
    'from_try', (select jsonb_build_object('id', t.id, 'stage', t.stage, 'image', t.image, 'raw', t.raw, 'recipe', t.recipe,
                                           'parent', (select jsonb_build_object('id', p.id, 'stage', p.stage, 'image', p.image)
                                                        from public.sprite_tries p where p.id = t.parent_try))
                   from public.sprite_tries t where t.id = j.from_try),
    'comments', (select coalesce(jsonb_agg(jsonb_build_object('body', m.body, 'x', m.x, 'y', m.y) order by m.id), '[]')
                   from public.sprite_comments m where m.candidate_id = j.parent_candidate));
end $$;

-- Housekeeping keeps the tries' pictures too.
create or replace function public.art_orphans()
returns setof text language sql security definer set search_path = '' as $$
  select o.name from storage.objects o
   where o.bucket_id = 'art' and o.created_at < now() - interval '5 minutes'
     and not exists (select 1 from public.species_images i where i.path = o.name)
     and not exists (select 1 from public.sprite_candidates c where o.name in (c.raw_front, c.raw_back, c.front, c.back, c.preview, c.icon))
     and not exists (select 1 from public.sprite_tries t where o.name in (t.image, t.raw));
$$;
