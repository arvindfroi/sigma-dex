"""Tiny Gen 4 HG script disassembler from pret's asm/macros/script.inc (opcode + arg sizes; follows jumps/calls,
not movement data). python legend/scrdis.py SCRIPT.inc NARC MEMBER"""
import sys, re, struct
sys.path.insert(0, '.')
from narc import unpack
INC, NARC, M = sys.argv[1], sys.argv[2], int(sys.argv[3])
ops = {}
for m in re.finditer(r'\.macro (\w+)([^\n]*)\n(.*?)\.endm', open(INC).read(), re.S):
    name, body = m.group(1), m.group(3).strip().split('\n')
    first = body[0].strip()
    mm = re.match(r'\.short (\d+)$', first)
    if not mm: continue
    args = []
    for l in body[1:]:
        l = l.strip(); t = l.split(' ')[0]
        if t in ('.byte', '.short', '.word', '.hword'):
            args.append(({'.byte': 1, '.short': 2, '.hword': 2, '.word': 4}[t], '-.-4' in l))
        elif l: args = None; break
    if args is not None and int(mm.group(1)) not in ops: ops[int(mm.group(1))] = (name, args)
d = unpack(open(NARC, 'rb').read())[M]
starts = []; o = 0
while o + 4 <= len(d) and struct.unpack_from('<H', d, o)[0] != 0xFD13:
    starts.append(o + 4 + struct.unpack_from('<i', d, o)[0]); o += 4
seen = {}; todo = [(s, f'script{i}') for i, s in enumerate(starts)]; labels = {s: f'script{i}' for i, s in enumerate(starts)}
while todo:
    pc, _ = todo.pop()
    while pc < len(d) and pc not in seen:
        op = struct.unpack_from('<H', d, pc)[0]
        if op not in ops: seen[pc] = f'?? op {op}'; break
        name, args = ops[op]; p = pc + 2; vals = []
        for sz, rel in args:
            v = int.from_bytes(d[p:p + sz], 'little', signed=rel); p += sz
            if rel:
                t = p + v; vals.append(f'@{t:04X}')
                if name not in ('ApplyMovement',) : todo.append((t, '')); labels.setdefault(t, f'L{t:04X}')
            else: vals.append(str(v))
        seen[pc] = name + ' ' + ', '.join(vals)
        if name in ('End', 'Return', 'GoTo', 'Jump'): break
        pc = p
for pc in sorted(seen):
    if pc in labels: print(f'{labels[pc]}:')
    print(f'  {pc:04X} {seen[pc]}')
