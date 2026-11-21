// The trainer studio's picture (2026-11-21): a picture of yourself (MY TRAINER) or of your own character (CREATE NPC)
// that the drawing PC paints a trainer sprite from. It is stored PRIVATE (bucket trainer-photos, table trainer_photos):
// nobody can see it on the website, only the drawing PC gets a short link for the job it draws. The upload answers with
// a token that the uploader's device keeps; with it, "remove" deletes the file and its row. No login, so JWT is off.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const MAX_BYTES = 3 * 1024 * 1024;
const TYPES: Record<string, string> = { "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp" };
const SLOT = /^(trainer|npc)-[a-z0-9-]{1,36}$/;

function reply(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });
}
function looksLike(type: string, b: Uint8Array) {
  if (type === "image/png") return b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47;
  if (type === "image/jpeg") return b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff;
  if (type === "image/webp") return b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50;
  return false;
}
async function sha256(text: string) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(d)).map((x) => x.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return reply(405, { message: "Use POST" });
  try {
    const form = await req.formData();
    const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    if (form.get("action") === "remove") {
      const id = Number(form.get("id"));
      const token = String(form.get("token") ?? "");
      if (!Number.isInteger(id) || token.length < 20) return reply(400, { message: "Which picture?" });
      const { data: row } = await supabase.from("trainer_photos").select("id, path, token_sha256").eq("id", id).maybeSingle();
      if (!row) return reply(200, { id, removed: true });
      if (row.token_sha256 !== await sha256(token)) return reply(403, { message: "Only the device that uploaded the picture can remove it" });
      await supabase.storage.from("trainer-photos").remove([row.path]);
      await supabase.from("trainer_photos").delete().eq("id", id);
      return reply(200, { id, removed: true });
    }

    const slot = String(form.get("slot") ?? "");
    if (!SLOT.test(slot)) return reply(400, { message: "Unknown trainer" });
    const file = form.get("file");
    if (!(file instanceof File)) return reply(400, { message: "No picture" });
    const ext = TYPES[file.type];
    if (!ext) return reply(400, { message: "Use a PNG, JPG or WEBP picture" });
    if (file.size > MAX_BYTES) return reply(400, { message: "The picture is larger than 3 MB" });
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (!looksLike(file.type, bytes)) return reply(400, { message: "That file is not the picture it says it is" });
    const hourAgo = new Date(Date.now() - 3600_000).toISOString();
    const { count } = await supabase.from("trainer_photos").select("id", { count: "exact", head: true }).gte("created_at", hourAgo);
    if ((count ?? 0) >= 60) return reply(429, { message: "Too many pictures in the last hour, try again later" });

    const token = crypto.randomUUID() + crypto.randomUUID();
    const path = `${slot}/${crypto.randomUUID()}.${ext}`;
    const { error } = await supabase.storage.from("trainer-photos").upload(path, bytes, { contentType: file.type });
    if (error) return reply(500, { message: "The picture could not be stored" });
    const editor = String(form.get("editor") ?? "").trim().slice(0, 40) || null;
    const { data: row, error: rowError } = await supabase.from("trainer_photos").insert({ slot, path, token_sha256: await sha256(token), editor }).select("id").single();
    if (rowError || !row) { await supabase.storage.from("trainer-photos").remove([path]); return reply(500, { message: "The picture could not be registered" }); }
    return reply(200, { id: row.id, token });
  } catch (_error) {
    return reply(400, { message: "The request could not be read" });
  }
});
