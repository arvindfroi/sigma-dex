"""Opening scene 1 code patch for Gravriel v4 (overlay 56 of Origin HG EN rc8 = pret src/intro_movie_scene_1.c):
IntroMovie_Scene1_CreateSprites builds the sun's template with BG priority 1 and the bird's with 0, and the renderer
overwrites every OAM's priority with them. The sun becomes Gravriel, so he must go behind BG1 (priority 1), where the
water in front of him is painted: his template gets priority 2.
  0x27a8  1c02  adds r2, r0, #0   (r2 = 1)   ->  2202  movs r2, #2
v6: BG1 (the near layer, which holds the water in front of him) no longer scrolls, so its water always lines up with
the sea on BG3 (a scrolling copy showed a second horizon). IntroMovie_StartBgScroll_VBlank(.., MAIN_1, 0, -0x20, 0xF0):
  0x22dc  43c0  mvns r0, r0      (r0 = -0x20) ->  2000  movs r0, #0
v7: the bird sprite (it draws the rings on the water) starts 5 frames after the scroll instead of 128, so the water
can react when he first surfaces; the fade then waits 213 frames instead of 90, so it starts at the same time as before.
In IntroMovie_Scene1_Main: 0x234a  2e80 cmp r6,#128 -> 2e05 cmp r6,#5;  0x235e  2e5a cmp r6,#90 -> 2ed5 cmp r6,#213
python grav/patch_prio.py OVERLAY.bin apply|revert   (checks the bytes around each first)"""
import sys, struct, os
path, mode = sys.argv[1], sys.argv[2]
b = bytearray(open(path, 'rb').read())
OFF = 0x27a8
ctx = struct.unpack_from('<8H', b, OFF - 6)
# 2001 movs r0,#1 | 1c0c | 1c29 adds r1,r5 | [1c02 / 2202] | 1c03 adds r3,r0 | bl
assert ctx[0] == 0x2001 and ctx[1] == 0x1c0c and ctx[2] == 0x1c29 and ctx[4] == 0x1c03, [hex(v) for v in ctx]
cur = struct.unpack_from('<H', b, OFF)[0]
want = 0x2202 if mode == 'apply' else 0x1c02
assert cur in (0x1c02, 0x2202), hex(cur)
struct.pack_into('<H', b, OFF, want)
print(mode, 'priority', hex(cur), '->', hex(want))
O2 = 0x22dc
c2 = struct.unpack_from('<6H', b, O2 - 2)
# 201f movs r0,#0x1f | [43c0 / 2000] | 9000 str r0,[sp] | 20f0 movs r0,#0xf0 | 9001 | 1c21
assert c2[0] == 0x201f and c2[2] == 0x9000 and c2[3] == 0x20f0 and c2[4] == 0x9001, [hex(v) for v in c2]
assert c2[1] in (0x43c0, 0x2000), hex(c2[1])
w2 = 0x2000 if (mode == 'apply' and os.environ.get('GRAV_BG1_STILL', '0') == '1') else 0x43c0   # v15: BG1 scrolls again
struct.pack_into('<H', b, O2, w2)
print(mode, 'BG1 scroll', hex(c2[1]), '->', hex(w2))
T1, T2 = 0x234a, 0x235e
if os.environ.get('GRAV_BIRD_EARLY', '1') == '1' or mode == 'revert':
    for off, orig, new in ((T1, 0x2e80, 0x2e05), (T2, 0x2e5a, 0x2ed5)):
        cur = struct.unpack_from('<H', b, off)[0]
        assert cur in (orig, new), (hex(off), hex(cur))
        w = new if mode == 'apply' else orig
        struct.pack_into('<H', b, off, w)
        print(mode, 'timer', hex(off), hex(cur), '->', hex(w))
# v13: BG2 (moon, glow and high clouds in Gravriel's scene) rises 16 px during the scroll instead of sinking, like the
# sun in Ho-Oh's scene; BG1 (water) stays still.  0x22f2 200f movs r0,#0xf / 0x22f4 43c0 mvns  ->  2010 movs r0,#16 / 46c0 nop
if os.environ.get('GRAV_BG2_RISE', '1') == '1' or mode == 'revert':
    O3 = 0x22f2
    c3 = struct.unpack_from('<6H', b, O3 - 2)
    assert c3[0] == 0xfa83 and c3[3] == 0x9000 and c3[4] == 0x20f0, [hex(v) for v in c3]
    cur = (c3[1], c3[2]); orig = (0x200f, 0x43c0); new = (0x2010, 0x46c0)
    assert cur in (orig, new), [hex(v) for v in cur]
    w = new if mode == 'apply' else orig
    struct.pack_into('<2H', b, O3, *w)
    print(mode, 'BG2 scroll', [hex(v) for v in cur], '->', [hex(v) for v in w])
# v15: the sprites load 3 palettes instead of 2 (palette 2 = the sea strip drawn in front of his waist), in
# IntroMovie_Scene1_LoadSpriteGfx: AddPlttResObjFromNarc(.., 2, ..)  0x270a 2002 movs r0,#2 -> 2003 movs r0,#3
if os.environ.get('GRAV_PAL3', '1') == '1' or mode == 'revert':
    O4 = 0x270a
    c4 = struct.unpack_from('<4H', b, O4 - 2)
    assert c4[0] == 0x9001 and c4[2] == 0x9002 and c4[3] == 0x214a, [hex(v) for v in c4]
    assert c4[1] in (0x2002, 0x2003, 0x2004), hex(c4[1])
    w4 = 0x2004 if mode == 'apply' else 0x2002          # 4 palettes: 3 = the fading ghost
    struct.pack_into('<H', b, O4, w4)
    print(mode, 'sprite palettes', hex(c4[1]), '->', hex(w4))
open(path, 'wb').write(b)
