// Attaches an image to a Pokemon, removes one, or moves one to another Pokemon (or to the
// "lost-and-found" pile of pictures nobody has matched yet). Access is guarded by the shared edit
// key when one is set (checked in the database), not by a login, which is why JWT verification is off.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const MAX_BYTES = 3 * 1024 * 1024;
const TYPES: Record<string, string> = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif" };
const SLUG = /^[a-z0-9]+(-[a-z0-9]+)*$/;

function reply(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });
}

// The file must really be the kind of image it claims to be.
function looksLike(type: string, b: Uint8Array) {
  if (type === "image/png") return b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47;
  if (type === "image/jpeg") return b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff;
  if (type === "image/gif") return b[0] === 0x47 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x38;
  if (type === "image/webp") return b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50;
  return false;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return reply(405, { message: "Use POST" });
  try {
    const form = await req.formData();
    const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    const { data: keyOk, error: keyError } = await supabase.rpc("check_edit_key", { p_key: String(form.get("key") ?? "") });
    if (keyError) return reply(500, { message: "Could not check the edit key" });
    if (!keyOk) return reply(403, { message: "Wrong edit key" });
    const editor = String(form.get("editor") ?? "").trim().slice(0, 40) || null;
    const hourAgo = new Date(Date.now() - 3600_000).toISOString();

    if (form.get("action") === "remove") {
      const id = Number(form.get("id"));
      if (!Number.isInteger(id)) return reply(400, { message: "Which image?" });
      const { data, error } = await supabase.from("species_images").update({ removed: true }).eq("id", id).select("id").maybeSingle();
      if (error || !data) return reply(404, { message: "That image does not exist" });
      return reply(200, { id, removed: true });
    }

    if (form.get("action") === "move") {
      const id = Number(form.get("id"));
      const to = String(form.get("species_id") ?? "");
      if (!Number.isInteger(id)) return reply(400, { message: "Which image?" });
      if (!SLUG.test(to) || to.length > 40) return reply(400, { message: "Unknown Pokemon" });
      const { count } = await supabase.from("species_image_moves").select("id", { count: "exact", head: true }).gte("created_at", hourAgo);
      if ((count ?? 0) >= 300) return reply(429, { message: "Too many pictures moved in the last hour, try again later" });
      const { data: image } = await supabase.from("species_images").select("id, species_id, caption, removed").eq("id", id).maybeSingle();
      if (!image || image.removed) return reply(404, { message: "That image does not exist" });
      if (String(image.caption ?? "").startsWith("[")) return reply(400, { message: "Sprite pictures cannot be moved" });
      if (image.species_id === to) return reply(200, { id, species_id: to });
      const { error } = await supabase.from("species_images").update({ species_id: to }).eq("id", id);
      if (error) return reply(500, { message: "The picture could not be moved" });
      await supabase.from("species_image_moves").insert({ image_id: id, from_species: image.species_id, to_species: to, editor });
      return reply(200, { id, species_id: to, from: image.species_id });
    }

    const species = String(form.get("species_id") ?? "");
    if (!SLUG.test(species) || species.length > 40) return reply(400, { message: "Unknown Pokemon" });
    const file = form.get("file");
    if (!(file instanceof File)) return reply(400, { message: "No image was sent" });
    const ext = TYPES[file.type];
    if (!ext) return reply(400, { message: "Only PNG, JPG, WEBP or GIF images" });
    if (file.size > MAX_BYTES) return reply(400, { message: "The image is larger than 3 MB" });
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (!looksLike(file.type, bytes)) return reply(400, { message: "That file is not a valid image" });

    const { count } = await supabase.from("species_images").select("id", { count: "exact", head: true }).gte("created_at", hourAgo);
    if ((count ?? 0) >= 200) return reply(429, { message: "Too many uploads in the last hour, try again later" });

    const path = `${species}/${crypto.randomUUID()}.${ext}`;
    const { error: uploadError } = await supabase.storage.from("art").upload(path, bytes, { contentType: file.type, cacheControl: "31536000" });
    if (uploadError) return reply(500, { message: "The image could not be stored" });

    const caption = String(form.get("caption") ?? "").trim().slice(0, 200) || null;
    const { data: row, error: insertError } = await supabase.from("species_images")
      .insert({ species_id: species, path, caption, editor, bytes: bytes.length })
      .select("id, species_id, path, caption, editor").single();
    if (insertError) {
      await supabase.storage.from("art").remove([path]);
      return reply(500, { message: "The image could not be registered" });
    }
    return reply(200, row);
  } catch (_error) {
    return reply(400, { message: "The request could not be read" });
  }
});
