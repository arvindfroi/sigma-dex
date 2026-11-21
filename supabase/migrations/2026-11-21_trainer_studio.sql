-- Migration "trainer studio" (2026-11-21): trainer battle sprites made on the website (docs/ART.md#the-trainer-studio).
-- A person uploads a picture (of themself for MY TRAINER, of their own character for CREATE NPC), picks a real gen 4 trainer
-- class as the base and a strength; the drawing PC repaints the base with the trainer LoRA (scripts/trainer_studio.py).
-- The jobs share the sprite studio's line: sprite_jobs / sprite_tries with stage 'trainer', species_id = the slot
-- ('trainer-<role id>' for a claimed character, 'npc-<id>' for an NPC), recipe = the base ('hgss:12' / 'pt:beauty'),
-- prompt = JSON {strength, fields, photo}.

alter table public.sprite_jobs drop constraint sprite_jobs_stage_check;
alter table public.sprite_jobs add constraint sprite_jobs_stage_check check (stage = any (array['art', 'front', 'back', 'icon', 'follower', 'trainer']));
alter table public.sprite_tries drop constraint sprite_tries_stage_check;
alter table public.sprite_tries add constraint sprite_tries_stage_check check (stage = any (array['art', 'front', 'back', 'icon', 'follower', 'trainer']));
-- a trainer's text fields are longer than a sprite prompt
alter table public.sprite_jobs drop constraint sprite_jobs_prompt_check;
alter table public.sprite_jobs add constraint sprite_jobs_prompt_check check (length(prompt) <= 3000);

-- NPCs made on the website: species_edits rows of kind 'npc', species_id 'npc-<id>', data = {name, by, about, sprite, deleted};
-- the newest row of an id wins (as claims). scripts/import_web.py skips them.
alter table public.species_edits drop constraint species_edits_kind_check;
alter table public.species_edits add constraint species_edits_kind_check
  check (kind = any (array['species', 'move', 'ability', 'reorder', 'request', 'team', 'teamnote', 'claim', 'shiny', 'cry', 'npc']));
alter table public.species_edits add constraint species_edits_npc_check check (
  kind <> 'npc'
  or (species_id ~ '^npc-[a-z0-9-]{1,36}$'
      and coalesce(char_length(data ->> 'name'), 0) <= 40
      and coalesce(char_length(data ->> 'by'), 0) <= 40
      and coalesce(char_length(data ->> 'about'), 0) <= 300));

-- The uploaded pictures are PRIVATE: a photo of a person must never be public without their consent. Only the edge
-- functions (service role) read them: the drawing PC gets a short-lived link for the job it draws. The uploader gets a
-- token (kept on their device) that removes the picture again.
insert into storage.buckets (id, name, public) values ('trainer-photos', 'trainer-photos', false) on conflict (id) do nothing;
create table if not exists public.trainer_photos (
  id bigserial primary key,
  slot text not null check (slot ~ '^(trainer|npc)-[a-z0-9-]{1,36}$'),
  path text not null,
  token_sha256 text not null,
  editor text check (length(editor) <= 40),
  created_at timestamptz not null default now()
);
alter table public.trainer_photos enable row level security;     -- no policies: the website cannot read the list

create or replace function public.request_trainer(p_slot text, p_base text, p_strength real, p_count integer, p_fields jsonb,
                                                  p_photo bigint, p_ref bigint, p_editor text)
returns bigint language plpgsql security definer set search_path = '' as $$
declare new_id bigint; k text;
begin
  if p_slot !~ '^(trainer|npc)-[a-z0-9-]{1,36}$' then raise exception 'Unknown trainer'; end if;
  if p_base !~ '^(hgss:[0-9]{1,3}|pt:[a-z0-9_]{1,40})$' then raise exception 'Choose a base trainer'; end if;
  if p_strength is null or p_strength < 0.5 or p_strength > 0.95 then raise exception 'The strength is 0.5 to 0.95'; end if;
  if p_count is null or p_count < 1 or p_count > 4 then raise exception 'Ask for 1 to 4 pictures'; end if;
  if jsonb_typeof(p_fields) <> 'object' then raise exception 'The description is missing'; end if;
  for k in select jsonb_object_keys(p_fields) loop
    if k not in ('cls', 'who', 'skin', 'hair', 'clothes', 'extra', 'held', 'pose', 'facing', 'build', 'mood') then raise exception 'Unknown field %', k; end if;
    if jsonb_typeof(p_fields -> k) <> 'string' or char_length(p_fields ->> k) > 240 then raise exception 'The field % is too long', k; end if;
  end loop;
  if (p_photo is null) = (p_ref is null) then raise exception 'Choose one picture'; end if;
  if p_photo is not null and not exists (select 1 from public.trainer_photos where id = p_photo and slot = p_slot) then
    raise exception 'That picture is gone, upload it again';
  end if;
  if p_ref is not null and not exists (select 1 from public.species_images where id = p_ref and species_id = p_slot and not removed) then
    raise exception 'That picture does not belong to this trainer';
  end if;
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running')) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour') >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, prompt, recipe)
  values (p_slot, p_slot || ' trainer', null, case when p_ref is null then '{}' else array[p_ref] end, 1, nullif(trim(p_editor), ''),
          'three-quarter', 'ds', 'tries', 'trainer', p_count,
          jsonb_build_object('strength', round(p_strength::numeric, 2), 'fields', p_fields, 'photo', p_photo)::text, p_base)
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer(text, text, real, integer, jsonb, bigint, bigint, text) to anon;

-- The worker says which steps it can draw (p_stages); a worker without the trainer code (no p_stages) never gets a
-- trainer job, so the website can take requests before every drawing PC has the new scripts.
drop function if exists public.claim_sprite_job();
create or replace function public.claim_sprite_job(p_stages text[] default null)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare j public.sprite_jobs;
begin
  insert into public.sprite_worker (id, seen_at, state) values (1, now(), 'idle')
  on conflict (id) do update set seen_at = now();
  update public.sprite_jobs set status = 'queued', started_at = null
   where status = 'running' and started_at < now() - interval '90 minutes';
  select * into j from public.sprite_jobs
   where status = 'queued' and (case when p_stages is null then coalesce(stage, '') <> 'trainer' else coalesce(stage, 'front') = any (p_stages) end)
   order by id limit 1 for update skip locked;
  if not found then
    update public.sprite_worker set state = 'idle' where id = 1;
    return null;
  end if;
  update public.sprite_jobs set status = 'running', started_at = now() where id = j.id;
  update public.sprite_worker set state = 'drawing ' || j.species_id where id = 1;
  delete from public.sprite_tries where job_id = j.id;
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
    'with_try', (select jsonb_build_object('id', t.id, 'stage', t.stage, 'image', t.image) from public.sprite_tries t where t.id = j.with_try),
    'comments', (select coalesce(jsonb_agg(jsonb_build_object('body', m.body, 'x', m.x, 'y', m.y) order by m.id), '[]')
                   from public.sprite_comments m where m.candidate_id = j.parent_candidate));
end $$;
revoke execute on function public.claim_sprite_job(text[]) from public, anon, authenticated;
grant execute on function public.claim_sprite_job(text[]) to service_role;

-- Housekeeping keeps the trainer bases (the grid on the website, put there by scripts/trainer_bases.py).
create or replace function public.art_orphans()
returns setof text language sql security definer set search_path = '' as $$
  select o.name from storage.objects o
   where o.bucket_id = 'art' and o.created_at < now() - interval '5 minutes'
     and o.name not like 'trainer-bases/%'
     and not exists (select 1 from public.species_images i where i.path = o.name)
     and not exists (select 1 from public.sprite_candidates c where o.name in (c.raw_front, c.raw_back, c.front, c.back, c.preview, c.icon, c.follower))
     and not exists (select 1 from public.sprite_tries t where o.name in (t.image, t.raw));
$$;
