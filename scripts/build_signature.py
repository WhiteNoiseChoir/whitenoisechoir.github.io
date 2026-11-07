#!/usr/bin/env python3
"""WhiteNoiseChoir Signature Collection — 10 *audition samples*, not approved masters.
Three independently generated colored noises + seven independent CC0 field recordings.
No YouTube audio. Every source, hash and acoustic check is recorded alongside output.
The signature/ directory is an unindexed listening lab. Do NOT auto-update main player.
"""
from __future__ import annotations
from pathlib import Path
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib, json, math, subprocess, tempfile, time
import numpy as np
from scipy.signal import welch

SR=44100
DURATION=60
XFADE_SEC=3
OUT=Path("signature/audio")
OUT.mkdir(parents=True,exist_ok=True)
ROOT=Path("signature")
LICENSE="https://creativecommons.org/publicdomain/zero/1.0/"
COLORS=[
  ("white","White Noise",0.0,"Original algorithm","White noise: approximately flat power spectral density."),
  ("pink","Pink Noise",1.0,"Original algorithm","Pink noise: approximately 1/f power spectral density."),
  ("brown","Brown Noise",2.0,"Original algorithm","Brown noise: approximately 1/f² power spectral density."),
]
FIELD=[
  ("rain-window","Rain on Window","ikayuka","https://freesound.org/people/ikayuka/sounds/273333/","https://cdn.freesound.org/previews/273/273333_1158384-hq.mp3","Rain hitting a window, possibly with storm ambience."),
  ("heavy-rain","Heavy Rain","MikeNavajas","https://freesound.org/people/MikeNavajas/sounds/681490/","https://cdn.freesound.org/previews/681/681490_11463865-hq.mp3","Real stereo heavy-rain recording."),
  ("ocean","Ocean Waves","florianreichelt","https://freesound.org/people/florianreichelt/sounds/450755/","https://cdn.freesound.org/previews/450/450755_6253486-hq.mp3","Real Hawaiian shore waves."),
  ("box-fan","Box Fan","ffdm","https://freesound.org/people/ffdm/sounds/824852/","https://cdn.freesound.org/previews/824/824852_17819872-hq.mp3","Real Lasko box fan recorded on high."),
  ("air-conditioner","Air Conditioner","LilMati (MATRIXXX_)","https://freesound.org/people/LilMati/sounds/515859/","https://cdn.freesound.org/previews/515/515859_6142149-hq.mp3","Real AC fan hum, as uploaded by creator."),
  ("fireplace","Fireplace","visionear","https://freesound.org/people/visionear/sounds/501417/","https://cdn.freesound.org/previews/501/501417_10869493-hq.mp3","Real indoor fireplace with transient crackling."),
  ("forest-rain","Forest Rain & Drips","INNORECORDS","https://freesound.org/people/INNORECORDS/sounds/457447/","https://cdn.freesound.org/previews/457/457447_9518146-hq.mp3","Forest after rain, dripping on foliage; not steady heavy rain."),
]

def ffmpeg_decode(path,seconds=DURATION+XFADE_SEC+2):
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-i",str(path),
         "-t",str(seconds),"-ar",str(SR),"-ac","2","-f","f32le","pipe:1"]
    p=subprocess.run(cmd,capture_output=True,check=True)
    return np.frombuffer(p.stdout,dtype="<f4").reshape(-1,2).copy()

def encode(id,pcm):
    dest=OUT/(id+".mp3")
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","f32le","-ar",str(SR),
         "-ac","2","-i","pipe:0","-codec:a","libmp3lame","-b:a","192k",str(dest)]
    p=subprocess.run(cmd,input=np.asarray(pcm,dtype="<f4").tobytes(),capture_output=True)
    if p.returncode!=0:raise RuntimeError(p.stderr.decode(errors="replace")[-900:])
    return dest

def normalize(x,level=-26):
    x=np.asarray(x,dtype=np.float32)
    x=x-x.mean(axis=0,keepdims=True)
    rms=float(np.sqrt(np.mean(x.astype(np.float64)**2)))
    if rms<1e-6:raise ValueError("Source silent or nearly silent")
    x*=10**(level/20)/rms
    peak=float(np.max(np.abs(x)))
    if peak>.69:x*=.69/peak
    return x

def continuous_loop(x):
    n=DURATION*SR; fade=XFADE_SEC*SR
    if len(x)<n+fade:raise ValueError("Source shorter than 63 seconds")
    # At the wrap boundary, output[-1]=source[n-1] and
    # output[0]=source[n]. The source is naturally continuous there.
    out=x[:n].copy()
    blend=np.linspace(0,1,fade,dtype=np.float32)[:,None]
    curve=np.sin(blend*np.pi/2)**2
    out[:fade]=x[n:n+fade]*(1-curve)+x[:fade]*curve
    return out

def generated_color(alpha,seed):
    n=SR*(DURATION+XFADE_SEC)
    f=np.fft.rfftfreq(n,1/SR)
    rng=np.random.default_rng(seed)
    def one():
        spectrum=(rng.standard_normal(len(f))+1j*rng.standard_normal(len(f)))
        slope=(np.maximum(f,22))**(-alpha/2.0)
        # Low-frequency rolloff below ~20 Hz and anti-harshness rolloff above ~15k.
        slope*=f/np.sqrt(f*f+22*22)
        slope*=1/np.sqrt(1+(f/15500)**10)
        spectrum*=slope
        spectrum[0]=0
        pcm=np.fft.irfft(spectrum,n=n).astype(np.float32)
        pcm/=pcm.std()+1e-12
        return pcm
    a=one()
    b=one()
    # Primarily centered presentation with small spatial decorrelation.
    x=np.stack([.93*a+.07*b,.93*a-.07*b],axis=1)
    return normalize(continuous_loop(x))

def download(url):
    err=None
    for k in range(3):
        try:
            req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; WhiteNoiseChoir-QualityLab/1.0)","Accept":"audio/*,*/*"})
            with urlopen(req,timeout=35) as rsp:
                data=rsp.read(35000000)
            if len(data)<50000:raise RuntimeError("Downloaded audio shorter than 50 KB")
            return data
        except Exception as ex:
            err=ex;time.sleep(1+2*k)
    raise RuntimeError(f"Cannot download sample {url}: {err}")

def build_field(entry):
    id,title,author,landing,url,description=entry
    original=download(url)
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"source.mp3"
        path.write_bytes(original)
        decoded=ffmpeg_decode(path)
    x=normalize(continuous_loop(decoded))
    dest=encode(id,x)
    return {"id":id,"title":title,"type":"field_recording","author":author,
      "source_page":landing,"preview_url":url,"license":"CC0-1.0","license_url":LICENSE,
      "description":description,"source_preview_sha256":hashlib.sha256(original).hexdigest(),
      "file":"audio/"+dest.name,"file_sha256":hashlib.sha256(dest.read_bytes()).hexdigest()}

def qa(path,expected_alpha=None):
    # QA based on decoded final MP3, not internal uncompressed float only.
    x=ffmpeg_decode(path,seconds=DURATION+1)
    n=min(len(x),DURATION*SR);x=x[:n]
    rms=float(np.sqrt(np.mean(np.square(x.astype(np.float64)))))
    pk=float(np.max(np.abs(x)))
    peak_db=20*math.log10(max(1e-12,pk))
    rms_db=20*math.log10(max(1e-12,rms))
    mono=x.mean(axis=1)
    specf,spec=welch(mono,fs=SR,nperseg=16384)
    valid=(specf>=110)&(specf<=6000)&(spec>1e-19)
    slope=float(np.polyfit(np.log10(specf[valid]),10*np.log10(spec[valid]),1)[0])
    # 250 ms RMS windows; detects unexpected hard silences, not soft passages.
    frame=SR//4
    windows=x[:(len(x)//frame)*frame].reshape(-1,frame,2)
    db=20*np.log10(np.sqrt(np.mean(windows.astype(np.float64)**2,axis=(1,2)))+1e-12)
    quiet=int((db<-65).sum())
    boundary=float(np.sqrt(np.mean((x[0]-x[-1])**2)))
    adjacent=float(np.sqrt(np.mean(np.diff(x,axis=0).astype(np.float64)**2)))+1e-12
    jump_ratio=boundary/adjacent
    errors=[]
    if len(x)<59.5*SR:errors.append("duration_too_short")
    if pk>=.995:errors.append("sample_clipping")
    if pk<=.003:errors.append("very_low_level")
    if quiet>=4:errors.append("unexpected_silence_windows")
    if jump_ratio>6:errors.append("loop_transition_needs_review")
    if expected_alpha is not None:
        target=-10*expected_alpha
        if abs(slope-target)>7:errors.append("spectrum_slope_outside_tolerance")
    return {"duration_seconds":round(len(x)/SR,3),"sample_rate":SR,"channels":2,
      "codec":"mp3","bitrate_kbps":192,"rms_dbfs":round(rms_db,2),
      "sample_peak_dbfs":round(peak_db,2),"spectral_slope_db_per_decade":round(slope,2),
      "quiet_windows_250ms_below_minus65dbfs":quiet,
      "loop_boundary_jump_vs_typical_adjacent_diff":round(jump_ratio,3),
      "technical_status":"PASS" if not errors else "REVIEW",
      "flags":errors,"listening_status":"PENDING_HUMAN_REVIEW",
      "note":"A measured PASS does not prove perceptual sound quality or a seamless long-duration listening experience."}

def run():
    records=[]
    for i,(id,title,alpha,author,description) in enumerate(COLORS):
        x=generated_color(alpha,91600+i*291)
        dest=encode(id,x)
        record={"id":id,"title":title,"type":"synthesized_color_noise",
          "author":author,"spectral_exponent_alpha":alpha,
          "description":description,"license":"original_dsp",
          "file":"audio/"+dest.name,"file_sha256":hashlib.sha256(dest.read_bytes()).hexdigest()}
        record["qa"]=qa(dest,expected_alpha=alpha)
        records.append(record)
        print("GENERATED",id,record["qa"]["technical_status"],flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(build_field,row):row for row in FIELD}
        field_records=[]
        for future in as_completed(tasks):
            rec=future.result()
            rec["qa"]=qa(OUT/(rec["id"]+".mp3"))
            field_records.append(rec)
            print("IMPORTED",rec["id"],rec["qa"]["technical_status"],flush=True)
        by_id={r["id"]:r for r in field_records}
        records.extend(by_id[row[0]] for row in FIELD)
    payload={"collection":"WhiteNoiseChoir Signature Collection — Audition Beta",
      "version":"batch-01","duration_seconds":DURATION,
      "purpose":"quality audition, not final long masters","tracks":records,
      "automated_qa_only":True,
      "qa_caveat":"QA is technical, not listening approval. Sources can have sudden noises or repeat audibly."}
    (ROOT/"manifest.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    summaries={"total":len(records),"technical_passes":sum(r["qa"]["technical_status"]=="PASS" for r in records),
      "technical_review":sum(r["qa"]["technical_status"]!="PASS" for r in records),
      "human_approved":0,"mean_rms_dbfs":round(float(np.mean([r["qa"]["rms_dbfs"] for r in records])),2)}
    (ROOT/"quality-summary.json").write_text(json.dumps(summaries,indent=2)+"\n",encoding="utf8")
    print("QA_SUMMARY",json.dumps(summaries),flush=True)
    if len(records)!=10:raise AssertionError("Need exactly 10 QA sources")
    if summaries["technical_review"]:
        print("WARNING: Technical review flags exist; no sounds automatically approved.",flush=True)

if __name__=="__main__":run()
