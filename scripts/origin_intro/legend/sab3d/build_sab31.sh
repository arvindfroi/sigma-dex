#!/bin/zsh
# Sabertann's Ho-Oh film with the painted (turnaround) textures: build_sab31.sh BASE_SKY BASE_PAGODA V [L_SKY L_PAGODA]
#   BASE_* = legend/sab3d/pv3sky etc. (tex_views.py output; legend/sab3d/pt19r = v30's textures), V = version tag
#   -> legend_test/jump_hooh2_$V.nds + rec_$V
# The film outgrows its slot (8-bpp textures): relocated to the end of the ROM (legend/relocate.py) and the in-RAM file
# table of the g7.dst savestate pointed at it (file 363 = a/2/4/3 at RAM 0x023BFDB8).
set -e -o pipefail
BS=$1; BP=$2; V=$3; LS=${4:-0}; LP=${5:-0}
cd ~/sigma-origin/title3d
export ROLL=1 PATHFRAME=1 RIPPLE_R=50 HALFRATE=1 FOOTLOCK=0 CADENCE=36
Y=~/sigma-origin/legend_test/y; L=~/sigma-origin/legend_test; PY="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"; PY2=~/sigma-toolchain/venv312/bin/python
C=$(seq -s, 1 18 | sed 's/,$//'); cp $Y/a243_orig $Y/r_${V}_0; i=0
for mm in "0 1" "5 6" "10 11" "15 16" "19 20" "23 24"; do
  set -- $(echo $mm); LL=$LP; H=0; B=$BP; [ $1 -lt 15 ] && LL=$LS && H=8 && B=$BS
  HIDE_TAIL=$H LIGHTS=$LL $PY2 legend/rig3d.py $Y/r_${V}_$i $Y/r_${V}_$((i+1)) $B legend/sab3d/bones_run19.json $1 $2 460 $C 3 2>&1 | grep -E "strips placed|textures rebuilt|Error|assert|Trace|line " | sed 's/bones {.*}//' | tr '\n' ' '; echo; i=$((i+1))
done
"$PY" legend/pack_shared.py $Y/r_${V}_6 $Y/a243_$V 1=6 11=6 16=20 24=20 | tail -1
$PY2 legend/sab3d/vram_check.py $Y/a243_$V
OUT=$($PY2 legend/relocate.py $L/base_hover.nds $Y/a243_orig $Y/a243_$V $L/jump_hooh2_$V.nds); echo $OUT
NS=$(echo $OUT | sed -E 's/.*-> (0x[0-9a-f]+) \(([0-9]+) bytes\).*/\1/'); NL=$(echo $OUT | sed -E 's/.*-> (0x[0-9a-f]+) \(([0-9]+) bytes\).*/\2/')
P=$($PY2 legend/grav3d/fat_pokes.py 0x023BFDB8 $NS $(printf '0x%x' $(( NS + NL ))))
cd $L; S="$P,wait:20,R,R,R,U,U,R,R,U,U,L,U,R,R,wait:180"
for i in $(seq 0 2399); do if [ $i -ge 1000 ]; then S="$S,shot:f$(printf %04d $i),wait:1"; else S="$S,wait:1"; fi; [ $((i % 36)) -eq 35 ] && [ $i -lt 600 ] && S="$S,A"; done
rm -rf rec_$V; timeout 3000 $PY2 ../lw/drive.py jump_hooh2_$V.nds rec_$V "$S" --load ../lw/g7.dst >/dev/null 2>&1
ls rec_$V | wc -l
