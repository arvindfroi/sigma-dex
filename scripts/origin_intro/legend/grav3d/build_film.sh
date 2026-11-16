#!/bin/zsh
# usage: build_film.sh G (export name, e.g. g6b) V (version tag, e.g. v6b)   -> legend_test/jump_lug_$V.nds + rec_lug$V
set -e
G=$1; V=$2
PY=~/sigma-toolchain/venv312/bin/python; PYV="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"; L=~/sigma-origin/legend_test
cd ~/sigma-origin/title3d/legend/grav3d
$PY tex_project.py $G.json ~/sigma-origin/title3d/grav/turn_11.png ${G}h | tail -1
cd ~/sigma-origin/title3d
DRIFT1=0 DRIFT2=0 $PY legend/grav3d/rig_lugia.py $L/x/files/a/2/4/4 $L/y/a244_$V legend/grav3d/${G}h.json 2>&1 | grep -E "display lists|group|file"
$PY legend/grav3d/cave_tint.py $L/y/a244_$V $L/y/a244_${V}w | tail -1
OUT=$($PY legend/relocate.py $L/jump_lug3.nds $L/x/files/a/2/4/4 $L/y/a244_${V}w $L/t1_$V.nds); echo $OUT
"$PYV" legend/inplace.py $L/t1_$V.nds $L/x/files/a/0/4/4 $L/y/a044_room2 $L/t2_$V.nds
"$PYV" legend/inplace.py $L/t2_$V.nds $L/x/files/a/0/7/0 $L/y/a070_room $L/t3_$V.nds
$PY legend/grav3d/room_weather.py $L/t3_$V.nds $L/jump_lug_$V.nds 10
if [ -n "$3" ]; then $PY legend/grav3d/fog_test.py $L/jump_lug_$V.nds $L/t4_$V.nds $3 $4 && mv $L/t4_$V.nds $L/jump_lug_$V.nds; fi
rm $L/t1_$V.nds $L/t2_$V.nds $L/t3_$V.nds
NS=$(echo $OUT | sed -E 's/.*-> (0x[0-9a-f]+) \(([0-9]+) bytes\).*/\1/'); NL=$(echo $OUT | sed -E 's/.*-> (0x[0-9a-f]+) \(([0-9]+) bytes\).*/\2/')
NE=$(printf '0x%x' $(( NS + NL )))
P=$($PY legend/grav3d/fat_pokes.py 0x023BFDC0 $NS $NE); echo "pokes $NS..$NE"
cd $L
S="$P,wait:20,R,R,R,U,U,R,R,U,U,L,U,R,R,wait:180"
for i in $(seq 0 3099); do
  if [ $i -ge 2240 ] && [ $i -lt 2560 ]; then S="$S,shot:f$(printf %04d $i),wait:1"
  elif [ $i -ge 2560 ] && [ $((i % 6)) -eq 0 ]; then S="$S,shot:f$(printf %04d $i),wait:1"
  else S="$S,wait:1"; fi
  [ $((i % 36)) -eq 35 ] && [ $i -lt 500 ] && S="$S,A"
done
rm -rf rec_lug$V; timeout 3000 $PY ../lw/drive.py jump_lug_$V.nds rec_lug$V "$S" --load ../lw/g7.dst >/dev/null 2>&1
ls rec_lug$V | wc -l
