-- 2026-11-26 (Arvind: "kan vi velge hvor mye referansene teller? med ludvig vil jeg at det skal ligne mer på ham"): Ludvig the
-- hedgehog came out as a human boy, because the VS LoRA draws human trainers. The VS job takes a likeness: how much the
-- picture counts against the VS habit. The drawing PC turns the VS LoRA down to it and gives the picture more weight
-- (trainer_studio.VS_LIKENESS, the combinations tested on Ludvig). null = the studio recipe as before.
drop function if exists public.request_trainer_vs(bigint, integer, text, jsonb);
create function public.request_trainer_vs(p_try bigint, p_count integer, p_editor text, p_fields jsonb default null, p_likeness numeric default null)
returns bigint
language plpgsql
security definer
set search_path to ''
as $function$
declare t public.sprite_tries; j public.sprite_jobs; walk bigint; new_id bigint; settings jsonb; ph bigint;
begin
  select * into t from public.sprite_tries where id = p_try and stage = 'trainer' and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'Choose a finished battle sprite first'; end if;
  if p_count is null or p_count < 1 or p_count > 4 then raise exception 'Ask for 1 to 4 pictures'; end if;
  if p_likeness is not null and not (round(p_likeness, 2) = any (array[0.75, 0.60, 0.45, 0.30])) then raise exception 'Choose a likeness from the list'; end if;
  walk := t.id;
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
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'fields', coalesce(public.trainer_fields(p_fields), settings -> 'fields'), 'photo', ph,
            'likeness', round(p_likeness, 2)))::text, j.recipe)
  returning id into new_id;
  return new_id;
end $function$;
grant execute on function public.request_trainer_vs(bigint, integer, text, jsonb, numeric) to anon, authenticated;
