#!/usr/bin/env bash
set -euo pipefail
mkdir -p qa-output /tmp/wnc-wildlife-source-probe
FILE=/tmp/wnc-wildlife-source-probe/Crickets_choir.ogg
REPORT=qa-output/WREC-015-source-probe.txt
SOURCE='https://upload.wikimedia.org/wikipedia/commons/4/4c/Crickets_choir.ogg'
{
 echo 'WhiteNoiseChoir Wildlife Source Probe: WREC-015'
 echo 'Source page: https://commons.wikimedia.org/wiki/File:Crickets_choir.ogg'
 echo 'Creator: Serg Childed'
 echo 'License displayed on Commons: CC BY-SA 4.0'
 echo 'Wikimedia VRT permission ticket 2020080210004823'
 echo 'Original source URL: ' "$SOURCE"
 echo 'Do not publish before attribution, share-alike compatibility, listening and loop QA.'
} > "$REPORT"
if ! curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 --max-time 240 --user-agent 'WhiteNoiseChoir-ResearchQA/1.0' -o "$FILE" "$SOURCE"; then
 echo 'STATUS: DOWNLOAD_BLOCKED' >> "$REPORT"
 exit 1
fi
{
 echo 'STATUS: DOWNLOAD_OK'
 stat -c 'Bytes: %s' "$FILE"
 sha256sum "$FILE" | awk '{print "SHA256:", $1}'
 echo
 echo 'ffprobe:'
 ffprobe -v error -show_entries format=duration,size,bit_rate,format_name:stream=index,codec_name,sample_rate,channels -of json "$FILE"
 echo
 echo 'FFmpeg volumedetect:'
 ffmpeg -hide_banner -nostats -i "$FILE" -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume|histogram_' | tail -n 15 || true
 echo
 echo 'FFmpeg silencedetect intervals > 2 sec below -55dB:'
 ffmpeg -hide_banner -nostats -i "$FILE" -af silencedetect=noise=-55dB:d=2 -f null - 2>&1 | grep -E 'silence_start:|silence_end:' | head -n 50 || true
 echo
 echo 'STATUS: AUTOMATED_METADATA_ONLY_PASS'
 echo 'Human listening, isolation of voices, stereo imaging, loop seam and licensing review: NOT_TESTED'
} >> "$REPORT"
rm -f "$FILE"
