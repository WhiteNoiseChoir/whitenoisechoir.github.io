#!/usr/bin/env python3
"""Render an independent 10-minute Green Noise v1 master for WhiteNoiseChoir.
'Green noise' is not an acoustics standard: this is a documented mid-band design.
Original seeded Gaussian noise -> 3-pole high-pass 165 Hz -> 3-pole low-pass 1550 Hz.
All 600 seconds are independent source material. 5s circular splice crossfade.
The 44.1kHz/192kbps dual-mono MP3 is not a 10-minute listening limit.
"""
from __future__ import annotations
import gc, hashlib, json, math, re, subprocess
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt, welch

SR=44100
SECONDS=600
FADE_SECONDS=5
SEED=2026110805
HP=165
LP=1550
ORDER=3
OUT=Path("audio/green-noise.mp3")
MANIFEST=Path("audio/green-noise-master-manifest.json")

def sh(args):
    p=subprocess.run(args,capture_output=True,check=False)
    if p.returncode:
        raise RuntimeError(f"Command {args[0]} failed: {p.stderr.decode(errors='replace')[-800:]}")
    return p.stdout

def db(v):
    return 20*math.log10(max(1e-12,float(v)))

def encode(mono,path):
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
         "-f","f32le","-ar",str(SR),"-ac","2","-i","pipe:0",
         "-c:a","libmp3lame","-b:a","192k",str(path)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        step=SR*5
        for start in range(0,len(mono),step):
            a=mono[start:start+step]
            stereo=np.column_stack((a,a)).astype("<f4",copy=False)
            p.stdin.write(stereo.tobytes())
        p.stdin.close()
        err=p.stderr.read().decode(errors="replace")
        if p.wait():
            raise RuntimeError("MP3 encode failed: "+err[-1000:])
    finally:
        if p.poll() is None:p.kill();p.wait()

def decode_window(start,length=15):
    data=sh(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-xerror",
          "-ss",str(start),"-i",str(OUT),"-t",str(length),"-vn","-ac","1","-ar",str(SR),"-f","f32le","pipe:1"])
    a=np.frombuffer(data,dtype="<f4")
    if len(a)<SR*(length-.1) or not np.isfinite(a).all():
        raise RuntimeError(f"MP3 decode invalid at {start}s")
    return a

def bands(a):
    f,p=welch(a,fs=SR,nperseg=16384)
    result={}
    for label,(lo,hi) in {"bass":(35,105),"mid":(300,900),"treble":(4000,8000)}.items():
        result[label]=10*math.log10(max(float(p[(f>=lo)&(f<hi)].mean()),1e-22))
    return result

def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    count=(SECONDS+FADE_SECONDS)*SR
    rng=np.random.default_rng(SEED)
    noise=rng.standard_normal(count,dtype=np.float32)
    sos=np.vstack((
        butter(ORDER,HP,btype="highpass",fs=SR,output="sos"),
        butter(ORDER,LP,btype="lowpass",fs=SR,output="sos"),
    ))
    x=sosfilt(sos,noise).astype(np.float32)
    del noise
    n=SECONDS*SR
    fade=FADE_SECONDS*SR
    mono=x[:n].copy()
    t=np.sin(np.linspace(0,np.pi/2,fade,dtype=np.float32))**2
    mono[:fade]=(x[n:n+fade]*(1-t)+mono[:fade]*t)
    del x,t
    mono-=float(mono.mean(dtype=np.float64))
    target=10**(-28.5/20)
    mono*=(target/(math.sqrt(float(np.mean(mono*mono,dtype=np.float64)))+1e-12))
    max_sample=float(np.max(np.abs(mono)))
    ceiling=10**(-6/20)
    if max_sample>ceiling:mono*=ceiling/max_sample
    encode(mono,OUT)
    del mono
    gc.collect()
    probe=json.loads(sh(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(OUT)]))
    stream=next(s for s in probe["streams"] if s["codec_type"]=="audio")
    duration=float(probe["format"]["duration"])
    if stream["codec_name"]!="mp3" or int(stream["sample_rate"])!=SR or int(stream["channels"])!=2 or abs(duration-SECONDS)>.2:
        raise RuntimeError("Wrong duration, channels or codec")
    levels=[];measure=[]
    for start in (30,280,570):
        a=decode_window(start)
        levels.append(round(db(math.sqrt(float(np.mean(a*a,dtype=np.float64)))),2))
        bands_db=bands(a);measure.append({k:round(v,2) for k,v in bands_db.items()})
        if bands_db["mid"]-bands_db["bass"]<10 or bands_db["mid"]-bands_db["treble"]<12:
            raise RuntimeError("The decoded audio is not distinct mid-band Green Noise: "+str(bands_db))
        if float(np.max(np.abs(a)))>.95:raise RuntimeError("Clipping detected")
        quarter=SR//4
        for start_quarter in range(0,len(a)-quarter,quarter):
            if db(math.sqrt(float(np.mean(a[start_quarter:start_quarter+quarter]**2,dtype=np.float64))))<-65:
                raise RuntimeError("Unexpected silent window")
    if max(levels)-min(levels)>2.5:raise RuntimeError("Unstable window loudness")
    summary=json.loads(sh(["ffprobe","-v","error","-show_entries","format=bit_rate","-of","json",str(OUT)]))
    bitrate=int(summary["format"]["bit_rate"])
    if not 183000<=bitrate<=201000:raise RuntimeError("Wrong bitrate")
    h=hashlib.sha256(OUT.read_bytes()).hexdigest()
    manifest={
        "id":"green-noise",
        "title":"Green Noise",
        "definition":"WhiteNoiseChoir original Green Noise v1; non-standard name, reproducible mid-band synthesis",
        "sound_character":"Steady mid-frequency filtered broadband texture, not field-recorded nature",
        "file":"audio/green-noise.mp3",
        "file_sha256":h,
        "bytes":OUT.stat().st_size,
        "algorithm":"independent_original_gaussian_noise_iir_bandpass_3pole_hp_3pole_lp",
        "seed":SEED,
        "filters":{"highpass_hz":HP,"lowpass_hz":LP,"order_each":ORDER,"target_band_hz":[250,1000],"implementation":"scipy.signal.butter IIR cascaded"},
        "qa":{
            "duration_seconds":round(duration,3),
            "sample_rate":SR,
            "channels":2,
            "stereo_mode":"centered_dual_mono",
            "codec":"mp3",
            "bitrate_kbps":192,
            "measured_rms_dbfs_15s":levels,
            "spectral_density_db_3windows":measure,
            "technical_status":"PASS",
            "long_form_human_listening_status":"PENDING_USER_REVIEW"
        }
    }
    MANIFEST.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print("GREEN_MASTER_QA",json.dumps({"sha256":h,"duration":duration,"size_bytes":OUT.stat().st_size,"levels":levels,"bands":measure,"result":"PASS","human_review":"PENDING"}),flush=True)

if __name__=="__main__":
    main()
