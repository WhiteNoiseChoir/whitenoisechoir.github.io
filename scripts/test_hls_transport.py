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
LONG={
    "white-noise","pink-noise","brown-noise","green-noise","rain-on-window-real","fireplace-real",
    "blue-noise","violet-noise","soft-white-noise","deep-brown-noise",
    "warm-pink-noise","mid-noise","low-rumble","desk-fan-synth",
    "air-conditioner-synth","cabin-hum-synth","wind-synth","shower-synth",
}
NEW_RAIN={"light-rain-real","rain-tin-roof-real","distant-thunder-real"}
SHORT={"box-fan-real","heavy-rain-real","ocean-waves-real","waterfall-real"}
WAVE2={"rain-on-tent-real","rain-car-roof-real","rolling-thunder-real"}
WAVE3={"rain-leaves-real","rain-lake-real"}
WATER_OCEAN={"rushing-river-real","forest-stream-real","gentle-ocean-real"}
WATER_OCEAN_WAVE2={"bodetal-brook-real","crashing-ocean-real"}
EXPECTED=LONG | SHORT | NEW_RAIN | WAVE2 | WAVE3 | WATER_OCEAN | WATER_OCEAN_WAVE2
assert len(LONG)==18 and len(SHORT)==4 and len(EXPECTED)==35


def rms(values):
    if not values:
        return 0.0
    return math.sqrt(sum(float(x)*float(x) for x in values)/len(values))


def decibels(value):
    return 20*math.log10(max(1e-12,value))


def check(ident):
    playlist=Path("audio/continuous")/ident/"continuous.m3u8"
    rows = json.loads(Path("audio/continuous/manifest.json").read_text())["records"]
    source = next(x for x in rows if x["id"] == ident)
    target = max(0, int(round(source["source_cycle_seconds"])) - 10)
    duration = 30
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin",
         "-ss",str(target),"-i",str(playlist),
         "-t",str(duration),"-vn","-ar",str(SR),"-ac","1",
         "-f","f32le","pipe:1"]
    proc=subprocess.run(cmd,capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"Could not decode HLS boundary for {ident}: {proc.stderr.decode(errors='replace')[-800:]}")
    if len(proc.stdout)%4:
        raise RuntimeError(f"Malformed decoded PCM for {ident}")
    samples=array.array("f")
    samples.frombytes(proc.stdout)
    actual_duration=len(samples)/SR
    if not (duration-1 <= actual_duration <= duration+0.5):
        raise RuntimeError(f"Truncated audio at source boundary for {ident}: {actual_duration:.2f}s")
    if not all(math.isfinite(float(v)) for v in samples):
        raise RuntimeError(f"Non-finite audio from {ident}")
    # The selected source splice occurs about 10 seconds into this window.
    before=samples[2*SR:8*SR]
    after=samples[12*SR:18*SR]
    before_level=decibels(rms(before))
    after_level=decibels(rms(after))
    if abs(before_level-after_level)>(14 if ident in (NEW_RAIN | WAVE2 | WAVE3 | WATER_OCEAN | WATER_OCEAN_WAVE2) else 10 if ident in SHORT else 6):
        raise RuntimeError(f"Unexpected loudness change across loop in {ident}: {before_level:.1f} to {after_level:.1f}dBFS")
    # Reject prolonged dead air at the splice (around 600 seconds).
    frame=SR//4
    around=samples[9*SR:14*SR]
    windows=[decibels(rms(around[i:i+frame])) for i in range(0,len(around)-frame,frame)]
    if min(windows)<(-72 if ident=="rain-tin-roof-real" else -64):
        raise RuntimeError(f"Digital silence across loop of {ident}: {min(windows)}dBFS")
    return {
        "id":ident,"source_cycle_seconds":source["source_cycle_seconds"],"decoded_seconds_across_source_boundary":round(actual_duration,2),
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
    print("PASS: all 35 HLS streams decode continuously across each source cycle.",flush=True)


if __name__=="__main__":
    main()
