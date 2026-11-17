#!/bin/zsh
# v5 (head-on, Ho-Oh style): full frames, no base/anim split. Three detail levels.
B=/Applications/Blender.app/Contents/MacOS/Blender
PY="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"
cd "$(dirname "$0")"
export SAB_TRAILS=${SAB_TRAILS:-0} SAB_YAW=${SAB_YAW:-25} SAB_EL=${SAB_EL:-9} SAB_CW=${SAB_CW:-4.0} SAB_CH=${SAB_CH:-6.4} SAB_TZ=${SAB_TZ:-3.75} SAB_TX=0
for cfg in ${SAB_PPU0:-22}:4:v5px ${SAB_PPU1:-13}:6:v5px14 7:12:v5px7; do
  ppu=${cfg%%:*}; rest=${cfg#*:}; ss=${rest%%:*}; px=${rest#*:}
  SAB_LAYER=all $B -b sabertann.blend -P render_passes.py -- passes_v5_${ppu} $ppu $ss > log_v5_${ppu}.txt 2>&1 || { echo FAIL $ppu; exit 1; }
  "$PY" pixelize.py passes_v5_${ppu} ${px} || { echo FAILPX $ppu; exit 1; }
  echo done $ppu
done
echo ALLDONE
