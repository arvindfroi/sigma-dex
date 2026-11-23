-- Battle animation previews (2026-11-23; Arvind: "gifen på nettsiden bør vises MED animasjonsscripet (det bør vi også
-- kunne velge btw)"). A frame-2 try gets a small animated picture of frame 1 and frame 2 played with the battle
-- animation the Pokemon borrows (engine.anim_from, or the closest official Pokemon). The drawing PC makes it right after
-- the try, and again when someone picks another animation (a cheap job, stage 'animprev', no GPU). The picture is our
-- own sprite moving; the game data that says how it moves stays on the drawing PC.
alter table public.sprite_tries add column if not exists anim text;          -- path of the animated preview (WebP)
alter table public.sprite_tries add column if not exists anim_from text;     -- the official Pokemon it was played as

alter table public.sprite_jobs drop constraint if exists sprite_jobs_stage_check;
alter table public.sprite_jobs add constraint sprite_jobs_stage_check check (stage = any (array['art', 'front', 'back', 'icon',
  'follower', 'trainer', 'front2', 'back2', 'vs', 'map', 'anim', 'tback', 'throw', 'animprev']));

create or replace function public.request_anim_preview(p_try bigint, p_donor text, p_editor text)
returns bigint language plpgsql security definer set search_path = '' as $function$
declare t public.sprite_tries; j public.sprite_jobs; new_id bigint;
begin
  select * into t from public.sprite_tries where id = p_try and stage in ('front2', 'back2') and status in ('done', 'broken') and image is not null;
  if not found then raise exception 'That frame 2 does not exist'; end if;
  if p_donor is null or p_donor !~ '^[A-Za-z0-9 .''’:♀♂é-]{2,20}$' then raise exception 'Which Pokemon''s animation?'; end if;
  -- the same preview already made, or already asked for: nothing to do
  if t.anim is not null and t.anim_from = p_donor then return null; end if;
  select * into j from public.sprite_jobs where stage = 'animprev' and from_try = p_try and status in ('queued', 'running')
     and prompt = jsonb_build_object('donor', p_donor)::text limit 1;
  if found then return j.id; end if;
  if (select count(*) from public.sprite_jobs where stage = 'animprev' and status in ('queued', 'running')) >= 60 then
    raise exception 'Too many previews waiting, try again in a minute' using errcode = '54000';
  end if;
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, from_try, prompt)
  values (t.species_id, t.species_id || ' sprite', null, '{}', 1, nullif(trim(p_editor), ''), 'three-quarter', 'ds', 'tries', 'animprev', 1, t.id,
          jsonb_build_object('donor', p_donor)::text)
  returning id into new_id;
  return new_id;
end $function$;
grant execute on function public.request_anim_preview(bigint, text, text) to anon, authenticated;

-- the nightly clean-up must keep the previews (it removes art files nothing points to)
create or replace function public.art_orphans()
returns setof text language sql security definer set search_path = '' as $function$
  select o.name from storage.objects o
   where o.bucket_id = 'art' and o.created_at < now() - interval '5 minutes'
     and o.name not like 'trainer-bases/%'
     and not exists (select 1 from public.species_images i where i.path = o.name)
     and not exists (select 1 from public.sprite_candidates c where o.name in (c.raw_front, c.raw_back, c.front, c.back, c.preview, c.icon, c.follower, c.front2, c.back2))
     and not exists (select 1 from public.sprite_tries t where o.name in (t.image, t.raw, t.overworld, t.anim));
$function$;
