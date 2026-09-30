#!/bin/bash
# Full build in the Higgsfield sandbox: bash run.sh <commit-sha> "<master upload url>" "<review upload url>"
set -e
SHA=$1; UP_MASTER=$2; UP_REVIEW=$3
W=~/work; mkdir -p $W/pl && cd $W
pip install -q opencv-python-headless scipy >/dev/null 2>&1 || true
R=https://raw.githubusercontent.com/hacker123as/ila-firdawsi-app/$SHA/ad/pipeline
for f in screen.py build.py score.py audio.py shots.json fetch.sh; do curl -sfL -o pl/$f "$R/$f"; done
bash pl/fetch.sh $W
python3 pl/score.py $W/score.wav
python3 pl/audio.py $W
python3 pl/build.py $W
ffmpeg -v error -y -i $W/picture_4k.mp4 -i $W/mix.wav -map 0:v -map 1:a -c:v libx264 -preset slow -crf 16 -profile:v high -pix_fmt yuv420p \
  -r 24 -movflags +faststart -c:a aac -b:a 320k -shortest $W/IlaFirdawsi_Commercial_4K.mp4
ffmpeg -v error -y -i $W/IlaFirdawsi_Commercial_4K.mp4 -vf scale=1920:1080:flags=lanczos -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 192k -movflags +faststart $W/IlaFirdawsi_Commercial_1080p.mp4
ffprobe -v error -show_entries format=duration,size:stream=width,height,r_frame_rate -of compact $W/IlaFirdawsi_Commercial_4K.mp4
[ -n "$UP_REVIEW" ] && curl -sf -X PUT -H "Content-Type: video/mp4" --upload-file $W/IlaFirdawsi_Commercial_1080p.mp4 "$UP_REVIEW" -o /dev/null -w "review upload %{http_code}\n"
[ -n "$UP_MASTER" ] && curl -sf -X PUT -H "Content-Type: video/mp4" --upload-file $W/IlaFirdawsi_Commercial_4K.mp4 "$UP_MASTER" -o /dev/null -w "master upload %{http_code}\n"
echo DONE
