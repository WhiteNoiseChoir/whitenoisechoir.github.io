#!/usr/bin/env python3
"""WhiteNoiseChoir: original procedural audio, generated at build time.
All output recordings are new DSP, not third-party field recordings.
Nature and machine tracks are labeled as simulations.
"""
from pathlib import Path
import subprocess
import numpy as np
from scipy import signal
from scipy import fft
SR = 44100
SECONDS = 72
N = SR * SECONDS
DIR = Path("dist/audio")
DIR.mkdir(parents=True, exist_ok=True)
F = fft.rfftfreq(N, 1 / SR)
T = np.arange(N, dtype=np.float32) / SR

def noise(alpha, seed, low=24, high=14800):
    r = np.random.default_rng(seed)
    z = (r.standard_normal(F.size).astype("float32") + 1j*r.standard_normal(F.size).astype("float32"))
    profile = np.maximum(F, low)**(-alpha/2)
    profile *= F / np.sqrt(F**2+low**2)
    profile *= 1/np.sqrt(1+(F/high)**8)
    z *= profile
    z[0] = 0
    x = fft.irfft(z, n=N).astype("float32")
    x -= x.mean()
    x /= (x.std()+1e-8)
    return x
def low(x, h):
    return signal.sosfiltfilt(signal.butter(3,h,fs=SR,btype="lowpass",output="sos"),x).astype("float32")
def high(x, h):
    return signal.sosfiltfilt(signal.butter(3,h,fs=SR,btype="highpass",output="sos"),x).astype("float32")
def band(x, lo, hi):
    return signal.sosfiltfilt(signal.butter(3,[lo,hi],fs=SR,btype="bandpass",output="sos"),x).astype("float32")
def modulation(cycles):
    return np.sin((2*np.pi*cycles/SECONDS)*T).astype("float32")
w=noise(0,900)
p=noise(1,901)
b=noise(2,902)
bl=noise(-1,903)
v=noise(-2,904)
sounds = [
 ("white-noise",w,-22),("pink-noise",p,-22),("brown-noise",b,-22),("blue-noise",bl,-24),
 ("violet-noise",v,-26),("soft-white-noise",low(w,3600),-24),
 ("deep-brown-noise",low(b,500),-23),("warm-pink-noise",low(p,1900),-23),
 ("mid-noise",band(w,160,3500),-22),("low-rumble",low(b,230),-24),
 ("desk-fan-synth",.58*low(p,2900)+.1*noise(0,910,100,8000)+.30*modulation(3600)+.09*modulation(7200),-24),
 ("box-fan-synth",.72*low(w,2300)+.35*modulation(4320)+.12*modulation(8640),-24),
 ("air-conditioner-synth",.72*low(b,2200)+.22*modulation(3600)+.07*modulation(7200)+.20*low(w,3000),-24),
 ("cabin-hum-synth",.55*low(p,2600)+.38*band(noise(0,914),75,900)+.17*modulation(6120),-24),
 ("wind-synth",low(w,1400)*(.60+.18*modulation(9)+.11*modulation(17)),-24),
 ("rain-wash-synth",.76*high(w,650)+.2*low(p,3000),-25),
 ("heavy-rain-synth",.56*high(w,240)+.36*low(bl,5500)+.17*b,-24),
 ("ocean-swell-synth",low(p,2400)*(.62+.24*modulation(9)+.07*modulation(18))+.15*low(b,280),-24),
 ("waterfall-synth",.52*high(w,550)+.34*low(p,6200)+.12*low(b,1100),-25),
 ("shower-synth",.65*high(w,1000)+.33*band(noise(0,920),700,7600),-25),
]
for i,(name,x,level) in enumerate(sounds,1):
    x=np.asarray(x,dtype=np.float32)
    x-=x.mean()
    rms=float(np.sqrt(np.mean(x.astype(np.float64)**2)))
    if rms>0: x*=10**(level/20)/rms
    peak=float(np.max(np.abs(x)))
    if peak>.30:x*=.30/peak
    result=subprocess.run([
        "ffmpeg","-hide_banner","-loglevel","error","-y",
        "-f","f32le","-ar",str(SR),"-ac","1","-i","pipe:0",
        "-c:a","libmp3lame","-b:a","112k",str(DIR/(name+".mp3"))
    ],input=x.astype("<f4").tobytes(),capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr.decode())
    print(f"[{i:02}/{len(sounds)}] {name}", flush=True)
print(f"Generated {len(sounds)} original 72-second MP3 files")
