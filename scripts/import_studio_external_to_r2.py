#!/usr/bin/env python3
"""Import six V4/V5 Freesound preview files into R2 with SHA-256 verification.

This is a *temporary listening-quality* asset import, NOT an import of the
high-resolution Freesound originals. Never mark a preview as a release master.
Each result is printed as STUDIO_R2_ASSET_JSON for catalog pinning after CI QA.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

import boto3
from botocore.config import Config

BUCKET="whitenoisechoir-media"
ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
PUBLIC="https://media.whitenoisechoir.com"
SOURCES={
  12: ("wood-creak","https://cdn.freesound.org/previews/506/506660_4921277-hq.mp3","https://freesound.org/people/Rudmer_Rotteveel/sounds/506660/","CC0"),
  13: ("porch-dripping","https://cdn.freesound.org/previews/180/180948_2596329-hq.mp3","https://freesound.org/people/jc144940/sounds/180948/","CC0"),
  56: ("sleeping-dog","https://cdn.freesound.org/previews/482/482998_6150892-lq.mp3","https://freesound.org/people/SpaceJoe/sounds/482998/","CC0"),
  57: ("soft-crickets","https://cdn.freesound.org/previews/857/857163_12970089-lq.mp3","https://freesound.org/people/Goldenboy76/sounds/857163/","CC0"),
  59: ("frog-creek","https://cdn.freesound.org/previews/802/802736_3530854-lq.mp3","https://freesound.org/people/clif_creates/sounds/802736/","CC0"),
  60: ("cricket-creek","https://cdn.freesound.org/previews/802/802735_3530854-lq.mp3","https://freesound.org/people/clif_creates/sounds/802735/","CC0")
}
FROG_R2="asset-library/raw/sha256/0a/0a3c133128b94306396567cfc22ded8363645869d762c2bbc76b5c3519017cff.m4a"

def download(url: str, destination: Path) -> None:
    headers={"User-Agent":"WhiteNoiseChoir-AssetIntake/1.0 (+https://whitenoisechoir.com/)",
             "Accept":"audio/mpeg, audio/*;q=0.9, */*;q=0.5"}
    error=None
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers=headers)
            with urllib.request.urlopen(req,timeout=55) as response, destination.open("wb") as out:
                ctype=response.headers.get("Content-Type","").lower()
                if "text/html" in ctype or "json" in ctype: raise ValueError("Origin returned HTML/JSON instead of audio")
                size=0
                while True:
                    b=response.read(256*1024)
                    if not b: break
                    size+=len(b)
                    if size>65*1024*1024: raise ValueError("Refusing source larger than 65 MB")
                    out.write(b)
            if size<4096: raise ValueError("File shorter than 4 KB")
            return
        except Exception as exc:
            error=str(exc)
            if destination.exists(): destination.unlink()
            time.sleep(attempt*2+1)
    raise RuntimeError("Origin download failed (3 attempts): "+str(error)[:400])

def probe(path: Path):
    res=subprocess.run(["ffprobe","-v","error","-show_entries",
                        "format=duration,format_name:stream=codec_name,sample_rate,channels,codec_type",
                        "-of","json",str(path)],capture_output=True,text=True,timeout=45)
    if res.returncode: raise RuntimeError("ffprobe: "+res.stderr[-250:])
    data=json.loads(res.stdout)
    audio=next((s for s in data.get("streams",[]) if s.get("codec_type")=="audio"),None)
    if not audio: raise RuntimeError("No audio stream in downloaded file")
    duration=float(data.get("format",{}).get("duration") or 0)
    if duration<1 or duration>3600: raise RuntimeError("Unexpected file duration "+str(duration))
    check=subprocess.run(["ffmpeg","-hide_banner","-v","error","-nostdin","-i",str(path),
        "-t","3","-ac","1","-f","null","-"],capture_output=True,text=True,timeout=45)
    if check.returncode: raise RuntimeError("Audio decode failed: "+check.stderr[-250:])
    return {"codec":audio.get("codec_name"),"channels":audio.get("channels"),
            "sample_rate":audio.get("sample_rate"),"duration":round(duration,3)}

def main():
    if not os.getenv("R2_ACCESS_KEY_ID") or not os.getenv("R2_SECRET_ACCESS_KEY"):
        raise RuntimeError("Missing R2_ACCESS_KEY_ID and/or R2_SECRET_ACCESS_KEY GitHub secrets")
    session=boto3.session.Session()
    s3=session.client("s3",endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",
        region_name="auto",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
                      connect_timeout=20,read_timeout=90,retries={"mode":"standard","max_attempts":5},
                      request_checksum_calculation="when_required",response_checksum_validation="when_required"))
    good=[];failed=[]
    with tempfile.TemporaryDirectory(prefix="studio-r2-") as td:
        root=Path(td)
        for ident,(slug,url,source,license) in SOURCES.items():
            name=slug+".mp3"
            path=root/name
            try:
                download(url,path)
                meta=probe(path)
                blob=path.read_bytes()
                sha=hashlib.sha256(blob).hexdigest()
                key=f"asset-library/raw/sha256/{sha[:2]}/{sha}.mp3"
                content_type="audio/mpeg"
                try:head=s3.head_object(Bucket=BUCKET,Key=key)
                except s3.exceptions.ClientError as exc:
                    if str(exc.response.get("Error",{}).get("Code")) not in ("404","NoSuchKey","NotFound"):raise
                    head=None
                if head is None:
                    s3.put_object(Bucket=BUCKET,Key=key,Body=blob,ContentType=content_type,
                        CacheControl="public, max-age=31536000, immutable",
                        Metadata={"sha256":sha,"asset-quality":"preview-mp3","source":"freesound"})
                    action="uploaded"
                else:
                    if int(head["ContentLength"])!=len(blob):raise RuntimeError("Existing object has unexpected length")
                    action="reused"
                fetched=s3.get_object(Bucket=BUCKET,Key=key)
                remote=fetched["Body"].read()
                fetched["Body"].close()
                if len(remote)!=len(blob) or hashlib.sha256(remote).hexdigest()!=sha:
                    raise RuntimeError("R2 checksum verification failed")
                entry={"asset_id":ident,"slug":slug,"key":key,"public_url":f"{PUBLIC}/{key}",
                    "source_url":source,"preview_url":url,"license":license,
                    "size":len(blob),"sha256":sha,"quality":"external_preview_mp3_not_master",
                    "qa":"technical_pass_listening_pending","status":"STORED_R2",**meta,"upload_action":action}
                good.append(entry)
                print("STUDIO_R2_ASSET_JSON "+json.dumps(entry,ensure_ascii=False),flush=True)
            except Exception as exc:
                entry={"asset_id":ident,"slug":slug,"error":str(exc)[:450]}
                failed.append(entry)
                print("STUDIO_R2_IMPORT_ERROR "+json.dumps(entry,ensure_ascii=False),flush=True)
    report={"date":"2026-11-12","assets":good,"failures":failed,
            "note":"Six CC0 MP3 preview assets imported for editing/listening only. High-res originals still need separate authentication/download and QA."}
    out=Path("studio-r2-import-report.json")
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("STUDIO_R2_IMPORT_SUMMARY "+json.dumps({"passed":len(good),"failed":len(failed)},ensure_ascii=False),flush=True)
    if failed:raise SystemExit(1)

if __name__=="__main__":main()
