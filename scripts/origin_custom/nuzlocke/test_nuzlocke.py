"""Emulator test of the nuzlocke build (see README.md here). Drives the English patch's harness
(~/origin-en/work/tools/emu_harness.py, py-desmume) on Arvind's own files; nothing here is committed data.

  ~/sigma-toolchain/venv312/bin/python scripts/origin_custom/nuzlocke/test_nuzlocke.py prep
  ~/sigma-toolchain/venv312/bin/python scripts/origin_custom/nuzlocke/test_nuzlocke.py all

prep: test save from ~/sigma-origin/saves/pallet_start_rc8_ai_all.dsv with a copy of the lead as a 2nd Pokemon and
properly empty PC boxes (fix_test_save_pc.py); all: warp to Route 1 grass, battle 1 catch (allowed), battle 2 ball
refused, battle 3 a 1-HP lead with only Splash faints and must end up in box 24.
venv312 needs ndspy (pip install ndspy==4.2.0)."""
import sys, struct, json, shutil
from pathlib import Path
EN = Path.home() / 'origin-en'
sys.path[:0] = [str(EN / 'work/tools'), str(EN / 'work/advanced-ai/testbench/lib'), str(Path(__file__).resolve().parent)]
import emu_harness as E
from savetool import Save, image, Mon, PARTY

def decode136(raw):
    # stand-in for the harness's save_core decoder (needs an npm build): box data only
    raw = bytes(raw[:136]) + bytes(100)
    m = Mon(raw)
    a, b = m.blocks['A'], m.blocks['B']
    plain = b''.join(bytes(m.blocks[c]) for c in 'ABCD')
    ok = (sum(struct.unpack('<64H', plain)) & 0xFFFF) == m.checksum
    return dict(species=struct.unpack_from('<H', a, 0)[0], item=struct.unpack_from('<H', a, 2)[0],
                form=b[0x18] >> 3, pid=m.pid, checksum_ok=ok)
E.decode_pokemon = decode136

S = Path(__file__).resolve().parent
OUT = Path.home() / 'sigma-origin/nuzlocke_run'
OUT.mkdir(exist_ok=True)
import os
ROM = Path(os.environ.get('NZ_ROM', Path.home() / 'sigma-origin/rc8/nuzlocke_test.nds'))
SYMS = json.loads(Path(str(ROM) + '.symbols.json').read_text()) if Path(str(ROM) + '.symbols.json').exists() else {}
SRC = Path.home() / 'sigma-origin/saves/pallet_start_rc8_ai_all.dsv'
NZ_NO_CATCH = SYMS.get('nz_no_catch', 0x023D21CE)
ROUTE1, ROUTE1_SEC = 9, 149

def map_chunks(map_id):
    import ndspy.rom, ndspy.narc
    rom = ndspy.rom.NintendoDSRom.fromFile(str(ROM))
    a9 = rom.loadArm9().sections[0].data
    hdr = a9[0x020F37C4 - 0x02000000 + 24 * map_id:][:24]
    mx = ndspy.narc.NARC(rom.getFileByName('a/0/4/1')).files[struct.unpack_from('<H', hdr, 4)[0]]
    w, hgt, has_headers, name_len = mx[0], mx[1], mx[2], mx[4]
    assert has_headers
    ids = struct.unpack_from('<%dH' % (w * hgt), mx, 5 + name_len)
    return {(k % w, k // w) for k, m in enumerate(ids) if m == map_id}

def grass_tile():
    g = E.MapGrid(str(ROM), ROUTE1)
    mine = map_chunks(ROUTE1)
    print('route 1 chunks', sorted(mine))
    tiles = {t for t in g.find(2) if (t[0] // 32, t[1] // 32) in mine}
    for (x, y) in sorted(tiles, key=lambda t: (t[1], t[0])):
        if all((x + d, y) in tiles for d in (-3, -2, -1, 1, 2, 3)):
            return x, y
    raise SystemExit('no grass run')

def prep():
    x, y = grass_tile()
    s = Save(data=image(SRC.read_bytes()))
    n = s.u('<I', 0x94)[0]
    raw = bytes(s.data[s.base + PARTY:s.base + PARTY + 236])
    s.data[s.base + PARTY + 236:s.base + PARTY + 472] = raw      # a copy of the lead as slot 2 (test only)
    s.put('<I', 0x94, 2)
    path = OUT / 'start.sav'
    path.write_bytes(s.to_bytes())
    import fix_test_save_pc; fix_test_save_pc.fix(str(path), str(path))
    (OUT / 'grass.json').write_text(json.dumps([x, y]))
    print('grass on Route 1 at', (x, y), 'party', n, '-> 2', path)

def nz_state(h):
    misc = h.array(9)
    st = h.read(misc + 0x7C, 40)
    magic, mode, _, deaths = struct.unpack_from('<IBBH', st, 0)
    used = st[8 + ROUTE1_SEC // 8] >> (ROUTE1_SEC % 8) & 1
    return dict(magic=hex(magic), mode=mode, deaths=deaths, route1_used=used, no_catch=h.u8(NZ_NO_CATCH))

def boot():
    h = E.Harness(str(ROM), str(OUT / 'start.sav'), out=str(OUT), verbose=False)
    h.boot_to_menu(); h.continue_game(); h.press('B', after=40); h.press('B', after=40)
    x, y = json.loads((OUT / 'grass.json').read_text())
    h.warp(ROUTE1, x, y)
    h.step(120)
    print('location', h.location(), 'party', party(h))
    return h

def party(h):
    a = h.array(E.ARR_PARTY)
    out = []
    for i in range(h.u32(a + 4)):
        m = Mon(h.read(a + 8 + 236 * i, 236))
        out.append((struct.unpack_from('<H', m.blocks['A'], 0)[0], struct.unpack_from('<H', m.party, 6)[0]))
    return out  # (species, hp)

def box(h, b):
    pc = h.array(41) if False else None
    return pc

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'prep':
        prep()
    elif cmd == 'b1':
        h = boot()
        print('before', nz_state(h))
        log = h.walk_until_battle()
        print('wild', log.rows[-1] if log.rows else None)
        h.wait_screen('battle_menu', 1500)
        print('in battle 1', nz_state(h))
        h.save_state(str(OUT / 'b1.dst'))
        h.screenshot('b1_menu')
        h.close()

def balls(h):
    raw = h.read(h.array(E.ARR_BAG) + E.POCKETS['balls'][0], 4 * 24)
    return {struct.unpack_from('<H', raw, i)[0]: struct.unpack_from('<H', raw, i + 2)[0] for i in range(0, 96, 4)
            if struct.unpack_from('<H', raw, i)[0]}

def throw_ball(h, tag):
    h.touch(*E.BATTLE_BUTTONS['bag'], frames=10, after=90)
    h.touch(192, 58, frames=10, after=90)     # POKé BALLS
    h.touch(64, 30, frames=10, after=90)      # first ball
    h.touch(104, 169, frames=10, after=20)    # USE
    shots = []
    for i in range(8):
        h.step(30)
        shots.append(h.screenshot('%s_%d' % (tag, i)))
    return shots

def until_menu_or_field(h, max_frames=6000):
    for i in range(0, max_frames, 30):
        h.step(30)
        if h.in_field():
            return 'field'
        if h.on_screen('battle_menu'):
            return 'menu'
        if i % 90 == 60:
            h.press('A', after=0)
    h.screenshot('stuck_%d' % h.frame)
    return 'stuck'

def sheet(paths, name, cols=4):
    from PIL import Image
    rows = (len(paths) + cols - 1) // cols
    s = Image.new('RGB', (256 * cols, 384 * rows), 'white')
    for i, p in enumerate(paths):
        s.paste(Image.open(p), (256 * (i % cols), 384 * (i // cols)))
    s.save(OUT / name)
    return OUT / name


def back_to_battle_menu(h):
    for _ in range(5):
        if h.on_screen('battle_menu') or h.in_field():
            return
        h.touch(232, 169, frames=10, after=80)      # the bag's return arrow

def single_battle(h, tries=6):
    """Walk until a wild battle with ONE wild Pokemon (Origin also has wild double battles, where a Ball cannot be
    aimed at all); doubles are fled."""
    for _ in range(tries):
        log = h.walk_until_battle()
        h.wait_screen('battle_menu', 1500)
        h.step(30)
        if len(log.rows) == 1:
            return log
        print('  (wild double battle, fleeing)')
        h.flee(battle_menu_wait=10)
    raise RuntimeError('no single wild battle')

def step_b1(h):
    print('battle 1 state', nz_state(h), 'balls', balls(h))
    shots = throw_ball(h, 't1')
    r = until_menu_or_field(h)
    print('after throw 1:', r, 'balls', balls(h), 'party', party(h) if r == 'field' else '-')
    if r == 'menu':
        h.flee(battle_menu_wait=10)
    print('after battle 1', nz_state(h), 'party', party(h))
    sheet(shots, 'throw1.png')

def step_b2(h):
    log = single_battle(h)
    print('wild 2', log.rows[-1]['species'])
    print('battle 2 state', nz_state(h), 'balls', balls(h))
    h.save_state(str(OUT / 'b2.dst'))
    shots = throw_ball(h, 't2')
    print('after refused throw: balls', balls(h))
    sheet(shots, 'throw2.png')
    for _ in range(4):
        if h.on_screen('battle_menu'):
            break
        h.touch(232, 169, frames=10, after=80)     # the bag's return arrow
    h.flee(battle_menu_wait=10)
    print('after battle 2: in field', h.in_field(), nz_state(h))
    h.save_state(str(OUT / 'after_b2.dst'))

def resume_b2(h):
    h.load_state(str(OUT / 'b2.dst'))
    h.step(10)
    shots = throw_ball(h, 't2')
    for _ in range(4):
        if h.on_screen('battle_menu'):
            break
        h.touch(232, 169, frames=10, after=80)
    h.flee(battle_menu_wait=10)
    print('in field after battle 2', h.in_field(), nz_state(h), 'balls', balls(h))
    h.save_state(str(OUT / 'after_b2.dst'))

if __name__ == '__main__' and sys.argv[1] == 'rb2':
    h = E.Harness(str(ROM), str(OUT / 'start.sav'), out=str(OUT), verbose=False)
    resume_b2(h)
    h.close()

if __name__ == '__main__' and sys.argv[1] == 'b12':
    h = E.Harness(str(ROM), str(OUT / 'start.sav'), out=str(OUT), verbose=False)
    h.load_state(str(OUT / 'b1.dst'))
    step_b1(h)
    step_b2(h)
    h.close()

def edit_lead_fragile(h):
    a = h.array(E.ARR_PARTY) + 8
    m = Mon(h.read(a, 236))
    m.set_hp(1)
    struct.pack_into('<4H', m.blocks['B'], 0x08, 150, 0, 0, 0)    # Splash only
    struct.pack_into('<4B', m.blocks['B'], 0x10, 40, 0, 0, 0)
    h.write(a, m.encode())

def pc_box(h, b):
    pc = h.array(41)
    out = []
    for s in range(30):
        raw = h.read(pc + 0x1000 * b + 0x88 * s, 0x88)
        if any(raw):
            out.append(decode136(raw)['species'])
    name = h.read(pc + 0x18008 + 40 * b, 40)
    return out, name.hex()

if __name__ == '__main__' and sys.argv[1] == 'b3':
    h = E.Harness(str(ROM), str(OUT / 'start.sav'), out=str(OUT), verbose=False)
    h.load_state(str(OUT / 'after_b2.dst'))
    h.step(10)
    edit_lead_fragile(h)
    print('party before', party(h), 'box 24', pc_box(h, 23))
    log = h.walk_until_battle()
    print('wild 3', log.rows[-1]['species'])
    h.wait_screen('battle_menu', 1500)
    h.save_state(str(OUT / 'b3.dst'))
    shots = []
    for t in range(12):
        state = h.battle_turn(0, shots=shots)
        print('turn', t, state)
        if state != 'menu':
            break
    shots.append(h.screenshot('b3_end'))
    sheet(shots[-8:], 'b3_turns.png')
    h.save_state(str(OUT / 'b3_faint.dst'))
    h.close()

def step_b3(h):
    edit_lead_fragile(h)
    print('party before battle 3', party(h), 'box 24', pc_box(h, 23)[0][:3])
    log = single_battle(h)
    print('wild 3', log.rows[-1]['species'])
    for t in range(15):
        try:
            st = h.battle_turn(0)
        except RuntimeError:
            st = 'prompt'
        if st != 'menu':
            break
    print('battle 3 turn', t, st)
    shots = [h.screenshot('f0')]
    h.touch(190, 28, frames=10, after=90)     # the second Pokemon
    h.touch(128, 108, frames=10, after=60)    # SHIFT
    h.run_until(lambda h: h.on_screen('battle_menu'), 1800, every=15)
    shots.append(h.screenshot('f1'))
    print('fled', h.flee(battle_menu_wait=10))
    h.step(60)
    shots.append(h.screenshot('f2'))
    sheet(shots, 'b3_flow.png', cols=3)
    print('party after battle 3', party(h))
    print('box 24 after', pc_box(h, 23))
    print('state after', nz_state(h))
    h.save_state(str(OUT / 'after_b3.dst'))

if __name__ == '__main__' and sys.argv[1] == 'all':
    h = boot()
    print('before', nz_state(h))
    log = h.walk_until_battle()
    print('wild 1', log.rows[-1]['species'])
    h.wait_screen('battle_menu', 1500)
    h.save_state(str(OUT / 'b1.dst'))
    step_b1(h)
    step_b2(h)
    print('balls after battle 2', balls(h))
    step_b3(h)
    h.close()


# ---------------------------------------------------------------------------------------------- hardcore round

def options_word(h):
    return h.u16(h.array(E.ARR_PARTY) - 0x90 + 0x60)     # Options at general block +0x60

def mon_level_hp(h, slot):
    a = h.array(E.ARR_PARTY) + 8 + 236 * slot
    m = Mon(h.read(a, 236))
    return m.party[4], struct.unpack_from('<H', m.party, 6)[0]

def set_hp(h, slot, hp):
    a = h.array(E.ARR_PARTY) + 8 + 236 * slot
    m = Mon(h.read(a, 236)); m.set_hp(hp); h.write(a, m.encode())

def leave_field_bag(h):
    for _ in range(4):
        if h.in_field() and not h.on_screen('battle_menu'):
            pass
        h.press('B', after=60)
    h.step(60)

def prep_hc():
    prep()
    from savetool import gen4_slow_exp
    path = OUT / 'start.sav'
    s = Save(data=image(path.read_bytes()))
    m = s.mon(0); m.set_level(12, 12 ** 3); s.set_mon(0, m)          # lead at the 0-badge cap (12)
    v = s.u('<H', 0x60)[0]
    s.put('<H', 0x60, (v | 0x20) & ~0x08 & ~0x40)                     # ITEMS ALL, CAP off, style SHIFT
    path.write_bytes(s.to_bytes())
    import fix_test_save_pc; fix_test_save_pc.fix(str(path), str(path))
    print('hardcore prep: lead Lv12, options 0x%04X' % s.u('<H', 0x60)[0])

def battle_bag_use(h, category_xy, tag):
    h.touch(*E.BATTLE_BUTTONS['bag'], frames=10, after=90)
    h.touch(*category_xy, frames=10, after=90)
    h.touch(64, 30, frames=10, after=90)
    h.touch(104, 169, frames=10, after=20)
    shots = []
    for i in range(4):
        h.step(30); shots.append(h.screenshot('%s_%d' % (tag, i)))
    for _ in range(4):
        if h.on_screen('battle_menu'):
            break
        h.touch(232, 169, frames=10, after=80)
    return shots

def open_pc_box24(h, tag):
    h.run_script(program=E.script_bytes(("LockAll",), ("ScrCmd_158", 2), ("ReleaseAll",), ("End",)), settle=400)
    h.touch(13, 27, frames=8, after=120)
    return h.screenshot(tag)

if __name__ == '__main__' and sys.argv[1] == 'prep_hc':
    prep_hc()

if __name__ == '__main__' and sys.argv[1] == 'hc':
    h = boot()
    print('options before', hex(options_word(h)), 'state', nz_state(h))
    # field: Rare Candy on the Lv12 lead (cap 12) must be refused, on the Lv5 second Pokemon allowed
    h.bag_put_first(50, 5, 'medicine')
    h.level_up_with_candy(0) if False else None
    h.open_bag(); h.bag_pocket('medicine')
    h.touch(*E.BAG_SLOTS[0], frames=12, after=60); h.touch(*E.BAG_USE, frames=12, after=60)
    h.touch(*E.PARTY_SLOTS[0], frames=12, after=120)
    shots = [h.screenshot('hc_candy_capped')]
    for _ in range(3): h.press('A', after=90)
    print('candy on Lv12 lead -> lead', mon_level_hp(h, 0))
    h.touch(*E.BAG_SLOTS[0], frames=12, after=60); h.touch(*E.BAG_USE, frames=12, after=60)
    h.touch(*E.PARTY_SLOTS[1], frames=12, after=120)
    for _ in range(4): h.press('A', after=90)
    print('candy on Lv5 second -> second', mon_level_hp(h, 1))
    leave_field_bag(h)
    # field: Revive on a fainted party Pokemon must be refused
    set_hp(h, 1, 0)
    h.bag_put_first(28, 5, 'medicine')
    h.open_bag(); h.bag_pocket('medicine')
    h.touch(*E.BAG_SLOTS[0], frames=12, after=60); h.touch(*E.BAG_USE, frames=12, after=60)
    h.touch(*E.PARTY_SLOTS[1], frames=12, after=120)
    shots.append(h.screenshot('hc_revive'))
    for _ in range(3): h.press('A', after=90)
    print('revive on fainted second -> second', mon_level_hp(h, 1))
    leave_field_bag(h)
    set_hp(h, 1, 20)
    h.bag_put_first(17, 5, 'medicine')
    # battle 1: options forced, Potion refused, Ball allowed
    log = single_battle(h)
    print('wild 1', log.rows[-1]['species'], 'options in battle', hex(options_word(h)), nz_state(h))
    shots += battle_bag_use(h, (64, 58), 'hc_potion')[:2]
    print('after potion try: in battle menu', h.on_screen('battle_menu'))
    throw_ball(h, 'hc_t1'); back_to_battle_menu(h); r = until_menu_or_field(h)
    if r == 'menu': h.flee(battle_menu_wait=10)
    print('after battle 1', party(h), nz_state(h))
    step_b2(h)
    step_b3(h)
    shots.append(open_pc_box24(h, 'hc_pc'))
    sheet(shots, 'hc_round.png', cols=4)
    h.close()
