#!/usr/bin/env python3
"""R2 approved-media migration. Copy only; never modify or delete website data."""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ROOT=Path(__file__).resolve().parents[1]
BUCKET="whitenoisechoir-media"
ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
PUBLIC_BASE="https://media.whitenoisechoir.com"
PILOT_ID="white-noise"
ORIGIN="https://whitenoisechoir.github.io"
SCOPE=os.environ.get("R2_MIGRATION_SCOPE","pilot").strip().lower()
assert SCOPE in ("pilot","full"),"Unrecognized upload scope"
assert os.environ.get("R2_ACCESS_KEY_ID") and os.environ.get("R2_SECRET_ACCESS_KEY"),"Two GitHub R2 S3 secrets are required"
s3=boto3.session.Session().client(
 "s3",region_name="auto",endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",
 aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
 aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
 config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
               retries={"max_attempts":6,"mode":"standard"},
               request_checksum_calculation="when_required",
               response_checksum_validation="when_required",
               connect_timeout=20,read_timeout=120))

def sha256(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1024*1024),b""):
   h.update(block)
 return h.hexdigest()

def mime(p):
 return {".mp3":"audio/mpeg",".m3u8":"application/vnd.apple.mpegurl",".ts":"video/mp2t"}[p.suffix]

def inventory():
 m=json.loads((ROOT/"audio/continuous/manifest.json").read_text(encoding="utf8"))
 rows=m["records"];ids={r["id"] for r in rows}
 assert len(rows)==len(ids)==35 and ids==set(m["applies_to"])
 assert len(json.loads((ROOT/"catalog/library.json").read_text())["sounds"])==35
 selected=[r for r in rows if SCOPE=="full" or r["id"]==PILOT_ID]
 assert len(selected)==(35 if SCOPE=="full" else 1)
 files=[]
 for r in selected:
  ident=r["id"]
  assert re.fullmatch("[a-z0-9-]+",ident)
  master=ROOT/r["master_file"];playlist=ROOT/r["playlist_file"]
  assert master==ROOT/"audio"/(ident+".mp3")
  assert playlist==ROOT/"audio/continuous"/ident/"continuous.m3u8"
  assert master.is_file() and playlist.is_file()
  assert sha256(master)==r["master_sha256"] and sha256(playlist)==r["playlist_sha256"],ident+" SHA mismatch"
  lines=playlist.read_text("utf8").splitlines()
  assert lines[0]=="#EXTM3U" and lines[-1]=="#EXT-X-ENDLIST"
  assert "#EXT-X-PLAYLIST-TYPE:VOD" in lines
  segments=sorted(playlist.parent.glob("part_*.ts"))
  assert len(segments)==r["segment_count_per_source_cycle"],ident
  assert all(re.fullmatch(r"part_\d{3}\.ts",p.name) for p in segments)
  referenced={line.strip() for line in lines if line.strip().endswith(".ts")}
  assert referenced=={p.name for p in segments},ident+" mismatched segment references"
  assert lines.count("#EXT-X-DISCONTINUITY")>=1007
  files.extend([master,playlist,*segments])
 assert len(files)==len(set(files))
 assert all(p.is_file() and p.stat().st_size>0 and not p.is_symlink() and p.is_relative_to(ROOT/"audio") for p in files)
 return files,{"scope":SCOPE,"sources":len(selected),"masters":len(selected),
   "playlists":len(selected),"ts_segments":len(files)-2*len(selected),
   "objects":len(files),"source_bytes":sum(p.stat().st_size for p in files)}

def head(key):
 try: return s3.head_object(Bucket=BUCKET,Key=key)
 except ClientError as exc:
  code=str(exc.response.get("Error",{}).get("Code",""))
  if code in ("404","NoSuchKey","NotFound"):return None
  raise

def copy_and_verify(p):
 key=p.relative_to(ROOT).as_posix()
 digest=sha256(p);size=p.stat().st_size;content_type=mime(p)
 old=head(key)
 if old is None:
  with p.open("rb") as file:
   s3.put_object(Bucket=BUCKET,Key=key,Body=file,ContentLength=size,ContentType=content_type,
     CacheControl="public, max-age=300",
     Metadata={"sha256":digest,"origin":"whitenoisechoir-approved-github"})
  status="uploaded"
 else:
  assert int(old["ContentLength"])==size,"BLOCK existing size mismatch "+key
  assert old.get("Metadata",{}).get("sha256")==digest,"BLOCK existing SHA mismatch "+key
  assert old.get("ContentType","").split(";")[0]==content_type,"BLOCK existing MIME mismatch "+key
  status="reused"
 h=head(key)
 assert h and int(h["ContentLength"])==size and h.get("Metadata",{}).get("sha256")==digest
 assert h.get("ContentType","").split(";")[0]==content_type
 obj=s3.get_object(Bucket=BUCKET,Key=key)
 body=obj["Body"];remote=hashlib.sha256();actual=0
 try:
  for chunk in body.iter_chunks(chunk_size=1024*1024):
   if chunk:remote.update(chunk);actual+=len(chunk)
 finally:body.close()
 assert actual==size and remote.hexdigest()==digest,"REMOTE CORRUPTION "+key
 return {"key":key,"bytes":size,"status":status}

def public_check(p):
 key=p.relative_to(ROOT).as_posix()
 req=Request(PUBLIC_BASE+"/"+key,headers={"Range":"bytes=0-2047",
                  "Origin":ORIGIN,"User-Agent":"WhiteNoiseChoir-R2-Audit/1.0"})
 with urlopen(req,timeout=40) as response:
  code=response.status;data=response.read();hdr=dict(response.headers.items())
 assert code==206,"Public byte Range expected 206, got "+str(code)+" for "+key
 with p.open("rb") as file:expected=file.read(2048)
 assert data==expected,"Public byte Range content mismatch "+key
 assert hdr.get("Content-Type","").split(";")[0]==mime(p),"Public Content-Type invalid "+key
 print("R2_PUBLIC_RANGE_PASS",json.dumps({"key":key,"http":code,
        "verified_bytes":len(data),"cors_allow_origin":
        hdr.get("Access-Control-Allow-Origin") or "NOT_SET_CONFIGURE_BUCKET_CORS"}),flush=True)

def main():
 files,report=inventory()
 print("R2_MIGRATION_START",json.dumps(report),flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
  results=list(pool.map(copy_and_verify,files))
 report["uploaded"]=sum(x["status"]=="uploaded" for x in results)
 report["reused"]=sum(x["status"]=="reused" for x in results)
 report["verified_objects"]=len(results)
 report["verified_bytes"]=sum(x["bytes"] for x in results)
 assert report["verified_bytes"]==report["source_bytes"]
 for ident in ([PILOT_ID] if SCOPE=="pilot" else [PILOT_ID,"crashing-ocean-real"]):
  base=ROOT/"audio/continuous"/ident
  chosen=[ROOT/"audio"/(ident+".mp3"),base/"continuous.m3u8"]
  seg=sorted(base.glob("part_*.ts"))
  assert seg
  chosen.extend([seg[0],seg[-1]])
  for p in chosen:public_check(p)
 print("R2_MIGRATION_PASS",json.dumps(report,sort_keys=True),flush=True)
 print("SAFE: Production player, all source files, SEO, GitHub Pages and original HLS remain untouched. "
       "CORS and actual iPhone listening still require separate verification.",flush=True)

if __name__=="__main__":main()
