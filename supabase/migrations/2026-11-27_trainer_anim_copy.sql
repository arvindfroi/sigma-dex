-- 2026-11-27 (Arvind: "we dont do the pose copy technique when doing the animation?? ... jeg kopierer silver men at det er mirrored
-- og endret fasongen hans ... det er et av de svakere punktene"; "Ja, bygg det inn"): ANIM can copy the game's own poses
-- (scripts/trainer_studio.py POSE COPY). The job gets the person's choices (copy, flip, width, height) and what the drawing PC needs
-- from the front: its base, strength, seed and the base's mirror/width/height (filled in when the animation is the base's own).
drop function if exists public.request_trainer_anim(bigint, integer, integer, text, text, bigint, jsonb, numeric);
create function public.request_trainer_anim(p_try bigint, p_script integer, p_count integer, p_editor text, p_extra text default null, p_frames bigint default null,
  p_fields jsonb default null, p_strength numeric default null, p_copy boolean default null, p_flip boolean default null, p_width numeric default null, p_height numeric default null)
returns bigint
language plpgsql
security definer
set search_path to ''
as $function$
declare t public.sprite_tries; fr public.sprite_tries; j public.sprite_jobs; new_id bigint; settings jsonb; ph bigint;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'trainer' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Choose a finished battle sprite first'; end if;
  if p_script is null or not (p_script = any (array[23,66,67,70,72,73,74,75,76,86,87,88,89,97,98,99,100,103,104,105,106,107,108,109,110,112,123,124])
                              or p_script between 1000 and 1018) then
    raise exception 'Choose an animation first';
  end if;
  if p_count is null or p_count < 1 or p_count > 4 then raise exception 'Ask for 1 to 4 animations'; end if;
  if p_strength is not null and (p_strength < 0.3 or p_strength > 0.75) then raise exception 'The strength is 0.30 to 0.75'; end if;
  if p_width is not null and (p_width < 0.7 or p_width > 1.4) then raise exception 'The width is 0.70 to 1.40'; end if;
  if p_height is not null and (p_height < 0.85 or p_height > 1.1) then raise exception 'The height is 0.85 to 1.10'; end if;
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
            'extra', nullif(left(trim(p_extra), 200), ''), 'strength', round(p_strength, 2),
            'copy', p_copy, 'flip', p_flip, 'width', round(p_width, 2), 'height', round(p_height, 2),
            'base', j.recipe, 'base_strength', settings -> 'strength', 'base_seed', t.seed,
            'base_flip', settings -> 'flip', 'base_width', settings -> 'width', 'base_height', settings -> 'height'))::text, 'anim:' || p_script)
  returning id into new_id;
  return new_id;
end $function$;
grant execute on function public.request_trainer_anim(bigint, integer, integer, text, text, bigint, jsonb, numeric, boolean, boolean, numeric, numeric) to anon, authenticated;
