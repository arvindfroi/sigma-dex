#!/bin/zsh
# v7 end to end: (model already built) render 3 detail levels -> sprite data -> night BGs -> ROM -> shots -> video
# usage: h3d/build_v7_variant.sh NAME YAW EL PPU0
set -e
cd "$(dirname "$0")/.."
NAME=$1; export SAB_YAW=$2 SAB_EL=$3 SAB_PPU0=$4 SAB_PPU1=${SAB_PPU1:-11} SAB_PPU2=7
PY="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"
h3d/render_v7.sh > h3d/render_$NAME.log 2>&1
SAB_TLEAP=160 SAB_S0=${SAB_S0:-0.36} SAB_CELL=16 SAB_MOON=night/art/moon.png "$PY" build_saber_v5.py out_a262_$NAME.narc | tail -4
"$PY" night/build_night.py out_a262_$NAME.narc night/out_$NAME.narc | tail -1
cp night/out_$NAME.narc ../rc8/x_night/files/a/2/6/2
(cd ../rc8 && ~/sigma-hgengine/tools/dsrom build -c x_night/config.yaml -o sabertann_$NAME.nds > /dev/null 2>&1)
rm -rf shots_$NAME; S="wait:380"; for i in $(seq 0 159); do S="$S,shot:n$(printf %03d $i),wait:4"; done
~/sigma-toolchain/venv312/bin/python ../lw/drive.py ../rc8/sabertann_$NAME.nds shots_$NAME "$S" > /dev/null 2>&1
mkdir -p "variants/$NAME"; cp -R saber3d/v5px saber3d/v5px14 saber3d/v5px7 "variants/$NAME/"
LABEL_A="Origin HG (Ho-Oh)" LABEL_B="${LABEL_B:-Sabertann v7 (3D fra tegningen)}" "$PY" night/make_video.py ../rc8/origin_hg_en_rc8.nds ../rc8/sabertann_$NAME.nds "/Users/arvind/Sigma pokemon pc port attempt/sabertann_intro_$NAME" 380 640
echo built $NAME
