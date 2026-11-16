/* Nuzlocke and Hardcore Nuzlocke for Origin HeartGold (EN rc8 + advanced trainer AI). Our own code; see README.md.
 *
 * Both modes:
 *   - First encounter per area: the first random wild battle in an area (map section) uses it up. In every later
 *     random wild battle there, a Poke Ball is refused in the battle Bag (nothing is used up).
 *   - Graveyard: after a battle every fainted Pokemon is marked dead and leaves the party for the last PC box
 *     ("GRAVES": box names hold 8 letters), where its icon is grey. A wiped party moves nothing (the blackout decides).
 *   - No revives: Revive, Max Revive, Revival Herb and Sacred Ash are refused in battle and on the party screen.
 * Hardcore only:
 *   - The difficulty options are forced before every battle: level CAP on, ITEMS DEFAULT, battle style SET.
 *   - No Bag items in battle except Poke Balls.
 *   - Rare Candy is refused on a Pokemon at or above the level cap.
 *
 * All game functions below are Origin's own, at the addresses of this build (the build script checks the bytes).
 */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#define GAME(addr, ret, ...) ((ret (*)(__VA_ARGS__))((addr) | 1))   /* Thumb functions: bit 0 set */
#define BattleEnd_CopyBack   GAME(0x02051574, void, void *setup, void *fs)       /* US sub_0205239C */
#define SaveArray_Party_Get  GAME(0x0207365C, void *, void *save)
#define Party_GetCount       GAME(0x02073398, int, void *party)
#define Party_GetMon         GAME(0x0207339C, void *, void *party, int slot)
#define Party_RemoveMon      GAME(0x020732C4, int, void *party, int slot)
#define GetMonData           GAME(0x0206D848, u32, void *mon, int field, void *buf)
#define SetMonData           GAME(0x0206DF70, void, void *mon, int field, const void *value)
#define GetBoxMonData        GAME(0x0206D948, u32, void *boxmon, int field, void *buf)
#define Boxmon_GetIconPal    GAME(0x020731A4, u32, void *boxmon)
#define SaveArray_PC_Get     GAME(0x0202754C, void *, void *save)
#define PC_PlaceInBox        GAME(0x02072AD4, int, void *pc, u32 box, void *boxmon) /* first empty slot */
#define SaveArray_Misc_Get   GAME(0x0202AE2C, u8 *, void *save)                  /* apricorn trees at +0 */
#define Save_GetOptions      GAME(0x02029348, u16 *, void *save)
#define Save_Current         GAME(0x02001194, void *, void)
#define MapHeader_MapSec     GAME(0x0203A800, u32, u32 map)
#define Save_GetProfile      GAME(0x0202933C, void *, void *save)
#define Profile_HasBadge     GAME(0x02029428, u32, void *profile, u32 badge)
#define Save_GetVars         GAME(0x0204F858, void *, void *save)
#define Vars_GetFlag         GAME(0x0204F864, u32, void *vars, u32 flag)

#define MON_DATA_DEAD 53            /* MON_DATA_UNUSED_RIBBON_53: our "died in a nuzlocke" mark */
#define MON_DATA_IS_EGG 76
#define MON_DATA_LEVEL 161
#define MON_DATA_HP 163

#define ITEM_REVIVE 28
#define ITEM_MAX_REVIVE 29
#define ITEM_REVIVAL_HERB 37
#define ITEM_SACRED_ASH 44
#define ITEM_RARE_CANDY 50
#define BAG_POKE_BALLS 2            /* battle Bag category */
#define MSG_NO_ITEMS 0x32           /* battle Bag text bank 5, added by the build script */
#define MSG_NO_REVIVE 0x33

#define OPT_CAP_ON 0x0008           /* Options word: the English patch's difficulty bits and battle style */
#define OPT_ITEMS_ALL 0x0020
#define OPT_STYLE_SET 0x0040

#define FS_SAVE 0x0C
#define FS_LOCATION 0x20
#define GRAVEYARD_BOX 23            /* the last of Origin's 24 boxes */
#define PC_BOX_NAMES 0x18008        /* box names, 20 code units each */
#define NZ_STATE 0x7C               /* SaveMisc: apricorn slots 31..127 (Origin uses 0..30; loops patched) */
#define GREY_PAL_SHIFT 7            /* PC icons use OBJ palettes 3-5; grey copies sit in 10-12 */
#define OBJ_PAL_MAIN ((volatile u16 *)0x05000200)

#ifndef NZ_TEST_MODE
#define NZ_TEST_MODE 1
#endif

/* our save data: 388 bytes free, 40 used. The magic matters: before the loop patch the game's daily apricorn
   loops wrote 1 into bytes 0 and 1 of every slot, so old saves have that pattern here. */
#define NZ_MAGIC 0x315A554E         /* "NUZ1" */
struct nz_state {
    u32 magic;
    u8 mode;                        /* 0 off, 1 nuzlocke, 2 hardcore nuzlocke */
    u8 unused;
    u16 deaths;
    u8 area_used[32];               /* one bit per map section 0..255 */
};

u8 nz_no_catch;                     /* set while a random wild battle runs in an area already used */
u8 nz_battle_mode;                  /* the mode of the battle being fought (set when a field battle is set up) */

extern const u16 nz_graveyard_name[];   /* game text codes, written by the build script */
extern const u16 nz_grey_icon_pal[48];  /* grey copies of the three icon palettes, from the ROM, by the build */

static struct nz_state *nz_get(void *save)
{
    struct nz_state *st = (struct nz_state *)(SaveArray_Misc_Get(save) + NZ_STATE);
    if (st->magic != NZ_MAGIC) {    /* first use; the real game will set the mode from Gravriel's new-game menu */
        u8 *p = (u8 *)st;
        for (unsigned i = 0; i < sizeof *st; i++)
            p[i] = 0;
        st->magic = NZ_MAGIC;
        st->mode = NZ_TEST_MODE;
    }
    return st;
}

static int is_revive(u32 item)
{
    return item == ITEM_REVIVE || item == ITEM_MAX_REVIVE || item == ITEM_REVIVAL_HERB || item == ITEM_SACRED_ASH;
}

/* Level cap from the badges, the same rule as the English patch's CAP setting (caps.c, Apache-2.0): the highest
   gym maximum up to the first gym not yet beaten, in the guide's order. Erika's and Clair's badges also count when
   their flags (1220, 209) are set. To be replaced by our own table once our trainers' levels are set. */
static u32 nz_level_cap(void *save)
{
    static const u8 ids[16] = {0, 1, 2, 3, 5, 6, 4, 7, 8, 9, 10, 11, 13, 12, 14, 15};
    static const u8 maxima[16] = {12, 20, 25, 38, 55, 65, 80, 100, 80, 80, 88, 80, 80, 80, 85, 85};
    void *profile = Save_GetProfile(save), *vars = Save_GetVars(save);
    u32 badges = 0, cap = 0;
    for (u32 i = 0; i < 16; i++)
        if (Profile_HasBadge(profile, i))
            badges |= 1u << i;
    if (Vars_GetFlag(vars, 1220))
        badges |= 1u << 3;
    if (Vars_GetFlag(vars, 209))
        badges |= 1u << 15;
    for (u32 i = 0; i < 16; i++) {
        if (maxima[i] > cap)
            cap = maxima[i];
        if (!(badges & (1u << ids[i])))
            return cap;
    }
    return 100;
}

/* Every battle set up from the field (wild, trainer, scripted) passes here before the save is copied in. */
void nz_on_battle_setup(void *save)
{
    struct nz_state *st = nz_get(save);
    nz_battle_mode = st->mode;
    if (st->mode == 2) {
        u16 *opt = Save_GetOptions(save);
        *opt = (u16)((*opt | OPT_CAP_ON | OPT_STYLE_SET) & ~OPT_ITEMS_ALL);
    }
}

/* Random wild battle starts (grass, cave, water, fishing, rock smash). */
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

/* Battle Bag, before any item is used: 0 = go on, else the refusal message. */
u32 nz_bag_item_check(u32 category, u32 item)
{
    if (!nz_battle_mode)
        return 0;
    if (is_revive(item))
        return MSG_NO_REVIVE;
    if (nz_battle_mode == 2 && category != BAG_POKE_BALLS)
        return MSG_NO_ITEMS;
    return 0;
}

/* Party screen, "use item on a Pokemon": nonzero blocks it (the game then says it has no effect, item kept). */
u32 nz_party_item_blocked(void *party, u32 item, u32 slot)
{
    void *save = Save_Current();
    if (!save)
        return 0;
    struct nz_state *st = nz_get(save);
    if (!st->mode)
        return 0;
    if (is_revive(item))
        return 1;
    if (st->mode == 2 && item == ITEM_RARE_CANDY)
        return GetMonData(Party_GetMon(party, slot), MON_DATA_LEVEL, 0) >= nz_level_cap(save);
    return 0;
}

/* PC box icons: a dead Pokemon gets the grey copy of its palette. */
u32 nz_icon_palette(void *boxmon)
{
    u32 pal = Boxmon_GetIconPal(boxmon);
    if (GetBoxMonData(boxmon, MON_DATA_DEAD, 0))
        pal += GREY_PAL_SHIFT;
    return pal;
}

/* PC box start-up, right after it loaded the three icon palettes into OBJ slots 3-5: our grey ones into 10-12. */
void nz_load_grey_palettes(void)
{
    for (int i = 0; i < 48; i++)
        OBJ_PAL_MAIN[(3 + GREY_PAL_SHIFT) * 16 + i] = nz_grey_icon_pal[i];
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
    nz_battle_mode = 0;

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
    static const u32 one = 1;
    for (int i = n - 1; i >= 0; i--) {
        void *mon = Party_GetMon(party, i);
        if (GetMonData(mon, MON_DATA_IS_EGG, 0) || GetMonData(mon, MON_DATA_HP, 0))
            continue;
        SetMonData(mon, MON_DATA_DEAD, &one);
        /* a party Pokemon starts with its box data, so the same pointer is the box Pokemon */
        if (PC_PlaceInBox(pc, GRAVEYARD_BOX, mon)) {
            Party_RemoveMon(party, i);
            st->deaths++;
            nz_name_graveyard(pc);
        }
    }
}
