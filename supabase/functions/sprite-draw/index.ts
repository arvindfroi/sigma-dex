// Saves a sprite version drawn by hand in the website's sprite studio: the edited front, back and
// icon of an earlier version. Open to anyone (there is no edit key), so it checks the pictures
// strictly and limits how many versions can be saved per hour.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const MAX_BYTES = 200 * 1024;
const SIZES: Record<string, number[]> = { front: [64, 80], back: [64, 80], icon: [32] };
// The size of a try's picture per step (studio v3/v4).
const TRY_SIZE: Record<string, [number, number]> = { art: [640, 640], front: [80, 80], back: [80, 80], icon: [32, 32], follower: [128, 64] };
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "content-type, apikey, authorization" };

function reply(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
}
// A PNG's width and height are in its first chunk (IHDR), bytes 16-23.
function pngSize(b: Uint8Array): [number, number] | null {
  if (b.length < 24 || b[0] !== 0x89 || b[1] !== 0x50 || b[2] !== 0x4e || b[3] !== 0x47) return null;
  const v = new DataView(b.buffer, b.byteOffset);
  return [v.getUint32(16), v.getUint32(20)];
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  if (req.method !== "POST") return reply(405, { message: "Use POST" });
  try {
    const form = await req.formData();
    const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    // Studio v3 (2026-10-14): a try mirrored or drawn on in the studio becomes a new try of the same step and Pokemon,
    // which can be picked and drawn from like the others (Arvind: "you must be able to mirror; people should be able to
    // draw new details right on top, to change their design along the way"). 2026-10-15: also recoloured (the back on
    // the front's colours, the icon in an icon palette; "we should be able to play with it in the sprite studio").
    if (form.get("try") !== null) {
      const tryId = Number(form.get("try"));
      const { data: from } = await supabase.from("sprite_tries").select("id, species_id, stage, status, raw").eq("id", tryId).maybeSingle();
      if (!from || !["done", "broken"].includes(from.status)) return reply(404, { message: "That picture does not exist" });
      const since = new Date(Date.now() - 3600 * 1000).toISOString();
      const { count } = await supabase.from("sprite_tries").select("id", { count: "exact", head: true }).is("job_id", null).gt("created_at", since);
      if ((count ?? 0) >= 200) return reply(429, { message: "Too many drawings saved in the last hour, try again later" });
      const file = form.get("image");
      if (!(file instanceof File)) return reply(400, { message: "Nothing was drawn" });
      const limit = from.stage === "art" ? 1536 * 1024 : MAX_BYTES;
      if (file.size > limit) return reply(400, { message: "The picture is too large" });
      const bytes = new Uint8Array(await file.arrayBuffer());
      const size = pngSize(bytes);
      const want = TRY_SIZE[from.stage as string];
      if (!size || !want || size[0] !== want[0] || size[1] !== want[1]) return reply(400, { message: "The picture has the wrong size" });
      const asked = String(form.get("how") ?? "");
      const how = asked === "mirrored" || asked === "recoloured" ? asked : "drawn";
      const path = `tries/${from.species_id}/${how}-${tryId}-${crypto.randomUUID().slice(0, 8)}.png`;
      const { error: upError } = await supabase.storage.from("art").upload(path, bytes, { contentType: "image/png", cacheControl: "31536000" });
      if (upError) return reply(500, { message: "The picture could not be stored" });
      const editor = String(form.get("editor") ?? "").trim().slice(0, 40) || null;
      const { data: row, error } = await supabase.from("sprite_tries").insert({
        job_id: null, species_id: from.species_id, stage: from.stage, n: 1, status: "done", image: path, raw: from.raw,
        recipe: how === "drawn" ? "drawn by hand" : how, note: String(form.get("note") ?? "").trim().slice(0, 300) || null,
        parent_try: tryId, editor, seconds: null, finished_at: new Date().toISOString(),
      }).select("id").single();
      if (error) return reply(500, { message: "The picture could not be saved" });
      return reply(200, row);
    }

    // Studio v4 (2026-10-15): drawing on the sprite in use (an approved version) makes a new try of that step, picked like
    // the others, so the studio has one way of working (Arvind: "editing an existing sprite is stressful").
    if (form.get("version") !== null) {
      const versionId = Number(form.get("version"));
      const view = String(form.get("view") ?? "");
      if (!["front", "back", "icon", "follower"].includes(view)) return reply(400, { message: "Which part was drawn on?" });
      const { data: version } = await supabase.from("sprite_candidates").select("id, species_id, gen").eq("id", versionId).maybeSingle();
      if (!version || version.gen !== 4) return reply(404, { message: "That sprite does not exist" });
      const since = new Date(Date.now() - 3600 * 1000).toISOString();
      const { count } = await supabase.from("sprite_tries").select("id", { count: "exact", head: true }).is("job_id", null).gt("created_at", since);
      if ((count ?? 0) >= 200) return reply(429, { message: "Too many drawings saved in the last hour, try again later" });
      const file = form.get("image");
      if (!(file instanceof File)) return reply(400, { message: "Nothing was drawn" });
      if (file.size > MAX_BYTES) return reply(400, { message: "The picture is too large" });
      const bytes = new Uint8Array(await file.arrayBuffer());
      const size = pngSize(bytes), want = TRY_SIZE[view];
      if (!size || size[0] !== want[0] || size[1] !== want[1]) return reply(400, { message: "The picture has the wrong size" });
      const path = `tries/${version.species_id}/drawn-v${versionId}-${crypto.randomUUID().slice(0, 8)}.png`;
      const { error: upError } = await supabase.storage.from("art").upload(path, bytes, { contentType: "image/png", cacheControl: "31536000" });
      if (upError) return reply(500, { message: "The picture could not be stored" });
      const editor = String(form.get("editor") ?? "").trim().slice(0, 40) || null;
      const note = ("drawn on sprite #" + versionId + ". " + String(form.get("note") ?? "").trim()).trim().slice(0, 300);
      const { data: row, error } = await supabase.from("sprite_tries").insert({
        job_id: null, species_id: version.species_id, stage: view, n: 1, status: "done", image: path, recipe: "drawn by hand",
        note, parent_try: null, editor, seconds: null, finished_at: new Date().toISOString(),
      }).select("id").single();
      if (error) return reply(500, { message: "The picture could not be saved" });
      return reply(200, row);
    }

    const parentId = Number(form.get("parent"));
    if (!Number.isInteger(parentId)) return reply(400, { message: "Which version was drawn on?" });
    const { data: parent } = await supabase.from("sprite_candidates").select("*").eq("id", parentId).maybeSingle();
    if (!parent) return reply(404, { message: "That version does not exist" });
    const since = new Date(Date.now() - 3600 * 1000).toISOString();
    const { count } = await supabase.from("sprite_candidates").select("id", { count: "exact", head: true }).eq("kind", "drawn").gt("created_at", since);
    if ((count ?? 0) >= 200) return reply(429, { message: "Too many drawings saved in the last hour, try again later" });

    const stamp = crypto.randomUUID().slice(0, 8);
    const paths: Record<string, string | null> = { front: parent.front, back: parent.back, icon: parent.icon };
    let changed = 0;
    for (const name of Object.keys(SIZES)) {
      const file = form.get(name);
      if (!(file instanceof File)) continue;                // not drawn on: the parent's picture is kept
      if (file.size > MAX_BYTES) return reply(400, { message: `The ${name} picture is too large` });
      const bytes = new Uint8Array(await file.arrayBuffer());
      const size = pngSize(bytes);
      if (!size || size[0] !== size[1] || !SIZES[name].includes(size[0])) return reply(400, { message: `The ${name} picture has the wrong size` });
      const path = `candidates/${parent.species_id}/drawn-${parentId}-${stamp}-${name}.png`;
      const { error } = await supabase.storage.from("art").upload(path, bytes, { contentType: "image/png", cacheControl: "31536000" });
      if (error) return reply(500, { message: `The ${name} picture could not be stored` });
      paths[name] = path;
      changed++;
    }
    if (!changed) return reply(400, { message: "Nothing was drawn" });
    const editor = String(form.get("editor") ?? "").trim().slice(0, 40) || null;
    const { data: row, error } = await supabase.from("sprite_candidates").insert({
      job_id: null, species_id: parent.species_id, seed: 0, prompt: "drawn by hand on version #" + parentId,
      raw_front: parent.raw_front, raw_back: parent.raw_back, preview: null, gen: parent.gen, kind: "drawn",
      parent_id: parentId, note: String(form.get("note") ?? "").trim().slice(0, 800) || null, editor, ...paths,
    }).select("id").single();
    if (error) return reply(500, { message: "The drawing could not be saved" });
    return reply(200, row);
  } catch (_error) {
    return reply(400, { message: "The request could not be read" });
  }
});
