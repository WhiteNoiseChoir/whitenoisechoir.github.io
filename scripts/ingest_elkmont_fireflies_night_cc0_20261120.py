#!/usr/bin/env python3
"""Append-only CC0 night forest field-recording intake for Elkmont firefly episode.

Sources are user-directed, individually vetted Freesound public pages. This
imports MP3 previews, NOT original WAV masters or release-approved audio.
No existing object, catalog, player, Studio or production data is modified.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request
import urllib.parse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from mutagen.mp3 import MP3
import imageio_ffmpeg

ACCOUNT_ID = "7483501ad8365fe26b0448b96b54fb9f"
BUCKET = "whitenoisechoir-media"
REPORT = Path("audits/elkmont-fireflies-night-cc0-20261120.json")
# Author/title/license/date were checked on Freesound 2026-11-19.
SOURCES = [
  {
    "slug": "north-carolina-woodland-crickets-night-333221",
    "source_url": "https://freesound.org/people/hdfreema/sounds/333221/",
    "author": "hdfreema",
    "sound_id": 333221,
    "preview_base": "https://cdn.freesound.org/previews/333/333221_2098408",
    "duration": 220.057,
    "category": "night-insects-forest-bed",
    "region": "Charlotte, North Carolina, USA; BACK PORCH facing woods, NOT recorded at Elkmont",
    "description": "Summer night crickets and insects, recording from back porch facing forest; CHECK FOR HUMAN/DOG/TRAFFIC BEFORE RELEASE."
  },
  {
    "slug": "tennessee-southern-summer-evening-crickets-746366",
    "source_url": "https://freesound.org/people/RyanKingArt/sounds/746366/",
    "author": "RyanKingArt",
    "sound_id": 746366,
    "preview_base": "https://cdn.freesound.org/previews/746/746366_11069322",
    "duration": 45.046,
    "category": "evening-insects-supplement",
    "region": "Middle Tennessee, USA; July 13, 2024 (NOT Elkmont or early June)",
    "description": "Stereo field recording insects and crickets; seasonal/geographic mismatch requires gain and listening review."
  }
]

def get_bytes(url: str, limit: int) -> tuple[bytes,str]:
    req=urllib.request.Request(url,headers={
      "User-Agent":"WhiteNoiseChoir/1.0 (+https://whitenoisechoir.com/; scoped licensed-source preservation)",
      "Accept":"audio/mpeg,text/html;q=0.8,*/*;q=0.5"})
    with urllib.request.urlopen(req,timeout=35) as r:
        final=urllib.parse.urlparse(r.geturl())
        if final.scheme!="https" or final.hostname not in ("freesound.org","cdn.freesound.org"):
            raise ValueError("UNEXPECTED_REDIRECT_HOST")
        content_type=(r.headers.get("Content-Type") or "").lower()
        blob=r.read(limit+1)
    if len(blob)>limit or len(blob)<1000:
        raise ValueError("INVALID_SOURCE_LENGTH")
    return blob,content_type

def verify_page(item: dict) -> None:
    raw,ctype=get_bytes(item["source_url"],700000)
    if "html" not in ctype and b"<html" not in raw[:4000].lower():
        raise ValueError("SOURCE_PAGE_NOT_HTML")
    page=raw.decode("utf8",errors="replace")
    # Fail closed if page author, sound identity or CC0 rights cannot be verified.
    required=(item["author"],"Creative Commons 0",str(item["sound_id"]))
    if not all(s.lower() in page.lower() for s in required):
        raise ValueError("SOURCE_AUTHOR_ID_OR_CC0_NOT_VERIFIED")
    if "Attribution NonCommercial" in page or "Attribution-NonCommercial" in page:
        raise ValueError("AMBIGUOUS_LICENSE_BLOCK")
    if item["preview_base"] not in page:
        raise ValueError("PUBLISHED_PREVIEW_ID_NOT_VERIFIED")

def download_preview(item: dict) -> tuple[bytes,str,str]:
    # Published OG preview provides base/ID. Try higher-quality preview first.
    # Do not infer that it is the freely downloadable 320kbps original.
    errors=[]
    for quality in ("hq","lq"):
        uri=item["preview_base"]+"-"+quality+".mp3"
        try:
            raw,ctype=get_bytes(uri,30*1024*1024)
            if "html" in ctype or raw[:1]==b"<":
                raise ValueError("AUDIO_RESPONSE_IS_HTML")
            return raw,uri,quality
        except Exception as ex:
            errors.append(quality+":"+str(ex)[:140])
    raise ValueError("ALL_PREVIEWS_UNAVAILABLE: "+";".join(errors))

def audio_probe(raw: bytes, target: Path, expected: float) -> dict:
    target.write_bytes(raw)
    # GitHub hosted images may not include ffprobe. Parse MP3 headers using
    # mutagen and decode the ENTIRE file with a bundled ffmpeg executable.
    try:
        info = MP3(str(target)).info
        duration = float(info.length)
        samplerate = int(info.sample_rate or 0)
        channels = int(info.channels or 0)
    except Exception as ex:
        raise ValueError("MP3_HEADER_PROBE_FAILED: "+str(ex)[:180])
    if duration < 8 or abs(duration-expected) > 5:
        raise ValueError("AUDIO_DURATION_MISMATCH "+str(duration))
    ffmpeg = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
    check = subprocess.run([ffmpeg,"-v","error","-nostdin","-i",str(target),
        "-f","null","-"],capture_output=True,text=True,timeout=95)
    if check.returncode:
        raise ValueError("FULL_AUDIO_DECODE_FAILED "+check.stderr[-190:])
    return {"duration":round(duration,3),"codec":"mp3",
      "sample_rate_hz":samplerate,"channels":channels}

def put_append_only(s3, key: str, raw: bytes, content_type: str, metadata=None) -> str:
    try:
        head=s3.head_object(Bucket=BUCKET,Key=key)
    except ClientError as ex:
        if str(ex.response.get("Error",{}).get("Code")) in ("404","NoSuchKey","NotFound"):
            head=None
        else:
            raise
    if head is not None:
        if int(head["ContentLength"]) != len(raw):
            raise ValueError("HASH_KEY_CONFLICT_WRONG_OBJECT_SIZE")
        return "already_exists"
    s3.put_object(Bucket=BUCKET,Key=key,Body=raw,
      ContentType=content_type,Metadata=metadata or {},CacheControl="public,max-age=31536000,immutable")
    return "uploaded"

def main() -> None:
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    result={"schema":"wnc.elkmont-fireflies-night-cc0-intake.v1",
       "date":"2026-11-20","quality":"public_preview_not_original_not_release_approved",
       "assets":[],"errors":[]}
    try:
        if not all(os.getenv(k) for k in ("R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY")):
            raise ValueError("R2_GITHUB_SECRETS_NOT_CONFIGURED")
        s3=boto3.client("s3",endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",
          region_name="auto",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
          aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
          config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
            connect_timeout=15,read_timeout=65,retries={"mode":"standard","max_attempts":4},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required"))
        with tempfile.TemporaryDirectory() as temp:
            for item in SOURCES:
                try:
                    verify_page(item)
                    raw,preview_url,quality=download_preview(item)
                    measured=audio_probe(raw,Path(temp)/(item["slug"]+".mp3"),item["duration"])
                    sha=hashlib.sha256(raw).hexdigest()
                    key="asset-library/raw/sha256/"+sha[:2]+"/"+sha+".mp3"
                    state=put_append_only(s3,key,raw,"audio/mpeg",
                       {"sha256":sha,"license":"CC0-1.0","source":"freesound",
                        "quality":"preview","sound_id":str(item["sound_id"])})
                    # Strict readback: no successful status until R2 bytes match the source.
                    res=s3.get_object(Bucket=BUCKET,Key=key)
                    back=res["Body"].read()
                    res["Body"].close()
                    if hashlib.sha256(back).hexdigest()!=sha:
                        raise ValueError("R2_READBACK_SHA256_MISMATCH")
                    row={k:v for k,v in item.items() if k not in ("preview_base","duration")}
                    row.update({"assetRef":"r2-"+sha,"r2_key":key,"sha256":sha,
                      "bytes":len(raw),"r2_bucket":BUCKET,
                      "source_audio_url":preview_url,
                      "source_license":"CC0-1.0","quality_tier":quality+"_preview_mp3",
                      "provenance":"FIELD_RECORDING_BY_UPLOADER",
                      "status":"STORED_R2_SHA_FULL_DECODE_VERIFIED_LISTENING_PENDING",
                      "studio_registered":False,"release_approved":False,
                      "r2_action":state,**measured})
                    provenance_key="asset-library/provenance/elkmont-fireflies-night-20261120/"+item["slug"]+".json"
                    prov=json.dumps(row,ensure_ascii=False,indent=2).encode("utf8")
                    put_append_only(s3,provenance_key,prov,"application/json")
                    result["assets"].append(row)
                    record={
                        "audio_sha256":sha,"audio_storage_key":key,"file_bytes":len(raw),
                        "duration_seconds":measured["duration"],
                        "title":"Elkmont Candidate Forest Night "+str(item["sound_id"]),
                        "source_page":item["source_url"],
                        "license_evidence_url":item["source_url"],
                        "license_url":"https://creativecommons.org/publicdomain/zero/1.0/",
                        "license":"CC0-1.0","creator":item["author"],
                        "source_provider":"Freesound",
                        "group_hint":"nature insects forest nocturnal crickets evening",
                        "source_tags":"field recording, night, North Carolina, Tennessee, insects, crickets, ecology review",
                        "region":item["region"],
                        "audio_quality":"Freesound preview MP3, not original WAV",
                        "audio_preview_url":preview_url,
                        "audio_qa":"FULL_DECODE_PASS_LISTENING_PENDING",
                        "release_approved":False,
                    }
                    record_key="asset-library/records/sha256/"+sha[:2]+"/"+sha+".json"
                    put_append_only(s3,record_key,
                        json.dumps(record,ensure_ascii=False,sort_keys=True).encode("utf8"),
                        "application/json")
                    row["catalog_metadata_sidecar"]=record_key
                    print("ELKMONT_NIGHT_IMPORTED "+json.dumps(row,ensure_ascii=False),flush=True)
                except Exception as ex:
                    error={"slug":item["slug"],"error":str(ex)[:400]}
                    result["errors"].append(error)
                    print("ELKMONT_NIGHT_IMPORT_ERROR "+json.dumps(error),flush=True)
    except Exception as ex:
        result["errors"].append({"slug":"global","error":str(ex)[:350]})
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("ELKMONT_NIGHT_SUMMARY "+json.dumps({
        "saved":len(result["assets"]),"errors":len(result["errors"]),
        "studio_registered":0,"release_approved":False}),flush=True)
    if result["errors"]:
        raise SystemExit(2)

if __name__=="__main__":
    main()
