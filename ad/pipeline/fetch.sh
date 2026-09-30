#!/bin/bash
# Pull every input into $1 (the sandbox workdir).
set -e
W=$1; mkdir -p $W/plates $W/ui $W/fonts $W/vo
C=https://d8j0ntlcm91z4.cloudfront.net/user_3JxekxfRx9DiL6C77tMD5mjXb7k
R=https://raw.githubusercontent.com/hacker123as/ila-firdawsi-app/claude/elegant-noether-gz4tim/ad
get() { [ -s "$2" ] || curl -sfL --retry 3 -o "$2" "$1"; }
get $C/hf_20260930_075454_49a994cc-d352-4439-aeae-f70dca8085da.mp4 $W/plates/v1.mp4
get $C/hf_20260930_075508_9783f532-ca8b-4545-9cd5-931e813d594a.mp4 $W/plates/v2.mp4
get $C/hf_20260930_075706_1c99f43d-85b2-407c-b8ec-99624e012389.mp4 $W/plates/v3.mp4
get $C/hf_20260930_075707_64efcd34-4379-406e-8cf1-a59ba5540db2.mp4 $W/plates/v4.mp4
get $C/hf_20260930_075706_67551c25-eead-4584-b31e-000d0d2ae48b.mp4 $W/plates/v5.mp4
get $C/hf_20260930_075815_f7150333-3fdb-4f7e-a779-39695c5536b7.mp4 $W/plates/v6.mp4
get $C/hf_20260930_080025_5cbac3d3-b343-47d6-83e0-6e6e49430d7b.mp4 $W/plates/v7.mp4
get $C/hf_20260930_080502_2a8cd2b3-ecb0-4be8-bd35-aebbdd4f23de.mp4 $W/plates/v9.mp4
# voice: Soraya (lines 1-4), brand name take 2 ("Eela Fir-dow-see")
get $C/hf_20260930_075607_0b6347a7-d69a-4eb7-a20f-e39d07d74536.wav $W/vo/l1.wav
get $C/hf_20260930_075608_fa35754e-4840-43bb-9bc6-af65403401c9.wav $W/vo/l2.wav
get $C/hf_20260930_075607_ba947b61-4e8d-4c01-ac98-62263e520b9b.wav $W/vo/l3.wav
get $C/hf_20260930_075607_36b424f9-b7cc-4426-b427-c959701700e1.wav $W/vo/l4.wav
get $C/hf_20260930_081235_aef86d6d-c554-4d2e-b14a-2719a0d329ef.wav $W/vo/l5.wav
for f in A_home_before B_modal_a B_modal_b B_modal_c C_focus_cam_q0 D_focus_cam_s0 E_focus_cam_q1 F_focus_cam_s1 G_focus_cam_q2 H_focus_complete I_prayer_before J_prayer_after J_home_after M_qibla I_prayer_scroll1; do get $R/ui/$f.png $W/ui/$f.png; done
get $R/endcard_splash_4k.mp4 $W/endcard_splash_4k.mp4
get "https://github.com/google/fonts/raw/main/ofl/nunito/Nunito%5Bwght%5D.ttf" $W/fonts/Nunito.ttf
get "https://github.com/google/fonts/raw/main/ofl/fraunces/Fraunces%5BSOFT,WONK,opsz,wght%5D.ttf" $W/fonts/Fraunces.ttf
ffmpeg -v error -y -i $W/plates/v1.mp4 -vn -ac 2 -ar 48000 $W/city.wav
# a quiet frame of the prayer for the Focus Mode camera preview, and the montage backdrop
ffmpeg -v error -y -ss 8.5 -i $W/plates/v7.mp4 -frames:v 1 $W/camfill.png
ffmpeg -v error -y -ss 4.6 -i $W/plates/v6.mp4 -frames:v 1 $W/montage_bg.png
echo fetched
