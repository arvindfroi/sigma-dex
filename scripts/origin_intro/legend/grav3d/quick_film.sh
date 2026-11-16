#!/bin/zsh
# quick film test: quick_film.sh TJSON TAG   (atlas json already made) -> rec_q_TAG with shots 2440..2510 step 10
set -e -o pipefail
TJ=$1; V=$2; PY=~/sigma-toolchain/venv312/bin/python; L=~/sigma-origin/legend_test
cd ~/sigma-origin/title3d
DRIFT1=0 DRIFT2=0 LIGHTS=${LIGHTS:-0} $PY legend/grav3d/rig_lugia.py $L/x/files/a/2/4/4 $L/y/a244_q$V $TJ 2>&1 | grep -E "textures|^model|Error|Trace|assert"
$PY legend/grav3d/cave_tint.py $L/y/a244_q$V $L/y/a244_q${V}w | tail -1
OUT=$($PY legend/relocate.py $L/jump_lug3.nds $L/x/files/a/2/4/4 $L/y/a244_q${V}w $L/jump_lug_q$V.nds)
NL=$(stat -f %z $L/y/a244_q${V}w); P=$($PY legend/grav3d/fat_pokes.py 0x023BFDC0 0x109dcc00 $(printf '0x%x' $((0x109dcc00 + NL))))
cd $L; S="$P,wait:20,R,R,R,U,U,R,R,U,U,L,U,R,R,wait:180"
for i in $(seq 0 2512); do if [ $i -ge 2440 ] && [ $((i % 10)) -eq 0 ]; then S="$S,shot:f$(printf %04d $i),wait:1"; else S="$S,wait:1"; fi; [ $((i % 36)) -eq 35 ] && [ $i -lt 500 ] && S="$S,A"; done
rm -rf rec_q_$V; timeout 2000 $PY ../lw/drive.py jump_lug_q$V.nds rec_q_$V "$S" --load ../lw/g7.dst >/dev/null 2>&1; echo "$V $(ls rec_q_$V | wc -l)"
