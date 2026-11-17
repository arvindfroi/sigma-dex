-- Renders one of a HeartGold / Origin ROM's own sequences with Creature Maker's DS player (the game's own
-- instruments) to a WAV, and writes the notes it plays as a ground truth (JSON), for testing the song -> SSEQ chain.
-- Local only: the WAV holds the game's instrument samples and must never be shared.
--
--   cd ~/creature-maker/editor
--   luajit "<sigma repo>/scripts/music/hg_song_render.lua" ROM.nds SEQ_ID SECONDS out.wav out_notes.json
package.path = "./?.lua;./?/init.lua;" .. package.path

local rom, id, seconds, wavPath, jsonPath = arg[1], tonumber(arg[2]), tonumber(arg[3] or 60), arg[4], arg[5]
assert(rom and id and wavPath and jsonPath, "usage: hg_song_render.lua ROM.nds SEQ_ID SECONDS out.wav out.json")

local Paths = require("cm.paths")
local Sseq = require("cm.song.sseq")
local Song = require("cm.song")
local world = require("cm.rom.gen4").world(require("cm.rom.nds").read(Paths.read(rom)))
local a = assert(Sseq.find(world), "no sound archive")
local rec = assert(a:seq(id), "no sequence " .. id)
local s = assert(Sseq.parse(a:file(rec.file), a:programs(rec.bank)))
s.id, s.file, s.bank, s.volume, s.player = id, a:file(rec.file), rec.bank, rec.volume, rec.player

-- audio
local RATE = 44100
local ds = require("cm.song.dsplay").new(assert(Sseq.spec(a, s)), RATE)
local L, R = ds:render(math.floor(seconds * RATE))
local n = #L
local ffi = require("ffi")
local buf = ffi.new("int16_t[?]", n * 2)
local function clip(v) return math.max(-1, math.min(1, v or 0)) end
for i = 1, n do
  buf[(i - 1) * 2] = math.floor(clip(L[i]) * 32767 + 0.5)
  buf[(i - 1) * 2 + 1] = math.floor(clip(R[i]) * 32767 + 0.5)
end
local function u32(x) return string.char(x % 256, math.floor(x / 256) % 256, math.floor(x / 65536) % 256, math.floor(x / 16777216) % 256) end
local function u16(x) return string.char(x % 256, math.floor(x / 256) % 256) end
local bytes = n * 4
local f = assert(io.open(wavPath, "wb"))
f:write("RIFF" .. u32(36 + bytes) .. "WAVE" .. "fmt " .. u32(16) .. u16(1) .. u16(2) .. u32(RATE) .. u32(RATE * 4)
  .. u16(4) .. u16(16) .. "data" .. u32(bytes) .. ffi.string(buf, bytes))
f:close()

-- ground truth: the notes as the engine plays them through once (plus the loop, repeated up to `seconds`)
local played = Sseq.play(s)
local out = { "{\"seq\":" .. id .. ",\"bank\":" .. rec.bank .. ",\"player\":" .. rec.player .. ",\"bytes\":" .. #s.file
  .. ",\"tempos\":[" }
for i, t in ipairs(played.tempos or {}) do
  out[#out + 1] = (i > 1 and "," or "") .. string.format("[%.4f,%d]", t.t or 0, t.tempo or 0)
end
out[#out + 1] = "],\"notes\":["
local first = true
for _, ch in ipairs(played.channels or {}) do
  for _, e in ipairs(ch.events or {}) do
    if (e.kind == "note" or e.kind == "drum") and e.t then -- a drum's kind says which: "drum:kick"
      out[#out + 1] = (first and "" or ",") .. string.format("[%d,%.4f,%.4f,%d,%d,\"%s\"]", ch.number or -1, e.t,
        e.dur or 0, e.pitch or -1, e.program or e.voice or -1, e.kind == "drum" and ("drum:" .. tostring(e.drum)) or e.kind)
      first = false
    end
  end
  if ch.loop then out[#out + 1] = "" end
end
local loops = {}
for _, ch in ipairs(played.channels or {}) do
  if ch.loop and ch.loop.t then loops[#loops + 1] = string.format("[%d,%.4f,%.4f]", ch.number or -1, ch.loop.t, ch.ends and ch.ends.t or -1) end
end
out[#out + 1] = "],\"loops\":[" .. table.concat(loops, ",") .. "]}"
local j = assert(io.open(jsonPath, "w"))
j:write(table.concat(out))
j:close()
print(string.format("seq %d: %d bytes, bank %d, player %d; wrote %.1f s of audio and %s", id, #s.file, rec.bank,
  rec.player, n / RATE, jsonPath))
