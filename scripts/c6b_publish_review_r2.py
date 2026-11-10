#!/usr/bin/env python3
"""Publish EXACTLY four C6B audition-only MP3s to isolated R2 review/ keys.

This is not production promotion. Reads GitHub Actions artifact from approved run,
pins its two original review-file SHA256s, derives two balanced listen-only copies,
verifies remote SHA256 and HTTP byte-range, and never edits live audio/catalog/SEO.
"""
from __future__ import annotations
import hashlib, json, os, re, subprocess, time
from pathlib import Path
from urllib.request import Request, urlopen
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
BUCKET="whitenoisechoir-media"
PUBLIC="https://media.whitenoisechoir.com"
PREFIX="review/c6b-20261110/"
INPUT=Path("audits/c6b-audition-artifacts")
OUTPUT=Path("audits/c6b-online-audition")
PIN={
 "SND-0039":"4585825b1f4b8c65c3023fe34d29df2b24e8d272fc0978733fbff32ff6300519",
 "SND-0040":"4f1e1129bc044fe771947d478d0a30be7fcba968df590ee0dfe380d080086269",
}
assert os.environ.get("R2_ACCESS_KEY_ID") and os.environ.get("R2_SECRET_ACCESS_KEY"), "Missing bucket-scoped R2 credentials"
client=boto3.session.Session().client(
 "s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",
 aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
 aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
 config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
  retries={"max_attempts":5,"mode":"standard"},
  request_checksum_calculation="when_required",
  response_checksum_validation="when_required",connect_timeout=20,read_timeout=120))
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
 return h.hexdigest()
def exec_cmd(args,timeout=210):
 q=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if q.returncode:raise RuntimeError("Failed "+str(args[:2])+": "+q.stderr[-1100:])
 return q.stdout
def info(p):
 return json.loads(exec_cmd(["ffprobe","-v","error","-show_entries",
  "format=duration,size:stream=codec_name,channels,sample_rate",
  "-of","json",str(p)],90))
def validate_mp3(p,expected_sha=None):
 assert p.is_file() and p.stat().st_size>10_000_000,"Missing or short MP3 "+str(p)
 value=sha(p)
 if expected_sha:assert value==expected_sha,"GitHub artifact has unexpected SHA "+str(p)
 probe=info(p)
 dur=float(probe["format"]["duration"])
 assert 599.5<=dur<=600.6,"Unexpected 10-minute master duration "+str(dur)
 assert any(s.get("codec_name")=="mp3" and s.get("channels")==2 and int(s.get("sample_rate",0))==44100
            for s in probe["streams"]),"Unexpected MP3 codec/layout"
 exec_cmd(["ffmpeg","-hide_banner","-nostdin","-v","error","-xerror",
  "-i",str(p),"-map","0:a:0","-f","null","-"],210)
 return {"bytes":p.stat().st_size,"sha256":value,"duration_seconds":round(dur,3)}
def normalize(src,dst):
 # Preview normalization ONLY: not a substitute for listening or validated final mastering.
 exec_cmd(["ffmpeg","-hide_banner","-nostdin","-v","error","-xerror",
  "-i",str(src),"-map","0:a:0","-af","loudnorm=I=-28:TP=-3.5:LRA=13",
  "-ar","44100","-ac","2","-c:a","libmp3lame","-b:a","192k","-t","600",
  "-y",str(dst)],210)
 return validate_mp3(dst)
def head(key):
 try:return client.head_object(Bucket=BUCKET,Key=key)
 except ClientError as e:
  if str(e.response.get("Error",{}).get("Code")) in ("NoSuchKey","404","NotFound"):return None
  raise
def upload(p,key,detail):
 assert key.startswith(PREFIX) and re.fullmatch(r"review/c6b-20261110/SND-00(?:39|40)-(?:raw|balanced)\.mp3",key),key
 prev=head(key)
 if prev:
  assert int(prev["ContentLength"])==detail["bytes"] and prev.get("Metadata",{}).get("sha256")==detail["sha256"],"Existing remote review object differs"
  state="existing-identical"
 else:
  with p.open("rb") as f:
   client.put_object(Bucket=BUCKET,Key=key,Body=f,ContentLength=detail["bytes"],
    ContentType="audio/mpeg",CacheControl="public, max-age=300",
    Metadata={"sha256":detail["sha256"],"kind":"c6b-unapproved-audition","production":"no"})
  state="review-uploaded"
 metadata=head(key)
 assert metadata and int(metadata["ContentLength"])==detail["bytes"]
 assert metadata.get("Metadata",{}).get("sha256")==detail["sha256"]
 assert metadata.get("ContentType","").split(";")[0]=="audio/mpeg"
 obj=client.get_object(Bucket=BUCKET,Key=key)
 try:
  h=hashlib.sha256()
  for b in obj["Body"].iter_chunks(chunk_size=1048576):
   if b:h.update(b)
 finally:obj["Body"].close()
 assert h.hexdigest()==detail["sha256"],"Remote file is not the validated local MP3"
 return {"key":key,"url":PUBLIC+"/"+key,"status":state,**detail}
def public_range(item,p):
 u=item["url"]
 for attempt in range(4):
  try:
   req=Request(u,headers={"Range":"bytes=0-2047","User-Agent":"WNC-C6B-Audition-Range-QA/1.0"})
   with urlopen(req,timeout=40) as result:
    status=result.status
    content=result.read()
    mime=(result.headers.get("Content-Type") or "").split(";")[0]
   with p.open("rb") as f:expected=f.read(2048)
   assert status==206 and content==expected and mime=="audio/mpeg",f"Bad public transport {status} {mime}"
   return "PASS_HTTP_206_EXACT_BYTES"
  except Exception:
   if attempt==3:raise
   time.sleep(2+attempt*3)
def main():
 assert INPUT.is_dir(),"Download validated GH Actions 42763529255 artifact first"
 ledger=json.loads((INPUT/"audit.json").read_text())
 assert ledger["staged_review_mp3_count"]==2 and ledger["production_mp3_published"]==0
 OUTPUT.mkdir(parents=True,exist_ok=True)
 out=[]
 for id in ("SND-0039","SND-0040"):
  src=INPUT/(id+".mp3")
  original=validate_mp3(src,PIN[id])
  assert any(r.get("record_id")==id and r.get("review_mp3_sha256")==PIN[id] for r in ledger["reports"]),"Artifact report mismatch"
  raw=upload(src,PREFIX+id+"-raw.mp3",original)
  raw["variant"]="raw-public-hq-preview-derivative"
  raw["http_range_qa"]=public_range(raw,src)
  out.append(raw)
  balanced_path=OUTPUT/(id+"-balanced.mp3")
  balanced=normalize(src,balanced_path)
  processed=upload(balanced_path,PREFIX+id+"-balanced.mp3",balanced)
  processed["variant"]="volume-balanced-audition-derivative"
  processed["http_range_qa"]=public_range(processed,balanced_path)
  out.append(processed)
  print("C6B_REVIEW_ONLINE_SOURCE_PASSED",json.dumps({"record_id":id,"raw_sha":original["sha256"],
   "balanced_sha":balanced["sha256"],"raw_url":raw["url"],"balanced_url":processed["url"]}),flush=True)
 assert len(out)==4
 report={
  "phase":"C6B-ONLINE-OWNER-AUDITION-ONLY","source_artifact_run":42763529255,
  "r2_prefix":PREFIX,"media":out,
  "original_authenticated_source_acquired":False,
  "owner_listening_approved":False,
  "comprehensive_acoustic_qa_certified":False,
  "reused_public_freesound_hq_lossy_preview":True,
  "published_to_existing_production_catalog":False,
  "new_indexable_routes":0,"old_production_sources_retained":35,
  "old_presets_retained":45,
  "note":"No file in audio/, audio/continuous/, catalog/library.json or sitemap.xml changed; no approved R2/HLS production key touched."
 }
 (OUTPUT/"online-review-audit.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
 print("C6B_4_ONLINE_AUDITION_OBJECTS_PASS",json.dumps({"items":len(out),"public_range":True,"approval":False}),flush=True)
if __name__=="__main__":main()
