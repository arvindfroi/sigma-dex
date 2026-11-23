-- Trainer studio BASE step (2026-11-22): a width slider. The swap keeps the base's body, so a stout person on a slim base
-- came out slim; the base frame is widened by `width` (1.0-1.4, NEAREST around the body centre, feet kept) before it is the
-- start picture. Sent as p_fields.width (a string, like the other fields), stored as prompt.width.
create or replace function public.request_trainer(p_slot text, p_base text, p_strength real, p_count integer, p_fields jsonb, p_photo bigint, p_ref bigint, p_editor text)
 returns bigint language plpgsql security definer set search_path to '' as $function$
declare new_id bigint; k text; w numeric := null; f jsonb := coalesce(p_fields, '{}'::jsonb);
begin
  if p_slot !~ '^(trainer|npc)-[a-z0-9-]{1,36}$' then raise exception 'Unknown trainer'; end if;
  if p_base !~ '^(hgss:[0-9]{1,3}|pt:[a-z0-9_]{1,40})$' then raise exception 'Choose a base trainer'; end if;
  if p_strength is null or p_strength < 0.5 or p_strength > 0.95 then raise exception 'The strength is 0.5 to 0.95'; end if;
  if p_count is null or p_count < 1 or p_count > 4 then raise exception 'Ask for 1 to 4 pictures'; end if;
  if jsonb_typeof(f) <> 'object' then raise exception 'The description is missing'; end if;
  for k in select jsonb_object_keys(f) loop
    if k not in ('words', 'width', 'cls', 'who', 'skin', 'hair', 'clothes', 'extra', 'held', 'pose', 'facing', 'build', 'mood') then raise exception 'Unknown field %', k; end if;
    if jsonb_typeof(f -> k) <> 'string' or char_length(f ->> k) > (case when k = 'words' then 400 else 240 end) then
      raise exception 'The text is too long'; end if;
  end loop;
  if f ? 'width' then
    if (f ->> 'width') !~ '^[01](\.[0-9]{1,2})?$' then raise exception 'The width is 1.0 to 1.4'; end if;
    w := round((f ->> 'width')::numeric, 2);
    if w < 1.0 or w > 1.4 then raise exception 'The width is 1.0 to 1.4'; end if;
    if w = 1.0 then w := null; end if;
  end if;
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
          jsonb_strip_nulls(jsonb_build_object('strength', round(p_strength::numeric, 2), 'words', nullif(trim(coalesce(f ->> 'words', '')), ''), 'width', w,
            'fields', case when f - 'words' - 'width' = '{}'::jsonb then null else f - 'words' - 'width' end, 'photo', p_photo))::text, p_base)
  returning id into new_id;
  return new_id;
end $function$;
