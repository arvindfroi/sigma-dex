#!/bin/zsh
# legend/to_video.sh SHOTDIR OUT.mp4 [fps=20]  - both screens, 2x nearest
ffmpeg -y -loglevel error -framerate ${3:-20} -pattern_type glob -i "$1/f*.png" -vf "scale=512:768:flags=neighbor" -c:v libx264 -pix_fmt yuv420p -crf 18 "$2"
