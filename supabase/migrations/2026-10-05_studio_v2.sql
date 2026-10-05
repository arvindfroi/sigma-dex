-- Sprite studio v2 (2026-10-05): DS sprites (80x80) from the approved pipeline, one at a time,
-- AI changes to the whole sprite or to a marked area, and versions drawn by hand on the website.

-- Jobs: 'new' draws a sprite from the chosen pictures; 'edit' changes an earlier version.
alter table public.sprite_jobs drop constraint sprite_jobs_style_check;
alter table public.sprite_jobs add constraint sprite_jobs_style_check
  check (style in ('pixel', 'emerald-light', 'emerald-medium', 'sprite-xl', 'sprite-clean', 'sprite-official', 'ds'));
alter table public.sprite_jobs
  add column mode text not null default 'new' check (mode in ('new', 'edit')),
  add column view text check (view in ('front', 'back', 'icon', 'both')),
  add column area jsonb check (area is null or (jsonb_typeof(area) = 'object' and pg_column_size(area) < 400));

-- Versions: the DS ones have an icon; hand-drawn ones have no job; each knows the version it came from.
alter table public.sprite_candidates
  alter column job_id drop not null,
  alter column preview drop not null,
  add column icon text,
  add column gen int not null default 3 check (gen in (3, 4)),
  add column kind text not null default 'ai' check (kind in ('ai', 'edit', 'drawn')),
  add column parent_id bigint references public.sprite_candidates (id),
  add column note text check (length(note) <= 800),
  add column editor text check (length(editor) <= 40);

create or replace function public.art_orphans()
returns setof text language sql security definer set search_path = '' as $$
  select o.name from storage.objects o
   where o.bucket_id = 'art' and o.created_at < now() - interval '5 minutes'
     and not exists (select 1 from public.species_images i where i.path = o.name)
     and not exists (select 1 from public.sprite_candidates c where o.name in (c.raw_front, c.raw_back, c.front, c.back, c.preview, c.icon));
$$;

-- Ask the AI to change a version: the whole sprite or a marked area (x0, y0, x1, y1 as fractions of the frame).
create function public.request_sprite_edit(p_parent bigint, p_instruction text, p_view text, p_area jsonb, p_editor text)
returns bigint language plpgsql security definer set search_path = '' as $$
declare c public.sprite_candidates; new_id bigint;
begin
  select * into c from public.sprite_candidates where id = p_parent;
  if not found then raise exception 'That sprite does not exist'; end if;
  if length(trim(coalesce(p_instruction, ''))) < 3 then raise exception 'Say what should change'; end if;
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running')) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour') >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  if p_area is not null and not (
      jsonb_typeof(p_area->'x0') = 'number' and jsonb_typeof(p_area->'y0') = 'number'
      and jsonb_typeof(p_area->'x1') = 'number' and jsonb_typeof(p_area->'y1') = 'number') then
    raise exception 'The marked area is not readable';
  end if;
  insert into public.sprite_jobs (species_id, look, notes, parent_candidate, ref_image_ids, variations, editor, pose, style, mode, view, area)
  values (c.species_id, c.species_id, trim(p_instruction), c.id, '{}', 1, nullif(trim(p_editor), ''), 'three-quarter', 'ds', 'edit',
          coalesce(p_view, 'front'), p_area)
  returning id into new_id;
  return new_id;
end $$;
revoke all on function public.request_sprite_edit(bigint, text, text, jsonb, text) from public;
grant execute on function public.request_sprite_edit(bigint, text, text, jsonb, text) to anon, authenticated;

create or replace function public.claim_sprite_job()
returns jsonb language plpgsql security definer set search_path = '' as $$
declare j public.sprite_jobs;
begin
  insert into public.sprite_worker (id, seen_at, state) values (1, now(), 'idle')
  on conflict (id) do update set seen_at = now();
  update public.sprite_jobs set status = 'queued', started_at = null
   where status = 'running' and started_at < now() - interval '30 minutes';
  select * into j from public.sprite_jobs where status = 'queued' order by id limit 1 for update skip locked;
  if not found then
    update public.sprite_worker set state = 'idle' where id = 1;
    return null;
  end if;
  update public.sprite_jobs set status = 'running', started_at = now() where id = j.id;
  update public.sprite_worker set state = 'drawing ' || j.species_id where id = 1;
  return jsonb_build_object(
    'id', j.id, 'species_id', j.species_id, 'look', j.look, 'notes', j.notes, 'variations', j.variations,
    'pose', j.pose, 'style', j.style, 'mode', j.mode, 'view', j.view, 'area', j.area,
    'refs', (select coalesce(jsonb_agg(i.path order by array_position(j.ref_image_ids, i.id)), '[]') from public.species_images i where i.id = any (j.ref_image_ids) and not i.removed),
    'parent', (select jsonb_build_object('id', c.id, 'raw_front', c.raw_front, 'raw_back', c.raw_back, 'seed', c.seed,
                                         'front', c.front, 'back', c.back, 'icon', c.icon, 'gen', c.gen)
                 from public.sprite_candidates c where c.id = j.parent_candidate),
    'comments', (select coalesce(jsonb_agg(jsonb_build_object('body', m.body, 'x', m.x, 'y', m.y) order by m.id), '[]')
                   from public.sprite_comments m where m.candidate_id = j.parent_candidate));
end $$;

-- Approving a DS version attaches it as [ds-front] / [ds-back] / [ds-icon] pictures (scripts/sprites.py auto
-- copies them to assets/sprites-ds/); the older 64x64 versions keep the [front] / [back] route.
create or replace function public.review_sprite(p_key text, p_candidate bigint, p_status text, p_editor text)
returns text language plpgsql security definer set search_path = '' as $$
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
       or (c.gen = 4 and (caption like '[ds-front] %' or caption like '[ds-back] %' or caption like '[ds-icon] %')));
  end if;
  if p_status = 'approved' then
    update public.sprite_candidates set status = 'superseded' where species_id = c.species_id and status = 'approved' and gen = c.gen and id <> c.id;
    if c.gen = 4 then
      insert into public.species_images (species_id, path, caption, editor, bytes)
      select c.species_id, v.path, v.caption, nullif(trim(p_editor), ''), 0
        from (values (c.front, '[ds-front] sprite #' || c.id), (c.back, '[ds-back] sprite #' || c.id), (c.icon, '[ds-icon] sprite #' || c.id)) v (path, caption)
       where v.path is not null;
    else
      insert into public.species_images (species_id, path, caption, editor, bytes) values
        (c.species_id, c.front, '[front] AI draft #' || c.id, nullif(trim(p_editor), ''), 0),
        (c.species_id, c.back, '[back] AI draft #' || c.id, nullif(trim(p_editor), ''), 0);
    end if;
  end if;
  update public.sprite_candidates set status = p_status, reviewed_by = nullif(trim(p_editor), '') where id = c.id;
  return p_status;
end $$;
