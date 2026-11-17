#!/bin/zsh
# one intro variant end to end: model -> 7 frames x 3 detail levels -> sprite data -> night BGs -> ROM -> video
# usage: night/build_variant.sh NAME YAW HEADTURN CW [PPU0]
set -e
cd "$(dirname "$0")/.."
NAME=$1; YAW=$2; HT=$3; CW=$4; P0=${5:-22}; export SAB_PPU1=${SAB_PPU1:-13}
B=/Applications/Blender.app/Contents/MacOS/Blender
PY="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"
(cd saber3d && cat model_head.py model_body.py > model.py && SAB_HEADTURN=$HT $B -b --factory-startup -P model.py > log_model.txt 2>&1 \
  && SAB_YAW=$YAW SAB_CW=$CW SAB_CH=6.6 SAB_TZ=3.9 SAB_PPU0=$P0 ./rerender_v5.sh > rerender_$NAME.log 2>&1)
SAB_PPU0=$P0 SAB_TLEAP=160 SAB_S0=${SAB_S0:-0.34} SAB_CELL=16 SAB_MOON=night/art/moon.png "$PY" build_saber_v5.py out_a262_$NAME.narc | tail -3
"$PY" night/build_night.py out_a262_$NAME.narc night/out_$NAME.narc | tail -1
cp night/out_$NAME.narc ../rc8/x_night/files/a/2/6/2
(cd ../rc8 && ~/sigma-hgengine/tools/dsrom build -c x_night/config.yaml -o sabertann_$NAME.nds > /dev/null 2>&1)
rm -rf shots_$NAME; S="wait:380"; for i in $(seq 0 159); do S="$S,shot:n$(printf %03d $i),wait:4"; done
~/sigma-toolchain/venv312/bin/python ../lw/drive.py ../rc8/sabertann_$NAME.nds shots_$NAME "$S" > /dev/null 2>&1
mkdir -p "variants/$NAME"; cp -R saber3d/v5px saber3d/v5px14 saber3d/v5px7 "variants/$NAME/"
LABEL_A="Origin HG (Ho-Oh)" LABEL_B="Sabertann $NAME" "$PY" night/make_video.py ../rc8/origin_hg_en_rc8.nds ../rc8/sabertann_$NAME.nds "/Users/arvind/Sigma pokemon pc port attempt/sabertann_intro_$NAME" 380 640
echo built $NAME
