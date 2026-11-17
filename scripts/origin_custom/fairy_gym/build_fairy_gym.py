"""Azalea Gym becomes a Fairy gym (Arvind, 2026-11-17; GutnDin's idea): Bugsy's party check bans the types strong
against Fairy (Poison and Steel) instead of Fire, Flying and Rock, and his refusal line says so.

  ~/sigma-toolchain/venv312/bin/python scripts/origin_custom/fairy_gym/build_fairy_gym.py IN.nds OUT.nds

- Script file 866 (a/0/1/2) has 203 PlayerHasSpecies checks in a row (L393 on). Only their species ids change: the
  species with Poison or Steel in any form, from the EN patch's species list (~/origin-en/site/src/data/species.json,
  national ids, 168 of them on 2026-11-17). Fewer than 203: the last id repeats. Our own species are added at export.
- Message bank 559 (Azalea Gym), line 22: the refusal. The EN patch's charmaps encode it.
Nothing here holds game data; it reads Arvind's own ROM and writes a new one."""
import json, os, struct, sys
from pathlib import Path
EN = Path.home() / 'origin-en'
sys.path[:0] = [str(EN / 'work/tools'), str(EN / 'work/tools/docs')]
import ndspy.rom, ndspy.narc
import romdata as R
import msgtool as M

SCRIPT_FILE, MSG_BANK, MSG_LINE, SLOTS = 866, 559, 22, 203
LINE = ("Bugsy: None of your Pokémon can be{NEWLINE}Poison or Steel type.{SCROLL}"
        "Those two would make this battle{NEWLINE}far too easy for you!")


def banned_species():
    sp = json.loads((EN / 'site/src/data/species.json').read_text())
    return sorted({x.get('baseSpeciesId') or x['id'] for x in sp if set(x['types']) & {'Poison', 'Steel'}})


def patch_script(data, ids):
    C = R.cmds()
    op = next(o for o, c in C.items() if (c.get('name') if isinstance(c, dict) else str(c)) in ('PlayerHasSpecies',)
              or 'PlayerHasSpecies' in str(c))
    _, ins = R.disasm(bytes(data))
    pcs = sorted(pc for pc, (o, a, n, t) in ins.items() if o == op)
    assert len(pcs) == SLOTS, len(pcs)
    if len(ids) > SLOTS:
        raise SystemExit('%d species do not fit in %d checks: the script has to be rebuilt longer' % (len(ids), SLOTS))
    ids = ids + [ids[-1]] * (SLOTS - len(ids))
    out = bytearray(data)
    for pc, sid in zip(pcs, ids):
        assert struct.unpack_from('<H', out, pc)[0] == op
        struct.pack_into('<H', out, pc + 4, sid)          # PlayerHasSpecies var(u16), species(u16)
    return bytes(out)


def patch_text(data):
    cm = M.Charmap.load(R.CHARMAPS)
    seed, strings, trailer = M.decrypt_bank(bytes(data))
    strings[MSG_LINE] = M.encode_text(LINE, cm) + [0xFFFF]
    return M.encrypt_bank(seed, strings, trailer)


def main(src, dst):
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    ids = banned_species()
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    scripts.files[SCRIPT_FILE] = patch_script(scripts.files[SCRIPT_FILE], ids)
    rom.setFileByName('a/0/1/2', scripts.save())
    msgs = ndspy.narc.NARC(rom.getFileByName('a/0/2/7'))
    msgs.files[MSG_BANK] = patch_text(msgs.files[MSG_BANK])
    rom.setFileByName('a/0/2/7', msgs.save())
    rom.saveToFile(dst)
    print('banned species:', len(ids), '->', dst)


if __name__ == '__main__':
    main(*sys.argv[1:3])
