@ Weather Switch for Origin HeartGold v4.0.3 (BW-style battle engine in overlay 14).
@ On entry: rain -> sun, sun -> rain, anything else -> random rain or sun.
    .syntax unified
    .thumb
    .equ GetEventVar,     0x0220fcc0   @ r0 = var id; var 6 = poke id of the event
    .equ GetWeather,      0x02205784   @ current weather (0 when suppressed by Cloud Nine/Air Lock)
    .equ BattleRand,      0x0222646c   @ r0 = range -> 0..range-1
    .equ AbilitySetWeather,0x0223ab80  @ (pokeID, weather, extending item, 0, [sp]=1, 0, 0) as Drizzle/Drought do
    .equ WEATHER_RAIN, 1
    .equ WEATHER_SUN, 2
    .equ ITEM_HEAT_ROCK, 284
    .equ ITEM_DAMP_ROCK, 285

    .section .text.handler, "ax"
    .global ws_handler
    .thumb_func
ws_handler:                     @ r1 = poke id that owns this handler
    push {r4, lr}
    sub sp, #12
    movs r4, r1
    movs r0, #6
    bl GetEventVar
    cmp r0, r4
    bne done                    @ someone else switched in
    bl GetWeather
    cmp r0, #WEATHER_RAIN
    beq to_sun
    cmp r0, #WEATHER_SUN
    beq to_rain
    movs r0, #2
    bl BattleRand
    cmp r0, #0
    beq to_rain
to_sun:
    movs r1, #WEATHER_SUN
    ldr r2, =ITEM_HEAT_ROCK
    b set
to_rain:
    movs r1, #WEATHER_RAIN
    ldr r2, =ITEM_DAMP_ROCK
set:
    movs r3, #1
    str r3, [sp, #0]
    movs r3, #0
    str r3, [sp, #4]
    str r3, [sp, #8]
    movs r0, r4
    bl AbilitySetWeather
done:
    add sp, #12
    pop {r4, pc}
    .pool

    .section .text.add, "ax"
    .global ws_add
    .thumb_func
ws_add:                         @ r0 = u32* count; returns the handler table
    movs r1, #2
    str r1, [r0]
    ldr r0, =ws_table
    bx lr
    .pool
    .align 2
ws_table:
    .word 10, ws_handler        @ event 10: Pokemon enters the field (same events as Drizzle)
    .word 31, ws_handler        @ event 31: after its ability changes
