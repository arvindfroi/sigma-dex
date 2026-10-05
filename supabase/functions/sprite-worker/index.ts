// The door for the sprite worker (the PC with the GPU): take the next job, hand in the sprites
// it drew, report that a job is finished. Guarded by the worker key (checked in the database),
// not by a login, which is why JWT verification is off.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const MAX_BYTES = 3 * 1024 * 1024;
const FILES = ["raw_front", "raw_back", "front", "back", "preview", "icon"];
const NEEDED = ["front", "back"];

function reply(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
const isPng = (b: Uint8Array) => b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47;

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return reply(405, { message: "Use POST" });
  try {
    const form = await req.formData();
    const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
    const { data: keyOk, error: keyError } = await supabase.rpc("check_worker_key", { p_key: String(form.get("key") ?? "") });
    if (keyError) return reply(500, { message: "Could not check the worker key" });
    if (!keyOk) return reply(403, { message: "Wrong worker key" });
    const action = String(form.get("action") ?? "");

    if (action === "claim") {
      const { data, error } = await supabase.rpc("claim_sprite_job");
      if (error) return reply(500, { message: error.message });
      return reply(200, { job: data });
    }

    // Housekeeping: delete files in the art bucket that nothing points to any more.
    if (action === "purge_orphans") {
      const { data, error } = await supabase.rpc("art_orphans");
      if (error) return reply(500, { message: error.message });
      const paths = (data ?? []) as string[];
      let removed = 0;
      for (let i = 0; i < paths.length; i += 100) {
        const { data: gone, error: removeError } = await supabase.storage.from("art").remove(paths.slice(i, i + 100));
        if (removeError) return reply(500, { message: removeError.message, removed });
        removed += gone?.length ?? 0;
      }
      return reply(200, { orphans: paths.length, removed });
    }

    const jobId = Number(form.get("job_id"));
    if (!Number.isInteger(jobId)) return reply(400, { message: "Which job?" });
    const { data: job } = await supabase.from("sprite_jobs").select("id, species_id, status, mode, notes, parent_candidate, editor").eq("id", jobId).maybeSingle();
    if (!job || job.status !== "running") return reply(409, { message: "That job is not running" });

    if (action === "finish") {
      const error = String(form.get("error") ?? "").trim().slice(0, 500) || null;
      await supabase.from("sprite_jobs").update({ status: error ? "failed" : "done", error, finished_at: new Date().toISOString() }).eq("id", jobId);
      await supabase.from("sprite_worker").update({ state: "idle", seen_at: new Date().toISOString() }).eq("id", 1);
      return reply(200, { id: jobId, status: error ? "failed" : "done" });
    }

    // Progress shown on the website while a job runs ("drawing waffy: front 2 of 3").
    if (action === "progress") {
      const state = String(form.get("state") ?? "").slice(0, 120);
      await supabase.from("sprite_worker").update({ state, seen_at: new Date().toISOString() }).eq("id", 1);
      return reply(200, { ok: true });
    }

    if (action === "candidate") {
      const stamp = crypto.randomUUID().slice(0, 8);
      const paths: Record<string, string> = {};
      for (const name of FILES) {
        const file = form.get(name);
        const kept = form.get(name + "_path");            // a file the parent version already has (edits keep the artwork)
        if (!(file instanceof File)) {
          if (typeof kept === "string" && kept.startsWith(`candidates/${job.species_id}/`)) { paths[name] = kept; continue; }
          if (NEEDED.includes(name) || name.startsWith("raw_")) return reply(400, { message: `${name} is missing` });
          continue;
        }
        if (file.size > MAX_BYTES) return reply(400, { message: `${name} is larger than 3 MB` });
        const bytes = new Uint8Array(await file.arrayBuffer());
        if (!isPng(bytes)) return reply(400, { message: `${name} is not a PNG` });
        const path = `candidates/${job.species_id}/${jobId}-${stamp}-${name}.png`;
        const { error } = await supabase.storage.from("art").upload(path, bytes, { contentType: "image/png", cacheControl: "31536000" });
        if (error) return reply(500, { message: `${name} could not be stored` });
        paths[name] = path;
      }
      const gen = Number(form.get("gen")) === 4 ? 4 : 3;
      const { data: row, error } = await supabase.from("sprite_candidates").insert({
        job_id: jobId, species_id: job.species_id, seed: Number(form.get("seed")) || 0,
        prompt: String(form.get("prompt") ?? "").slice(0, 6000), style_version: String(form.get("style_version") ?? "").slice(0, 40) || null,
        gen, kind: job.mode === "edit" ? "edit" : "ai", parent_id: job.parent_candidate, note: job.mode === "edit" ? job.notes : null, editor: job.editor,
        ...paths,
      }).select("id").single();
      if (error) return reply(500, { message: "The sprite could not be registered" });
      return reply(200, row);
    }
    return reply(400, { message: "Unknown action" });
  } catch (_error) {
    return reply(400, { message: "The request could not be read" });
  }
});
