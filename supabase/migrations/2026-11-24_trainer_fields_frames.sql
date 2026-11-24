-- Trainer studio (2026-11-24):
-- 1. The description fields of the PICTURE step (who, skin, hair, clothes ...) go with every later step too: the map figure,
--    VS, animation, back and throw jobs copy them from the trainer job (before, only the free words), so the drawing PC
--    describes the person the same way in every step (scripts/trainer_studio.py words_of).
-- 2. ANIM: the poses are not locked to one animation (Arvind: "jeg vil ikke at de framesa skal være låst til den animasjonen").
--    p_frames = a set of poses made earlier for this battle sprite (an anim try, maybe for another script): the job keeps them
--    (frames = its picture, frames_try) and draws only the poses the new script still lacks.
-- 3. Claude's batch jobs do not count against the map and VS queue limits (as in request_trainer).

create or replace function public.request_trainer_map(p_try bigint, p_count integer, p_editor text, p_extra text default null)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; j public.sprite_jobs; walk bigint; new_id bigint; settings jsonb;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'trainer' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Choose a finished battle sprite first'; end if;
  if p_count is null or p_count < 1 or p_count > 6 then raise exception 'Ask for 1 to 6 map figures'; end if;
  walk := t.id;                                   -- a drawn-on try has no job: its first try's job has the picture
  for i in 1..10 loop
    select * into j from public.sprite_jobs where id = (select job_id from public.sprite_tries where id = walk);
    exit when found;
    select parent_try into walk from public.sprite_tries where id = walk;
    exit when walk is null;
  end loop;
  if j.id is null then raise exception 'The picture of this trainer is gone'; end if;
  settings := coalesce(nullif(j.prompt, '')::jsonb, '{}'::jsonb);
  if (settings ->> 'photo') is not null and not exists (select 1 from public.trainer_photos where id = (settings ->> 'photo')::bigint and slot = t.species_id) then
    raise exception 'The uploaded picture is gone, upload it again in 1 PICTURE';
  end if;
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running') and not batch) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour' and not batch) >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' map', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'three-quarter', 'ds', 'tries', 'map', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'fields', settings -> 'fields', 'photo', settings -> 'photo', 'extra', nullif(left(trim(p_extra), 200), '')))::text, j.recipe)
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_map(bigint, integer, text, text) to anon;
create or replace function public.request_trainer_vs(p_try bigint, p_count integer, p_editor text)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; j public.sprite_jobs; walk bigint; new_id bigint; settings jsonb;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'trainer' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Choose a finished battle sprite first'; end if;
  if p_count is null or p_count < 1 or p_count > 4 then raise exception 'Ask for 1 to 4 pictures'; end if;
  walk := t.id;                                   -- a drawn-on try has no job: its first try's job has the picture
  for i in 1..10 loop
    select * into j from public.sprite_jobs where id = (select job_id from public.sprite_tries where id = walk);
    exit when found;
    select parent_try into walk from public.sprite_tries where id = walk;
    exit when walk is null;
  end loop;
  if j.id is null then raise exception 'The picture of this trainer is gone'; end if;
  settings := coalesce(nullif(j.prompt, '')::jsonb, '{}'::jsonb);
  if (settings ->> 'photo') is not null and not exists (select 1 from public.trainer_photos where id = (settings ->> 'photo')::bigint and slot = t.species_id) then
    raise exception 'The uploaded picture is gone, upload it again in 1 PICTURE';
  end if;
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running') and not batch) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour' and not batch) >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' vs', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'three-quarter', 'ds', 'tries', 'vs', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'fields', settings -> 'fields', 'photo', settings -> 'photo'))::text, j.recipe)
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_vs(bigint, integer, text) to anon;
create or replace function public.request_trainer_back(p_try bigint, p_shape text, p_count integer, p_editor text, p_extra text default null,
                                                       p_vs bigint default null)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; v public.sprite_tries; j public.sprite_jobs; new_id bigint; settings jsonb;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'trainer' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Choose a finished battle sprite first'; end if;
  if p_shape is null or p_shape not in ('long', 'short', 'spiky', 'cap', 'tied', 'stout') then raise exception 'Choose a shape first'; end if;
  if p_count is null or p_count < 1 or p_count > 8 then raise exception 'Ask for 1 to 8 backs'; end if;
  if p_vs is not null then
    select * into v from public.sprite_tries where id = p_vs and stage = 'vs' and species_id = t.species_id and status in ('done', 'broken') and image is not null;
    if not found then raise exception 'That VS portrait is not one of this trainer''s'; end if;
  end if;
  j := public.trainer_job_of(t.id);
  if j.id is null then raise exception 'The picture of this trainer is gone'; end if;
  settings := coalesce(nullif(j.prompt, '')::jsonb, '{}'::jsonb);
  if (settings ->> 'photo') is not null and not exists (select 1 from public.trainer_photos where id = (settings ->> 'photo')::bigint and slot = t.species_id) then
    raise exception 'The uploaded picture is gone, upload it again in 1 PICTURE';
  end if;
  perform public.trainer_queue_check();
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' back', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'back', 'ds', 'tries', 'tback', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'fields', settings -> 'fields', 'photo', settings -> 'photo', 'shape', p_shape,
            'extra', nullif(left(trim(p_extra), 200), ''), 'vs_try', v.id, 'vs_image', v.image))::text, 'back:' || p_shape)
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_back(bigint, text, integer, text, text, bigint) to anon;
create or replace function public.request_trainer_throw(p_try bigint, p_editor text, p_count integer default 1)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; j public.sprite_jobs; new_id bigint; settings jsonb;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'tback' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Pick a back first'; end if;
  if p_count is null or p_count < 1 or p_count > 2 then raise exception 'Ask for 1 or 2 throws'; end if;
  if exists (select 1 from public.sprite_jobs where stage = 'throw' and from_try = t.id and status in ('queued', 'running')) then
    raise exception 'The throw of this back is already being drawn';
  end if;
  j := public.trainer_job_of(t.id);
  settings := coalesce(nullif(j.prompt, '')::jsonb, '{}'::jsonb);
  perform public.trainer_queue_check();
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' throw', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'back', 'ds', 'tries', 'throw', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'fields', settings -> 'fields'))::text, 'throw:v5c750')
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_throw(bigint, text, integer) to anon;
drop function if exists public.request_trainer_anim(bigint, integer, integer, text, text);
create or replace function public.request_trainer_anim(p_try bigint, p_script integer, p_count integer, p_editor text, p_extra text default null, p_frames bigint default null)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; fr public.sprite_tries; j public.sprite_jobs; new_id bigint; settings jsonb;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'trainer' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Choose a finished battle sprite first'; end if;
  if p_script is null or not (p_script = any (array[23,66,67,70,72,73,74,75,76,86,87,88,89,97,98,99,100,103,104,105,106,107,108,109,110,112,123,124])) then
    raise exception 'Choose an animation first';
  end if;
  if p_count is null or p_count < 1 or p_count > 4 then raise exception 'Ask for 1 to 4 animations'; end if;
  if p_frames is not null then
    select * into fr from public.sprite_tries where id = p_frames and stage = 'anim' and species_id = t.species_id and status in ('done', 'broken') and image is not null;
    if not found then raise exception 'Those poses are not this trainer''s'; end if;
  end if;
  j := public.trainer_job_of(t.id);
  if j.id is null then raise exception 'The picture of this trainer is gone'; end if;
  settings := coalesce(nullif(j.prompt, '')::jsonb, '{}'::jsonb);
  perform public.trainer_queue_check();
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' anim', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'three-quarter', 'ds', 'tries', 'anim', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'fields', settings -> 'fields', 'photo', settings -> 'photo', 'script', p_script, 'frames', fr.image, 'frames_try', fr.id,
            'extra', nullif(left(trim(p_extra), 200), '')))::text, 'anim:' || p_script)
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_anim(bigint, integer, integer, text, text, bigint) to anon;
create or replace function public.trainer_queue_check()
returns void language plpgsql security definer set search_path = '' as $$
begin
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running') and not batch) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour' and not batch) >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
end $$;
