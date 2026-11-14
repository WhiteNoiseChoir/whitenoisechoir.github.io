#!/usr/bin/env python3
"""Publish R2 sidecar metadata ONLY to WhiteNoiseChoir/wnc-metadata-index (PRIVATE).
No audio uploads, no printed metadata, no public repo commits of index files.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit, urlunsplit

BUCKET = "whitenoisechoir-media"
ENDPOINT = "https://7483501ad8365fe26b0448b96b54fb9f.r2.cloudflarestorage.com"
DEST = "WhiteNoiseChoir/wnc-metadata-index"
AUDIO_PREFIXES = ("asset-library/commons/sha256/","asset-library/raw/sha256/","asset-library/kenney/sha256/","asset-library/cc0-github-mirror/sha256/")
SIDECARS = ("asset-library/records/sha256/","asset-library/commons/records/","asset-library/kenney/records/","asset-library/cc0-github-mirror/records/")
AUDIO = re.compile(r"/([0-9a-f]{64})\.[a-z0-9]+$",re.I)
JSON_FILE = re.compile(r"/([0-9a-f]{64})\.json$",re.I)
PART_SIZE = 250
MAX_JSON_BYTES = 200000

def clean(value, limit=200):
    if value is None: return ""
    if isinstance(value,dict):value=list(value.values())
    if isinstance(value,(list,tuple)):value=" ".join(clean(v,80) for v in value)
    return " ".join(str(value).split())[:limit]

def safe_url(value):
    try:
        p=urlsplit(clean(value,1100))
        if p.scheme!="https" or not p.hostname or p.username or p.password:return ""
        return urlunsplit((p.scheme,p.netloc,p.path,"",""))[:650]
    except ValueError:return ""

def group_name(value):
    return re.sub(r"[^a-z0-9-]+","-",clean(value or "unclassified",60).lower()).strip("-") or "unclassified"

def objects(s3,prefixes):
    paginator=s3.get_paginator("list_objects_v2")
    for prefix in prefixes:
        for page in paginator.paginate(Bucket=BUCKET,Prefix=prefix):
            yield from page.get("Contents",[])

def make_row(rec,digest,audio_index):
    if not isinstance(rec,dict):return None
    if clean(rec.get("audio_sha256")).lower()!=digest:return None
    media=audio_index.get(digest,[])
    prefer=clean(rec.get("audio_storage_key"),500)
    found=next((x for x in media if x["key"]==prefer),None)
    if not found and media:found=sorted(media,key=lambda x:x["key"])[0]
    try:
        duration=float(rec.get("duration_seconds") or rec.get("duration") or 0)
        if duration<=0 or duration>604800:duration=None
    except (TypeError,ValueError):duration=None
    lic=clean(rec.get("license"),40)
    group=group_name(rec.get("group_hint") or rec.get("category_initial") or rec.get("taxonomy_query_category") or rec.get("iconic_taxon"))
    return {"id":("r2-" if found else "candidate-")+digest,
        "sha256":digest,"title":clean(rec.get("title") or rec.get("file_title") or rec.get("original_filename"),160),
        "group":group,
        "tags":clean([rec.get("scientific_name"),rec.get("source_tags"),rec.get("group_hint"),rec.get("discovery_hint"),rec.get("iconic_taxon")],350),
        "provider":clean(rec.get("source_provider"),70),
        "source":safe_url(rec.get("source_page") or rec.get("license_evidence_url")),
        "license":lic,"license_url":safe_url(rec.get("license_url")),
        "creator":clean(rec.get("attribution") or rec.get("creator") or rec.get("uploader"),120),
        "duration_s":round(duration,3) if duration else None,
        "r2_key":found["key"] if found else None,
        "bytes":found["bytes"] if found else None,
        "availability":"R2_OBJECT_LISTED" if found else "METADATA_ONLY",
        "rights":"LICENSE_DECLARED_REVIEW" if lic.upper() in ("CC0","CC0-1.0","PUBLIC DOMAIN","PUBLIC-DOMAIN","CC-BY-3.0","CC-BY-4.0") else "NEEDS_RIGHTS_REVIEW",
        "playback":"NOT_VERIFIED_BY_INDEX"}

def build(s3,root):
    media=defaultdict(list)
    for obj in objects(s3,AUDIO_PREFIXES):
        m=AUDIO.search(obj["Key"])
        if m and obj["Size"]>0:media[m[1].lower()].append({"key":obj["Key"],"bytes":int(obj["Size"])})
    files=[(m[1].lower(),o["Key"]) for o in objects(s3,SIDECARS)
           if o["Size"]>0 and o["Size"]<=MAX_JSON_BYTES
           if (m:=JSON_FILE.search(o["Key"]))]
    def fetch(pair):
        d,key=pair
        try:
            b=s3.get_object(Bucket=BUCKET,Key=key)["Body"].read(MAX_JSON_BYTES+1)
            if len(b)>MAX_JSON_BYTES:return None
            return make_row(json.loads(b),d,media)
        except Exception:return None
    rows={}
    with ThreadPoolExecutor(max_workers=16) as pool:
        for row in pool.map(fetch,files):
            if not row:continue
            old=rows.get(row["sha256"])
            if old is None or (old["availability"]!="R2_OBJECT_LISTED" and row["availability"]=="R2_OBJECT_LISTED"):
                rows[row["sha256"]]=row
    if len(rows)<100:raise RuntimeError("Unexpectedly empty index; existing snapshot preserved")
    grouped=defaultdict(list)
    for row in rows.values():grouped[row["group"]].append(row)
    index=Path(root)/"index"
    index.mkdir(parents=True,exist_ok=True)
    groups=[]
    for label,data in sorted(grouped.items()):
        data.sort(key=lambda x:(x["title"].lower(),x["sha256"]))
        paths=[]
        for start in range(0,len(data),PART_SIZE):
            rel=f"groups/{label}/part-{start//PART_SIZE+1:03d}.jsonl"
            out=index/rel
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text("".join(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n" for x in data[start:start+PART_SIZE]),encoding="utf-8")
            paths.append("index/"+rel)
        groups.append({"group":label,"count":len(data),"files":paths})
    manifest={"schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "source":"R2 sidecar records","r2_unique_sha_object_names":len(media),
      "r2_sidecars_scanned":len(files),"index_unique_records":len(rows),
      "availability":dict(Counter(x["availability"] for x in rows.values())),
      "rights":dict(Counter(x["rights"] for x in rows.values())),
      "caution":"R2_OBJECT_LISTED is not checksum verified, browser ready, or licensed for publication.",
      "groups":groups}
    (index/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (Path(root)/"README.md").write_text(
      "# WhiteNoiseChoir AI metadata index (PRIVATE)\n\n"
      "Generated from R2 sidecars, no audio bytes. Start with index/manifest.json, then open group JSONL files.\n"
      "Metadata-only means no verified audio object. Listed R2 does NOT mean browser-ready.\n"
      "Never change this repository's visibility to public. Never include tokens or signed media URLs.\n",encoding="utf-8")
    return manifest

def git(args,cwd,env):
    r=subprocess.run(["git",*args],cwd=cwd,env=env,text=True,capture_output=True,timeout=240)
    if r.returncode:raise RuntimeError("Private GitHub repository sync failed; verify token, repository and branch permissions")
    return r.stdout.strip()

def snapshot_unchanged(source_dir, target_dir):
    """Skip unchanged index snapshots while ignoring only generated timestamps."""
    import filecmp
    source_dir=Path(source_dir)
    target_dir=Path(target_dir)
    if not source_dir.is_dir() or not target_dir.is_dir():return False
    left={str(p.relative_to(source_dir)):p for p in source_dir.rglob("*") if p.is_file()}
    right={str(p.relative_to(target_dir)):p for p in target_dir.rglob("*") if p.is_file()}
    if left.keys()!=right.keys() or "manifest.json" not in left:return False
    for key in left:
        if key=="manifest.json":continue
        if not filecmp.cmp(left[key],right[key],shallow=False):return False
    try:
        a=json.loads(left["manifest.json"].read_text())
        b=json.loads(right["manifest.json"].read_text())
    except (OSError,ValueError):return False
    for record in (a,b):
        record.pop("generated_utc",None)
        record.pop("generated_at_utc",None)
    return a==b

def publish(stage,token):
    import requests
    res=requests.get("https://api.github.com/repos/"+DEST,
        headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json"},timeout=30)
    if res.status_code!=200:raise RuntimeError("Private target repo not found or no token access")
    info=res.json()
    if not info.get("private") or info.get("full_name","").lower()!=DEST.lower():
        raise RuntimeError("SAFETY BLOCK: target must be the expected PRIVATE repository")
    branch=info["default_branch"]
    with tempfile.TemporaryDirectory() as d:
        ask=Path(d)/"askpass.sh"
        ask.write_text('#!/bin/sh\ncase "$1" in *Username*) echo x-access-token;; *) echo "$WNC_METADATA_REPO_TOKEN";; esac\n')
        ask.chmod(0o700)
        env={**os.environ,"GIT_ASKPASS":str(ask),"GIT_TERMINAL_PROMPT":"0","WNC_METADATA_REPO_TOKEN":token}
        dest=Path(d)/"repo"
        git(["clone","--quiet","--depth=1","--branch",branch,"https://github.com/"+DEST+".git",str(dest)],None,env)
        index=dest/"index"
        if index.is_symlink():raise RuntimeError("Unsafe symlink")
        if snapshot_unchanged(Path(stage)/"index",index):return False
        if index.exists():shutil.rmtree(index)
        shutil.copytree(Path(stage)/"index",index)
        shutil.copy2(Path(stage)/"README.md",dest/"README.md")
        git(["config","user.name","WhiteNoiseChoir Metadata Bot"],dest,env)
        git(["config","user.email","metadata-bot@users.noreply.github.com"],dest,env)
        git(["add","index","README.md"],dest,env)
        diff=subprocess.run(["git","diff","--cached","--quiet"],cwd=dest,env=env).returncode
        if diff not in (0,1):raise RuntimeError("Unable to check staged changes")
        if diff==1:
            git(["commit","--quiet","-m","Sync R2 metadata private index"],dest,env)
            git(["push","--quiet","origin",branch],dest,env)
        return diff==1

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--local-only",action="store_true")
    args=parser.parse_args()
    import boto3
    from botocore.config import Config
    token=os.getenv("WNC_METADATA_REPO_TOKEN","")
    if not args.local_only:
        if not token:raise RuntimeError("WNC_METADATA_REPO_TOKEN not configured. Nothing was uploaded.")
        # Fail closed before touching bulk R2 data.
        import requests
        r=requests.get("https://api.github.com/repos/"+DEST,headers={"Authorization":"Bearer "+token},timeout=25)
        if r.status_code!=200 or not r.json().get("private"):raise RuntimeError("Private repository/token check failed")
    s3=boto3.client("s3",region_name="auto",endpoint_url=ENDPOINT,
      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
      config=Config(signature_version="s3v4",s3={"addressing_style":"path"},retries={"max_attempts":5,"mode":"standard"}))
    with tempfile.TemporaryDirectory() as tmp:
        info=build(s3,tmp)
        if args.local_only:
            print("METADATA_INDEX_LOCAL_OK",json.dumps({"rows":info["index_unique_records"],"groups":len(info["groups"])}))
            return
        changed=publish(tmp,token)
        print("METADATA_INDEX_PRIVATE_SYNC_OK",json.dumps({"rows":info["index_unique_records"],"groups":len(info["groups"]),"updated":changed}))

if __name__=="__main__":main()
