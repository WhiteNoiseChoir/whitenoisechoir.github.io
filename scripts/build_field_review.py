#!/usr/bin/env python3
"""Create 4 audition-only longer CC0 recordings from the complete pinned previews.

Preserve authentic source character. No additional electronic noise, no 10-minute
padding, no mass-editing of production assets. These are REVIEW CANDIDATES.
"""
from pathlib import Path
import hashlib,json,math,re,subprocess,tempfile
from urllib.request import Request,urlopen

import numpy as np

BASE=Path("signature/field-review")
BASE.mkdir(parents=True,exist_ok=True)
SR=44100
XFADE=3
SOURCE_AUDIT=Path("audio/field-source-audit.json")
REGISTRY=Path("audio/cc0-sources.json")
SET={"box-fan-real","heavy-rain-real","ocean-waves-real","waterfall-real"}

def sha(data):return hashlib.sha256(data).hexdigest()
def db(v):return 20*math.log10(max(float(v),1e-12))
def rms(x):return math.sqrt(float(np.mean(np.square(x),dtype=np.float64)))

def run(cmd,**kw):
    r=subprocess.run(cmd,capture_output=True,**kw)
    if r.returncode:raise RuntimeError(r.stderr.decode(errors="replace")[-600:])
    return r

def download(url):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (WhiteNoiseChoir field-source review)","Accept":"audio/*,*/*"})
    with urlopen(req,timeout=60) as rsp:return rsp.read(35_000_000)

def decode(path):
    b=run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-i",str(path),
        "-ar",str(SR),"-ac","2","-f","f32le","pipe:1"]).stdout
    if len(b)%8:raise RuntimeError("Invalid decoded field sample")
    return np.frombuffer(b,dtype="<f4").reshape(-1,2).copy()

def source_seam_and_level(x):
    # Source duration is authoritative: preserve every independently recorded
    # variation except three seconds reserved for a low-cost sample splice.
    fade=SR*XFADE
    if len(x)<fade+SR*54:raise RuntimeError("Too-short source")
    n=len(x)-fade
    out=x[:n].copy()
    curve=np.sin(np.linspace(0,np.pi/2,fade,dtype=np.float32)[:,None])**2
    out[:fade]=x[n:n+fade]*(1-curve)+out[:fade]*curve
    out-=x.mean(axis=0,keepdims=True)
    level=rms(out)
    if level<1e-5:raise RuntimeError("Source silent")
    out*=10**(-28/20)/level
    peak=float(np.max(np.abs(out)))
    limit=10**(-5/20)
    if peak>limit:out*=limit/peak
    return out

def encode(path,pcm):
    command=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
        "-f","f32le","-ar",str(SR),"-ac","2","-i","pipe:0",
        "-c:a","libmp3lame","-b:a","192k",str(path)]
    p=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    step=SR*4
    try:
        for off in range(0,len(pcm),step):p.stdin.write(pcm[off:off+step].astype("<f4").tobytes())
        p.stdin.close()
        err=p.stderr.read().decode(errors="replace")
        if p.wait()!=0:raise RuntimeError("Encode failed "+err[-650:])
    finally:
        if p.poll() is None:p.kill();p.wait()

def qa(path,expected):
    with tempfile.TemporaryDirectory() as td:
        pcm=decode(path)
    dur=len(pcm)/SR
    pk=db(np.max(np.abs(pcm)))
    level=db(rms(pcm))
    frame=SR//4
    windows=pcm[:len(pcm)//frame*frame].reshape(-1,frame,2)
    quiet=int(np.count_nonzero(np.mean(np.square(windows),axis=(1,2),dtype=np.float64)<1e-13))
    diff=rms(pcm[0]-pcm[-1])
    typical=math.sqrt(float(np.mean(np.square(np.diff(pcm[::20],axis=0),dtype=np.float64))))+1e-12
    flags=[]
    if abs(dur-expected)>1.0:flags.append("duration_error")
    if pk>-3:flags.append("peak_headroom")
    if not -36<=level<=-23:flags.append("rms_out_of_range")
    if quiet>0:flags.append("digital_silence")
    if diff/typical>4:flags.append("loop_join_jump")
    return {"seconds":round(dur,2),"sample_peak_dbfs":round(pk,2),
            "rms_dbfs":round(level,2),"silent_250ms":quiet,
            "join_vs_adjacent_change":round(diff/typical,3),
            "channels":2,"sample_rate":SR,"bitrate_kbps":192,
            "status":"PASS" if not flags else "REVIEW","flags":flags,
            "human_approved":False}

def main():
    audit=json.loads(SOURCE_AUDIT.read_text())["tracks"]
    rows={r["id"]:r for r in json.loads(REGISTRY.read_text())}
    records=[]
    for entry in audit:
        id=entry["id"]
        if id not in SET:continue
        row=rows[id]
        source=download(row["preview_url"])
        if sha(source)!=entry["pinned_preview_sha256"]:
            raise RuntimeError("CC0 preview changed, requiring relicensing: "+id)
        with tempfile.TemporaryDirectory() as td:
            raw=Path(td)/"source.mp3";raw.write_bytes(source)
            pcm=decode(raw)
            actual=len(pcm)/SR
            if abs(actual-entry["accessible_preview_duration_seconds"])>1.0:
                raise RuntimeError(f"{id}: source duration changed")
            out=source_seam_and_level(pcm)
            path=BASE/(id+"-full.mp3")
            encode(path,out)
            q=qa(path,len(out)/SR)
        if q["status"]!="PASS":
            raise RuntimeError(f"{id} failed candidate QA: {q['flags']}")
        records.append({
            "id":id,"preview_file":str(path),"sha256":sha(path.read_bytes()),
            "bytes":path.stat().st_size,
            "creator":row["creator"],"source_url":row["source"],
            "license":row["license"],"pinned_source_sha256":entry["pinned_preview_sha256"],
            "independent_recording_seconds":round(actual,2),
            "source_material_used_seconds":round(len(out)/SR,2),
            "processing":"original complete source preview, simple linear level scaling and 3s loop splice; no repetition or extra synthetic noise",
            "qa":q,"listening_status":"PENDING_USER_APPROVAL",
        })
        print("REVIEW_CANDIDATE",json.dumps(records[-1]),flush=True)
    if {r["id"] for r in records}!=SET:raise RuntimeError("Missing one of four candidates")
    (BASE/"manifest.json").write_text(json.dumps({
        "version":"field-full-source-review-20261108",
        "status":"AUDITION_ONLY_NO_MAIN_SITE_ASSET_REPLACEMENT",
        "records":records},indent=2)+"\n")
    print("AUDIT_CANDIDATES_READY",len(records),flush=True)

if __name__=="__main__":
    main()
