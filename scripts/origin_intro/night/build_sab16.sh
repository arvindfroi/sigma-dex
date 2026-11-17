#!/bin/zsh
# Sabertann v16 = v15's frames (variants/v15) relit (night/saber_light.py) + the v16 scene (night/paint_v16.py).
# Locked 2026-11-14: v22 = SNAME=v22 night/build_sab16.sh (current scripts, default env).
# usage: night/build_sab16.sh   -> ../rc8/sabertann_${SNAME:-v16}.nds, shots_sab${SNAME:-v16}/
set -e
cd "$(dirname "$0")/.."
PY="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"; PY2=~/sigma-toolchain/venv312/bin/python
$PY2 night/saber_light.py variants/v15 saber3d
$PY2 night/paint_v16.py
export SAB_PPU0=16.0 SAB_PPU1=11 SAB_PPU2=7 SAB_OVER=1 SAB_NOF5=1 SAB_F0=1,2,3,4,6,7,8,9 SAB_F1=1,2,3,4 SAB_F2=1,3
SAB_TLEAP=160 SAB_S0=0.36 SAB_CELL=16 SAB_MOON=night/art_v16/moon.png "$PY" build_saber_v5.py out_a262_sab${SNAME:-v16}.narc | tail -2
NIGHT_ART=night/art_v16 "$PY" night/build_night.py out_a262_sab${SNAME:-v16}.narc night/out_sab${SNAME:-v16}.narc | tail -1
cp night/out_sab${SNAME:-v16}.narc ../rc8/x_night/files/a/2/6/2
(cd ../rc8 && ~/sigma-hgengine/tools/dsrom build -c x_night/config.yaml -o sabertann_${SNAME:-v16}.nds > /dev/null 2>&1)
[ -n "$NO_SHOTS" ] && { echo built rom only; exit 0; }
rm -rf shots_sab${SNAME:-v16}; S="wait:380"; for i in $(seq 0 159); do S="$S,shot:n$(printf %03d $i),wait:4"; done
$PY2 ../lw/drive.py ../rc8/sabertann_${SNAME:-v16}.nds shots_sab${SNAME:-v16} "$S" > /dev/null 2>&1
rm -rf variants/${SNAME:-v16}; mkdir -p variants/${SNAME:-v16}; cp -R saber3d/v5px saber3d/v5px14 saber3d/v5px7 variants/${SNAME:-v16}/
echo built sabertann v16
