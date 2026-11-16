/* Nuzlocke test for Origin HeartGold (EN rc8 + advanced trainer AI). Our own code; see README.md here.
 *
 * Two rules in this first test:
 *   1. First encounter per area: the first random wild battle in an area (map section) uses up that area.
 *      In every later random wild battle there, a Poke Ball is refused in the battle Bag (nothing is used up).
 *   2. Graveyard: after a battle, every fainted Pokemon leaves the party for the last PC box (named "GRAVES": box names hold 8 letters).
 *      When the whole party fainted nothing moves (the blackout decides what happens then).
 *
 * All game functions below are Origin's own, at the addresses of this build (checked by the build script).
 */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

/* game functions (Thumb, so the address has bit 0 set) */
#define GAME(addr, ret, ...) ((ret (*)(__VA_ARGS__))((addr) | 1))
#define BattleEnd_CopyBack   GAME(0x02051574, void, void *setup, void *fs)       /* US sub_0205239C */
#define SaveArray_Party_Get  GAME(0x0207365C, void *, void *save)
#define Party_GetCount       GAME(0x02073398, int, void *party)
#define Party_GetMon         GAME(0x0207339C, void *, void *party, int slot)
#define Party_RemoveMon      GAME(0x020732C4, int, void *party, int slot)
#define GetMonData           GAME(0x0206D848, u32, void *mon, int field, void *buf)
#define SaveArray_PC_Get     GAME(0x0202754C, void *, void *save)
#define PC_PlaceInBox        GAME(0x02072AD4, int, void *pc, u32 box, void *boxmon) /* first empty slot */
#define SaveArray_Misc_Get   GAME(0x0202AE2C, u8 *, void *save)                  /* apricorn trees at +0 */
#define MapHeader_MapSec     GAME(0x0203A800, u32, u32 map)

#define MON_DATA_IS_EGG 76
#define MON_DATA_HP 163

#define FS_SAVE 0x0C               /* FieldSystem: save data */
#define FS_LOCATION 0x20           /* FieldSystem: current location, map id first */
#define GRAVEYARD_BOX 23           /* the last of Origin's 24 boxes */
#define PC_BOX_NAMES 0x18008       /* box names, 20 code units each */
#define NZ_STATE 0x7C              /* in SaveMisc: apricorn slots 31..127 (Origin uses 0..30; loops patched) */

/* our save data: 388 bytes free, this test uses 40. The magic matters: before the loop patch the game's daily
   apricorn loops wrote 1 into bytes 0 and 1 of every slot, so old saves have that pattern here. */
#define NZ_MAGIC 0x315A554E        /* "NUZ1" */
struct nz_state {
    u32 magic;
    u8 mode;                       /* 0 off, 1 nuzlocke, 2 hardcore */
    u8 unused;
    u16 deaths;
    u8 area_used[32];              /* one bit per map section 0..255 */
};

u8 nz_no_catch;                    /* set while a random wild battle runs in an area already used */

extern const u16 nz_graveyard_name[];   /* game text codes, written by the build script */

static struct nz_state *nz_get(void *save)
{
    struct nz_state *st = (struct nz_state *)(SaveArray_Misc_Get(save) + NZ_STATE);
    if (st->magic != NZ_MAGIC) {   /* first use: this test build starts every save in nuzlocke mode */
        u8 *p = (u8 *)st;
        for (unsigned i = 0; i < sizeof *st; i++)
            p[i] = 0;
        st->magic = NZ_MAGIC;
        st->mode = 1;
    }
    return st;
}

/* Called when a random wild battle starts (grass, cave, water, fishing, rock smash). */
void nz_on_wild_start(u8 *fs, void *env)
{
    (void)env;
    struct nz_state *st = nz_get(*(void **)(fs + FS_SAVE));
    if (!st->mode)
        return;
    u32 sec = MapHeader_MapSec(**(u32 **)(fs + FS_LOCATION)) & 0xFF;
    u8 bit = 1 << (sec & 7);
    if (st->area_used[sec >> 3] & bit) {
        nz_no_catch = 1;
    } else {
        st->area_used[sec >> 3] |= bit;
        nz_no_catch = 0;
    }
}

static void nz_name_graveyard(void *pc)
{
    u16 *name = (u16 *)((u8 *)pc + PC_BOX_NAMES) + 20 * GRAVEYARD_BOX;
    for (int i = 0; i < 20; i++) {
        name[i] = nz_graveyard_name[i];
        if (name[i] == 0xFFFF)
            break;
    }
}

/* Replaces the battle-end call that copies the party back to the save. */
void nz_battle_end(void *setup, u8 *fs)
{
    BattleEnd_CopyBack(setup, fs);
    nz_no_catch = 0;

    void *save = *(void **)(fs + FS_SAVE);
    struct nz_state *st = nz_get(save);
    if (!st->mode)
        return;
    void *party = SaveArray_Party_Get(save);
    int n = Party_GetCount(party), alive = 0;
    for (int i = 0; i < n; i++) {
        void *mon = Party_GetMon(party, i);
        if (!GetMonData(mon, MON_DATA_IS_EGG, 0) && GetMonData(mon, MON_DATA_HP, 0))
            alive++;
    }
    if (!alive)
        return;
    void *pc = SaveArray_PC_Get(save);
    for (int i = n - 1; i >= 0; i--) {
        void *mon = Party_GetMon(party, i);
        if (GetMonData(mon, MON_DATA_IS_EGG, 0) || GetMonData(mon, MON_DATA_HP, 0))
            continue;
        /* a party Pokemon starts with its box data, so the same pointer is the box Pokemon */
        if (PC_PlaceInBox(pc, GRAVEYARD_BOX, mon)) {
            Party_RemoveMon(party, i);
            st->deaths++;
            nz_name_graveyard(pc);
        }
    }
}
