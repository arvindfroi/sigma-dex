-- Trainer studio steps ANIM and BACK (2026-11-22).
-- ANIM: the battle intro animation. The person picks one of the animated classes' scripts (data/trainer_anims.json) and the
--   drawing PC draws the extra poses from the picked battle sprite (stage 'anim', recipe 'anim:<class>').
-- BACK: the back seen in battle and the Poke Ball throw (player characters and tag-battle partners only), the LOCKED recipe
--   (title3d/legend/trainers/locked_back_throw_v1): 'tback' = several frame-1 tries on player backs of the chosen shape, the
--   person picks one, then 'throw' = frames 2-8 from that pick (backmotion v5 step 750).
alter table public.sprite_jobs drop constraint sprite_jobs_stage_check;
alter table public.sprite_jobs add constraint sprite_jobs_stage_check check (stage = any (array['art','front','back','icon','follower','trainer','front2','back2','vs','map','anim','tback','throw']));
alter table public.sprite_tries drop constraint sprite_tries_stage_check;
alter table public.sprite_tries add constraint sprite_tries_stage_check check (stage = any (array['art','front','back','icon','follower','trainer','front2','back2','vs','map','anim','tback','throw']));

-- the job (with the picture and the words) a try belongs to: a drawn-on try has none, so walk up its parents
create or replace function public.trainer_job_of(p_try bigint)
returns public.sprite_jobs language plpgsql stable security definer set search_path = '' as $$
declare j public.sprite_jobs; walk bigint := p_try;
begin
  for i in 1..12 loop
    select * into j from public.sprite_jobs where id = (select job_id from public.sprite_tries where id = walk);
    exit when found;
    select parent_try into walk from public.sprite_tries where id = walk;
    exit when walk is null;
  end loop;
  return j;
end $$;
revoke execute on function public.trainer_job_of(bigint) from public, anon, authenticated;

create or replace function public.trainer_queue_check()
returns void language plpgsql security definer set search_path = '' as $$
begin
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running')) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour') >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
end $$;
revoke execute on function public.trainer_queue_check() from public, anon, authenticated;

create or replace function public.request_trainer_anim(p_try bigint, p_script integer, p_count integer, p_editor text, p_extra text default null)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; j public.sprite_jobs; new_id bigint; settings jsonb;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'trainer' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Choose a finished battle sprite first'; end if;
  if p_script is null or not (p_script = any (array[23,66,67,70,72,73,74,75,76,86,87,88,89,97,98,99,100,103,104,105,106,107,108,109,110,112,123,124])) then
    raise exception 'Choose an animation first';
  end if;
  if p_count is null or p_count < 1 or p_count > 4 then raise exception 'Ask for 1 to 4 animations'; end if;
  j := public.trainer_job_of(t.id);
  if j.id is null then raise exception 'The picture of this trainer is gone'; end if;
  settings := coalesce(nullif(j.prompt, '')::jsonb, '{}'::jsonb);
  perform public.trainer_queue_check();
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' anim', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'three-quarter', 'ds', 'tries', 'anim', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'photo', settings -> 'photo', 'script', p_script,
            'extra', nullif(left(trim(p_extra), 200), '')))::text, 'anim:' || p_script)
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_anim(bigint, integer, integer, text, text) to anon;

create or replace function public.request_trainer_back(p_try bigint, p_shape text, p_count integer, p_editor text, p_extra text default null)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; j public.sprite_jobs; new_id bigint; settings jsonb;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'trainer' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Choose a finished battle sprite first'; end if;
  if p_shape is null or p_shape not in ('long', 'short', 'tied', 'stout') then raise exception 'Choose a shape first'; end if;
  if p_count is null or p_count < 1 or p_count > 8 then raise exception 'Ask for 1 to 8 backs'; end if;
  j := public.trainer_job_of(t.id);
  if j.id is null then raise exception 'The picture of this trainer is gone'; end if;
  settings := coalesce(nullif(j.prompt, '')::jsonb, '{}'::jsonb);
  if (settings ->> 'photo') is not null and not exists (select 1 from public.trainer_photos where id = (settings ->> 'photo')::bigint and slot = t.species_id) then
    raise exception 'The uploaded picture is gone, upload it again in 1 PICTURE';
  end if;
  perform public.trainer_queue_check();
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' back', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'back', 'ds', 'tries', 'tback', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'photo', settings -> 'photo', 'shape', p_shape,
            'extra', nullif(left(trim(p_extra), 200), '')))::text, 'back:' || p_shape)
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_back(bigint, text, integer, text, text) to anon;

create or replace function public.request_trainer_throw(p_try bigint, p_editor text)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; j public.sprite_jobs; new_id bigint;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'tback' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Pick a back first'; end if;
  if exists (select 1 from public.sprite_jobs where stage = 'throw' and from_try = t.id and status in ('queued', 'running')) then
    raise exception 'The throw of this back is already being drawn';
  end if;
  j := public.trainer_job_of(t.id);
  perform public.trainer_queue_check();
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' throw', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'back', 'ds', 'tries', 'throw', 1, t.id,
          '{}', 'throw:v5c750')
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_throw(bigint, text) to anon;
