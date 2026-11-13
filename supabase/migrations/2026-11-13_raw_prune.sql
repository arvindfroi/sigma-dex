-- Raw pictures of unpicked tries leave the website storage (2026-11-13).
-- The "art" bucket reached 2.19 GB, the free plan holds 1.1 GB (Supabase mail of 12 Nov: fair use from 13 Dec).
-- 1.9 GB of it were the raws of studio tries: the full-size picture the drawing PC made before it was read as pixels
-- (a front's raw is ~1.4 MB, its sprite 2 KB). The website never shows a raw. Arvind: remove the ones nobody picked,
-- keep every picked one, with a backup on the Legion.
--
-- This lists the raws that may go: no try using that file (hand-drawn tries share the raw of the try they were drawn
-- from) is picked, has a follow-up try, or was used by a job, nothing else points to it, and its newest try finished
-- more than p_days ago. The nightly backup on the Legion sends the raws it holds (sprite-worker "prune_raws") and only
-- those it holds, at the same size, are removed. The path stays in sprite_tries; the picture stays in
-- D:\SigmaBackup\files\<path>.
create or replace function public.raw_prune_candidates(p_days integer)
returns table (path text, bytes bigint) language sql stable security definer set search_path = '' as $$
  with r as (
    select t.raw as path,
           bool_or(t.picked
                   or exists (select 1 from public.sprite_tries c where c.parent_try = t.id)
                   or exists (select 1 from public.sprite_jobs j where t.id in (j.from_try, j.with_try))) as keep,
           max(coalesce(t.finished_at, t.created_at)) as newest
      from public.sprite_tries t
     where t.raw is not null
     group by t.raw)
  select r.path, (o.metadata->>'size')::bigint
    from r join storage.objects o on o.bucket_id = 'art' and o.name = r.path
   where not r.keep
     and r.newest < now() - make_interval(days => greatest(coalesce(p_days, 1), 1))
     and not exists (select 1 from public.sprite_candidates c where r.path in (c.raw_front, c.raw_back))
     and not exists (select 1 from public.species_images i where i.path = r.path);
$$;
revoke all on function public.raw_prune_candidates(integer) from public, anon, authenticated;
