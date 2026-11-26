-- 2026-11-26 (Arvind: "gjør det slik at vi kan velge styrke på basen på alle deler av trainer studio"): the steps that start
-- from a picture take a strength, as FRONT does (p_strength of request_trainer). BACK: the denoise from the player back
-- (null = the tested plan, 0.60 then 0.65). ANIM: the denoise of the swap that repaints each new pose (null = 0.55).
-- VS, MAP and the throw start from nothing (only reference pictures), so they have no base strength.
drop function if exists public.request_trainer_back(bigint, text, integer, text, text, bigint, jsonb);
create function public.request_trainer_back(p_try bigint, p_shape text, p_count integer, p_editor text, p_extra text default null,
                                            p_vs bigint default null, p_fields jsonb default null, p_strength numeric default null)
returns bigint
language plpgsql
security definer
set search_path to ''
as $function$
declare t public.sprite_tries; v public.sprite_tries; j public.sprite_jobs; new_id bigint; settings jsonb; ph bigint;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'trainer' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Choose a finished battle sprite first'; end if;
  if p_shape is null or p_shape not in ('long', 'short', 'spiky', 'cap', 'tied', 'stout') then raise exception 'Choose a shape first'; end if;
  if p_count is null or p_count < 1 or p_count > 8 then raise exception 'Ask for 1 to 8 backs'; end if;
  if p_strength is not null and (p_strength < 0.4 or p_strength > 0.85) then raise exception 'The strength is 0.40 to 0.85'; end if;
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
            'extra', nullif(left(trim(p_extra), 200), ''), 'vs_try', v.id, 'vs_image', v.image, 'strength', round(p_strength, 2)))::text, 'back:' || p_shape)
  returning id into new_id;
  return new_id;
end $function$;
grant execute on function public.request_trainer_back(bigint, text, integer, text, text, bigint, jsonb, numeric) to anon, authenticated;

drop function if exists public.request_trainer_anim(bigint, integer, integer, text, text, bigint, jsonb);
create function public.request_trainer_anim(p_try bigint, p_script integer, p_count integer, p_editor text, p_extra text default null,
                                            p_frames bigint default null, p_fields jsonb default null, p_strength numeric default null)
returns bigint
language plpgsql
security definer
set search_path to ''
as $function$
declare t public.sprite_tries; fr public.sprite_tries; j public.sprite_jobs; new_id bigint; settings jsonb; ph bigint;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'trainer' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Choose a finished battle sprite first'; end if;
  if p_script is null or not (p_script = any (array[23,66,67,70,72,73,74,75,76,86,87,88,89,97,98,99,100,103,104,105,106,107,108,109,110,112,123,124])) then
    raise exception 'Choose an animation first';
  end if;
  if p_count is null or p_count < 1 or p_count > 4 then raise exception 'Ask for 1 to 4 animations'; end if;
  if p_strength is not null and (p_strength < 0.3 or p_strength > 0.75) then raise exception 'The strength is 0.30 to 0.75'; end if;
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
            'extra', nullif(left(trim(p_extra), 200), ''), 'strength', round(p_strength, 2)))::text, 'anim:' || p_script)
  returning id into new_id;
  return new_id;
end $function$;
grant execute on function public.request_trainer_anim(bigint, integer, integer, text, text, bigint, jsonb, numeric) to anon, authenticated;
