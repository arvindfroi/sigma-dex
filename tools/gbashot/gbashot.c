/* Runs a GBA ROM without a window, presses buttons from a script and saves screenshots.
 *   gbashot game.gba script.txt outdir
 * Script lines:  run <frames> [A B START SELECT UP DOWN LEFT RIGHT L R ...]   hold those buttons for that many frames
 *                shot <name>                                                 save outdir/<name>.ppm
 */
#include <mgba/core/core.h>
#include <mgba/core/config.h>
#include <mgba/core/log.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void quiet(struct mLogger* l, int cat, enum mLogLevel level, const char* fmt, va_list args) { (void) l; (void) cat; (void) level; (void) fmt; (void) args; }
static struct mLogger sLogger = { .log = quiet };

static int key(const char* name) {
    static const char* names[] = { "A", "B", "SELECT", "START", "RIGHT", "LEFT", "UP", "DOWN", "R", "L" };
    for (int i = 0; i < 10; ++i) if (!strcmp(name, names[i])) return 1 << i;
    fprintf(stderr, "unknown button %s\n", name); exit(2);
}

int main(int argc, char** argv) {
    if (argc != 4) { fprintf(stderr, "usage: gbashot game.gba script.txt outdir\n"); return 2; }
    mLogSetDefaultLogger(&sLogger);
    struct mCore* core = mCoreFind(argv[1]);
    if (!core) { fprintf(stderr, "not a GBA ROM: %s\n", argv[1]); return 1; }
    core->init(core);
    mCoreInitConfig(core, NULL);
    unsigned w, h;
    core->desiredVideoDimensions(core, &w, &h);
    color_t* pixels = calloc(w * h, sizeof(color_t));
    core->setVideoBuffer(core, pixels, w);
    if (!mCoreLoadFile(core, argv[1])) { fprintf(stderr, "could not load %s\n", argv[1]); return 1; }
    core->reset(core);
    FILE* script = fopen(argv[2], "r");
    if (!script) { perror(argv[2]); return 1; }
    char line[512];
    long total = 0;
    while (fgets(line, sizeof line, script)) {
        char* word = strtok(line, " \t\r\n");
        if (!word || word[0] == '#') continue;
        if (!strcmp(word, "run")) {
            long frames = atol(strtok(NULL, " \t\r\n"));
            int keys = 0;
            while ((word = strtok(NULL, " \t\r\n"))) keys |= key(word);
            core->setKeys(core, keys);
            for (long i = 0; i < frames; ++i) core->runFrame(core);
            core->setKeys(core, 0);
            total += frames;
        } else if (!strcmp(word, "shot")) {
            char path[1024];
            snprintf(path, sizeof path, "%s/%s.ppm", argv[3], strtok(NULL, " \t\r\n"));
            FILE* out = fopen(path, "wb");
            fprintf(out, "P6\n%u %u\n255\n", w, h);
            for (unsigned i = 0; i < w * h; ++i) {
                unsigned char rgb[3] = { pixels[i] & 0xFF, (pixels[i] >> 8) & 0xFF, (pixels[i] >> 16) & 0xFF };
                fwrite(rgb, 1, 3, out);
            }
            fclose(out);
        }
    }
    fprintf(stderr, "ran %ld frames\n", total);
    return 0;
}
