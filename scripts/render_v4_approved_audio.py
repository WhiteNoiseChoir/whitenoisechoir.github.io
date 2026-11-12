#!/usr/bin/env python3
"""Render the approved 600 s Living Forest Creek V4 timeline on GitHub Actions.

Uses the ORIGINAL long R2 masters for offsets beyond 92 seconds. Does not
render video, grant Public status, or fabricate finished-release metadata.
Writes WAV and MP3, with a deterministic QA report and optional R2 upload.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.request import Request, urlopen

MEDIA = "https://media.whitenoisechoir.com/"
REPO = Path(__file__).resolve().parents[1]
PROJECT_PATH = REPO / "vi/Living-Forest-Creek/index.html"
OUTPUT = REPO / "v4-render-output"
DURATION = 600
R2_BUCKET = "whitenoisechoir-media"
R2_ACCOUNT = "7483501ad8365fe26b0448b96b54fb9"
R2_FOLDER = "releases/Living-Forest-Creek"

def run(cmd, timeout=900):
    started=time.time()
    res=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    if res.returncode:
        raise RuntimeError("ffmpeg failed "+str(res.returncode)+": "+res.stderr[-3800:])
    print("V4_RENDER_COMMAND",str(cmd[0]),"seconds",round(time.time()-started,1),flush=True)
    return res.stdout+res.stderr

def get_source_catalog():
    engine=(REPO/"studio-engine.js").read_text(encoding="utf8")
    match=re.search(r"^const assets = (\[[^\n]+\]);",engine,re.MULTILINE)
    if not match:raise ValueError("Studio base assets not found")
    assets=json.loads(match.group(1))
    catalog=(REPO/"studio-catalog.js").read_text(encoding="utf8")
    more=json.loads(catalog[catalog.index("["):catalog.rindex("]")+1])
    return assets+more

def get_project():
    text=PROJECT_PATH.read_text(encoding="utf8")
    match=re.search(r'<script id="studio-trial" type="application/json">(.*?)</script>',text,re.DOTALL)
    if not match:raise ValueError("V4 project data missing")
    trial=json.loads(match.group(1))
    project=trial["project"]
    if trial["slug"]!="Living-Forest-Creek" or len(project["tracks"])!=30 or project["length"]!=600:
        raise ValueError("Approved V4 timeline shape changed, abort production.")
    if any(t.get("mute") for t in project["tracks"]):
        raise ValueError("Muted assets present in approved V4, abort.")
    return project

def get_file(url,dest):
    request=Request(url,headers={
      "User-Agent":"WhiteNoiseChoir-Final-Audio-Release/1.0",
      "Accept":"audio/*,*/*;q=0.1"
    })
    errors=[]
    for attempt in range(3):
      try:
        with urlopen(request,timeout=65) as response, open(dest,"wb") as out:
          if response.status!=200:raise RuntimeError("HTTP "+str(response.status))
          mimetype=response.headers.get("Content-Type","").lower()
          if not ("audio/" in mimetype or "application/octet-stream" in mimetype):
            raise RuntimeError("Unexpected Content-Type "+mimetype)
          while True:
            chunk=response.read(1024*1024)
            if not chunk:break
            out.write(chunk)
            if out.tell()>80*1024*1024:raise RuntimeError("Source exceeds 80 MB")
        if Path(dest).stat().st_size<4000:raise RuntimeError("Audio too short")
        return
      except Exception as exc:
        errors.append(str(exc))
        if Path(dest).exists():Path(dest).unlink()
        time.sleep(1+attempt*2)
    raise RuntimeError("Source download failed: "+url+" | "+" | ".join(errors))

def compose_graph(tracks, id_to_input):
    sections=[]
    grouped={}
    for idx,track in enumerate(tracks):
        grouped.setdefault(track["asset"],[]).append(idx)
    for asset,parts in grouped.items():
        ix=id_to_input[asset]
        prefix=f"[{ix}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo"
        if len(parts)>1:
            labels="".join(f"[s{asset}_{i}]" for i in range(len(parts)))
            sections.append(f"{prefix},asplit={len(parts)}{labels}")
        else:
            sections.append(f"{prefix}[s{asset}_0]")
    seen={}
    for n,t in enumerate(tracks):
        asset=t["asset"]
        ordinal=seen.get(asset,0)
        seen[asset]=ordinal+1
        start=float(t["start"])
        seconds=min(float(t.get("duration",DURATION-start)),DURATION-start)
        offset=float(t.get("offset",0))
        if seconds<=0:raise ValueError("Invalid clip duration "+str(n))
        gain=float(t["gain"])
        pan=float(t.get("pan",0))
        if not 0<=gain<=1 or not -1<=pan<=1:raise ValueError("Invalid gain or pan")
        fades_in=min(seconds,float(t.get("fadeIn",0)))
        fades_out=min(seconds-fades_in,float(t.get("fadeOut",0)))
        chain=f"[s{asset}_{ordinal}]atrim=start={offset:.5f}:duration={seconds:.5f},asetpts=PTS-STARTPTS"
        lowpass=t.get("lowpass")
        highpass=t.get("highpass")
        if lowpass and float(lowpass)>100:chain+=f",lowpass=f={int(float(lowpass))}"
        if highpass and float(highpass)>10:chain+=f",highpass=f={int(float(highpass))}"
        if fades_in>0:chain+=f",afade=t=in:st=0:d={fades_in:.5f}"
        if fades_out>0:chain+=f",afade=t=out:st={seconds-fades_out:.5f}:d={fades_out:.5f}"
        # Equal-power constant-power stereo balance approximation.
        from math import cos,sin,pi
        l=cos((pan+1)*pi/4)*1.4142135623730951
        r=sin((pan+1)*pi/4)*1.4142135623730951
        chain+=f",pan=stereo|c0={l:.6f}*c0|c1={r:.6f}*c1"
        chain+=f",volume={gain:.6f}"
        if start>0:chain+=f",adelay={round(start*1000)}:all=1"
        chain+=f"[out{n}]"
        sections.append(chain)
    section_inputs="".join(f"[out{i}]" for i in range(len(tracks)))
    sections.append(f"{section_inputs}amix=inputs={len(tracks)}:duration=longest:normalize=0,"
      "volume=0.58,alimiter=limit=0.95:level=0,apad=whole_dur=600,atrim=duration=600,asetpts=PTS-STARTPTS[final]")
    return ";\n".join(sections)+"\n"

def probe(path):
    value=run(["ffprobe","-v","error","-show_entries","format=duration,size:stream=codec_name,channels,sample_rate,codec_type",
        "-of","json",str(path)],timeout=40)
    return json.loads(value)

def upload_r2(path,mime):
    import boto3
    from botocore.config import Config
    if not os.getenv("R2_ACCESS_KEY_ID") or not os.getenv("R2_SECRET_ACCESS_KEY"):
        return {"status":"SKIPPED","reason":"No R2 secrets available"}
    s3=boto3.session.Session().client("s3",
      endpoint_url=f"https://{R2_ACCOUNT}.r2.cloudflarestorage.com",
      region_name="auto",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
      aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
      config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
        connect_timeout=20,read_timeout=100,retries={"mode":"standard","max_attempts":3}))
    data=Path(path).read_bytes()
    sha=hashlib.sha256(data).hexdigest()
    key=f"{R2_FOLDER}/{sha}.{Path(path).suffix.lstrip('.')}"
    # Not overwrite-in-place: hash-addressed release assets are immutable.
    for attempt in range(2):
      try:
        s3.put_object(Bucket=R2_BUCKET,Key=key,Body=data,ContentType=mime,
          CacheControl="public,max-age=31536000,immutable",
          Metadata={"sha256":sha,"v4-audio":"approved-timeline-render-2026-11-12"})
        head=s3.head_object(Bucket=R2_BUCKET,Key=key)
        if int(head["ContentLength"])!=len(data):raise RuntimeError("R2 stored size mismatch")
        print("V4_RELEASE_R2_STORED",json.dumps({"key":key,"size":len(data),"sha256":sha}),flush=True)
        return {"status":"STORED_R2","key":key,"url":MEDIA+key,"sha256":sha,"bytes":len(data)}
      except Exception as exc:
        print("V4_R2_UPLOAD_RETRY",str(exc)[:220],flush=True)
        time.sleep(3)
    return {"status":"UPLOAD_FAILED","reason":"R2 API unreachable; master files retained in GH artifact"}

def main():
    OUTPUT.mkdir(exist_ok=True)
    project=get_project()
    assets=get_source_catalog()
    source_ids=sorted({t["asset"] for t in project["tracks"]})
    id_to_input={id:i for i,id in enumerate(source_ids)}
    provenance=[]
    with tempfile.TemporaryDirectory(prefix="wnc-v4-") as d:
      tmp=Path(d)
      originals=[]
      for i,asset_id in enumerate(source_ids):
        asset=assets[asset_id]
        # Use the original approved 10-minute MP3, not 92-second Studio proxy:
        # some V4 spot events intentionally have offsets past 92 seconds.
        key=asset.get("key")
        if not key or ".." in key or not key.startswith(("audio/","asset-library/")):
          raise RuntimeError(f"Asset {asset_id} is not imported into R2")
        file=tmp/("asset-"+str(asset_id)+Path(key).suffix)
        print("V4_SOURCE",i+1,len(source_ids),asset_id,key,flush=True)
        get_file(MEDIA+key,file)
        metadata=probe(file)
        originals.append(file)
        provenance.append({"id":asset_id,"name":asset["name"],"r2_key":key,
          "sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
          "bytes":file.stat().st_size,"metadata":metadata.get("format",{})})
      graph=compose_graph(project["tracks"],id_to_input)
      (OUTPUT/"filtergraph.txt").write_text(graph,encoding="utf8")
      cmd=["ffmpeg","-hide_banner","-loglevel","warning","-nostdin","-y"]
      for file in originals:
        cmd.extend(["-stream_loop","-1","-i",str(file)])
      cmd+=["-filter_complex_script",str(OUTPUT/"filtergraph.txt"),
        "-map","[final]","-ar","44100","-ac","2","-c:a","pcm_s16le",
        str(OUTPUT/"Living-Forest-Creek-V4-600s.wav")]
      run(cmd,timeout=900)
    wav=OUTPUT/"Living-Forest-Creek-V4-600s.wav"
    mp3=OUTPUT/"Living-Forest-Creek-V4-600s.mp3"
    run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-i",str(wav),
      "-ar","44100","-ac","2","-c:a","libmp3lame","-b:a","192k",str(mp3)],timeout=300)
    wavinfo=probe(wav);mp3info=probe(mp3)
    dur=float(wavinfo["format"]["duration"])
    if abs(dur-DURATION)>0.15:raise RuntimeError("WAV is not 600 seconds")
    stats=run(["ffmpeg","-hide_banner","-nostdin","-i",str(wav),"-af","volumedetect",
      "-f","null","-"],timeout=150)
    peak=re.findall(r"max_volume:\s*([-\d.]+) dB",stats)
    if not peak:raise RuntimeError("Peak QA missing")
    max_db=float(peak[-1])
    if max_db>-0.05:raise RuntimeError("Audio is clipping, peak "+str(max_db))
    tail=run(["ffmpeg","-hide_banner","-nostdin","-sseof","-15","-i",str(wav),
      "-af","volumedetect","-f","null","-"],timeout=50)
    means=re.findall(r"mean_volume:\s*([-\d.]+) dB",tail)
    if not means or float(means[-1])<-58:raise RuntimeError("Last 15s are near silent")
    result={"project":"Living Forest Creek V4","asset_count":len(source_ids),
      "tracks":len(project["tracks"]),"duration_seconds":dur,"audio_peak_dbfs":max_db,
      "last_15s_mean_dbfs":float(means[-1]),"wav":wavinfo,"mp3":mp3info,
      "sources":provenance,"created_files":{}}
    for path,mime in [(wav,"audio/wav"),(mp3,"audio/mpeg")]:
      result["created_files"][path.name]=upload_r2(path,mime)
    (OUTPUT/"qa-report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print("V4_RENDER_QA_PASS",json.dumps({k:v for k,v in result.items() if k not in ("sources","wav","mp3")},ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
