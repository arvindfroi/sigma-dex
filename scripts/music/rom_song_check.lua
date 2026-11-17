-- Boots a ROM written by song_to_rom.lua in melonDS (Creature Maker's core, no window) on a map that plays the new
-- sequence, reads which sequence the game's sound system is playing, and records what the game sounds like.
--
--   cd ~/creature-maker/editor
--   luajit "<sigma repo>/scripts/music/rom_song_check.lua" written.nds original.nds SEQ_ID SECONDS out.wav
--
-- original.nds: the ROM the save is made from (a new game played to its first room once, kept in Creature Maker's
-- saves folder), then moved to the map. Prints "PLAYS <id>" and writes the recording.
package.path = "./?.lua;./?/init.lua;" .. package.path

local written, original, seq, seconds, outWav = arg[1], arg[2], tonumber(arg[3]), tonumber(arg[4] or 30), arg[5]
assert(written and original and seq and outWav, "usage: rom_song_check.lua written.nds original.nds SEQ_ID SECONDS out.wav")

local Paths = require("cm.paths")
local Gen4 = require("cm.rom.gen4")
local image = Paths.read(written)
local world = Gen4.world(require("cm.rom.nds").read(image))

-- a map whose day music is the sequence, and an open cell near its middle
local header
for h, H in pairs(world.headers) do
  if type(H) == "table" and H.dayMusic == seq and (not header or h < header) then header = h end
end
assert(header, "no map plays sequence " .. seq)
local lay = assert(Gen4.layout(world, header), "map " .. header .. " has no place on a matrix")
local none = { objects = {}, warps = {}, bgs = {}, coords = {} }
local x, y = require("cm.rom.gen4write").free(world, header, none, lay.x + math.floor(lay.w / 2), lay.y + math.floor(lay.h / 2))
assert(x, "no open cell found on map " .. header)
print(string.format("map header %d, spot %d,%d", header, x, y))

local Start = require("cm.export.gen4start")
local save = Paths.saves .. "/sigma_music_check.sav"
assert(Start.at(original, { header = header, x = x, y = y, dir = 1 }, save))
local p = assert(Start.play(written, save, { frames = 300 }))
local w = p.where or {}
print(string.format("game is at map %s, %s,%s", tostring(w.map), tostring(w.x), tostring(w.y)))
local emu = require("cm.emu.gen4").new(p.game, {}, image)

local RATE = 32768
local L, R, n = {}, {}, 0
local heard = {}
while n < seconds * RATE do
  p.game:frame()
  local samples, got = p.game:audio()
  for i = 0, got - 1 do
    n = n + 1
    L[n], R[n] = samples[i * 2] / 32768, samples[i * 2 + 1] / 32768
  end
  if n % (RATE * 2) < got then
    local s = emu:song()
    if s then heard[#heard + 1] = s.id end
  end
end
local s = emu:song()
-- the sound heap (NitroSystem's frame heap "FRMH", found as Creature Maker's cm/emu/gen4.lua finds it: just after
-- the sound archive's header copy): what the song and its bank and wave archives left free
do
  local MAIN, SIZE = 0x02000000, 0x400000
  local ram = require("ffi").string(p.game:block(MAIN, SIZE), SIZE)
  local from = 1
  while true do
    local i = ram:find("SDAT\255\254", from, true)
    if not i then break end
    local h = ram:find("HMRF", i + 0x94, true)
    if h and h - i < 0x200 then
      local base = MAIN + h - 1
      local start, stop = p.game:u32(base + 0x18), p.game:u32(base + 0x1C)
      local head, tail = p.game:u32(base + 0x24), p.game:u32(base + 0x28)
      print(string.format("sound heap: %d bytes, %d used from the front, %d free (head %08x tail %08x)",
        stop - start, head - start, tail - head, head, tail))
      break
    end
    from = i + 1
  end
end
p.game:close()
os.remove(save)
print("songs seen while recording: " .. table.concat(heard, " "))
print((s and s.id == seq) and ("PLAYS " .. seq) or ("PLAYS " .. tostring(s and s.id) .. " (not " .. seq .. ")"))

local ffi = require("ffi")
local buf = ffi.new("int16_t[?]", n * 2)
local function clip(v) return math.max(-1, math.min(1, v or 0)) end
for i = 1, n do
  buf[(i - 1) * 2] = math.floor(clip(L[i]) * 32767 + 0.5)
  buf[(i - 1) * 2 + 1] = math.floor(clip(R[i]) * 32767 + 0.5)
end
local function u32(v) return string.char(v % 256, math.floor(v / 256) % 256, math.floor(v / 65536) % 256, math.floor(v / 16777216) % 256) end
local function u16(v) return string.char(v % 256, math.floor(v / 256) % 256) end
local f = assert(io.open(outWav, "wb"))
f:write("RIFF" .. u32(36 + n * 4) .. "WAVE" .. "fmt " .. u32(16) .. u16(1) .. u16(2) .. u32(RATE) .. u32(RATE * 4)
  .. u16(4) .. u16(16) .. "data" .. u32(n * 4) .. ffi.string(buf, n * 4))
f:close()
