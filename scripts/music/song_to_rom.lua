-- MIDI -> HeartGold SSEQ in the game's own instruments -> written into a HeartGold / Origin HeartGold ROM in the
-- place of one of its songs (every map that plays it, day or night), with Creature Maker's music code
-- (~/creature-maker/editor: cm/song/midi.lua, tune.lua, sseqwrite.lua, cm/rom/sdat.lua, gen4write.lua, nds.lua).
-- Then the new song is read back from the written ROM and rendered by Creature Maker's DS player.
--
--   cd ~/creature-maker/editor
--   CM_GEN4_ROM=/path/origin.nds luajit "<sigma repo>/scripts/music/song_to_rom.lua" song.mid SEQ_ID out.nds out.wav \
--       out.json [instruments.json]
--
-- instruments.json (optional): { "<track name or number>": "b702.5", ... } forces HeartGold sounds per track.
-- Size, as the game holds it: "ok" when the song and what it adds to the bank are no bigger than the song it takes
-- the place of; "unstable" when bigger (Arvind, 2026-11-16: tag it, don't refuse); not written when the sequence is
-- longer than its player's heap.
package.path = "./?.lua;./?/init.lua;" .. package.path

local midPath, like, outRom, outWav, outJson, instPath = arg[1], tonumber(arg[2]), arg[3], arg[4], arg[5], arg[6]
assert(midPath and like and outRom and outWav and outJson,
  "usage: song_to_rom.lua song.mid SEQ_ID out.nds out.wav out.json [instruments.json]")

local Paths = require("cm.paths")
local Tune = require("cm.song.tune")
local Sbnk = require("cm.song.sbnk")
local Sdat = require("cm.rom.sdat")
local Sseq = require("cm.song.sseq")
local SseqWrite = require("cm.song.sseqwrite")
local Voices = require("cm.song.voices")

local function write(path, bytes) local f = assert(io.open(path, "wb")) f:write(bytes) f:close() end
local function q(s) return '"' .. tostring(s):gsub('[%c"\\]', function(c) return string.format("\\u%04x", c:byte()) end) .. '"' end

local hg = assert(require("cm.games").gen4(), "no HeartGold ROM: set CM_GEN4_ROM")
local world = hg.world
local a = assert(hg:sseqAudio(), "no sound archive")

-- the song
local score = assert(require("cm.song.midi").read(Paths.read(midPath)))
local tune = assert(Tune.fromScore(score, "mine"))
if tune.loop == nil then tune.loop = 0 end -- a game song goes round for ever: from the start unless the MIDI says

-- forced sounds
local forced = {}
if instPath then
  local f = io.open(instPath, "r")
  if f then
    local text = f:read("*a") f:close()
    for k, v in text:gmatch('"([^"]+)"%s*:%s*"([^"]+)"') do forced[k] = v end
  end
end
-- the song it takes the place of
local rec = assert(a:seq(like), "no sequence " .. like)
local bankBytes = assert(a:file(a:bankFile(rec.bank)), "no bank " .. rec.bank)
local waves = {}
for s, f in pairs(a:waves(rec.bank) or {}) do waves[s] = f end
local files = {}
for _, f in pairs(waves) do if f then files[f] = true end end

-- "this is a trumpet, the game has one, so the trumpet's notes go to that sound": each track's General MIDI program
-- as MuScriptor's instrument group, then the most used HeartGold sound named so (data/music/hg_sound_names.tsv) among
-- those the slot can play (their wave archives the song may name); none so named: Creature Maker's choice by kind
local GROUPS = { -- MuScriptor's MT3_FULL_PLUS groups (muscriptor/tokenizer/mt3.py)
  { "acoustic_piano", { 0, 1, 3, 6, 7 } }, { "electric_piano", { 2, 4, 5 } }, { "chromatic_percussion", { 8, 15 } },
  { "organ", { 16, 23 } }, { "acoustic_guitar", { 24, 25 } }, { "clean_electric_guitar", { 26, 27, 28 } },
  { "distorted_electric_guitar", { 29, 30, 31 } }, { "acoustic_bass", { 32, 35 } },
  { "electric_bass", { 33, 34, 36, 37, 38, 39 } }, { "violin", { 40 } }, { "viola", { 41 } }, { "cello", { 42 } },
  { "contrabass", { 43 } }, { "orchestral_harp", { 46 } }, { "timpani", { 47 } },
  { "string_ensemble", { 44, 45, 48, 49 } }, { "synth_strings", { 50, 51 } }, { "voice", { 52, 53, 54 } },
  { "orchestra_hit", { 55 } }, { "trumpet", { 56, 59 } }, { "trombone", { 57 } }, { "tuba", { 58 } },
  { "french_horn", { 60 } }, { "brass_section", { 61, 62, 63 } }, { "soprano_and_alto_sax", { 64, 65 } },
  { "tenor_sax", { 66 } }, { "baritone_sax", { 67 } }, { "oboe", { 68 } }, { "english_horn", { 69 } },
  { "bassoon", { 70 } }, { "clarinet", { 71 } }, { "flutes", { 72, 79 } }, { "synth_lead", { 80, 87 } },
  { "synth_pad", { 88, 95 } },
}
local groupOf, familyOf = {}, {}
for _, g in ipairs(GROUPS) do
  local p = g[2]
  if #p == 2 and p[2] - p[1] > 1 then for x = p[1], p[2] do groupOf[x] = g[1] end
  else for _, x in ipairs(p) do groupOf[x] = g[1] end end
  familyOf[g[1]] = math.floor(p[1] / 8)
end
local named = {} -- group -> { { id, use } } best first
local namesPath = os.getenv("SOUND_NAMES")
if namesPath then
  for line in io.lines(namesPath) do
    if line:sub(1, 1) ~= "#" then
      local id, _, use, n1 = line:match("^([^\t]+)\t([^\t]*)\t([^\t]*)\t([^\t]+)")
      if id then
        named[n1] = named[n1] or {}
        table.insert(named[n1], { id = id, use = tonumber(use) or 0 })
      end
    end
  end
  for _, l in pairs(named) do table.sort(l, function(x, y) return x.use > y.use end) end
end
-- verified sounds (data/music/hg_instruments.tsv: the hacking guide's by-ear map, sounds checked by ear) go first
local verified = {}
local verifiedPath = os.getenv("SOUND_VERIFIED")
if verifiedPath then
  for line in io.lines(verifiedPath) do
    local id, group = line:match("^(b[%d%.]+)\t([%w_]+)")
    if id then
      verified[id] = true
      named[group] = named[group] or {}
      for k = #named[group], 1, -1 do if named[group][k].id == id then table.remove(named[group], k) end end
      local at = 1 -- verified sounds of a group keep the file's order, ahead of the guessed ones
      while named[group][at] and named[group][at].verified do at = at + 1 end
      table.insert(named[group], at, { id = id, use = math.huge, verified = true })
    end
  end
end
-- drums on HeartGold's own kit at each kind's General MIDI key (data/music/hg_drums.tsv)
local kitOf = {}
local drumsPath = os.getenv("SOUND_DRUMS")
if drumsPath then
  for line in io.lines(drumsPath) do
    local kind, id = line:match("^(%a+)\t(b[%d%.]+)")
    if kind then kitOf[kind] = id end
  end
end
-- borrowed archives: a bank names up to four wave archives and HeartGold's use two (the shared one and their own),
-- so a sound whose samples are in another song's archive can still play: that archive goes in a free slot, whole
-- (3 to 29 KB). The parts with the most notes choose first.
local allowed = {}
for f in pairs(SseqWrite.shared(a)) do allowed[f] = true end
for f in pairs(files) do allowed[f] = true end
local free = 0
for s = 0, 3 do if waves[s] == nil then free = free + 1 end end
local borrowed = {}
-- the music banks' own archives are 3-29 KB, the sound effects' 60-97 KB; what fits is what the sound heap has free
-- while the song plays (Route 29 in Origin: 28 KB with its own song), so make_track.py lowers this when the game
-- plays the song silent (an archive that didn't fit isn't loaded)
local BORROW_MAX = tonumber(os.getenv("BORROW_MAX") or "") or 32 * 1024
local function needs(s)
  local list = {}
  for f in pairs(s.files or {}) do
    if not allowed[f] then
      if (a:size(f) or math.huge) > BORROW_MAX then return nil end
      list[#list + 1] = f
    end
  end
  return list
end
local order = {}
for i, tr in ipairs(tune.tracks) do order[#order + 1] = { i = i, n = #(tr.notes or {}) } end
table.sort(order, function(x, y) return x.n > y.n end)
local how = {}
for _, o in ipairs(order) do
  local i, tr = o.i, tune.tracks[o.i]
  local st = score.tracks[i]
  local id = forced[tostring(i)] or forced[tr.name or ""]
  if id then
    local s = Voices.sound(hg, id)
    local need = s and needs(s) or {}
    if #need <= free then
      for _, f in ipairs(need) do allowed[f], borrowed[f], free = true, true, free - 1 end
    end
    how[i] = "forced" .. (#need > 0 and " (borrowed archive)" or "")
  elseif st and st.program and not Tune.isDrums(tr) then
    local group = groupOf[st.program]
    -- the instrument itself, else one of its General MIDI family (8 programs: pianos, chromatic percussion, organs,
    -- guitars, basses, strings, ensembles, brass, reeds, pipes, synth leads, synth pads), the most used first
    local tiers = { { label = "named " .. tostring(group), list = group and named[group] or {} } }
    local fam = {}
    for g, l in pairs(named) do
      if g ~= group and familyOf[g] and familyOf[g] == math.floor(st.program / 8) then
        for _, c in ipairs(l) do fam[#fam + 1] = { id = c.id, use = c.use, g = g } end
      end
    end
    table.sort(fam, function(x, y) return x.use > y.use end)
    tiers[2] = { label = "family of " .. tostring(group), list = fam }
    for _, tier in ipairs(tiers) do
      for _, c in ipairs(tier.list) do
        local s = Voices.sound(hg, c.id)
        local need = s and not s.drum and needs(s)
        if need and #need <= free then
          for _, f in ipairs(need) do
            allowed[f], borrowed[f] = true, true
            free = free - 1
          end
          id, how[i] = c.id, tier.label .. (c.g and (": " .. c.g) or "") .. (#need > 0 and " (borrowed archive)" or "")
          break
        end
      end
      if id then break end
    end
    if not id then how[i] = "kind (" .. tostring(group) .. ": no sound so named fits)" end
    if id and verified[id] then how[i] = how[i] .. " [verified]" end
  elseif Tune.isDrums(tr) and next(kitOf) then
    local used = {}
    for _, n in ipairs(tr.notes or {}) do if n.drum then used[n.drum] = true end end
    local got = {}
    for kind in pairs(used) do
      local kid = kitOf[kind]
      if kid and Voices.sound(hg, kid) then
        tune = Tune.choose(tune, i, hg.id, kid, kind)
        got[#got + 1] = kind
      end
    end
    table.sort(got)
    how[i] = "the game's own kit (program 39): " .. table.concat(got, ", ")
  end
  if id then tune = Tune.choose(tune, i, hg.id, id) end
end
local borrowedBytes = 0
for f in pairs(borrowed) do
  files[f] = true
  borrowedBytes = borrowedBytes + (a:size(f) or 0)
end
local player = a:player(rec.player)
local replaced = a:size(rec.file)

local chosen, why
for _, level in ipairs({ 0, 1, 2, 3, 4, false }) do
  local out, bad = SseqWrite.song(tune, hg, { files = files, from = Sbnk.count(bankBytes), waves = waves, lanes = level })
  assert(out, bad)
  local grown = assert(Sbnk.extend(bankBytes, out.programs))
  local own = out.swar and #out.swar or 0
  local try = { out = out, grown = grown, adds = #out.sseq + #grown - #bankBytes + own + borrowedBytes, level = level }
  if not (player and player.heap > 0 and #out.sseq > player.heap) then
    chosen = try
    if try.adds <= replaced then break end
  else
    why = string.format("the sequence (%d bytes) is longer than its player's heap (%d)", #out.sseq, player.heap)
  end
end

local report = { '"like":' .. like, '"bank":' .. rec.bank, '"player":' .. rec.player, '"replaced_bytes":' .. replaced,
  '"heap":' .. (player and player.heap or -1) }
if not chosen then
  report[#report + 1] = '"status":"too_big","why":' .. q(why)
  write(outJson, "{" .. table.concat(report, ",") .. "}")
  print("NOT written: " .. why)
  os.exit(2)
end
local out = chosen.out
local status = chosen.adds <= replaced and "ok" or "unstable"
report[#report + 1] = '"status":"' .. status .. '"'
report[#report + 1] = '"sseq_bytes":' .. #out.sseq
report[#report + 1] = '"adds_bytes":' .. chosen.adds
report[#report + 1] = '"lanes":' .. q(tostring(chosen.level))
report[#report + 1] = '"borrowed_archive_bytes":' .. borrowedBytes

-- which HeartGold sound each track plays
local plan = SseqWrite.plan(tune, hg, { files = files, from = Sbnk.count(bankBytes), waves = waves })
local label = {}
for _, v in ipairs(Voices.of(hg).list) do label[v.id] = v.label or v.kind end
local tracks = {}
for i, tr in ipairs(tune.tracks) do
  local p = plan.tracks[i] or {}
  local notes = 0
  for _, e in ipairs(tr.events or tr.notes or {}) do if e.kind ~= "rest" then notes = notes + 1 end end
  local function sid(x) return type(x) == "table" and (x.id or x.label) or x end
  p.sound = sid(p.sound)
  local drums = {}
  for kind, d in pairs(p.drums or {}) do drums[#drums + 1] = q(kind) .. ":" .. q(sid(d.sound)) end
  tracks[#tracks + 1] = "{" .. table.concat({ '"i":' .. i, '"name":' .. q(tr.name or ""), '"kind":' .. q(tr.kind or ""),
    '"program":' .. q(tostring(score.tracks[i] and score.tracks[i].program or "")), '"how":' .. q(how[i] or "kind"), '"track":' .. q(tostring(p.track)), '"sound":' .. q(tostring(p.sound)),
    '"sound_label":' .. q(tostring(label[p.sound] or "")), '"notes":' .. notes, '"drums":{' .. table.concat(drums, ",") .. "}" }, ",") .. "}"
end
report[#report + 1] = '"tracks":[' .. table.concat(tracks, ",") .. "]"

-- into the archive: a new sequence with the record of the one it replaces, the bank grown by the song's programs
local add = { files = { out.sseq, chosen.grown }, wave = {}, seq = { { file = 1, like = like } },
  set = { bank = { [rec.bank] = { file = 2, waves = {} } } } }
local waveOf = {}
for n = 0, a:count("wave") - 1 do
  local f = a:waveFile(n)
  if f and not waveOf[f] then waveOf[f] = n end
end
local was = a:waves(rec.bank) or {}
for s = 0, 3 do
  local f = out.waves[s]
  if f == false then
    add.files[#add.files + 1] = out.swar
    add.wave[#add.wave + 1] = { file = #add.files }
    add.set.bank[rec.bank].waves[s] = { new = #add.wave }
  elseif f and f ~= was[s] then
    add.set.bank[rec.bank].waves[s] = waveOf[f]
  end
end
local sdat, numbers = Sdat.add(a.bytes, add)
assert(sdat, numbers)
local newSeq = numbers.seq[1]
report[#report + 1] = '"new_seq":' .. newSeq

local draft = require("cm.rom.gen4write").draft(world, hg.data)
local maps = 0
for h, H in pairs(world.headers) do
  if type(H) == "table" and (H.dayMusic == like or H.nightMusic == like) then
    local ok, bad = draft:music(h, H.dayMusic == like and newSeq or H.dayMusic, H.nightMusic == like and newSeq or H.nightMusic)
    assert(ok, bad)
    maps = maps + 1
  end
end
report[#report + 1] = '"maps":' .. maps
local changes = draft:changes()
changes[a.id] = sdat
local rom = assert(require("cm.rom.nds").write(world.rom, changes))
write(outRom, rom)

-- read back from the written ROM and played by our DS player
local w2 = require("cm.rom.gen4").world(require("cm.rom.nds").read(rom))
local a2 = assert(Sseq.find(w2))
local r2 = assert(a2:seq(newSeq))
local s = assert(Sseq.parse(a2:file(r2.file), a2:programs(r2.bank)))
s.id, s.file = newSeq, a2:file(r2.file)
local RATE = 44100
local seconds = tonumber(os.getenv("SECONDS_OUT") or "75")
local L, R = require("cm.song.dsplay").new(assert(Sseq.spec(a2, s)), RATE):render(math.floor(seconds * RATE))
local ffi = require("ffi")
local n = #L
local buf = ffi.new("int16_t[?]", n * 2)
local function clip(v) return math.max(-1, math.min(1, v or 0)) end
for i = 1, n do
  buf[(i - 1) * 2] = math.floor(clip(L[i]) * 32767 + 0.5)
  buf[(i - 1) * 2 + 1] = math.floor(clip(R[i]) * 32767 + 0.5)
end
local function u32(x) return string.char(x % 256, math.floor(x / 256) % 256, math.floor(x / 65536) % 256, math.floor(x / 16777216) % 256) end
local function u16(x) return string.char(x % 256, math.floor(x / 256) % 256) end
write(outWav, "RIFF" .. u32(36 + n * 4) .. "WAVE" .. "fmt " .. u32(16) .. u16(1) .. u16(2) .. u32(RATE) .. u32(RATE * 4)
  .. u16(4) .. u16(16) .. "data" .. u32(n * 4) .. ffi.string(buf, n * 4))
report[#report + 1] = '"read_back_bytes":' .. #s.file
write(outJson, "{" .. table.concat(report, ",") .. "}")
print(string.format("%s: sseq %d bytes, adds %d (replaced %d, heap %d), new seq %d on %d map(s); wrote %s",
  status, #out.sseq, chosen.adds, replaced, player and player.heap or -1, newSeq, maps, outRom))
