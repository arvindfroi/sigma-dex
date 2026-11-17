@ The Lugia ritual's version switch (Arvind 2026-11-16/17): Origin is HeartGold, so the legendary cutscene code
@ (pret src/field/legend_cutscene_camera.c, Origin's overlay 2) takes Ho-Oh's path in the Whirl Islands too: autumn
@ leaves, Ho-Oh's camera presets, no Lugia-arrives effect. Its three reads of gGameVersion (0x020F2058) are replaced by
@ calls to these hooks, which answer SoulSilver (8) when the field is on map 244 (MAP_WHIRL_ISLANDS_B3F_LUGIA_CAVE) and
@ the real version everywhere else. gGameVersion itself never changes, so "met in" data, Bell Tower and the rest of the
@ game stay HeartGold.  FieldSystem->location is at +0x20, Location->mapId at +0.
    .syntax unified
    .thumb
    .text
    .global lv_common, lv_hook_r5_r0, lv_hook_r4_r1
    .thumb_func
lv_common:                      @ r0 = FieldSystem* -> r0 = version for the cutscene
    ldr r1, [r0, #0x20]
    ldr r1, [r1, #0]
    ldr r0, =0x020F2058
    ldrb r0, [r0]
    cmp r1, #244
    bne 1f
    movs r0, #8
1:  bx lr
    .thumb_func
lv_hook_r5_r0:                  @ ClearBellAnim (0x02252D5C) and LugiaArrivesEffect (0x02253FE2): FieldSystem in r5
    push {r1-r3, lr}
    adds r0, r5, #0
    bl lv_common
    pop {r1-r3, pc}
    .thumb_func
lv_hook_r4_r1:                  @ BirdFinalApproach (0x0225388E): FieldSystem in r4, the version wanted in r1, r2 kept
    push {r0, r2, r3, lr}
    adds r0, r4, #0
    bl lv_common
    adds r1, r0, #0
    pop {r0, r2, r3, pc}
    .pool
