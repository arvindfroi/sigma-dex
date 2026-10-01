    // Example of a new move that needs no new game logic: a damaging move with a chance
    // of a stat drop is plain data. Animation borrowed from Brick Break.
    [MOVE_SIGMA_STRIKE] =
    {
        .name = COMPOUND_STRING("Sigma Strike"),
        .description = COMPOUND_STRING(
            "A disciplined blow that\n"
            "may lower Defense."),
        .effect = EFFECT_HIT,
        .power = 80,
        .type = TYPE_FIGHTING,
        .accuracy = 100,
        .pp = 15,
        .target = TARGET_SELECTED,
        .priority = 0,
        .category = DAMAGE_CATEGORY_PHYSICAL,
        .makesContact = TRUE,
        .additionalEffects = ADDITIONAL_EFFECTS({
            .moveEffect = MOVE_EFFECT_STAT_MINUS,
            .defense = 1,
            .chance = 30,
        }),
        .contestEffect = CONTEST_EFFECT_HIGHLY_APPEALING,
        .contestCategory = CONTEST_CATEGORY_COOL,
        .battleAnimScript = gBattleAnimMove_BrickBreak,
    },
