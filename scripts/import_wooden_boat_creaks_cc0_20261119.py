#!/usr/bin/env python3
"""Scoped, idempotent import of three CC0 wooden-boat supplemental SFX to WNC public media R2.
These are AI-generated SFXMint CC0 MP3s, NOT field recordings or approved release masters.
Does not touch Studio code or any pre-existing asset.
"""
import hashlib, json, os, subprocess, tempfile, pathlib, urllib.request, urllib.error, re, time
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
BUCKET="whitenoisechoir-media"
PUBLIC="https://media.whitenoisechoir.com"
SOURCES=(
 ("boat-hull-creak-02","Wooden Hull Ship Creak 02","ship-creak-02",4.83),
 ("boat-mast-ropes-03","Mast And Rope Ship Creak 03","ship-creak-03",4.02),
 ("boat-storm-strain-10","Storm Strain Ship Creak 10","ship-creak-10",9.04),
)

def urlopen_bytes(url,limit):
    request=urllib.request.Request(url,headers={"User-Agent":"WhiteNoiseChoir/1.0 (owner-requested CC0 audio intake)","Accept":"audio/mpeg,text/html;q=0.8,*/*;q=0.2"})
    with urllib.request.urlopen(request,timeout=35) as res:
        content_type=(res.headers.get("Content-Type") or "").lower()
        raw=res.read(limit+1)
    if not raw or len(raw)>limit:raise ValueError("SOURCE_SIZE_INVALID")
    return raw,content_type

def probe(data,path,expected):
    path.write_bytes(data)
    p=subprocess.run(["ffprobe","-v","error","-of","json","-show_entries","format=duration:stream=codec_type,codec_name,sample_rate,channels",str(path)],capture_output=True,text=True,timeout=35)
    if p.returncode:raise ValueError("FFPROBE_FAILURE "+p.stderr[-220:])
    meta=json.loads(p.stdout)
    streams=[x for x in meta.get("streams",[]) if x.get("codec_type")=="audio"]
    if len(streams)!=1 or streams[0].get("codec_name")!="mp3":raise ValueError("NOT_ONE_MP3_AUDIO_STREAM")
    dur=float(meta["format"]["duration"])
    if dur<1 or dur>30 or abs(dur-expected)>1.5:raise ValueError("UNEXPECTED_DURATION:"+str(dur))
    dec=subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-i",str(path),"-f","null","-"],capture_output=True,text=True,timeout=55)
    if dec.returncode:raise ValueError("FULL_DECODE_FAILURE:"+dec.stderr[-200:])
    return dict(duration=round(dur,3),codec="mp3",sample_rate=streams[0].get("sample_rate"),channels=streams[0].get("channels"))

def main():
    if not os.getenv("R2_ACCESS_KEY_ID") or not os.getenv("R2_SECRET_ACCESS_KEY"):raise ValueError("MISSING_R2_SECRET")
    s3=boto3.client("s3",endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",region_name="auto",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",s3={"addressing_style":"path"},connect_timeout=15,read_timeout=60,retries={"mode":"standard","max_attempts":4},request_checksum_calculation="when_required",response_checksum_validation="when_required"))
    out={"schema":"wnc_wooden_boat_cc0_intake_v1","verified_date":"2026-11-19","description":"Supplemental AI-generated short creaks, not field recordings or release approved.","assets":[],"errors":[]}
    with tempfile.TemporaryDirectory() as td:
        for slug,title,stem,duration in SOURCES:
            page="https://sfxmint.com/sounds/"+stem
            audio="https://sfxmint.com/dl/"+stem+".mp3"
            try:
                page_raw,pt=urlopen_bytes(page,350000)
                text=page_raw.decode("utf-8",errors="replace")
                if "CC0 1.0" not in text or "AI-generated" not in text or stem not in text or "ship creak" not in text.lower():
                    raise ValueError("LICENSE_OR_SOURCE_PAGE_NOT_VERIFIED")
                if audio not in text:raise ValueError("DIRECT_URL_NOT_VERIFIED")
                raw,ctype=urlopen_bytes(audio,15000000)
                if "html" in ctype or raw[:1]==b"<":raise ValueError("AUDIO_ENDPOINT_HTML")
                measured=probe(raw,pathlib.Path(td)/(stem+".mp3"),duration)
                sha=hashlib.sha256(raw).hexdigest()
                key=f"asset-library/raw/sha256/{sha[:2]}/{sha}.mp3"
                try:head=s3.head_object(Bucket=BUCKET,Key=key)
                except ClientError as exc:
                    if str(exc.response.get("Error",{}).get("Code")) in ("404","NotFound","NoSuchKey"):head=None
                    else:raise
                if head is None:
                    s3.put_object(Bucket=BUCKET,Key=key,Body=raw,ContentType="audio/mpeg",CacheControl="public,max-age=31536000,immutable",Metadata={"sha256":sha,"license":"CC0-1.0","origin":"ai_generated","producer":"sfxmint"})
                    action="uploaded"
                else:
                    if head["ContentLength"]!=len(raw):raise ValueError("EXISTING_OBJECT_WRONG_SIZE")
                    action="reused"
                stored=s3.get_object(Bucket=BUCKET,Key=key)
                mirror=stored["Body"].read();stored["Body"].close()
                if len(mirror)!=len(raw) or hashlib.sha256(mirror).hexdigest()!=sha:raise ValueError("R2_READBACK_SHA_FAILURE")
                row={"slug":slug,"title":title,"assetRef":"r2-"+sha,"key":key,"sha256":sha,"source_url":page,"media_url":audio,"license":"CC0-1.0","origin":"AI_GENERATED","quality":"PREVIEW_MP3_LISTENING_QA_PENDING","release_approved":False,"bytes":len(raw),"r2_bucket":BUCKET,"r2_status":"STORED_R2_SHA_VERIFIED","action":action,**measured}
                out["assets"].append(row)
                print("WOODEN_BOAT_IMPORT_OK "+json.dumps(row,ensure_ascii=False),flush=True)
            except Exception as e:
                item={"slug":slug,"error":str(e)[:330]}
                out["errors"].append(item)
                print("WOODEN_BOAT_IMPORT_ERROR "+json.dumps(item),flush=True)
    pathlib.Path("audits").mkdir(exist_ok=True)
    pathlib.Path("audits/wooden-boat-cc0-intake-report.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("WOODEN_BOAT_IMPORT_SUMMARY "+json.dumps({"uploaded_or_reused":len(out["assets"]),"errors":len(out["errors"])},ensure_ascii=False),flush=True)
    if out["errors"]:raise SystemExit(2)

if __name__=="__main__":main()
