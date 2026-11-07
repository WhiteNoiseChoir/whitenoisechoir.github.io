#!/usr/bin/env python3
"""Decode HLS *through* the 10-minute master boundary, not just within segments.

This catches playlists/transport errors that could make playback stop after the
first complete copy of the source. It is NOT an iPhone lock-screen emulator.
"""
import array
import json
import math
from pathlib import Path
import subprocess
import sys

SR=8000
EXPECTED={"white-noise","pink-noise","brown-noise","rain-on-window-real","fireplace-real"}


def rms(values):
    if not values:
        return 0.0
    return math.sqrt(sum(float(x)*float(x) for x in values)/len(values))


def decibels(value):
    return 20*math.log10(max(1e-12,value))


def check(ident):
    playlist=Path("audio/continuous")/ident/"continuous.m3u8"
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin",
         "-ss","590","-i",str(playlist),
         "-t","30","-vn","-ar",str(SR),"-ac","1",
         "-f","f32le","pipe:1"]
    proc=subprocess.run(cmd,capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"Could not decode HLS boundary for {ident}: {proc.stderr.decode(errors='replace')[-800:]}")
    if len(proc.stdout)%4:
        raise RuntimeError(f"Malformed decoded PCM for {ident}")
    samples=array.array("f")
    samples.frombytes(proc.stdout)
    duration=len(samples)/SR
    if not (29 <= duration <= 30.5):
        raise RuntimeError(f"Truncated audio at 10-minute boundary for {ident}: {duration:.2f}s")
    if not all(math.isfinite(float(v)) for v in samples):
        raise RuntimeError(f"Non-finite audio from {ident}")
    # 590..620: the ten-minute splice occurs 10 seconds into this window.
    before=samples[2*SR:8*SR]
    after=samples[12*SR:18*SR]
    before_level=decibels(rms(before))
    after_level=decibels(rms(after))
    if abs(before_level-after_level)>6:
        raise RuntimeError(f"Unexpected loudness change across loop in {ident}: {before_level:.1f} to {after_level:.1f}dBFS")
    # Reject prolonged dead air at the splice (around 600 seconds).
    frame=SR//4
    around=samples[9*SR:14*SR]
    windows=[decibels(rms(around[i:i+frame])) for i in range(0,len(around)-frame,frame)]
    if min(windows)<-64:
        raise RuntimeError(f"Digital silence across loop of {ident}: {min(windows)}dBFS")
    return {
        "id":ident,"decoded_seconds_across_source_boundary":round(duration,2),
        "pre_boundary_rms_dbfs":round(before_level,1),
        "post_boundary_rms_dbfs":round(after_level,1),
        "quietest_250ms_across_boundary_dbfs":round(min(windows),1),
        "result":"PASS",
    }


def main():
    manifest=json.loads(Path("audio/continuous/manifest.json").read_text())
    if set(manifest["applies_to"])!=EXPECTED:
        raise RuntimeError("Unexpected stream manifest track inventory")
    results=[check(name) for name in sorted(EXPECTED)]
    for row in results:
        print("HLS_BOUNDARY_QA",json.dumps(row),flush=True)
    print("PASS: all five HLS streams decode continuously from minute 9:50 to 10:20.",flush=True)


if __name__=="__main__":
    main()
