-- Frame 2 in the sprite studio (2026-11-21): the second animation frame of the front ('front2', drawn from the picked
-- front, with the picked back if there is one) and of the back ('back2', drawn from the picked back, with the picked
-- front 2 if there is one). Saved with the set as sprite_candidates.front2 / back2 and the pictures [ds-front2] / [ds-back2].
alter table public.sprite_jobs drop constraint sprite_jobs_stage_check;
alter table public.sprite_jobs add constraint sprite_jobs_stage_check check (stage = any (array['art','front','back','icon','follower','trainer','front2','back2']));
alter table public.sprite_tries drop constraint sprite_tries_stage_check;
alter table public.sprite_tries add constraint sprite_tries_stage_check check (stage = any (array['art','front','back','icon','follower','trainer','front2','back2']));
alter table public.sprite_candidates add column if not exists front2 text, add column if not exists back2 text;

create or replace function public.request_tries(p_species_id text, p_stage text, p_count integer, p_from_try bigint, p_refs bigint[], p_prompt text, p_recipe text, p_editor text, p_with_try bigint)
 returns bigint language plpgsql security definer set search_path to ''
as $function$
declare t public.sprite_tries; w public.sprite_tries; new_id bigint;
begin
  if p_stage not in ('art', 'front', 'back', 'icon', 'follower', 'front2', 'back2') then raise exception 'Unknown step'; end if;
  if p_count is null or p_count < 1 or p_count > 16 then raise exception 'Ask for 1 to 16 pictures'; end if;
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running')) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour') >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  if exists (select 1 from unnest(coalesce(p_refs, '{}')) r
             where not exists (select 1 from public.species_images i where i.id = r and i.species_id = p_species_id and not i.removed)) then
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
end $function$;

-- the claim also sends the from-try's grandparent (a back's front's art, for back frame 2)
create or replace function public.claim_sprite_job(p_stages text[] default null::text[])
 returns jsonb language plpgsql security definer set search_path to ''
as $function$
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
                                           'parent', (select jsonb_build_object('id', p.id, 'stage', p.stage, 'image', p.image,
                                                                                'parent', (select jsonb_build_object('id', g.id, 'stage', g.stage, 'image', g.image)
                                                                                             from public.sprite_tries g where g.id = p.parent_try))
                                                        from public.sprite_tries p where p.id = t.parent_try))
                   from public.sprite_tries t where t.id = j.from_try),
    'with_try', (select jsonb_build_object('id', t.id, 'stage', t.stage, 'image', t.image) from public.sprite_tries t where t.id = j.with_try),
    'comments', (select coalesce(jsonb_agg(jsonb_build_object('body', m.body, 'x', m.x, 'y', m.y) order by m.id), '[]')
                   from public.sprite_comments m where m.candidate_id = j.parent_candidate));
end $function$;

drop function if exists public.assemble_sprite(bigint, bigint, bigint, bigint, text);
create or replace function public.assemble_sprite(p_front bigint, p_back bigint, p_icon bigint, p_follower bigint, p_editor text,
                                                  p_front2 bigint default null, p_back2 bigint default null)
 returns bigint language plpgsql security definer set search_path to ''
as $function$
declare f public.sprite_tries; b public.sprite_tries; i public.sprite_tries; w public.sprite_tries; f2 public.sprite_tries; b2 public.sprite_tries; new_id bigint;
begin
  select * into f from public.sprite_tries where id = p_front and stage = 'front' and status in ('done', 'broken');
  if not found then raise exception 'Choose a finished front'; end if;
  select * into b from public.sprite_tries where id = p_back and stage = 'back' and status in ('done', 'broken') and species_id = f.species_id;
  if not found then raise exception 'Choose a finished back of the same Pokemon'; end if;
  if p_icon is not null then
    select * into i from public.sprite_tries where id = p_icon and stage = 'icon' and status in ('done', 'broken') and species_id = f.species_id;
    if not found then raise exception 'Choose a finished icon of the same Pokemon'; end if;
  end if;
  if p_follower is not null then
    select * into w from public.sprite_tries where id = p_follower and stage = 'follower' and status in ('done', 'broken') and species_id = f.species_id;
    if not found then raise exception 'Choose a finished walking sprite of the same Pokemon'; end if;
  end if;
  if p_front2 is not null then
    select * into f2 from public.sprite_tries where id = p_front2 and stage = 'front2' and status in ('done', 'broken') and species_id = f.species_id;
    if not found then raise exception 'Choose a finished front 2 of the same Pokemon'; end if;
  end if;
  if p_back2 is not null then
    select * into b2 from public.sprite_tries where id = p_back2 and stage = 'back2' and status in ('done', 'broken') and species_id = f.species_id;
    if not found then raise exception 'Choose a finished back 2 of the same Pokemon'; end if;
  end if;
  insert into public.sprite_candidates (job_id, species_id, seed, prompt, style_version, raw_front, raw_back, front, back, icon, follower, front2, back2, gen, kind, note, editor)
  values (f.job_id, f.species_id, coalesce(f.seed, 0),
          format('put together from tries: front #%s (%s), back #%s (%s), icon %s, walking %s, front 2 %s, back 2 %s', f.id, f.recipe, b.id, b.recipe,
                 coalesce('#' || i.id || ' (' || i.recipe || ')', 'none'), coalesce('#' || w.id || ' (' || w.recipe || ')', 'none'),
                 coalesce('#' || f2.id || ' (' || f2.recipe || ')', 'none'), coalesce('#' || b2.id || ' (' || b2.recipe || ')', 'none')),
          'studio-v4', f.raw, b.raw, f.image, b.image, i.image, w.image, f2.image, b2.image, 4, 'ai', null, nullif(trim(p_editor), ''))
  returning id into new_id;
  return new_id;
end $function$;
grant execute on function public.assemble_sprite(bigint, bigint, bigint, bigint, text, bigint, bigint) to anon, authenticated;

create or replace function public.review_sprite(p_key text, p_candidate bigint, p_status text, p_editor text)
 returns text language plpgsql security definer set search_path to ''
as $function$
declare c public.sprite_candidates;
begin
  perform private.require_edit_key(p_key);
  if p_status not in ('candidate', 'approved', 'rejected') then
    raise exception 'Unknown status';
  end if;
  select * into c from public.sprite_candidates where id = p_candidate;
  if not found then raise exception 'That sprite does not exist'; end if;
  if c.status = 'approved' or p_status = 'approved' then
    update public.species_images set removed = true
     where species_id = c.species_id and not removed and (
       (c.gen = 3 and (caption like '[front] AI draft #%' or caption like '[back] AI draft #%'))
       or (c.gen = 4 and (caption like '[ds-front] %' or caption like '[ds-back] %' or caption like '[ds-icon] %' or caption like '[ds-follower] %'
                          or caption like '[ds-front2] %' or caption like '[ds-back2] %')));
  end if;
  if p_status = 'approved' then
    update public.sprite_candidates set status = 'superseded' where species_id = c.species_id and status = 'approved' and gen = c.gen and id <> c.id;
    if c.gen = 4 then
      insert into public.species_images (species_id, path, caption, editor, bytes)
      select c.species_id, v.path, v.caption, nullif(trim(p_editor), ''), 0
        from (values (c.front, '[ds-front] sprite #' || c.id), (c.back, '[ds-back] sprite #' || c.id), (c.icon, '[ds-icon] sprite #' || c.id),
                     (c.follower, '[ds-follower] sprite #' || c.id), (c.front2, '[ds-front2] sprite #' || c.id), (c.back2, '[ds-back2] sprite #' || c.id)) v (path, caption)
       where v.path is not null
      on conflict (path) do update set removed = false, caption = excluded.caption, species_id = excluded.species_id, editor = excluded.editor;
    else
      insert into public.species_images (species_id, path, caption, editor, bytes) values
        (c.species_id, c.front, '[front] AI draft #' || c.id, nullif(trim(p_editor), ''), 0),
        (c.species_id, c.back, '[back] AI draft #' || c.id, nullif(trim(p_editor), ''), 0)
      on conflict (path) do update set removed = false, caption = excluded.caption, species_id = excluded.species_id, editor = excluded.editor;
    end if;
  end if;
  update public.sprite_candidates set status = p_status, reviewed_by = nullif(trim(p_editor), '') where id = c.id;
  return p_status;
end $function$;

create or replace function public.art_orphans()
 returns setof text language sql security definer set search_path to ''
as $function$
  select o.name from storage.objects o
   where o.bucket_id = 'art' and o.created_at < now() - interval '5 minutes'
     and o.name not like 'trainer-bases/%'
     and not exists (select 1 from public.species_images i where i.path = o.name)
     and not exists (select 1 from public.sprite_candidates c where o.name in (c.raw_front, c.raw_back, c.front, c.back, c.preview, c.icon, c.follower, c.front2, c.back2))
     and not exists (select 1 from public.sprite_tries t where o.name in (t.image, t.raw, t.overworld));
$function$;
