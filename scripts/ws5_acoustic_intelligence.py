#!/usr/bin/env python3
"""WS5 Acoustic Intelligence v1: bounded signal analysis of real R2 audio.
No speculative content classification, no model calls, no source writes.
Read input originals by canonical WS1 SHA and store private, versioned metrics.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,re,subprocess,tempfile
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import boto3
import numpy as np
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET="whitenoisechoir-media"
ENDPOINT="https://7483501ad8365fe26b0448b96b54fb9f.r2.cloudflarestorage.com"
WS1="internal/ai-metadata-index/v1/current.json"
WS5="internal/ws5-acoustic-intelligence/v1/"
DIGEST=re.compile(r"^[0-9a-f]{64}$")
KEY_RE=re.compile(r"^asset-library/(?:raw|commons|kenney|cc0-github-mirror)/sha256/[0-9a-f]{2}/([0-9a-f]{64})\.(?:mp3|wav|ogg|oga|flac|m4a|opus|aiff?)$",re.I)
PREFER=re.compile(r"rain|lake|water|river|creek|stream|forest|wind|ocean|wave|thunder|fire|owl|frog|insect|night|bird|sleep|nature|ambient|noise",re.I)
SCHEMA="wnc_ws5_acoustic_v1"
SAMPLE_SECONDS=25
MAX_BYTES=16_000_000
MAX_COUNT=24
MAX_SCAN=50
def now():return datetime.now(timezone.utc).isoformat()
def command(args,timeout=100):
    p=subprocess.run(args,capture_output=True,timeout=timeout)
    if p.returncode:raise RuntimeError("Audio decoder returned nonzero code")
    return p
def jsonget(s3,key,limit=2000000):
    with s3.get_object(Bucket=BUCKET,Key=key)["Body"] as body:data=body.read(limit+1)
    if len(data)>limit:raise ValueError("oversize JSON")
    return json.loads(data)
def jsonput(s3,key,obj):
    payload=json.dumps(obj,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode("utf-8")
    s3.put_object(Bucket=BUCKET,Key=key,Body=payload,ContentType="application/json")
def digest_file(file):
    h=hashlib.sha256()
    with Path(file).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def media_sources(sqlite_file):
    import sqlite3
    db=sqlite3.connect("file:"+str(sqlite_file)+"?mode=ro",uri=True)
    db.row_factory=sqlite3.Row
    n=db.execute("select count(*) from assets").fetchone()[0]
    if n<15000:raise RuntimeError("Unexpectedly small WS1 source")
    rows=db.execute("select id,name,sound_family,r2_key from assets where source_class='nature' and has_r2_audio=1 and r2_key is not null").fetchall()
    db.close()
    selected=[]
    seen=set()
    for r in rows:
        rid=str(r["id"]);digest=rid[7:] if rid.startswith("nature:") else ""
        key=str(r["r2_key"] or "")
        match=KEY_RE.fullmatch(key)
        if not DIGEST.fullmatch(digest) or not match or match[1].lower()!=digest:continue
        if digest in seen:continue
        seen.add(digest)
        name=str(r["name"] or "")
        group=str(r["sound_family"] or "")
        priority=0 if PREFER.search(name+" "+group) else 1
        selected.append({"sha256":digest,"r2_key":key,"title":name[:160],"family":group[:100],"priority":priority})
    selected.sort(key=lambda v:(v["priority"],v["sha256"]))
    return selected,n
def waveform(src,start,seconds):
    p=command(["ffmpeg","-hide_banner","-nostdin","-v","error","-ss",str(start),"-i",str(src),
         "-t",str(seconds),"-vn","-map","0:a:0","-ac","1","-ar","16000","-f","f32le","pipe:1"],timeout=80)
    if not p.stdout:raise ValueError("Empty decoded sample")
    x=np.frombuffer(p.stdout,dtype="<f4")
    if not np.isfinite(x).all():raise ValueError("Nonfinite PCM values")
    return x
def profile(x):
    n=(len(x)//1600)*1600
    if n<16000:raise ValueError("Insufficient PCM")
    y=x[:n].reshape(-1,1600).astype(np.float64)
    rms=np.sqrt(np.mean(y*y,axis=1)+1e-15)
    peak=np.max(np.abs(y),axis=1)
    drms=20*np.log10(np.maximum(rms[1:],1e-8)/np.maximum(rms[:-1],1e-8))
    # Only acoustic measurements; this does not detect speech or music.
    frames=np.asarray(x[:min(len(x),16000*20)],dtype=np.float64)
    frames=frames[:(len(frames)//16000)*16000].reshape(-1,16000)
    spectra=np.abs(np.fft.rfft(frames*np.hanning(16000),axis=1))**2
    freqs=np.fft.rfftfreq(16000,1/16000)
    high=float(np.sum(spectra[:,freqs>4000])/max(np.sum(spectra),1e-16))
    centroid=float(np.sum(spectra*freqs)/max(np.sum(spectra),1e-16))
    return {"rms_dbfs":round(20*math.log10(float(np.sqrt(np.mean(x*x,dtype=np.float64))+1e-12)),2),
      "sample_peak_dbfs":round(20*math.log10(max(float(np.max(np.abs(x))),1e-9)),2),
      "silent_window_fraction":round(float(np.mean(rms<10**(-48/20))),3),
      "max_rms_jump_db_per_100ms":round(float(np.max(drms)) if len(drms) else 0,2),
      "peak_to_rms_db_p95":round(float(np.percentile(20*np.log10(np.maximum(peak,1e-8)/np.maximum(rms,1e-8)),95)),2),
      "centroid_hz":round(centroid,1),"highband_energy_ratio_gt4khz":round(high,5)}
def summarize(profiles):
    metrics={}
    for name in profiles[0]:
        v=[p[name] for p in profiles]
        metrics[name]=round(max(v) if "max_rms_jump" in name or "silent" in name or "peak_to_rms" in name or "highband" in name else float(np.mean(v)),4)
    return metrics
def inspect_one(s3,record,tmp):
    sha=record["sha256"];key=record["r2_key"]
    meta={"schema":SCHEMA,"sha256":sha,"r2_key":key,"title":record["title"],"family_hint":record["family"],
        "analyzed_at_utc":now(),"audio_source":"R2_ORIGINAL","model_audio_content_classifier":"NOT_RUN",
        "speech_detection":"NOT_RUN","music_detection":"NOT_RUN","sleep_approval":"NOT_APPROVED",
        "listening_qa":"PENDING","analysis_scope":"SAMPLED_WINDOWS_NOT_FULL_SIGNAL"}
    try:
        h=s3.head_object(Bucket=BUCKET,Key=key)
        bytecount=int(h["ContentLength"]);meta["file_bytes"]=bytecount
        if bytecount>MAX_BYTES:
            meta["status"]="SKIPPED_LARGE";meta["reason"]="File larger than phase-1 16MB per-item budget"
            return meta
        if bytecount<100:
            meta["status"]="SKIPPED_INVALID";return meta
        ext=key.rsplit(".",1)[-1]
        file=Path(tmp)/(sha+"."+ext)
        s3.download_file(BUCKET,key,str(file))
        if digest_file(file)!=sha:raise ValueError("SHA256_MISMATCH")
        pr=command(["ffprobe","-v","error","-select_streams","a:0","-show_entries",
             "stream=codec_name,channels,sample_rate:format=duration","-of","json",str(file)],timeout=35)
        info=json.loads(pr.stdout)
        stream=(info.get("streams") or [{}])[0]
        duration=float(info["format"]["duration"])
        if duration<=0 or duration>604800:raise ValueError("INVALID_DURATION")
        meta.update({"codec":stream.get("codec_name"),"channels":stream.get("channels"),
          "sample_rate_hz":int(stream.get("sample_rate") or 0),"duration_seconds":round(duration,3),
          "source_sha256_verified":True})
        starts=[0] if duration<=40 else [0,max(0,duration/2-SAMPLE_SECONDS/2),max(0,duration-SAMPLE_SECONDS-1)]
        starts=list(dict.fromkeys(round(v,2) for v in starts))
        features=[];ranges=[]
        for offset in starts:
            seconds=min(SAMPLE_SECONDS,max(1,duration-offset))
            x=waveform(file,offset,seconds)
            features.append(profile(x))
            ranges.append({"start":offset,"seconds":round(len(x)/16000,3)})
        values=summarize(features)
        risk=[]
        if values["max_rms_jump_db_per_100ms"]>18:risk.append("ABRUPT_LEVEL_JUMP_IN_SAMPLE")
        if values["peak_to_rms_db_p95"]>21:risk.append("HIGH_PEAK_TO_RMS_IN_SAMPLE")
        if values["silent_window_fraction"]>.55:risk.append("MOSTLY_QUIET_IN_SAMPLE")
        if values["highband_energy_ratio_gt4khz"]>.38:risk.append("HIGH_FREQUENCY_HEAVY_IN_SAMPLE")
        meta.update({"status":"SAMPLED_SIGNAL_ANALYZED","sample_ranges":ranges,
          "sample_coverage_seconds":round(sum(z["seconds"] for z in ranges),2),
          "features":values,"flags":risk,
          "heuristic_screening":"REVIEW" if risk else "NO_FLAG_IN_SAMPLED_WINDOWS",
          "suitability_score":None})
    except Exception as exc:
        meta["status"]="ERROR"
        meta["reason"]=str(exc)[:110]
    return meta
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--max-files",type=int,default=MAX_COUNT)
    ap.add_argument("--max-scan",type=int,default=MAX_SCAN)
    args=ap.parse_args()
    if not 1<=args.max_files<=64 or not 1<=args.max_scan<=100:raise ValueError("Batch exceeds safety cap")
    s3=boto3.client("s3",region_name="auto",endpoint_url=ENDPOINT,
       aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
       config=Config(signature_version="s3v4",s3={"addressing_style":"path"},retries={"max_attempts":4,"mode":"standard"}))
    with tempfile.TemporaryDirectory() as wd:
        current=jsonget(s3,WS1)
        sha=str(current["index_sha256"]).lower()
        key=str(current["index_r2_key"])
        if not DIGEST.fullmatch(sha) or not key.startswith("internal/ai-metadata-index/v1/versions/"):raise RuntimeError("Unexpected WS1 pointer")
        local=Path(wd)/"metadata.sqlite";s3.download_file(BUCKET,key,str(local))
        if digest_file(local)!=sha:raise RuntimeError("Canonical WS1 SQLite checksum mismatch")
        candidates,total=media_sources(local)
        prefix=WS5+"source-"+sha[:16]+"/"
        checkkey=prefix+"checkpoint.json"
        try:checkpoint=jsonget(s3,checkkey)
        except ClientError as e:
            if e.response.get("Error",{}).get("Code") not in ("NoSuchKey","404","NotFound"):raise
            checkpoint={"schema":SCHEMA,"source_index_sha256":sha,"cursor":0,"attempted":0,"analyzed":0,
                 "status_counts":{},"batch_keys":[],"started_utc":now()}
        if checkpoint.get("source_index_sha256")!=sha:raise RuntimeError("WS1 checkpoint version mismatch")
        start=int(checkpoint.get("cursor",0));end=min(len(candidates),start+args.max_scan)
        rows=[];evaluated=0
        statuses=Counter(checkpoint.get("status_counts",{}))
        for idx in range(start,end):
            if evaluated>=args.max_files:break
            row=candidates[idx]
            recpath=prefix+"records/"+row["sha256"]+".json"
            # Already analyzed on a rerun? Never re-download the same original.
            try:result=jsonget(s3,recpath,100000)
            except ClientError as e:
                if e.response.get("Error",{}).get("Code") not in ("NoSuchKey","404","NotFound"):raise
                result=inspect_one(s3,row,wd)
                jsonput(s3,recpath,result)
            statuses[result["status"]]+=1
            rows.append({"sha256":row["sha256"],"status":result["status"],"features":result.get("features"),
                 "heuristic_screening":result.get("heuristic_screening"),"flags":result.get("flags",[]),
                 "sample_coverage_seconds":result.get("sample_coverage_seconds",0)})
            evaluated+=1
        newcursor=start+evaluated
        if evaluated:
            batchkey=prefix+f"batches/{start:06d}-{newcursor:06d}.json"
            jsonput(s3,batchkey,{"schema":SCHEMA,"source_index_sha256":sha,"start":start,"end":newcursor,
                 "rows":rows,"generated_at":now()})
            checkpoint["batch_keys"].append(batchkey)
        checkpoint["cursor"]=newcursor
        checkpoint["attempted"]=newcursor
        checkpoint["analyzed"]=int(statuses.get("SAMPLED_SIGNAL_ANALYZED",0))
        checkpoint["status_counts"]=dict(statuses)
        checkpoint["candidate_count"]=len(candidates)
        checkpoint["canonical_ws1_total"]=total
        checkpoint["updated_at"]=now()
        checkpoint["completed"]=newcursor>=len(candidates)
        jsonput(s3,checkkey,checkpoint)
        print("WS5_ACOUSTIC_BATCH",json.dumps({"ws1_total":total,"candidate_r2":len(candidates),
          "start":start,"end":newcursor,"attempted":newcursor,"analyzed":checkpoint["analyzed"],
          "statuses":dict(statuses),"completed":checkpoint["completed"],
          "checkpoint_key":checkkey},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
