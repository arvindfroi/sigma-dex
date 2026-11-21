-- Trainer studio v2 (2026-11-21, Arvind: "it must mirror the sprite studio ... only one box is needed"): each try makes the
-- battle sprite AND the map figure (the 512x32 NPC sheet, sprite_tries.overworld), and the eleven text fields became one
-- box (p_fields = {"words": "..."}, stored as prompt.words). The old field names are still accepted.
alter table public.sprite_tries add column if not exists overworld text;

create or replace function public.request_trainer(p_slot text, p_base text, p_strength real, p_count integer, p_fields jsonb,
                                                  p_photo bigint, p_ref bigint, p_editor text)
returns bigint language plpgsql security definer set search_path = '' as $$
declare new_id bigint; k text;
begin
  if p_slot !~ '^(trainer|npc)-[a-z0-9-]{1,36}$' then raise exception 'Unknown trainer'; end if;
  if p_base !~ '^(hgss:[0-9]{1,3}|pt:[a-z0-9_]{1,40})$' then raise exception 'Choose a base trainer'; end if;
  if p_strength is null or p_strength < 0.5 or p_strength > 0.95 then raise exception 'The strength is 0.5 to 0.95'; end if;
  if p_count is null or p_count < 1 or p_count > 4 then raise exception 'Ask for 1 to 4 pictures'; end if;
  if jsonb_typeof(coalesce(p_fields, '{}'::jsonb)) <> 'object' then raise exception 'The description is missing'; end if;
  for k in select jsonb_object_keys(coalesce(p_fields, '{}'::jsonb)) loop
    if k not in ('words', 'cls', 'who', 'skin', 'hair', 'clothes', 'extra', 'held', 'pose', 'facing', 'build', 'mood') then raise exception 'Unknown field %', k; end if;
    if jsonb_typeof(p_fields -> k) <> 'string' or char_length(p_fields ->> k) > (case when k = 'words' then 400 else 240 end) then
      raise exception 'The text is too long'; end if;
  end loop;
  if (p_photo is null) = (p_ref is null) then raise exception 'Choose one picture'; end if;
  if p_photo is not null and not exists (select 1 from public.trainer_photos where id = p_photo and slot = p_slot) then
    raise exception 'That picture is gone, upload it again';
  end if;
  if p_ref is not null and not exists (select 1 from public.species_images where id = p_ref and species_id = p_slot and not removed) then
    raise exception 'That picture does not belong to this trainer';
  end if;
  if (select count(*) from public.sprite_jobs where status in ('queued', 'running')) >= 40 then
    raise exception 'The queue is full, try again when some sprites are done' using errcode = '54000';
  end if;
  if (select count(*) from public.sprite_jobs where created_at > now() - interval '1 hour') >= 120 then
    raise exception 'Too many sprite requests in the last hour, try again later' using errcode = '54000';
  end if;
  insert into public.sprite_jobs (species_id, look, notes, ref_image_ids, variations, editor, pose, style, mode, stage, count, prompt, recipe)
  values (p_slot, p_slot || ' trainer', null, case when p_ref is null then '{}' else array[p_ref] end, 1, nullif(trim(p_editor), ''),
          'three-quarter', 'ds', 'tries', 'trainer', p_count,
          jsonb_strip_nulls(jsonb_build_object('strength', round(p_strength::numeric, 2), 'words', nullif(trim(coalesce(p_fields ->> 'words', '')), ''),
            'fields', case when coalesce(p_fields, '{}'::jsonb) - 'words' = '{}'::jsonb then null else p_fields - 'words' end, 'photo', p_photo))::text, p_base)
  returning id into new_id;
  return new_id;
end $$;
grant execute on function public.request_trainer(text, text, real, integer, jsonb, bigint, bigint, text) to anon;

-- the map figures are kept like the other pictures of a try
create or replace function public.art_orphans()
 returns setof text language sql security definer set search_path to '' as $function$
  select o.name from storage.objects o
   where o.bucket_id = 'art' and o.created_at < now() - interval '5 minutes'
     and o.name not like 'trainer-bases/%'
     and not exists (select 1 from public.species_images i where i.path = o.name)
     and not exists (select 1 from public.sprite_candidates c where o.name in (c.raw_front, c.raw_back, c.front, c.back, c.preview, c.icon, c.follower))
     and not exists (select 1 from public.sprite_tries t where o.name in (t.image, t.raw, t.overworld));
$function$;
