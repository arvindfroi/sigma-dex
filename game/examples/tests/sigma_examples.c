#include "global.h"
#include "test/battle.h"

SINGLE_BATTLE_TEST("Sigma example: Sigma Strike damages the target")
{
    GIVEN {
        ASSUME(GetMoveType(MOVE_SIGMA_STRIKE) == TYPE_FIGHTING);
        ASSUME(GetMovePower(MOVE_SIGMA_STRIKE) == 80);
        PLAYER(SPECIES_WOBBUFFET);
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_SIGMA_STRIKE); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_SIGMA_STRIKE, player);
        HP_BAR(opponent);
    }
}

SINGLE_BATTLE_TEST("Sigma example: Sigma Strike lowers Defense 30% of the time")
{
    PASSES_RANDOMLY(30, 100, RNG_SECONDARY_EFFECT);
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET);
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_SIGMA_STRIKE); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_SIGMA_STRIKE, player);
        HP_BAR(opponent);
        ANIMATION(ANIM_TYPE_GENERAL, B_ANIM_STATS_CHANGE, opponent);
        MESSAGE("The opposing Wobbuffet's Defense fell!");
    } THEN {
        EXPECT_EQ(opponent->statStages[STAT_DEF], DEFAULT_STAT_STAGE - 1);
    }
}

SINGLE_BATTLE_TEST("Sigma example: Sigma Aura raises Speed by one stage on entry")
{
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET);
        OPPONENT(SPECIES_WOBBUFFET) { Ability(ABILITY_SIGMA_AURA); }
    } WHEN {
        TURN {}
    } SCENE {
        ABILITY_POPUP(opponent, ABILITY_SIGMA_AURA);
        ANIMATION(ANIM_TYPE_GENERAL, B_ANIM_STATS_CHANGE, opponent);
        MESSAGE("The opposing Wobbuffet's Speed rose!");
    } THEN {
        EXPECT_EQ(opponent->statStages[STAT_SPEED], DEFAULT_STAT_STAGE + 1);
    }
}

SINGLE_BATTLE_TEST("Sigma example: Sigma Aura triggers again after switching back in")
{
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET);
        OPPONENT(SPECIES_WOBBUFFET) { Ability(ABILITY_SIGMA_AURA); }
        OPPONENT(SPECIES_WYNAUT);
    } WHEN {
        TURN { SWITCH(opponent, 1); }
        TURN { SWITCH(opponent, 0); }
    } SCENE {
        ABILITY_POPUP(opponent, ABILITY_SIGMA_AURA);
        ABILITY_POPUP(opponent, ABILITY_SIGMA_AURA);
    } THEN {
        EXPECT_EQ(opponent->statStages[STAT_SPEED], DEFAULT_STAT_STAGE + 1);
    }
}
