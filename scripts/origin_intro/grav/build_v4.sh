#!/bin/zsh
# Gravriel v4: 2D sprite from his front view rising behind the BG1 water, new fog scene, priority code patch.
# Locked 2026-11-14: v16 = grav/build_v4.sh v16 with the defaults below.
# usage: grav/build_v4.sh NAME        -> ../rc8/gravriel_NAME.nds, shots_NAME/, four-way video in the repo root
set -e
cd "$(dirname "$0")/.."
NAME=$1; PY="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"; PY2=~/sigma-toolchain/venv312/bin/python
REPO="/Users/arvind/Sigma pokemon pc port attempt"
$PY2 grav/grav2d.py grav/px2d_$NAME | tail -1 | cut -c1-40
GP=${GPAINT:-paint_grav10}; GA=${GART:-art_grav10}   # defaults = locked v16
$PY2 night/$GP.py
G4_SEA=${G4_SEA-night/art_grav10/bottom.png} $PY grav/build_grav4.py grav/px2d_$NAME out_a262_grav_$NAME.narc | tail -3
NIGHT_ART=night/$GA $PY night/build_night.py out_a262_grav_$NAME.narc night/out_grav_$NAME.narc | tail -1
OV=../rc8/x_night/arm9_overlays/ov056.bin
cp night/out_grav_$NAME.narc ../rc8/x_night/files/a/2/6/2
$PY2 grav/patch_prio.py $OV apply
(cd ../rc8 && ~/sigma-hgengine/tools/dsrom build -c x_night/config.yaml -o gravriel_$NAME.nds > /dev/null 2>&1) || { $PY2 grav/patch_prio.py $OV revert; exit 1; }
$PY2 grav/patch_prio.py $OV revert
[ -n "$NO_SHOTS" ] && { echo built rom only; exit 0; }
rm -rf shots_grav_$NAME; S="wait:380"; for i in $(seq 0 159); do S="$S,shot:n$(printf %03d $i),wait:4"; done
$PY2 ../lw/drive.py ../rc8/gravriel_$NAME.nds shots_grav_$NAME "$S" > /dev/null 2>&1
R=../rc8
$PY2 night/make_video4.py "$REPO/intro_fire" "Lugia (SS)=$HOME/sigma-origin/ss/zip/Pokemon - SoulSilver Version (USA, Australia).nds" "Ho-Oh (HG)=$R/origin_hg_en_rc8.nds" "Sabertann v22=$R/sabertann_v22.nds" "Gravriel $NAME=$R/gravriel_$NAME.nds" | tail -2
echo built $NAME
