#!/usr/bin/env python3
"""Bulk-ingest byte-identical CC0 sound-effects from a pinned public GitHub mirror into R2.

This is an import of independently archived files, NOT a Kenney web-zip scraper.
Allowed packs list upstream provenance. No audio conversion or human QA.
The mirror's license records and original publisher license pages are recorded
for each sound. Nothing is connected to the published site or mixer.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import mimetypes
import os
import pathlib
import re
import subprocess
import sys
import time

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET="whitenoisechoir-media"
ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
MIRROR_REPO="Mcamento8/open-game-sfx-index"
MIRROR_SHA="34bbe8b525b5ceff3804915ea745532af11f6055"
ROOT="asset-library/cc0-github-mirror/"
RAW_ROOT="asset-library/raw/sha256/"
EXTENSIONS={".wav":"audio/wav", ".ogg":"audio/ogg", ".oga":"audio/ogg",
            ".opus":"audio/ogg", ".flac":"audio/flac", ".mp3":"audio/mpeg",
            ".aiff":"audio/aiff", ".aif":"audio/aiff", ".m4a":"audio/mp4"}

# Deliberately EXCLUDES music jingles, voiceover, and source files known to have
# been converted from AIFF in the mirror. These do not meet current intake policy.
# Licensing is CC0 per the publisher pages and mirror SOURCES.md/ATTRIBUTION.md.
PACKS={
 "interface-sounds":("ui-interfaces","Kenney","Kenney","https://kenney.nl/assets/interface-sounds"),
 "ui-audio":("ui-interfaces","Kenney","Kenney","https://kenney.nl/assets/ui-audio"),
 "impact-sounds":("foley-impacts","Kenney","Kenney","https://kenney.nl/assets/impact-sounds"),
 "rpg-audio":("rpg-foley","Kenney","Kenney","https://kenney.nl/assets/rpg-audio"),
 "digital-audio":("synthetic-effects","Kenney","Kenney","https://kenney.nl/assets/digital-audio"),
 "sci-fi-sounds":("sci-fi-machinery","Kenney","Kenney","https://kenney.nl/assets/sci-fi-sounds"),
 "casino-audio":("cards-dice-foley","Kenney","Kenney","https://kenney.nl/assets/casino-audio"),
 "oga-512-retro":("retro-digital-effects","OpenGameArt","SubspaceAudio","https://opengameart.org/content/512-sound-effects-8-bit-style"),
 "oga-rpg-pack":("rpg-foley","OpenGameArt","artisticdude","https://opengameart.org/content/rpg-sound-pack"),
 "oga-gui-lokif":("ui-interfaces","OpenGameArt","LokiF","https://opengameart.org/content/gui-sound-effects"),
 "oga-hits-punches":("foley-impacts","OpenGameArt","qubodup","https://opengameart.org/content/37-hitspunches"),
 "oga-zombies":("creature-effects","OpenGameArt","artisticdude","https://opengameart.org/content/zombies-sound-pack"),
 "oga-footsteps":("footsteps","OpenGameArt","TinyWorlds","https://opengameart.org/content/different-steps-on-wood-stone-leaves-gravel-and-mud"),
 "oga-battle":("battle-effects","OpenGameArt","Ogrebane","https://opengameart.org/content/battle-sound-effects"),
}
def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def iter_assets(root):
    audio_root=root/"audio"
    if not audio_root.is_dir():
        raise ValueError("Mirror checkout missing audio/ directory")
    for slug,(category,provider,creator,url) in PACKS.items():
        pack=audio_root/slug
        if not pack.is_dir():
            raise ValueError("Expected CC0 mirror pack missing: "+slug)
        for path in sorted(pack.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel=path.relative_to(root).as_posix()
            if (path.name.startswith("._") or "__MACOSX" in path.parts
                    or path.suffix.lower() not in EXTENSIONS):
                continue
            yield path,rel,slug,category,provider,creator,url

def ffprobe(path):
    proc=subprocess.run(
        ["ffprobe","-v","error","-show_entries",
         "format=duration:stream=codec_type,codec_name,sample_rate,channels,duration",
         "-of","json",str(path)],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=35)
    if proc.returncode:
        raise ValueError("ffprobe rejected source audio: "+proc.stderr[-120:])
    obj=json.loads(proc.stdout)
    audio=next((x for x in obj.get("streams",[]) if x.get("codec_type")=="audio"),None)
    if not audio:
        raise ValueError("audio stream missing")
    duration=float(obj.get("format",{}).get("duration") or audio.get("duration") or 0)
    if not 0.01<=duration<=86400:
        raise ValueError("invalid audio duration")
    return audio,round(duration,3)

def sha256(path):
    sha=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            sha.update(block)
    return sha.hexdigest()

def head(s3,key):
    try:
        return s3.head_object(Bucket=BUCKET,Key=key)
    except ClientError as exc:
        if str(exc.response.get("Error",{}).get("Code","")) in ("404","NoSuchKey","NotFound"):
            return None
        raise

def digest_map(s3):
    # Prevent duplicate payloads, even if first uploaded from Wikimedia Commons.
    found={}
    prefixes=["asset-library/commons/sha256/","asset-library/kenney/sha256/",ROOT+"sha256/",RAW_ROOT]
    for prefix in prefixes:
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET,Prefix=prefix):
            for item in page.get("Contents",[]):
                key=item["Key"]
                m=re.search(r"/([0-9a-f]{64})\.[a-z0-9]+$",key)
                if m:
                    found.setdefault(m.group(1),key)
    return found

def write_provenance(s3,digest,record):
    path=ROOT+"records/"+digest[:2]+"/"+digest+".json"
    if not head(s3,path):
        s3.put_object(Bucket=BUCKET,Key=path,
                      Body=(json.dumps(record,ensure_ascii=False,sort_keys=True)+"\n").encode(),
                      ContentType="application/json",
                      Metadata={"kind":"cc0-source-provenance","sha256":digest})
    if not head(s3,path):
        raise RuntimeError("sidecar missing from R2")
    return path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-root",required=True)
    parser.add_argument("--max-files",type=int,default=1500)
    parser.add_argument("--max-file-mb",type=int,default=50)
    parser.add_argument("--max-total-mb",type=int,default=900)
    parser.add_argument("--report",default="audits/cc0-mirror-harvest-report.json")
    args=parser.parse_args()
    assert 1<=args.max_files<=3000 and 1<=args.max_file_mb<=200 and 1<=args.max_total_mb<=3000
    assert os.environ.get("R2_ACCESS_KEY_ID") and os.environ.get("R2_SECRET_ACCESS_KEY")
    root=pathlib.Path(args.source_root).resolve()
    source_marker=root/".git"
    if not source_marker.exists():
        raise ValueError("Expected git checkout for source integrity")
    check=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if check!=MIRROR_SHA:
        raise ValueError("Mirror git SHA differs from verified pinned revision")
    if not (root/"SOURCES.md").is_file() or not (root/"ATTRIBUTION.md").is_file():
        raise ValueError("Mirror CC0 provenance documents missing")
    s3=boto3.session.Session().client("s3",region_name="auto",
        endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
                      retries={"max_attempts":5,"mode":"standard"},connect_timeout=15,
                      read_timeout=100,request_checksum_calculation="when_required",
                      response_checksum_validation="when_required"))
    stored=digest_map(s3)
    report={
      "status":"RUNNING","generated_at":now(),"bucket":BUCKET,
      "source":"public CC0 mirror with publisher provenance",
      "mirror_repo":MIRROR_REPO,"mirror_commit":MIRROR_SHA,
      "mirror_license_sources":[
          "https://github.com/"+MIRROR_REPO+"/blob/"+MIRROR_SHA+"/SOURCES.md",
          "https://github.com/"+MIRROR_REPO+"/blob/"+MIRROR_SHA+"/ATTRIBUTION.md"],
      "approved_pack_ids":list(PACKS),
      "unreviewed_content":True,"audio_bytes_unchanged":True,
      "classification_status":"pending","human_review_required_for_intake":False,
      "existing_production_untouched":True,
      "ready_for_public_website":False,"ready_for_mixer":False,
      "counts":{"NEW_R2":0,"REUSED_R2":0,"DUPLICATE_IN_BATCH":0,
                "SKIPPED_SIZE":0,"INVALID_AUDIO":0,"FAILED":0},
      "new_bytes":0,"packs":{},"errors":[]}
    seen=set()
    try:
        for path,rel,slug,category,provider,creator,original_page in iter_assets(root):
            if report["counts"]["NEW_R2"]>=args.max_files:
                break
            pack=report["packs"].setdefault(slug,{"scanned":0,"new":0,"reused":0,"errors":0})
            pack["scanned"]+=1
            size=path.stat().st_size
            if size<200 or size>args.max_file_mb*1024**2 or report["new_bytes"]+size>args.max_total_mb*1024**2:
                report["counts"]["SKIPPED_SIZE"]+=1
                continue
            try:
                digest=sha256(path)
                if digest in seen:
                    report["counts"]["DUPLICATE_IN_BATCH"]+=1
                    continue
                seen.add(digest)
                try:
                    stream,duration=ffprobe(path)
                except Exception as exc:
                    report["counts"]["INVALID_AUDIO"]+=1
                    report["errors"].append({"file":rel,"error":str(exc)[:140]})
                    continue
                existing=stored.get(digest)
                state="REUSED_R2" if existing else "NEW_R2"
                if existing:
                    info=head(s3,existing)
                    if not info or int(info.get("ContentLength",-1))!=size:
                        raise RuntimeError("R2 previously stored digest length mismatch")
                    pack["reused"]+=1
                    key=existing
                else:
                    ext=path.suffix.lower()
                    key=RAW_ROOT+digest[:2]+"/"+digest+ext
                    with path.open("rb") as handle:
                        s3.put_object(Bucket=BUCKET,Key=key,Body=handle,
                                      ContentLength=size,ContentType=EXTENSIONS[ext],
                                      Metadata={"sha256":digest,"license":"cc0-1.0",
                                                "mirror":"open-game-sfx-index"})
                    checked=head(s3,key)
                    if not checked or int(checked.get("ContentLength",-1))!=size or checked.get("Metadata",{}).get("sha256")!=digest:
                        raise RuntimeError("R2 audio object failed readback")
                    stored[digest]=key
                    pack["new"]+=1
                    report["new_bytes"]+=size
                provenance={
                  "schema_version":2,"audio_sha256":digest,"audio_storage_key":key,
                  "classification_status":"pending","classification_labels":[],
                  "source_pack":slug,"original_extension":path.suffix.lower(),
                  "source_provider":provider,"creator":creator,
                  "source_page":original_page,
                  "license":"CC0-1.0","license_evidence_url":original_page,
                  "mirror_repository":"https://github.com/"+MIRROR_REPO,
                  "mirror_revision":MIRROR_SHA,
                  "mirror_file_url":"https://github.com/"+MIRROR_REPO+"/blob/"+MIRROR_SHA+"/"+rel,
                  "mirror_license_records":"https://github.com/"+MIRROR_REPO+"/blob/"+MIRROR_SHA+"/ATTRIBUTION.md",
                  "original_filename":path.name,"mirror_path":rel,
                  "category_initial":category,"file_bytes":size,"duration_seconds":duration,
                  "codec":stream.get("codec_name"),"channels":stream.get("channels"),
                  "sample_rate_hz":stream.get("sample_rate"),
                  "license_checked_at":now(),
                  "audio_bytes_unchanged_from_mirror":True,
                  "source_not_listened_or_subjectively_reviewed":True,
                  "ready_for_public_website":False,"ready_for_mixer":False
                }
                record_key=write_provenance(s3,digest,provenance)
                report["counts"][state]+=1
                print("ASSET_IN_R2 "+json.dumps(
                    {"state":state,"pack":slug,"file":rel,"key":key,"record":record_key,
                    "bytes":size},ensure_ascii=False),flush=True)
            except Exception as exc:
                pack["errors"]+=1
                report["counts"]["FAILED"]+=1
                report["errors"].append({"file":rel,"error":str(exc)[:220]})
            if pack["scanned"]%75==0:
                print("BATCH_PROGRESS "+json.dumps(
                    {"pack":slug,"scanned":pack["scanned"],
                    "new":report["counts"]["NEW_R2"],
                    "reused":report["counts"]["REUSED_R2"],
                    "bytes":report["new_bytes"],"failed":report["counts"]["FAILED"]}),flush=True)
    finally:
        report.update(status="COMPLETE" if report["counts"]["NEW_R2"]>0 else "NO_NEW_FILES",
                      finished_at=now())
        out=pathlib.Path(args.report)
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        key=ROOT+"runs/"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%f")+".json"
        s3.put_object(Bucket=BUCKET,Key=key,Body=out.read_bytes(),
                      ContentType="application/json",Metadata={"kind":"cc0-harvest-report"})
        assert head(s3,key),"R2 run report not saved"
        print("HARVEST_FINAL "+json.dumps({
            "new":report["counts"]["NEW_R2"],"reused":report["counts"]["REUSED_R2"],
            "duplicate_in_batch":report["counts"]["DUPLICATE_IN_BATCH"],
            "bytes":report["new_bytes"],"errors":len(report["errors"]),
            "packs":report["packs"],"report_key":key}),flush=True)
    if not report["counts"]["NEW_R2"] and not report["counts"]["REUSED_R2"]:
        sys.exit(3)

if __name__=="__main__":
    main()
