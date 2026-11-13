#!/bin/zsh
# re-render all six pass sets (base/anim x 3 detail levels) and pixelize them
B=/Applications/Blender.app/Contents/MacOS/Blender
PY="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"
cd "$(dirname "$0")"
for cfg in 26:4:px 18:6:px18 9:12:px9; do
  ppu=${cfg%%:*}; rest=${cfg#*:}; ss=${rest%%:*}; px=${rest#*:}
  for layer in base anim; do
    SAB_LAYER=$layer $B -b sabertann.blend -P render_passes.py -- passes_${layer}_${ppu} $ppu $ss > log_${layer}_${ppu}.txt 2>&1 || { echo FAIL $layer $ppu; exit 1; }
    "$PY" pixelize.py passes_${layer}_${ppu} ${px}_${layer} || { echo FAILPX $layer $ppu; exit 1; }
    echo done $layer $ppu
  done
done
echo ALLDONE
