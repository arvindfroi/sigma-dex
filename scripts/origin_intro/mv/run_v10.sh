#!/bin/zsh
# v10 after the paint: eyes -> steady-hand clean -> Blender model -> a look from the intro angle and around
# usage: mv/run_v10.sh NAME   (expects mv/out/NAME.npz/.ply, NAME_lab/part/fit/extra from paint_mv.py)
set -e
cd "$(dirname "$0")/.."
N=$1; PY=~/sigma-toolchain/venv312/bin/python; B=/Applications/Blender.app/Contents/MacOS/Blender
export SAB_TEX=$PWD/h3d/tex
EYE_Z=${EYE_Z:-0.135} EYE_VIEW=front EYE_PARTS=mv/out/${N}_part.npy $PY mv/eyes.py mv/out/$N.npz mv/out/${N}_fit.json mv/out/${N}_extra.json ${EYE_UV:-444,358}
$PY h3d/clean_labels.py mv/out/$N.npz mv/out/${N}_lab.npy mv/out/${N}_part.npy mv/out/${N}c
SAB_WATER7=${SAB_WATER7:-0.03} SAB_JOINTS="$(cat mv/joints_D.json)" SAB_ZMIN=${SAB_ZMIN:--0.74} $B -b --factory-startup -P mv/build_v10.py -- mv/out/$N.ply mv/out/${N}c mv/out/${N}_extra.json "$PWD/mv/sab_v10.blend" 2>&1 | grep -i "error\|saved /\|Traceback\|line [0-9]" | head
CTR=0,-0.3,2.9 OSCALE=8.2 RES=440 $B -b mv/sab_v10.blend -P h3d/pose_preview.py -- mv/out/v10_look.png 1 "0,5;90,3;180,5;24,9;35,12" 2>&1 | grep -i "error\|saved mv\|Traceback"
