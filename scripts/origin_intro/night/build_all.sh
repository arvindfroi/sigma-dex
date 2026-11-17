#!/bin/zsh
# whole chain: model -> renders -> sprite data (moon + Sabertann) -> night BGs -> ROM -> emulator shots
set -e
cd "$(dirname "$0")/.."
B=/Applications/Blender.app/Contents/MacOS/Blender
PY="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"
OUT=${1:-sabertann_v4}
(cd saber3d && cat model_head.py model_body.py > model.py && $B -b --factory-startup -P model.py > log_model.txt 2>&1 && ./rerender_all.sh > rerender.log 2>&1)
SAB_CELL=32 SAB_LAMBDA=15 SAB_MOON=night/art/moon.png "$PY" build_saber_intro.py out_a262_$OUT.narc | tail -3
"$PY" night/build_night.py out_a262_$OUT.narc night/out_$OUT.narc | tail -1
cp night/out_$OUT.narc ../rc8/x_night/files/a/2/6/2
(cd ../rc8 && ~/sigma-hgengine/tools/dsrom build -c x_night/config.yaml -o $OUT.nds > /dev/null 2>&1)
rm -rf shots_$OUT; S="wait:380"; for i in $(seq 0 159); do S="$S,shot:n$(printf %03d $i),wait:4"; done
~/sigma-toolchain/venv312/bin/python ../lw/drive.py ../rc8/$OUT.nds shots_$OUT "$S" > /dev/null 2>&1
echo built ../rc8/$OUT.nds
