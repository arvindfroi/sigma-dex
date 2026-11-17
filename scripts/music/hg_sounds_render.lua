-- Every melodic sound of a HeartGold / Origin ROM (Creature Maker's Voices: 402 sounds, drums left out) played as a
-- short phrase by Creature Maker's DS player, one WAV each, plus sounds.json ({ id, kind, label, use }), so each sound
-- can be given an instrument name (scripts/music/name_sounds.py). Local only: the WAVs are the game's samples.
--
--   cd ~/creature-maker/editor
--   CM_GEN4_ROM=/path/origin.nds luajit "<sigma repo>/scripts/music/hg_sounds_render.lua" OUTDIR
package.path = "./?.lua;./?/init.lua;" .. package.path
local outDir = assert(arg[1], "usage: hg_sounds_render.lua OUTDIR")
os.execute(string.format("mkdir -p %q", outDir))

local hg = assert(require("cm.games").gen4(), "set CM_GEN4_ROM")
local Voices = require("cm.song.voices")
local Tune = require("cm.song.tune")
local Render = require("cm.song.render")

-- a phrase as a MIDI file: middle C, E, G, C, then a held C an octave down and a held C above (2 beats each), 120 bpm
local function vlq(n)
  local b = { string.char(n % 128) }
  n = math.floor(n / 128)
  while n > 0 do table.insert(b, 1, string.char(128 + n % 128)) n = math.floor(n / 128) end
  return table.concat(b)
end
local ev = {}
local function note(p, beats)
  ev[#ev + 1] = vlq(0) .. string.char(0x90, p, 100)
  ev[#ev + 1] = vlq(beats * 96) .. string.char(0x80, p, 0)
end
for _, p in ipairs({ 60, 64, 67, 72 }) do note(p, 1) end
note(48, 2)
note(72, 2)
local body = vlq(0) .. string.char(0xFF, 0x51, 3, 0x07, 0xA1, 0x20) .. table.concat(ev) .. vlq(0) .. string.char(0xFF, 0x2F, 0)
local function be32(n) return string.char(math.floor(n / 16777216) % 256, math.floor(n / 65536) % 256, math.floor(n / 256) % 256, n % 256) end
local midi = "MThd" .. be32(6) .. string.char(0, 0, 0, 1, 0, 96) .. "MTrk" .. be32(#body) .. body
local base = assert(Tune.fromScore(assert(require("cm.song.midi").read(midi)), "probe"))
base.loop = nil

local list = Voices.of(hg).list
local SseqWrite = require("cm.song.sseqwrite")
local Dsplay = require("cm.song.dsplay")
local ffi = require("ffi")
local rows = {}
local done = 0
local N = 44100 * 6
for _, v in ipairs(list) do
  if not v.drum and v.kind ~= "drum" then
    local tune = Tune.choose(base, 1, hg.id, v.id)
    -- the writer only takes sounds whose wave archives the song may name: give it this sound's own
    local files = {}
    for k in pairs(v.files or {}) do files[k] = true end -- a set: { [file] = true }
    local spec = SseqWrite.spec(tune, hg, { files = files })
    local plan = SseqWrite.plan(tune, hg, { files = files })
    local got = plan.tracks[1] and plan.tracks[1].sound
    if spec and got and got.id == v.id then
      local p = Dsplay.new(spec, 44100)
      local L, R = ffi.new("float[?]", N), ffi.new("float[?]", N)
      local at = 0
      while at < N do
        local k = math.min(4096, N - at)
        local l, r = p:fill(k)
        for i = 0, k - 1 do L[at + i], R[at + i] = l[i], r[i] end
        at = at + k
      end
      local f = assert(io.open(outDir .. "/" .. v.id .. ".wav", "wb"))
      f:write(Render.wav({ L, R }, N, 44100))
      f:close()
      done = done + 1
      rows[#rows + 1] = string.format('{"id":"%s","kind":"%s","label":"%s","use":%.1f}', v.id, tostring(v.kind),
        tostring(v.label or ""):gsub('"', "'"), v.use or 0)
    end
  end
end
local f = assert(io.open(outDir .. "/sounds.json", "w"))
f:write("[" .. table.concat(rows, ",\n") .. "]")
f:close()
print(string.format("%d of %d sounds rendered to %s", done, #list, outDir))
