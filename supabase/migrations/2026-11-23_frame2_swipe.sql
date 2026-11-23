-- Frame 2 swipe (2026-11-23; Arvind: "lager du bare alle de til de best eksplosive først. også går jeg gjennom de og
-- godkjenner eller avviser det (som tinder) også de som vi avvist går videre til mer rolig, også repeat").
-- 1. sprite_jobs.batch: jobs Claude puts in for the whole dex (one big FRONT 2 and BACK 2 per saved sprite). The worker
--    takes people's jobs first (order by batch, id), and batch jobs do not count against the queue and hourly limits.
--    No RPC can set it; only the service role (the batch script) does.
-- 2. frame2_verdict(key, try, verdict, next, editor): the swipe page's YES / NO / UNDO for one frame-2 try.
--    yes  = the try becomes the saved sprite's FRONT 2 / BACK 2 (a copy of the saved sprite with that frame, approved).
--    no   = the try is marked as turned down; with next (big / clear / calm) one new try in that size is queued at
--           once, ahead of the batch, so the next card comes back soon.
--    undo = take the last yes or no back (the earlier saved sprite comes back; a queued redraw is cancelled).

alter table public.sprite_jobs add column if not exists batch boolean not null default false;
create index if not exists sprite_jobs_queue on public.sprite_jobs (batch, id) where status = 'queued';

create or replace function public.claim_sprite_job(p_stages text[] default null::text[])
returns jsonb language plpgsql security definer set search_path = '' as $function$
declare j public.sprite_jobs;
begin
  insert into public.sprite_worker (id, seen_at, state) values (1, now(), 'idle')
  on conflict (id) do update set seen_at = now();
  update public.sprite_jobs set status = 'queued', started_at = null
   where status = 'running' and started_at < now() - interval '90 minutes';
  select * into j from public.sprite_jobs
   where status = 'queued' and (case when p_stages is null then coalesce(stage, '') <> 'trainer' else coalesce(stage, 'front') = any (p_stages) end)
   order by batch, id limit 1 for update skip locked;
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
    'stage', j.stage, 'count', j.count, 'prompt', j.prompt, 'recipe', j.recipe, 'batch', j.batch,
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

-- request_tries: unchanged except that batch jobs are left out of the two limits
create or replace function public.request_tries(p_species_id text, p_stage text, p_count integer, p_from_try bigint, p_refs bigint[], p_prompt text, p_recipe text, p_editor text, p_with_try bigint)
returns bigint language plpgsql security definer set search_path = '' as $function$
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

create or replace function public.frame2_verdict(p_key text, p_try bigint, p_verdict text, p_next text, p_editor text)
returns jsonb language plpgsql security definer set search_path = '' as $function$
declare t public.sprite_tries; j public.sprite_jobs; c public.sprite_candidates; new_id bigint; f2 text; b2 text; ed text := nullif(trim(p_editor), '');
begin
  perform private.require_edit_key(p_key);
  select * into t from public.sprite_tries where id = p_try and stage in ('front2', 'back2');
  if not found then raise exception 'That frame 2 does not exist'; end if;
  select * into j from public.sprite_jobs where id = t.job_id;
  if p_verdict = 'yes' then
    if t.status not in ('done', 'broken') or t.image is null then raise exception 'That frame 2 is not finished'; end if;
    select * into c from public.sprite_candidates where species_id = t.species_id and status = 'approved' and gen = 4 order by id desc limit 1;
    if not found then raise exception 'This Pokemon has no saved sprite yet'; end if;
    f2 := case when t.stage = 'front2' then '#' || t.id || ' (' || coalesce(t.recipe, '') || ')' else coalesce(substring(c.prompt from 'front 2 (#[0-9]+ \([^)]*\))'), case when c.front2 is null then 'none' else 'kept' end) end;
    b2 := case when t.stage = 'back2' then '#' || t.id || ' (' || coalesce(t.recipe, '') || ')' else coalesce(substring(c.prompt from 'back 2 (#[0-9]+ \([^)]*\))'), case when c.back2 is null then 'none' else 'kept' end) end;
    insert into public.sprite_candidates (job_id, species_id, seed, prompt, style_version, raw_front, raw_back, front, back, preview, icon, follower, front2, back2,
                                          gen, kind, parent_id, note, editor)
    values (c.job_id, c.species_id, c.seed,
            regexp_replace(coalesce(c.prompt, ''), ', front 2 .*$', '') || format(', front 2 %s, back 2 %s', f2, b2),
            c.style_version, c.raw_front, c.raw_back, c.front, c.back, c.preview, c.icon, c.follower,
            case when t.stage = 'front2' then t.image else c.front2 end, case when t.stage = 'back2' then t.image else c.back2 end,
            c.gen, c.kind, c.id, c.note, ed)
    returning id into new_id;
    update public.sprite_tries set picked = true, picked_by = ed, picked_at = now() where id = t.id;
    perform public.review_sprite(p_key, new_id, 'approved', p_editor);
    return jsonb_build_object('verdict', 'yes', 'candidate', new_id);
  elsif p_verdict = 'no' then
    update public.sprite_tries set picked = false, picked_by = ed, picked_at = now() where id = t.id;
    if p_next is null then return jsonb_build_object('verdict', 'no'); end if;
    if p_next not in ('big', 'clear', 'calm') then raise exception 'Unknown size'; end if;
    if j.from_try is null then raise exception 'That frame 2 has no frame 1'; end if;
    if (select count(*) from public.sprite_jobs where status in ('queued', 'running') and not batch) >= 60 then
      raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
    end if;
    insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt)
    values (t.species_id, t.species_id || ' sprite', null, '{}', 1, ed, 'three-quarter', 'ds', 'tries', t.stage, 1, j.from_try,
            jsonb_build_object('size', p_next, 'after', t.id)::text)
    returning id into new_id;
    return jsonb_build_object('verdict', 'no', 'job', new_id);
  elsif p_verdict = 'undo' then
    if t.picked then                          -- a yes: the sprite saved before it comes back
      select * into c from public.sprite_candidates where species_id = t.species_id and status = 'approved' and gen = 4 order by id desc limit 1;
      if found and (c.front2 is not distinct from t.image or c.back2 is not distinct from t.image) and c.parent_id is not null then
        perform public.review_sprite(p_key, c.parent_id, 'approved', p_editor);
      end if;
    else                                      -- a no: the redraw it asked for is cancelled if it has not started
      update public.sprite_jobs set status = 'failed', error = 'cancelled (undo in the frame 2 swipe)', finished_at = now()
       where status = 'queued' and stage = t.stage and species_id = t.species_id and prompt like '%"after": ' || t.id || '}%';
    end if;
    update public.sprite_tries set picked = false, picked_by = null, picked_at = null where id = t.id;
    return jsonb_build_object('verdict', 'undo');
  end if;
  raise exception 'Unknown verdict';
end $function$;
grant execute on function public.frame2_verdict(text, bigint, text, text, text) to anon, authenticated;
