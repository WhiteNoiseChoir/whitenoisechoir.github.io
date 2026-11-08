#!/usr/bin/env python3
"""Add only a new 7-day native HLS timeline for Green Noise without modifying old streams."""
from __future__ import annotations
import hashlib, json, math, subprocess, sys, tempfile, shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_continuous_hls import run_ffmpeg,parse_playlist,verify_transport,build_loop

ROOT=Path("audio")
MASTER=ROOT/"green-noise.mp3"
REGISTRY=ROOT/"green-noise-master-manifest.json"
TARGET=ROOT/"continuous"/"green-noise"
GLOBAL=ROOT/"continuous"/"manifest.json"

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def db(value):return 20*math.log10(max(value,1e-12))
def decode_boundary(path):
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-xerror","-ss","590",
        "-i",str(path),"-t","25","-ar","8000","-ac","1","-f","f32le","pipe:1"]
    p=subprocess.run(cmd,capture_output=True,check=False)
    if p.returncode:raise RuntimeError("HLS decode failed: "+p.stderr.decode(errors="replace")[-800:])
    import numpy as np
    x=np.frombuffer(p.stdout,dtype="<f4")
    if len(x)<24.9*8000 or not np.isfinite(x).all():raise RuntimeError("HLS truncation/nonfinite")
    def rms(a):return db(float(np.sqrt(np.mean(np.square(a,dtype=np.float64)))))
    before=rms(x[2*8000:8*8000]);after=rms(x[12*8000:18*8000])
    if abs(before-after)>4:raise RuntimeError(f"Source cycle loudness changed {before:.2f} -> {after:.2f}")
    for i in range(9*8000,14*8000-2000,2000):
        if rms(x[i:i+2000])<-64:raise RuntimeError("HLS boundary dead air")
    return (round(before,2),round(after,2))

def main():
    master=json.loads(REGISTRY.read_text(encoding="utf-8"))
    if master["id"]!="green-noise" or master["qa"]["technical_status"]!="PASS" or sha(MASTER)!=master["file_sha256"]:
        raise RuntimeError("Green master failed input approval/hash validation")
    with tempfile.TemporaryDirectory(dir=ROOT/"continuous") as td:
        tmp=Path(td)
        run_ffmpeg(MASTER,tmp)
        parts=parse_playlist(tmp/"source.m3u8",expected_seconds=600)
        verify_transport(tmp/parts[0][0])
        cycles,length=build_loop(parts,tmp/"continuous.m3u8")
        if length<7*86400:raise RuntimeError("HLS must span at least 7 days")
        TARGET.mkdir(exist_ok=True,parents=True)
        for prev in TARGET.glob("part_*.ts"):prev.unlink()
        for filename,_ in parts:shutil.copy2(tmp/filename,TARGET/filename)
        shutil.copy2(tmp/"continuous.m3u8",TARGET/"continuous.m3u8")
        boundary=decode_boundary(TARGET/"continuous.m3u8")
        record={
            "id":"green-noise","master_file":str(MASTER),"master_sha256":master["file_sha256"],
            "playlist_file":str(TARGET/"continuous.m3u8"),
            "playlist_sha256":sha(TARGET/"continuous.m3u8"),
            "segment_count_per_source_cycle":len(parts),
            "source_cycle_seconds":round(sum(d for _,d in parts),3),
            "original_source_length_category":"10_MINUTE_MASTER",
            "source_license":"original_dsp","source_page":None,
            "editorial_status":"PENDING_NEW_BATCH_HUMAN_REVIEW",
            "repeated_cycles":cycles,
            "native_stream_duration_hours":round(length/3600,2),
            "audio_codec":"AAC-LC in MPEG-TS","sample_rate":44100,"channels":2,"bitrate_kbps":192,
            "long_form_listening_status":"PENDING_IPHONE_LOCK_SCREEN_REVIEW",
            "notes":"Green noise is a user-defined mid-band spectrum, not a standard noise color. Seven-day HLS repeats the 10-minute independently synthesized master; device playback can still be interrupted."
        }
        global_manifest=json.loads(GLOBAL.read_text(encoding="utf-8"))
        prior=[x for x in global_manifest["records"] if x["id"]!="green-noise"]
        if len(prior)!=21 or len({x["id"] for x in prior})!=21:
            raise RuntimeError("Refuse to alter existing 21 source HLS records")
        global_manifest["records"]=prior+[record]
        global_manifest["applies_to"]=sorted([x["id"] for x in global_manifest["records"]])
        global_manifest["version"]="continuous-hls-v3-green-20261108"
        global_manifest["playlist_type"]="static multi-cycle HLS VOD, seven days per track, 22 sound IDs"
        global_manifest["source_length_disclosure"]="18 independently produced/arranged 10-minute masters; 4 short 54-second CC0 demos. HLS changes transport continuity, not unique recording length."
        GLOBAL.write_text(json.dumps(global_manifest,indent=2)+"\n",encoding="utf-8")
        print("GREEN_HLS_QA",json.dumps({"segments":len(parts),"cycles":cycles,"hours":round(length/3600,2),"boundary_levels_dbfs":boundary,"playlist_sha256":record["playlist_sha256"],"status":"PASS"}),flush=True)

if __name__=="__main__":
    main()
