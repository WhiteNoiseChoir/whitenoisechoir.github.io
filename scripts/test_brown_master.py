#!/usr/bin/env python3
"""Validate the actual 10-minute Brown Noise MP3 and the HLS source-cycle boundary.
Technical checks only: human listening remains necessary on real devices.
"""
from __future__ import annotations
import hashlib, json, math, shutil, subprocess, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
F=ROOT/"audio"/"brown-noise.mp3"
HLS=ROOT/"audio"/"continuous"/"brown-noise"/"continuous.m3u8"
M=ROOT/"audio"/"color-master-manifest.json"
SR=16000

def run(args):
    p=subprocess.run(args,capture_output=True,check=False)
    if p.returncode:raise RuntimeError(f"Command failed: {' '.join(map(str,args))}: {p.stderr.decode(errors='replace')[-1100:]}")
    return p.stdout

def level(values):
    return 20*math.log10(max(1e-12,math.sqrt(float(np.mean(np.square(values,dtype=np.float64))))))

def decode(path,ss,length,sr=SR):
    raw=run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-xerror","-ss",str(ss),"-i",str(path),"-t",str(length),"-vn","-ac","1","-ar",str(sr),"-f","f32le","pipe:1"])
    a=np.frombuffer(raw,dtype="<f4")
    assert len(a)>=length*sr*.985, f"Truncated decode at {ss}s: {len(a)/sr:.3f}s"
    assert np.isfinite(a).all(), f"Non-finite PCM at {ss}s"
    return a

def spectral_slope(a):
    frame=8192;hop=4096
    window=np.hanning(frame).astype("float64")
    pieces=[a[n:n+frame].astype("float64") for n in range(0,len(a)-frame+1,hop)]
    psd=np.mean([np.abs(np.fft.rfft((q-q.mean())*window))**2 for q in pieces],axis=0)
    f=np.fft.rfftfreq(frame,1/SR)
    edges=np.geomspace(100,5500,23)
    xs,ys=[],[]
    for lo,hi in zip(edges[:-1],edges[1:]):
        region=psd[(f>=lo)&(f<hi)]
        if len(region):
            xs.append(math.log10(math.sqrt(lo*hi)))
            ys.append(10*math.log10(max(1e-20,float(region.mean()))))
    return float(np.polyfit(xs,ys,1)[0])

def main():
    assert F.exists() and HLS.exists() and M.exists(),"Production source or manifest missing"
    manifest=json.loads(M.read_text())
    b=next(t for t in manifest["tracks"] if t["id"]=="brown-noise")
    expected_sha=b["file_sha256"]
    digest=hashlib.sha256(F.read_bytes()).hexdigest()
    assert digest==expected_sha, f"MP3 differs from signed technical manifest: {digest}"
    meta=json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(F)]))
    stream=next(s for s in meta["streams"] if s["codec_type"]=="audio")
    duration=float(meta["format"]["duration"])
    assert stream["codec_name"]=="mp3"
    assert int(stream["sample_rate"])==44100
    assert int(stream["channels"])==2
    assert 598<=duration<=602,f"MP3 duration {duration}"
    assert 183000 <= int(meta["format"]["bit_rate"])<=201000
    windows=[decode(F,pos,9) for pos in (25,280,570)]
    rms=[round(level(a),2) for a in windows]
    slopes=[round(spectral_slope(a),2) for a in windows]
    assert max(rms)-min(rms)<3.0, f"Excessive short-window level variation: {rms}"
    assert all(-27<=x<=-13 for x in slopes),f"Brown Noise spectral slope unexpected: {slopes}"
    for a in windows:
        assert np.max(np.abs(a))<.98,"Audio clipped"
        blocks=[a[i:i+SR//4] for i in range(0,len(a)-SR//4+1,SR//4)]
        assert min(level(block) for block in blocks)>-64,"Unexpected silent quarter-second window"
    bridge=decode(HLS,590,25,8000)
    # 590s..615s crosses first HLS source master boundary at 600s.
    before=level(bridge[2*8000:8*8000])
    after=level(bridge[12*8000:18*8000])
    assert abs(before-after)<4.0,f"HLS source-cycle level jump: {before:.2f} -> {after:.2f}"
    print("BROWN_MASTER_QA",json.dumps({
        "sha256":digest,
        "duration_seconds":round(duration,3),
        "codec":stream["codec_name"],
        "sample_rate_hz":int(stream["sample_rate"]),
        "channels":int(stream["channels"]),
        "bitrate_bps":int(meta["format"]["bit_rate"]),
        "rms_dbfs_3x9s":rms,
        "spectral_slope_db_decade_3x9s":slopes,
        "hls_decoded_boundary_seconds":25,
        "rms_before_hls_boundary_dbfs":round(before,2),
        "rms_after_hls_boundary_dbfs":round(after,2),
        "review":"AUTOMATED_TECHNICAL_PASS_ONLY; subjective quality pending"
    },sort_keys=True),flush=True)
    print("PASS: Brown Noise source integrity, dynamics, measured spectral tilt and HLS boundary",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("FAIL BROWN_MASTER_QA",repr(e),file=sys.stderr)
        sys.exit(1)
