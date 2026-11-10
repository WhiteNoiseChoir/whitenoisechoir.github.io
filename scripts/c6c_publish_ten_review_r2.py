#!/usr/bin/env python3
"""C6C: upload ONLY 10 distinct 600-second synthetic review MP3s and noindex HTML.

Immutable key prefix review/c6c-20261110/; all production keys and release ledgers
are untouched. Upload HTML last only after all 10 remote sound objects pass QA.
"""
from __future__ import annotations
import concurrent.futures,hashlib,json,os,re,time
from pathlib import Path
from urllib.request import Request,urlopen
from botocore.config import Config
from botocore.exceptions import ClientError
import boto3

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/"catalog/c6c-ten-synthetic-review.json").read_text())
RENDER=json.loads((ROOT/"audits/c6c-original-render/audit.json").read_text())
OUT=ROOT/"audits/c6c-live-review"
PAGE=ROOT/"signature/c6c-online-review/index.html"
AUDIO_ROOT=ROOT/"audits/c6c-original-render"
PREFIX="review/c6c-20261110/"
BUCKET="whitenoisechoir-media"
ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
PUBLIC="https://media.whitenoisechoir.com/"
assert os.environ.get("R2_ACCESS_KEY_ID") and os.environ.get("R2_SECRET_ACCESS_KEY")
s3=boto3.session.Session().client(
 "s3",region_name="auto",
 endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",
 aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
 aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
 config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
  retries={"max_attempts":5,"mode":"standard"},
  request_checksum_calculation="when_required",
  response_checksum_validation="when_required",connect_timeout=20,read_timeout=140))

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()

def head(key):
 try:return s3.head_object(Bucket=BUCKET,Key=key)
 except ClientError as e:
  if str(e.response.get("Error",{}).get("Code","")) in ("404","NoSuchKey","NotFound"):return None
  raise

def put_immutable(key,path,mime,expected,cache):
 assert key.startswith(PREFIX) and key.count("/") == 2,key
 assert path.is_file()
 n=path.stat().st_size
 assert sha(path)==expected,"Refusing local SHA mismatch "+key
 previous=head(key)
 if previous:
  assert previous.get("Metadata",{}).get("sha256")==expected, "Refusing overwrite of different existing R2 review item "+key
  assert int(previous["ContentLength"])==n,"Size mismatch for existing "+key
  action="already-exists-identical"
 else:
  with path.open("rb") as f:
   s3.put_object(Bucket=BUCKET,Key=key,Body=f,ContentLength=n,
    ContentType=mime,CacheControl=cache,
    Metadata={"sha256":expected,"kind":"c6c-original-synthetic-audition","release":"no"})
  action="uploaded-review-only"
 state=head(key)
 assert state and int(state["ContentLength"])==n
 assert state.get("Metadata",{}).get("sha256")==expected
 assert state.get("ContentType","").split(";")[0]==mime.split(";")[0]
 remote=s3.get_object(Bucket=BUCKET,Key=key)
 try:
  digest=hashlib.sha256()
  for block in remote["Body"].iter_chunks(chunk_size=1048576):
   if block:digest.update(block)
 finally:remote["Body"].close()
 assert digest.hexdigest()==expected, "REMOTE_SHA_MISMATCH "+key
 return {"key":key,"url":PUBLIC+key,"bytes":n,"sha256":expected,"action":action}

def public_check(item,path,mime):
 url=item["url"]+"?h="+item["sha256"][:12]
 for retry in range(4):
  try:
   if mime=="audio/mpeg":
    request=Request(url,headers={"Range":"bytes=0-2047","User-Agent":"WNC-C6C-Public-Range/1.0"})
    with urlopen(request,timeout=35) as f:
     status=f.status;data=f.read();typecheck=f.headers.get("Content-Type","").split(";")[0]
    with path.open("rb") as f:expect=f.read(2048)
    assert status==206 and data==expect and typecheck=="audio/mpeg",("public range",item["key"],status,typecheck)
    return "HTTP_206_BYTE_RANGE_PASS"
   else:
    request=Request(url,headers={"Cache-Control":"no-cache","User-Agent":"WNC-C6C-Public-HTML/1.0"})
    with urlopen(request,timeout=40) as f:
     status=f.status;content=f.read();ctype=f.headers.get("Content-Type","").split(";")[0]
    assert status==200 and ctype=="text/html" and hashlib.sha256(content).hexdigest()==item["sha256"]
    return "HTTP_200_EXACT_HTML_SHA_PASS"
  except Exception:
   if retry==3:raise
   time.sleep(2+retry*2)

def upload_audio(entry):
 ident=entry["record_id"]
 assert re.fullmatch(r"SND-[0-9]{4}",ident)
 path=AUDIO_ROOT/(ident+".mp3")
 assert entry["full_mp3_decode"]=="PASS"
 assert entry["rendered_independent_seconds"]==600
 assert entry["source_kind"]=="original_procedural_DSP"
 assert entry["source_is_sample_loop"] is False
 assert entry["owner_listening_approved"] is False
 assert path.stat().st_size==entry["bytes"]
 key=PREFIX+ident+".mp3"
 uploaded=put_immutable(key,path,"audio/mpeg",entry["sha256"],"public, max-age=300")
 uploaded["http_check"]=public_check(uploaded,path,"audio/mpeg")
 uploaded["record_id"]=ident
 print("C6C_REVIEW_AUDIO_LIVE_PASS",json.dumps(uploaded,sort_keys=True),flush=True)
 return uploaded

def main():
 expected={row["id"] for row in MANIFEST["items"]}
 actual={row["record_id"] for row in RENDER["items"]}
 assert len(expected)==len(actual)==10 and expected==actual
 assert RENDER["rendered_count"]==10
 assert RENDER["new_production_mp3"]==0 and RENDER["owner_approval"] is False
 assert len({row["sha256"] for row in RENDER["items"]})==10
 html=PAGE.read_text(encoding="utf8")
 assert '<meta name="robots" content="noindex,nofollow,noarchive">' in html
 assert '<audio id="audio" controls loop preload="metadata"' in html
 assert '<input id="loop" type="checkbox" checked>' in html
 assert 'application/ld+json' not in html and 'rel="canonical"' not in html
 for ident in expected:assert '<option value="'+ident+'">' in html
 OUT.mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  media=list(pool.map(upload_audio,RENDER["items"]))
 assert len(media)==10 and all(x["http_check"]=="HTTP_206_BYTE_RANGE_PASS" for x in media)
 assert len(set(x["sha256"] for x in media))==10
 # Put the webpage last: no publicly advertised links until all 10 are verified.
 page_key=PREFIX+"index.html"
 page_file=PAGE
 page=put_immutable(page_key,page_file,"text/html; charset=utf-8",sha(page_file),"public, max-age=120, must-revalidate")
 page["http_check"]=public_check(page,page_file,"text/html")
 assert page["http_check"]=="HTTP_200_EXACT_HTML_SHA_PASS"
 report={
  "phase":"C6C_10_UNAPPROVED_ORIGINAL_SYNTH_ONLINE_AUDITION",
  "all_ten_media_verified":True,"num_audition_sources":10,
  "media":media,"review_page":page,
  "sha_validation":True,"source_kind":"original_independent_DSP_no_external_samples",
  "public_on_R2_review_only":True,"owner_listening_approved":False,
  "production_sources_unchanged":35,"presets_unchanged":45,
  "seo_indexing_enabled":False,"new_sitemap_urls":0,
  "no_approval_or_production_release":True
 }
 (OUT/"audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
 print("C6C_TEN_NEW_ORIGINAL_600S_SYNTH_SOUNDS_LIVE_REVIEW_PASS",json.dumps({
  "url":page["url"],"verified_media":len(media),"owner_approved":False
 }),flush=True)

if __name__=="__main__":main()
