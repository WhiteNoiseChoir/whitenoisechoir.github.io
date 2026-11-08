#!/usr/bin/env python3
"""Technical source validation for long-form White/Pink/Brown Noise originals.

Usage: python3 scripts/test_noise_color_master.py pink-noise [white-noise ...]
This validates actual audio bytes. Subjective listening remains a separate gate.
"""
from __future__ import annotations
import hashlib, json, math, subprocess, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
TRACKS={"white-noise":0.0,"pink-noise":-10.0,"brown-noise":-20.0}
SR=16000

def run(cmd):
    process=subprocess.run(cmd,capture_output=True,check=False)
    if process.returncode:
        raise RuntimeError(f"{cmd[0]} returned {process.returncode}: {process.stderr.decode(errors='replace')[-700:]}")
    return process.stdout

def samples(filepath,offset,length,sample_rate=SR):
    pcm=run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-xerror","-ss",str(offset),"-i",str(filepath),"-t",str(length),"-vn","-ar",str(sample_rate),"-ac","1","-f","f32le","pipe:1"])
    array=np.frombuffer(pcm,dtype="<f4")
    assert len(array)>=length*sample_rate*.985, f"Truncated audio {filepath} at {offset}"
    assert np.isfinite(array).all(),f"Non-finite samples {filepath}"
    return array

def level(a):
    return 20*math.log10(max(1e-12,math.sqrt(float(np.mean(np.square(a,dtype=np.float64))))))

def slope_db_per_decade(a):
    frame=8192;hop=4096;window=np.hanning(frame)
    spectra=[]
    for start in range(0,len(a)-frame+1,hop):
        chunk=a[start:start+frame].astype("float64")
        spectra.append(np.abs(np.fft.rfft((chunk-chunk.mean())*window))**2)
    assert spectra,"No spectral frames"
    psd=np.mean(spectra,axis=0)
    f=np.fft.rfftfreq(frame,1/SR)
    edges=np.geomspace(100,5500,23)
    x,y=[],[]
    for lo,hi in zip(edges[:-1],edges[1:]):
        band=psd[(f>=lo)&(f<hi)]
        if band.size:
            x.append(math.log10(math.sqrt(lo*hi)))
            y.append(10*math.log10(max(1e-20,float(band.mean()))))
    return float(np.polyfit(x,y,1)[0])

def check(track_id, manifest):
    assert track_id in TRACKS,f"Unsupported track {track_id}"
    entry=next(x for x in manifest["tracks"] if x["id"]==track_id)
    target=TRACKS[track_id]
    file=ROOT/"audio"/(track_id+".mp3")
    stream=ROOT/"audio"/"continuous"/track_id/"continuous.m3u8"
    assert file.is_file() and stream.is_file(),f"Missing source or HLS for {track_id}"
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    assert digest==entry["file_sha256"],f"Master checksum mismatch for {track_id}"
    probe=json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(file)]))
    audio=next(s for s in probe["streams"] if s["codec_type"]=="audio")
    duration=float(probe["format"]["duration"])
    assert audio["codec_name"]=="mp3" and int(audio["channels"])==2 and int(audio["sample_rate"])==44100
    assert 599<=duration<=601,f"Wrong duration for {track_id}: {duration}"
    bitrate=int(probe["format"]["bit_rate"])
    assert 183000<=bitrate<=201000,f"Unexpected bitrate for {track_id}: {bitrate}"
    measured=[samples(file,offset,9) for offset in (25,280,570)]
    rms=[level(a) for a in measured]
    slopes=[slope_db_per_decade(a) for a in measured]
    assert max(rms)-min(rms)<3.0,f"Inconsistent loudness {track_id}: {rms}"
    assert all(abs(s-target)<=4.0 for s in slopes),f"Bad spectrum {track_id}: target={target}; measured={slopes}"
    for x in measured:
        assert np.max(np.abs(x))<0.98,f"Clipping {track_id}"
        frames=[x[i:i+SR//4] for i in range(0,len(x)-SR//4+1,SR//4)]
        assert min(level(frame) for frame in frames)>-64,f"Dead air in {track_id}"
    bridge=samples(stream,590,25,8000)
    before=level(bridge[2*8000:8*8000]);after=level(bridge[12*8000:18*8000])
    assert abs(after-before)<4.0,f"HLS audio boundary discontinuity {track_id}: {before} -> {after}"
    result={"id":track_id,"master_sha256":digest,"duration_seconds":round(duration,3),
        "bitrate_bps":bitrate,"sample_rate":int(audio["sample_rate"]),"channels":int(audio["channels"]),
        "target_spectral_slope_db_decade":target,
        "measured_spectral_slopes_db_decade":[round(x,2) for x in slopes],
        "levels_dbfs_9s_windows":[round(x,2) for x in rms],
        "hls_before_boundary_dbfs":round(before,2),
        "hls_after_boundary_dbfs":round(after,2),"technical_status":"PASS",
        "human_long_listening_status":"NOT_AUTOMATICALLY_VERIFIED"}
    print("NOISE_COLOR_MASTER_QA "+json.dumps(result,sort_keys=True),flush=True)

def main():
    selected=sys.argv[1:] or ["pink-noise"]
    manifest=json.loads((ROOT/"audio"/"color-master-manifest.json").read_text())
    for name in selected:check(name,manifest)
    print(f"PASS: {len(selected)} noise-color MP3 master(s), spectral checks and HLS source-cycle boundaries",flush=True)

if __name__=="__main__":
    try:main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
