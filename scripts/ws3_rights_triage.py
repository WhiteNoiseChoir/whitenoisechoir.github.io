#!/usr/bin/env python3
"""WS3 private, conservative rights/provenance triage for Wikimedia candidate metadata.
Does not fetch or download audio. A license label is never a YouTube clearance.
"""
import collections,datetime,hashlib,html,json,os,re
from urllib.parse import urlsplit,urlunsplit,unquote
import boto3
from botocore.config import Config

ROOT="internal/ws3-sleep-relax-discovery/v1/"
BUCKET="whitenoisechoir-media"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
def normalize(s):
 return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",s or ""))).strip()[:500]
def rights(label,url):
 s=(label+" "+url).lower()
 if re.search(r"cc.by.nc|by-nc|noncommercial|non-commercial|cc.by.nd|by-nd|no.derivatives|all rights reserved|copyrighted|fair use",s):return "RESTRICTED_REVIEW"
 if re.search(r"(^|[^a-z])(?:cc0|public domain|pd-old|pd-us|pdm)([^a-z]|$)",s):return "POTENTIAL_PUBLIC_DOMAIN_REVIEW"
 if re.search(r"cc.by.sa|by-sa|sharealike",s):return "ATTRIBUTION_SHAREALIKE_REVIEW"
 if re.search(r"cc.by|by-4|by-3|attribution",s):return "ATTRIBUTION_REVIEW"
 return "UNKNOWN_RIGHTS"
def getjson(s3,key):
 o=s3.get_object(Bucket=BUCKET,Key=key)
 try:return json.loads(o["Body"].read())
 finally:o["Body"].close()
def main():
 s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",
  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
  config=Config(signature_version="s3v4",retries={"max_attempts":2,"mode":"standard"}))
 summary=getjson(s3,ROOT+"provider-candidates/latest-summary.json")
 key=summary.get("checkpoint_key")
 if not key or not key.startswith(ROOT+"provider-candidates/wikimedia-commons/"):
  raise RuntimeError("No verified WS3 Wikimedia checkpoint")
 report=getjson(s3,key)
 candidates=report.get("candidates",[])
 if len(candidates)!=summary.get("unique_candidates"):raise RuntimeError("Candidate count mismatch")
 seen_ids=set();seen_urls=set();rows=[];counts=collections.Counter()
 for r in candidates:
  source_id=r["source_id"];url=r["source_page"]
  parts=urlsplit(url)
  if parts.scheme!="https" or parts.netloc!="commons.wikimedia.org" or not parts.path.startswith("/wiki/File:"):
   counts["invalid_source_url"]+=1
   continue
  canonical=urlunsplit((parts.scheme,parts.netloc,parts.path,"",""))
  if source_id in seen_ids or canonical in seen_urls:
   counts["duplicate_within_candidate_batch"]+=1
   continue
  seen_ids.add(source_id);seen_urls.add(canonical)
  license_label=normalize(r.get("license_short_name",""))
  license_url=normalize(r.get("license_url",""))
  artist=normalize(r.get("artist_html",""))
  attribution=normalize(r.get("attribution_html",""))
  label=rights(license_label,license_url)
  license_parts=urlsplit(license_url)
  license_url_valid=license_parts.scheme=="https" and bool(license_parts.hostname) and not license_parts.username and not license_parts.password
  if not license_url_valid:
   counts["invalid_or_missing_license_url"]+=1
   label="UNKNOWN_RIGHTS"
  counts[label]+=1
  if not artist and not attribution:counts["missing_attribution"]+=1
  if not license_label or not license_url_valid:counts["incomplete_license_evidence"]+=1
  rows.append({"source_id":source_id,"source_page":canonical,"category":r.get("category"),
   "license_label":license_label,"license_url":license_url,"license_url_syntax_valid":license_url_valid,"artist_text":artist,"attribution_text":attribution,
   "rights_triage":label,"license_verified_for_youtube":False,"has_r2_audio":False,
   "source_page_live_verified":False,"dedup_against_full_index":False,"status":"REQUIRES_SOURCE_AND_RIGHTS_REVIEW"})
 rows.sort(key=lambda x:x["source_id"])
 fingerprint=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 target=ROOT+"rights-triage/wikimedia/"+fingerprint[:24]+".json"
 try:s3.head_object(Bucket=BUCKET,Key=target);reused=True
 except s3.exceptions.ClientError as e:
  if e.response.get("Error",{}).get("Code") not in ("404","NoSuchKey","NotFound"):raise
  reused=False
 if not reused:
  body=json.dumps({"schema":"wnc_ws3_rights_triage_v2","source_checkpoint":key,
    "source_candidates":len(candidates),"rows":rows,"counts":dict(counts),
    "notice":"Metadata triage only. Not proof of copyright, suitability, audio quality or YouTube clearance."},ensure_ascii=False).encode()
  s3.put_object(Bucket=BUCKET,Key=target,Body=body,ContentType="application/json",CacheControl="private,no-store")
  if s3.head_object(Bucket=BUCKET,Key=target)["ContentLength"]!=len(body):raise RuntimeError("R2 HEAD size mismatch")
 summary_out={"schema":"wnc_ws3_rights_triage_summary_v2","checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "source_candidates":len(candidates),"triaged_candidates":len(rows),"counts":dict(counts),
  "triage_checkpoint":target,"checkpoint_reused":reused,"youtube_license_verified":0,
  "source_page_live_verified":0,"dedup_against_full_index":False,"audio_downloads":0,
  "next_stage":"cross_index_dedup_and_source_page_verification"}
 s3.put_object(Bucket=BUCKET,Key=ROOT+"rights-triage/latest-summary.json",
  Body=json.dumps(summary_out).encode(),ContentType="application/json",CacheControl="private,no-store")
 print("WS3_RIGHTS_TRIAGE "+json.dumps({k:v for k,v in summary_out.items() if k!="triage_checkpoint"}))
if __name__=="__main__":main()
