-- Trainer studio step 4 VS (2026-11-21): the VS-screen portrait (96x64) drawn from the trainer's battle sprite and the
-- person's picture (VS LoRA pkmn_vs_klein_v1 step 2000, kind "both"; Arvind: "looks much better"). Its own stage 'vs', so
-- the battle tiles stay apart; the job copies the battle try's picture (photo) and words.
alter table public.sprite_jobs drop constraint sprite_jobs_stage_check;
alter table public.sprite_jobs add constraint sprite_jobs_stage_check check (stage = any (array['art','front','back','icon','follower','trainer','front2','back2','vs']));
alter table public.sprite_tries drop constraint sprite_tries_stage_check;
alter table public.sprite_tries add constraint sprite_tries_stage_check check (stage = any (array['art','front','back','icon','follower','trainer','front2','back2','vs']));

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
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running')) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour') >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt, recipe)
  values (t.species_id, t.species_id || ' vs', null, j.ref_image_ids, 1, nullif(trim(p_editor), ''), 'three-quarter', 'ds', 'tries', 'vs', p_count, t.id,
          jsonb_strip_nulls(jsonb_build_object('words', settings ->> 'words', 'photo', settings -> 'photo'))::text, j.recipe)
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer_vs(bigint, integer, text) to anon;
