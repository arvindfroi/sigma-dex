-- Unchosen studio tries leave the website storage (2026-11-23).
-- The "art" bucket was at 1.34 GB of the free plan's 1.1 GB. Arvind, asked how much goes if the old tries nobody chose
-- are removed for the Pokemon that have a saved sprite set: "ta den du" (unchosen tries older than 7 days).
--
-- This lists the files that may go: every file (picture, raw, animation preview, overworld) of a Pokemon studio try
-- (art, front, back, icon, follower, front 2, back 2) of a Pokemon that has an approved set, whose tries all finished
-- more than p_days (at least 7) ago, unless something still needs it:
--   - a sprite set that is approved or waiting for review (sprite_candidates 'approved' / 'candidate') points to it,
--   - it belongs to a try such a set uses, or a waiting or running job starts from (from_try / with_try),
--   - it is the picture of a try one of those was made from (parent_try, all the way back; their raws may go),
--   - it is an uploaded picture (species_images).
-- Trainer studio tries and Pokemon without an approved set are never listed. The nightly backup on the Legion sends the
-- files it holds (sprite-worker "prune_unchosen") and only those it holds, at the same size, are removed; their tries
-- get pruned_at, so the studio stops showing them. The pictures stay in D:\SigmaBackup\files\<path>.
alter table public.sprite_tries add column if not exists pruned_at timestamptz;

create or replace function public.unchosen_prune_candidates(p_days integer)
returns table (path text, bytes bigint) language sql stable security definer set search_path = '' as $$
  with recursive
  sets as (
    select c.species_id, array[c.front, c.back, c.icon, c.follower, c.front2, c.back2, c.raw_front, c.raw_back, c.preview] as paths
      from public.sprite_candidates c where c.status in ('approved', 'candidate')),
  set_paths as (select unnest(paths) as p from sets),
  seed as (
    select t.id from public.sprite_tries t join set_paths k on k.p in (t.image, t.raw)
    union select j.from_try from public.sprite_jobs j where j.status in ('queued', 'running') and j.from_try is not null
    union select j.with_try from public.sprite_jobs j where j.status in ('queued', 'running') and j.with_try is not null),
  chain(id) as (
    select id from seed
    union select t.parent_try from public.sprite_tries t join chain c on t.id = c.id where t.parent_try is not null),
  kept as (    -- every file of a try a set uses (or a job starts from); the pictures of the tries they were made from
    select x.p from public.sprite_tries t join seed s on s.id = t.id
      cross join lateral (values (t.image), (t.raw), (t.anim), (t.overworld)) x(p) where x.p is not null
    union select x.p from public.sprite_tries t join chain c on c.id = t.id
      cross join lateral (values (t.image), (t.anim), (t.overworld)) x(p) where x.p is not null
    union select p from set_paths where p is not null),
  files as (
    select x.p as path, max(coalesce(t.finished_at, t.created_at)) as newest
      from public.sprite_tries t
      cross join lateral (values (t.image), (t.raw), (t.anim), (t.overworld)) x(p)
     where x.p is not null
       and t.stage in ('art', 'front', 'back', 'icon', 'follower', 'front2', 'back2')
       and t.species_id in (select species_id from public.sprite_candidates where status = 'approved')
     group by x.p)
  select f.path, (o.metadata->>'size')::bigint
    from files f join storage.objects o on o.bucket_id = 'art' and o.name = f.path
   where f.newest < now() - make_interval(days => greatest(coalesce(p_days, 7), 7))
     and not exists (select 1 from kept k where k.p = f.path)
     and not exists (select 1 from public.species_images i where i.path = f.path);
$$;
revoke all on function public.unchosen_prune_candidates(integer) from public, anon, authenticated;
