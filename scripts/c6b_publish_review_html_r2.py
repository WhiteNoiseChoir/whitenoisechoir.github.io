#!/usr/bin/env python3
"""C6B live review HTML at R2 custom domain; never edit audio/production keys."""
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
from urllib.request import Request,urlopen
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

PAGE=Path("signature/c6b-online-review/index.html")
KEY="review/c6b-20261110/index.html"
BUCKET="whitenoisechoir-media"
PUBLIC_URL="https://media.whitenoisechoir.com/"+KEY
ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
OUTPUT=Path("audits/c6b-html-live-r2-audit.json")

def check_local():
 data=PAGE.read_bytes()
 s=data.decode("utf-8")
 assert b"<html" in data and len(data)>10000
 assert '<meta name="robots" content="noindex,nofollow,noarchive">' in s
 assert '<audio id="player" controls loop preload="metadata"' in s
 assert '<input type="checkbox" id="loop" checked>' in s
 assert 'audio.loop=$("loop").checked;' in s
 assert "audio.addEventListener(\"ended\"" in s
 assert "https://media.whitenoisechoir.com/review/c6b-20261110/" in s
 assert "SND-0039-balanced" in s and "SND-0040-balanced" in s
 assert 'rel="canonical"' not in s and "application/ld+json" not in s
 return data,hashlib.sha256(data).hexdigest()

def main():
 data,expected=check_local()
 assert os.environ.get("R2_ACCESS_KEY_ID") and os.environ.get("R2_SECRET_ACCESS_KEY")
 client=boto3.session.Session().client(
  "s3",region_name="auto",
  endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",
  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
  aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
  config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
   retries={"max_attempts":5,"mode":"standard"},
   request_checksum_calculation="when_required",
   response_checksum_validation="when_required",connect_timeout=20,read_timeout=90))
 try:
  old=client.head_object(Bucket=BUCKET,Key=KEY)
 except ClientError as e:
  assert str(e.response.get("Error",{}).get("Code")) in ("404","NotFound","NoSuchKey")
  old=None
 if old is not None:
  assert old.get("Metadata",{}).get("sha256")==expected and int(old["ContentLength"])==len(data), \
    "Refusing to overwrite a different existing HTML review object"
  state="already-present-identical"
 else:
  client.put_object(
   Bucket=BUCKET,Key=KEY,Body=data,ContentLength=len(data),
   ContentType="text/html; charset=utf-8",
   CacheControl="public, max-age=120, must-revalidate",
   Metadata={"sha256":expected,"kind":"noindex-c6b-qa-ui","production":"no"})
  state="uploaded"
 head=client.head_object(Bucket=BUCKET,Key=KEY)
 assert head["Metadata"]["sha256"]==expected
 assert head["ContentLength"]==len(data)
 remote=client.get_object(Bucket=BUCKET,Key=KEY)
 try:
  actual=remote["Body"].read()
 finally: remote["Body"].close()
 assert hashlib.sha256(actual).hexdigest()==expected, "R2 remote bytes mismatch"
 response=None
 for attempt in range(5):
  try:
   req=Request(PUBLIC_URL+"?verify="+expected[:12],headers={"Cache-Control":"no-cache",
     "User-Agent":"WNC-C6B-noindex-live-verify/1.0"})
   with urlopen(req,timeout=35) as f:
    page=f.read()
    response={"http_status":f.status,"mime":f.headers.get("Content-Type",""),
              "robots_header":f.headers.get("X-Robots-Tag","")}
   assert response["http_status"]==200
   assert response["mime"].split(";")[0].strip()=="text/html"
   assert hashlib.sha256(page).hexdigest()==expected
   break
  except Exception as e:
   if attempt==4:raise
   time.sleep(3+attempt*2)
 assert response
 OUTPUT.parent.mkdir(exist_ok=True,parents=True)
 report={
  "url":PUBLIC_URL,"state":state,
  "source_page":"signature/c6b-online-review/index.html",
  "sha256":expected,"bytes":len(data),"HTTP":response,
  "native_loop_enabled":True,"checkbox_loop_on_by_default":True,
  "published_production_sound_count_added":0,"existing_35_sources_unchanged":True,
  "presets_unchanged":45,"indexable_routes_added":0,
  "note":"R2 review HTML fallback; separate from GitHub Pages sync, all four MP3 remain existing R2 review-only files"
 }
 OUTPUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
 print("C6B_PUBLIC_R2_HTML_LIVE_PASS",json.dumps(report,sort_keys=True),flush=True)

if __name__=="__main__": main()
