-- Trainer studio (2026-11-24, Arvind: "jeg klarer ikke å lage vs trainer sprites på ryuga og klarer ikke å lage backsprites"):
-- a new upload replaces the trainer's private picture, so the picture saved with an older battle sprite's job is gone, and VS,
-- back and map refused ("The uploaded picture is gone"). Now they take the trainer's CURRENT picture when the old one is gone
-- (trainer_photo_now) and put its id in the new job, so the worker fetches that one; they refuse only when the trainer has none.
create or replace function public.trainer_photo_now(p_slot text, p_photo bigint)
returns bigint language sql stable security definer set search_path = '' as $$
  select coalesce((select id from public.trainer_photos where id = p_photo and slot = p_slot),
                  case when p_photo is null then null else (select id from public.trainer_photos where slot = p_slot order by id desc limit 1) end)
$$;
create or replace function public.request_trainer_map(p_try bigint, p_count integer, p_editor text, p_extra text default null, p_fields jsonb default null)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; j public.sprite_jobs; walk bigint; new_id bigint; settings jsonb; ph bigint;
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
  ph := public.trainer_photo_now(t.species_id, (settings ->> 'photo')::bigint);
  if (settings ->> 'photo') is not null and ph is null then
    raise exception 'The picture of this trainer is gone: upload a new one in 1 PICTURE, then try again';
  end if;
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running') and not batch) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour' and not batch) >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' map', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'three-quarter', 'ds', 'tries', 'map', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'fields', coalesce(public.trainer_fields(p_fields), settings -> 'fields'), 'photo', ph, 'extra', nullif(left(trim(p_extra), 200), '')))::text, j.recipe)
  returning id into new_id;
  return new_id;
end $$;
create or replace function public.request_trainer_vs(p_try bigint, p_count integer, p_editor text, p_fields jsonb default null)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; j public.sprite_jobs; walk bigint; new_id bigint; settings jsonb; ph bigint;
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
  ph := public.trainer_photo_now(t.species_id, (settings ->> 'photo')::bigint);
  if (settings ->> 'photo') is not null and ph is null then
    raise exception 'The picture of this trainer is gone: upload a new one in 1 PICTURE, then try again';
  end if;
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running') and not batch) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour' and not batch) >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' vs', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'three-quarter', 'ds', 'tries', 'vs', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'fields', coalesce(public.trainer_fields(p_fields), settings -> 'fields'), 'photo', ph))::text, j.recipe)
  returning id into new_id;
  return new_id;
end $$;
create or replace function public.request_trainer_back(p_try bigint, p_shape text, p_count integer, p_editor text, p_extra text default null,
                                                       p_vs bigint default null, p_fields jsonb default null)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; v public.sprite_tries; j public.sprite_jobs; new_id bigint; settings jsonb; ph bigint;
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
  ph := public.trainer_photo_now(t.species_id, (settings ->> 'photo')::bigint);
  if (settings ->> 'photo') is not null and ph is null then
    raise exception 'The picture of this trainer is gone: upload a new one in 1 PICTURE, then try again';
  end if;
  perform public.trainer_queue_check();
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' back', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'back', 'ds', 'tries', 'tback', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'fields', coalesce(public.trainer_fields(p_fields), settings -> 'fields'), 'photo', ph, 'shape', p_shape,
            'extra', nullif(left(trim(p_extra), 200), ''), 'vs_try', v.id, 'vs_image', v.image))::text, 'back:' || p_shape)
  returning id into new_id;
  return new_id;
end $$;
create or replace function public.request_trainer_anim(p_try bigint, p_script integer, p_count integer, p_editor text, p_extra text default null, p_frames bigint default null, p_fields jsonb default null)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; fr public.sprite_tries; j public.sprite_jobs; new_id bigint; settings jsonb; ph bigint;
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
  ph := public.trainer_photo_now(t.species_id, (settings ->> 'photo')::bigint);
  perform public.trainer_queue_check();
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' anim', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'three-quarter', 'ds', 'tries', 'anim', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'fields', coalesce(public.trainer_fields(p_fields), settings -> 'fields'), 'photo', ph, 'script', p_script, 'frames', fr.image, 'frames_try', fr.id,
            'extra', nullif(left(trim(p_extra), 200), '')))::text, 'anim:' || p_script)
  returning id into new_id;
  return new_id;
end $$;
