#!/usr/bin/env python3
"""WhiteNoiseChoir Batch 03: twelve ORIGINAL ten-minute DSP ambient masters.

Each named waveform is independently synthesized over the full 605 seconds.
No short MP3 cloning, unlicensed field recording, fake natural provenance,
or replacement of previously approved 5 master MP3s. Last 5 seconds
cross-fade naturally into beginning to reduce the 600-second loop boundary.
Encoded MP3s receive post-encode QC before promotion.

TECHNICAL PASS != NATURAL/PLEASANT HUMAN APPROVAL.
"""
from __future__ import annotations
from pathlib import Path
import gc
import hashlib
import json
import math
import re
import shutil
import subprocess
import tempfile

import numpy as np
from scipy.fft import irfft, rfftfreq
from scipy.signal import welch

SR = 44100
SECONDS = 600
WRAP = 5
FRAMES = (SECONDS + WRAP) * SR
OUT = Path("audio")
OUT.mkdir(parents=True, exist_ok=True)
VERSION = "extended-dsp-v1-20261108"

# (id, name, independent random seed, exponent of power spectrum, character,
#  target level in dBFS, high-frequency cutoff, modulation class).
TRACKS = [
 ("blue-noise","Blue Noise",2026110801,-1.0,"blue",-30.0,14000,"none"),
 ("violet-noise","Violet Noise",2026110802,-2.0,"violet",-32.0,14000,"none"),
 ("soft-white-noise","Soft White Noise",2026110803,0.0,"soft-white",-28.5,4200,"none"),
 ("deep-brown-noise","Deep Brown Noise",2026110804,2.0,"deep-brown",-26.0,550,"none"),
 ("warm-pink-noise","Warm Pink Noise",2026110805,1.0,"warm-pink",-27.0,2000,"none"),
 ("mid-noise","Neutral Mid Noise",2026110806,0.0,"mid",-28.0,4500,"none"),
 ("low-rumble","Low Rumble",2026110807,1.7,"rumble",-26.5,280,"none"),
 ("desk-fan-synth","Desk Fan (Synthetic)",2026110808,0.8,"desk-fan",-27.5,2650,"fan"),
 ("air-conditioner-synth","Air Conditioner (Synthetic)",2026110809,1.2,"ac",-27.5,1900,"ac"),
 ("cabin-hum-synth","Airplane Cabin (Synthetic)",2026110810,1.0,"cabin",-27.5,2350,"cabin"),
 ("wind-synth","Gentle Wind (Synthetic)",2026110811,1.3,"wind",-27.5,1400,"wind"),
 ("shower-synth","Shower (Synthetic)",2026110812,0.0,"shower",-29.0,10500,"shower"),
]
EXPECTED = {x[0] for x in TRACKS}
assert len(TRACKS) == len(EXPECTED) == 12

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(2*1024*1024),b""):h.update(block)
    return h.hexdigest()

def dB(x):
    return 20*math.log10(max(float(x),1e-12))

def rms(x):
    return math.sqrt(float(np.mean(np.square(x),dtype=np.float64)))

def lowpass(freqs, cutoff):
    return 1/np.sqrt(1+(freqs/cutoff)**8)

def highpass(freqs, cutoff):
    return (freqs/np.sqrt(freqs*freqs+cutoff*cutoff))**3

def shaped_random(seed,alpha,kind,cutoff):
    """Full-length deterministic independent 1/f^alpha real noise.

    A coherent non-periodic 605s random texture with octave-domain spectral
    identity, not repeated 60s PCM. Smooth filtering keeps timbre stable.
    """
    freqs=rfftfreq(FRAMES,1/SR).astype(np.float32)
    rng=np.random.default_rng(seed)
    # Gentle 22Hz high-pass and 15.5kHz anti-harshness shaping.
    profile=np.power(np.maximum(freqs,22.0),-alpha/2.0).astype(np.float32)
    profile*=freqs/np.sqrt(freqs*freqs+22*22)
    profile*=lowpass(freqs,15500)
    profile*=lowpass(freqs,cutoff)
    if kind=="mid":
        profile*=highpass(freqs,155)
    elif kind=="rumble":
        profile*=highpass(freqs,37)
    elif kind=="deep-brown":
        profile*=highpass(freqs,28)
    elif kind=="shower":
        profile*=highpass(freqs,680)
    elif kind=="cabin":
        profile*=highpass(freqs,65)
    elif kind=="ac":
        profile*=highpass(freqs,46)
    elif kind=="desk-fan":
        profile*=highpass(freqs,80)

    spectra=(rng.standard_normal(freqs.size,dtype=np.float32)+
             1j*rng.standard_normal(freqs.size,dtype=np.float32)).astype(np.complex64)
    spectra *= profile
    spectra[0]=0.0
    del freqs,profile
    out=irfft(spectra,n=FRAMES,workers=1).astype(np.float32)
    del spectra
    out-=float(np.mean(out,dtype=np.float64))
    out/=rms(out)+1e-12
    return out

def apply_character(x,kind,seed,style):
    rng=np.random.default_rng(seed+111)
    n=len(x)
    # Stable synthetic machine harmonics at low relative level.
    if style in ("fan","ac","cabin"):
        t=np.arange(n,dtype=np.float32)/np.float32(SR)
        if style=="fan":
            f=112.0
            wave=np.sin(2*np.pi*f*t)+0.35*np.sin(2*np.pi*(f*2)*t)
            amount=.10
            # Fan blades produce a constant quiet rumble, not loud sweeping tones.
            env=1.0+.026*np.sin(2*np.pi*.48*t)
        elif style=="ac":
            f=60.0
            wave=np.sin(2*np.pi*f*t)+.42*np.sin(2*np.pi*120*t)
            amount=.11
            env=1.0+.012*np.sin(2*np.pi*.14*t)
        else:
            f=87.0
            wave=np.sin(2*np.pi*f*t)+.30*np.sin(2*np.pi*174*t)
            amount=.11
            env=1.0+.022*np.sin(2*np.pi*.08*t)
        x *= env.astype(np.float32)
        wave=(wave/(math.sqrt(float(np.mean(np.square(wave,dtype=np.float64))))+1e-12)).astype(np.float32)
        x = (x + amount*wave).astype(np.float32)
        del wave,t,env
    elif style=="wind":
        # Infrasonic slow wind-gust envelope; avoids artificial abrupt swells.
        t=np.arange(n,dtype=np.float32)/np.float32(SR)
        envelope=(.90 + .085*np.sin(2*np.pi*.035*t)+.045*np.sin(2*np.pi*.087*t))
        x *= envelope.astype(np.float32)
        del t,envelope
    elif style=="shower":
        # Very small slow density changes, never white noise branded "real shower".
        t=np.arange(n,dtype=np.float32)/np.float32(SR)
        envelope=(.97+.025*np.sin(2*np.pi*.057*t))
        x *= envelope.astype(np.float32)
        del t,envelope
    return x

def loop_and_level(x,target_db):
    n=SR*SECONDS
    fade=SR*WRAP
    out=x[:n].copy()
    ramp=np.sin(np.linspace(0,np.pi/2,fade,dtype=np.float32))**2
    # Last sample at 599.999s and first at 0s are adjacent in original
    # independent noise at 600.000s, reducing boundary discontinuity.
    out[:fade]=x[n:n+fade]*(1-ramp)+out[:fade]*ramp
    del ramp,x
    out-=float(np.mean(out,dtype=np.float64))
    out *= (10**(target_db/20))/(rms(out)+1e-12)
    peak=float(np.max(np.abs(out)))
    ceiling=10**(-5/20)
    if peak>ceiling:out*=ceiling/peak
    return out

def write_mp3(path,mono):
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
         "-f","f32le","-ar",str(SR),"-ac","2","-i","pipe:0",
         "-c:a","libmp3lame","-b:a","192k",str(path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        step=SR*5
        for k in range(0,len(mono),step):
            block=mono[k:k+step]
            stereo=np.empty((len(block),2),dtype=np.float32)
            stereo[:,0]=block
            stereo[:,1]=block
            proc.stdin.write(stereo.astype("<f4",copy=False).tobytes())
        proc.stdin.close()
        err=proc.stderr.read().decode(errors="replace")
        rc=proc.wait()
        if rc:raise RuntimeError(f"FFmpeg encoder error: {err[-600:]}")
    finally:
        if proc.poll() is None:proc.kill();proc.wait()

def r128(path):
    p=subprocess.run(["ffmpeg","-hide_banner","-nostats","-nostdin","-i",str(path),
       "-filter:a","ebur128=peak=true","-f","null","-"],
       capture_output=True,text=True)
    if p.returncode:raise RuntimeError(f"EBU R128 failed: {p.stderr[-500:]}")
    lu=re.search(r"Integrated loudness:\s*I:\s*([-+]?\d+(?:\.\d+)?)\s*LUFS",p.stderr)
    pk=re.search(r"True peak:\s*Peak:\s*([-+]?\d+(?:\.\d+)?)\s*dBFS",p.stderr)
    if not lu or not pk:raise RuntimeError("Missing EBU R128 measurements")
    return float(lu.group(1)),float(pk.group(1))

def decode(path):
    p=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin",
         "-i",str(path),"-ar",str(SR),"-ac","1","-f","f32le","pipe:1"],
         capture_output=True,check=True)
    if len(p.stdout)%4:raise RuntimeError("Misaligned final MP3 PCM")
    return np.frombuffer(p.stdout,dtype="<f4")

def qa(path,alpha,kind,target):
    arr=decode(path)
    secs=len(arr)/SR
    level=dB(rms(arr))
    peak=dB(np.max(np.abs(arr)))
    crest=peak-level
    s=np.concatenate([arr[0:20*SR],arr[180*SR:200*SR],arr[360*SR:380*SR],arr[570*SR:590*SR]])
    freq,psd=welch(s,fs=SR,nperseg=16384)
    valid=(freq>=120)&(freq<=6000)&(psd>1e-18)
    slope=float(np.polyfit(np.log10(freq[valid]),10*np.log10(psd[valid]),1)[0])
    bands=((80,250),(250,750),(750,2000),(2000,5000),(5000,10000))
    spectral_bands=[]
    for lo,hi in bands:
        good=(freq>=lo)&(freq<hi)
        spectral_bands.append(round(dB(math.sqrt(float(np.mean(psd[good])))),2))
    window=SR//4
    windows=arr[:(len(arr)//window)*window].reshape(-1,window)
    quiet=int(np.count_nonzero(np.mean(np.square(windows),axis=1,dtype=np.float64)<1e-13))
    typical=math.sqrt(float(np.mean(np.square(np.diff(arr[::10]).astype(np.float64)))))+1e-12
    boundary=abs(float(arr[0]-arr[-1]))/typical
    lufs,truepk=r128(path)
    drift=[]
    for at in range(0,len(arr)-10*SR+1,10*SR):
        drift.append(dB(rms(arr[at:at+10*SR])))
    max_drift=max(drift)-min(drift)
    flags=[]
    if not(599.8<=secs<=600.2):flags.append("duration_not_10min")
    if peak>-3 or truepk>-1.5:flags.append("insufficient_peak_headroom")
    if crest>24:flags.append("excessive_crest")
    if not(-35<=level<=-23):flags.append("rms_out_of_range")
    if not(-42<=lufs<=-16):flags.append("lufs_out_of_range")
    if quiet>0:flags.append("digital_silence")
    if boundary>4:flags.append("loop_jump")
    if max_drift>(6 if kind=="wind" else 3.8):flags.append("unwanted_loudness_drift")
    if abs(level-target)>3:flags.append("master_level_changed_from_target")
    if kind in ("blue","violet"):
        if abs(slope-(-10*alpha))>4.5:flags.append("noise_color_slope_failed")
    info={
        "duration_seconds":round(secs,3),"codec":"mp3","sample_rate":SR,
        "channels":2,"stereo_mode":"centered_dual_mono","bitrate_kbps":192,
        "rms_dbfs":round(level,2),"sample_peak_dbfs":round(peak,2),
        "crest_factor_db":round(crest,2),
        "integrated_loudness_lufs":round(lufs,1),"true_peak_dbtp":round(truepk,1),
        "spectral_slope_db_per_decade":round(slope,2),
        "spectral_band_amplitude_dbfs":spectral_bands,
        "silent_250ms_windows":quiet,
        "max_10s_rms_variation_db":round(max_drift,2),
        "loop_boundary_jump_vs_decimated_adjacent":round(boundary,3),
        "technical_status":"PASS" if not flags else "REVIEW",
        "flags":flags,
        "listening_approval":"PENDING_REAL_DEVICE_REVIEW",
        "label_validity":"Synthetic DSP; no field recording represented",
    }
    del arr,s,windows,freq,psd
    return info

def run():
    records=[]
    for id,title,seed,alpha,kind,target,cutoff,style in TRACKS:
        print("START",id,"type",kind,flush=True)
        x=shaped_random(seed,alpha,kind,cutoff)
        x=apply_character(x,kind,seed,style)
        x=loop_and_level(x,target)
        with tempfile.TemporaryDirectory(dir=OUT) as td:
            tmp=Path(td)/(id+".mp3")
            write_mp3(tmp,x)
            del x
            gc.collect()
            results=qa(tmp,alpha,kind,target)
            print("QA",json.dumps({"id":id,**results}),flush=True)
            if results["technical_status"]!="PASS":
                raise RuntimeError(f"Sound {id} failed QA: {results['flags']}")
            dest=OUT/(id+".mp3")
            shutil.copy2(tmp,dest)
        records.append({
            "id":id,"title":title,"file":str(dest),
            "file_sha256":digest(dest),"bytes":dest.stat().st_size,
            "algorithm":"full_length_independent_original_frequency_domain_DSP",
            "noise_power_exponent_alpha":alpha,"spectral_character":kind,
            "seed":seed,"target_rms_dbfs":target,
            "metadata_note":"Synthetic sound texture; differs from a field recording.",
            "qa":results,
        })
        print("PUBLISHED_QA_CANDIDATE",id,digest(dest),flush=True)
    if {r["id"] for r in records} != EXPECTED:
        raise RuntimeError("Wrong batch track inventory")
    manifest={
        "version":VERSION,"group":"WhiteNoiseChoir synthetic-noise and machine ambience",
        "master_duration_seconds":SECONDS,"master_maximum_policy_seconds":1200,
        "rendered_from":"new independent original DSP per full-length track",
        "track_count":len(records),"tracks":records,
        "human_approval":"PENDING; technical QA does not prove sound labels are perceptually accurate or pleasant",
        "preserves":["white-noise","pink-noise","brown-noise","rain-on-window-real","fireplace-real"],
    }
    (OUT/"extended-dsp-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print("BATCH_COMPLETE",json.dumps({"count":len(records),"pass":len(records),"source":"original_independent_DSP"}),flush=True)

if __name__=="__main__":
    run()
