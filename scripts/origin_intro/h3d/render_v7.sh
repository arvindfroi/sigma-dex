#!/bin/zsh
# v7: render the three detail levels of the Hunyuan-based model into saber3d/v5px*, where build_saber_v5.py reads them
B=/Applications/Blender.app/Contents/MacOS/Blender
PY="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"
cd "$(dirname "$0")/../saber3d"
export SAB_TRAILS=${SAB_TRAILS:-0} SAB_YAW=${SAB_YAW:-20} SAB_EL=${SAB_EL:-9} SAB_CW=${SAB_CW:-7.0} SAB_CH=${SAB_CH:-8.0} SAB_TZ=${SAB_TZ:-3.6} SAB_TX=${SAB_TX:-0} SAB_DEPTHLINE=${SAB_DEPTHLINE:-0.5}
BL=${SAB_BLEND:-../h3d/sab_v7.blend}
for cfg in ${SAB_PPU0:-17}:4:v5px ${SAB_PPU1:-11}:6:v5px14 ${SAB_PPU2:-6}:12:v5px7; do
  ppu=${cfg%%:*}; rest=${cfg#*:}; ss=${rest%%:*}; px=${rest#*:}
  [ -n "$ONLY0" ] && [ "$px" != v5px ] && continue
  SAB_LAYER=all $B -b $BL -P render_passes.py -- passes_v7_${ppu} $ppu $ss > log_v7_${ppu}.txt 2>&1 || { echo FAIL $ppu; tail -5 log_v7_${ppu}.txt; exit 1; }
  "$PY" pixelize.py passes_v7_${ppu} ${px} || { echo FAILPX $ppu; exit 1; }
  echo done $ppu
done
