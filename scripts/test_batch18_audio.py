#!/usr/bin/env python3
"""Audit all 18 selected production sound masters without modifying or rendering audio.
Metadata and provenance must agree with the bytes actually committed to GitHub.
Human listening quality is a separate sign-off.
"""
from __future__ import annotations
import array, hashlib, json, math, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
def load(path):return json.loads((ROOT/path).read_text(encoding="utf-8"))
catalog=load("catalog/library.json")
batch=load("catalog/batch18-20261108.json")
extended=load("audio/extended-dsp-manifest.json")
colored=load("audio/color-master-manifest.json")
natural=load("audio/master-manifest.json")
green=load("audio/green-noise-master-manifest.json")
hls=load("audio/continuous/manifest.json")
manifest={x["id"]:x for x in extended["tracks"]+colored["tracks"]+natural["masters"]+[green]}
transport={x["id"]:x for x in hls["records"]}
assert len(transport)==22
assert len(batch["sound_ids"])==18 and len(set(batch["sound_ids"]))==18
def execute(cmd):
    p=subprocess.run(cmd,capture_output=True,check=False)
    if p.returncode:raise RuntimeError("Failed "+cmd[0]+": "+p.stderr.decode(errors="replace")[-1100:])
    return p.stdout
def checksum(p):
    sh=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):sh.update(block)
    return sh.hexdigest()
def decode(p,offset,seconds):
    cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-xerror","-ss",str(offset),"-i",str(p),
         "-t",str(seconds),"-vn","-ac","1","-ar","8000","-f","f32le","pipe:1"]
    raw=execute(cmd)
    y=array.array("f");y.frombytes(raw)
    if sys.byteorder!="little":y.byteswap()
    assert len(y)>seconds*8000*.96,f"Truncated audio from {p}"
    assert all(math.isfinite(v) for v in y),f"Non-finite decoded samples from {p}"
    n=len(y)
    peak=max(abs(v) for v in y)
    rms=math.sqrt(sum(float(v)*v for v in y)/n)
    assert 0<peak<0.995,f"Clipping or all-silence {p}: {peak}"
    rmsdb=20*math.log10(max(rms,1e-10))
    assert rmsdb>-65,f"Unexpectedly silent sample {p}: {rmsdb:.1f}"
    return round(rmsdb,2)
for id in batch["sound_ids"]:
    data=manifest[id]
    qa=data.get("qa") or data.get("technical_qa")
    assert qa and qa["technical_status"]=="PASS",id
    master=ROOT/"audio"/(id+".mp3")
    playlist=ROOT/"audio"/"continuous"/id/"continuous.m3u8"
    assert master.is_file() and playlist.is_file(),id
    assert checksum(master)==data["file_sha256"],id+" SHA256 mismatch"
    meta=json.loads(execute(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(master)]))
    stream=next(z for z in meta["streams"] if z.get("codec_type")=="audio")
    duration=float(meta["format"]["duration"])
    assert stream["codec_name"]=="mp3" and int(stream["channels"])==2 and int(stream["sample_rate"])==44100,id
    assert 599.0<=duration<=601.0,(id,duration)
    bitrate=int(meta["format"]["bit_rate"])
    assert 183000<=bitrate<=201000,(id,bitrate)
    before=decode(master,38,3)
    after=decode(master,558,3)
    # Rain and fire are intentionally dynamic; no artificial loudness-match requirement.
    if id not in ("rain-on-window-real","fireplace-real"):
        assert abs(after-before)<10,(id,before,after)
    records=transport[id]
    assert records["native_stream_duration_hours"]>=167.9,id
    assert records["repeated_cycles"]>=900,id
    assert "#EXTM3U" in playlist.read_text(encoding="utf-8")[:100],id
    assert checksum(playlist)==records["playlist_sha256"],id
    parts=list(playlist.parent.glob("part_*.ts"))
    assert len(parts)==records["segment_count_per_source_cycle"],id
    if id in ("rain-on-window-real","fireplace-real"):
        assert data["independent_source_duration_seconds"]==60,id
        assert data["source_page"].startswith("https://freesound.org/"),id
        assert data["license"]=="CC0-1.0",id
    print("BATCH18_AUDIO "+json.dumps({"id":id,"duration":round(duration,3),"bitrate":bitrate,"rms_38s":before,"rms_558s":after,"master_sha256":data["file_sha256"],"status":"PASS"}),flush=True)
print("PASS: 18 real committed master MP3s, source SHA-256, audio decode, sample rate, duration, HLS SHA-256 and source provenance",flush=True)
