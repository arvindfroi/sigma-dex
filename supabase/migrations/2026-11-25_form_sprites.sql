-- Forms with their own sprites (2026-11-25, Arvind: "Kan du fikse at folk kan lage forms til eksisterende pokemon OG gi de
-- egne sprites på nettsiden"). A form stays in its base's data.forms; its sprites are made under its own sprite id
-- '<base>-form-<name>' (fm.sid). The only database change: a form's sprite studio may use its BASE's pictures as reference
-- pictures (start the form's art from the base species' art), so a reference picture belongs to the job's Pokemon when it is
-- the Pokemon's own or, for a form id, its base's. Everything else in request_tries is as before.
create or replace function public.request_tries(p_species_id text, p_stage text, p_count integer, p_from_try bigint, p_refs bigint[], p_prompt text, p_recipe text, p_editor text, p_with_try bigint)
returns bigint language plpgsql security definer set search_path = '' as $$
declare t public.sprite_tries; w public.sprite_tries; new_id bigint;
begin
  if p_stage not in ('art', 'front', 'back', 'icon', 'follower', 'front2', 'back2') then raise exception 'Unknown step'; end if;
  if p_count is null or p_count < 1 or p_count > 16 then raise exception 'Ask for 1 to 16 pictures'; end if;
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running') and not batch) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour' and not batch) >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  if exists (select 1 from unnest(coalesce(p_refs, '{}')) r
             where not exists (select 1 from public.species_images i where i.id = r and not i.removed
                               and (i.species_id = p_species_id or p_species_id like i.species_id || '-form-%'))) then
    raise exception 'A reference picture does not belong to this Pokemon';
  end if;
  if p_from_try is not null then
    select * into t from public.sprite_tries where id = p_from_try;
    if not found or t.species_id <> p_species_id then raise exception 'That picture does not belong to this Pokemon'; end if;
    if t.status not in ('done', 'broken') then raise exception 'That picture is not finished'; end if;
  end if;
  if p_with_try is not null then
    select * into w from public.sprite_tries where id = p_with_try;
    if not found or w.species_id <> p_species_id or w.status not in ('done', 'broken') then raise exception 'That picture does not belong to this Pokemon'; end if;
  end if;
  if p_stage = 'art' and coalesce(array_length(p_refs, 1), 0) = 0 then raise exception 'Choose a picture to cut the creature out of'; end if;
  if p_stage = 'front' and p_from_try is null and coalesce(array_length(p_refs, 1), 0) = 0 then raise exception 'Choose the art to draw from'; end if;
  if p_stage = 'front' and p_from_try is not null and t.stage not in ('art', 'front') then raise exception 'A front is drawn from art'; end if;
  if p_stage in ('back', 'icon', 'follower', 'front2') and (p_from_try is null or t.stage <> 'front') then raise exception 'Choose the front first'; end if;
  if p_stage = 'follower' and (p_with_try is null or w.stage <> 'back') then raise exception 'Choose the back first'; end if;
  if p_stage = 'front2' and p_with_try is not null and w.stage <> 'back' then raise exception 'The second picture must be a back'; end if;
  if p_stage = 'back2' and (p_from_try is null or t.stage <> 'back') then raise exception 'Choose the back first'; end if;
  if p_stage = 'back2' and p_with_try is not null and w.stage <> 'front2' then raise exception 'The second picture must be a front 2'; end if;
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, with_try, prompt, recipe)
  values (p_species_id, p_species_id || ' sprite', null, coalesce(p_refs, '{}'), 1, nullif(trim(p_editor), ''),
          'three-quarter', 'ds', 'tries', p_stage, p_count, p_from_try, p_with_try, nullif(trim(p_prompt), ''), nullif(trim(p_recipe), ''))
  returning id into new_id;
  return new_id;
end $$;
