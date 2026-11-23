-- Trainer studio, back A/B (2026-11-23; Arvind: "Ja vs + foto var bra"; locked_back_throw_v2 "Step 1 update"):
-- the back's frame 1 now uses the person's photo + their picked VS portrait, so the back job carries the picked VS try
-- (its picture path goes into the job's prompt as vs_image; the worker reads only that). The shapes are named by what
-- the base backs show (long / short / spiky / cap / tied / stout), and the throw may make 2 tries (the second on the
-- other template, Barry 14 or Barry wide 21).

drop function if exists public.request_trainer_back(bigint, text, integer, text, text);
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
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'photo', settings -> 'photo', 'shape', p_shape,
            'extra', nullif(left(trim(p_extra), 200), ''), 'vs_try', v.id, 'vs_image', v.image))::text, 'back:' || p_shape)
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_back(bigint, text, integer, text, text, bigint) to anon;

drop function if exists public.request_trainer_throw(bigint, text);
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
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words'))::text, 'throw:v5c750')
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_throw(bigint, text, integer) to anon;
