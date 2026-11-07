#!/usr/bin/env python3
"""Import CC0 ambient field recordings from public Freesound preview audio.
Every entry has a verified source page and Creative Commons Zero license.
Downloads become locally hosted short crossfaded loops: NEVER hotlinked.
These samples still require a listening quality review before production approval.
"""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile, subprocess, json, time, os, hashlib
import numpy as np

SR=44100
TARGET=54
OVERLAP=2
DEST=Path("dist/audio")
DEST.mkdir(parents=True,exist_ok=True)
# License checked at each individual Freesound source on 2026-11-07.
SOURCES=[
 ("desk-fan-real","Desk Fan – Electric Fan 02","unfa","https://freesound.org/people/unfa/sounds/170869/","https://cdn.freesound.org/previews/170/170869_1038806-hq.mp3"),
 ("box-fan-real","Box Fan – Lasko recording","ffdm","https://freesound.org/people/ffdm/sounds/824852/","https://cdn.freesound.org/previews/824/824852_17819872-hq.mp3"),
 ("air-conditioner-real","Air Conditioner Fan Hum","MATRIXXX_","https://freesound.org/people/MATRIXXX_/sounds/515859/","https://cdn.freesound.org/previews/515/515859_6142149-hq.mp3"),
 ("wind-in-trees-real","Wind Through Trees","Yoyodaman234","https://freesound.org/people/Yoyodaman234/sounds/335889/","https://cdn.freesound.org/previews/335/335889_2792951-hq.mp3"),
 ("rain-on-window-real","Rain on Window","ikayuka","https://freesound.org/people/ikayuka/sounds/273333/","https://cdn.freesound.org/previews/273/273333_1158384-hq.mp3"),
 ("heavy-rain-real","Rain – Lluvia 3min Stereo","MikeNavajas","https://freesound.org/people/MikeNavajas/sounds/681490/","https://cdn.freesound.org/previews/681/681490_11463865-hq.mp3"),
 ("ocean-waves-real","Waves of Hawaii","florianreichelt","https://freesound.org/people/florianreichelt/sounds/450755/","https://cdn.freesound.org/previews/450/450755_6253486-hq.mp3"),
 ("waterfall-real","Waterfall","Fabrizio84","https://freesound.org/people/Fabrizio84/sounds/458711/","https://cdn.freesound.org/previews/458/458711_2841496-hq.mp3"),
 ("shower-real","Taking a Shower","florianreichelt","https://freesound.org/people/florianreichelt/sounds/451762/","https://cdn.freesound.org/previews/451/451762_6253486-hq.mp3"),
 ("fireplace-real","Fireplace Crackling","visionear","https://freesound.org/people/visionear/sounds/501417/","https://cdn.freesound.org/previews/501/501417_10869493-hq.mp3"),
 ("forest-birds-real","Forest Birds","NightVoice","https://freesound.org/people/NightVoice/sounds/123999/","https://cdn.freesound.org/previews/123/123999_362645-hq.mp3")
]
ACTIVE={"box-fan-real","rain-on-window-real","heavy-rain-real","ocean-waves-real","waterfall-real"}
SOURCES=[entry for entry in SOURCES if entry[0] in ACTIVE]
def run(cmd,**kwargs):
    r=subprocess.run(cmd,capture_output=True,**kwargs)
    if r.returncode:
        raise RuntimeError((r.stderr or b"").decode(errors="replace")[-1200:])
    return r.stdout

def download(url):
    last=None
    for i in range(2):
        try:
            req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; WhiteNoiseChoir/1.0; CC0 audio archival)","Accept":"audio/*,*/*"})
            with urlopen(req,timeout=18) as response:
                raw=response.read(30_000_000)
            if len(raw)<40000: raise ValueError("Audio file too short")
            return raw
        except Exception as exc:
            last=exc
            time.sleep(1+i*2)
    raise RuntimeError(f"Cannot fetch CC0 preview: {url} ({last})")

def process(entry):
    soundid,title,creator,page,audio=entry
    raw=download(audio)
    with tempfile.TemporaryDirectory() as temporary:
        incoming=Path(temporary)/"original.mp3"
        incoming.write_bytes(raw)
        pcm=run(["ffmpeg","-hide_banner","-loglevel","error","-i",str(incoming),"-t",str(TARGET+OVERLAP+1),
                 "-ar",str(SR),"-ac","2","-f","f32le","pipe:1"])
        samples=np.frombuffer(pcm,dtype="<f4")
        frames=len(samples)//2
        if frames<SR*(TARGET+OVERLAP):
            raise ValueError(f"Source too short for a seamless {TARGET}s loop: {soundid}, {frames/SR:.1f}sec")
        samples=samples[:SR*(TARGET+OVERLAP)*2].reshape(-1,2)
        end=TARGET*SR; overlap=OVERLAP*SR
        out=samples[:end].copy()
        # Overlap-add start with samples immediately following the last frame.
        # The output boundary therefore aligns adjacent samples of the source.
        # Fade from source's natural continuation to its first two seconds.
        t=np.linspace(0,1,overlap,dtype=np.float32)[:,None]
        fade=np.sin(t*np.pi*.5)**2
        out[:overlap]=samples[end:end+overlap]*(1-fade)+samples[:overlap]*fade
        out-=out.mean(axis=0,keepdims=True)
        rms=np.sqrt(np.mean(out.astype(np.float64)**2))
        if rms<1e-6:raise ValueError(f"Silent source: {soundid}")
        out*= (10**(-26/20))/rms
        peak=float(np.max(np.abs(out)))
        if peak>0.58:out*=0.58/peak
        output=DEST/(soundid+".mp3")
        run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","f32le","-ar",str(SR),
             "-ac","2","-i","pipe:0","-c:a","libmp3lame","-b:a","128k",str(output)],
            input=out.astype("<f4").tobytes())
    return {"id":soundid,"title":title,"creator":creator,"source":page,"preview_url":audio,
            "license":"CC0-1.0","file":f"audio/{soundid}.mp3",
            "preview_sha256":hashlib.sha256(raw).hexdigest(),"derived_duration_seconds":TARGET}

if __name__=="__main__":
    results={}
    with ThreadPoolExecutor(max_workers=5) as executor:
        todo={executor.submit(process,e):e[0] for e in SOURCES}
        for f in as_completed(todo):
            result=f.result()
            print("Imported",result["id"],flush=True)
            results[result["id"]]=result
    manifest=[results[s[0]] for s in SOURCES]
    (DEST/"cc0-sources.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    assert len(manifest)==len(SOURCES)
    print(f"Imported {len(manifest)} CC0 ambient recordings. Human listening QA still required.")
