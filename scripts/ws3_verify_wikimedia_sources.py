#!/usr/bin/env python3
"""WS3 Wikimedia source-page verification. Metadata only; not a YouTube license clearance."""
import datetime,hashlib,json,os,time,urllib.parse,urllib.request,urllib.error
import boto3
from botocore.config import Config
ROOT="internal/ws3-sleep-relax-discovery/v1/"
BUCKET="whitenoisechoir-media"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
API="https://commons.wikimedia.org/w/api.php"
def load(s3,key):
 obj=s3.get_object(Bucket=BUCKET,Key=key)
 try:return json.loads(obj["Body"].read())
 finally:obj["Body"].close()
def main():
 s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",retries={"max_attempts":2,"mode":"standard"}))
 prior=load(s3,ROOT+"cross-index-dedup/latest-summary.json")
 if prior.get("schema")!="wnc_ws3_cross_index_dedup_v1":raise RuntimeError("Expected cross-index dedup V1")
 checkpoint=load(s3,prior["checkpoint_key"])
 rows=checkpoint["rows"]
 titles=[]
 for row in rows:
  parsed=urllib.parse.urlsplit(row["source_page"])
  if parsed.scheme!="https" or parsed.hostname!="commons.wikimedia.org" or not parsed.path.startswith("/wiki/File:"):raise RuntimeError("Invalid source page")
  titles.append(urllib.parse.unquote(parsed.path[len("/wiki/"):]).replace("_"," "))
 params={"action":"query","format":"json","prop":"imageinfo","iiprop":"extmetadata|mime|size","titles":"|".join(titles)}
 url=API+"?"+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={"User-Agent":"WhiteNoiseChoir-WS3-MetadataAudit/1.0 (GitHub WhiteNoiseChoir/whitenoisechoir.github.io)","Accept":"application/json"})
 try:
  with urllib.request.urlopen(req,timeout=25) as response:
   if response.status!=200:raise RuntimeError("Provider HTTP "+str(response.status))
   data=json.load(response)
 except urllib.error.HTTPError as exc:
  if exc.code in (403,429):raise RuntimeError("Provider blocked/rate-limited HTTP "+str(exc.code)+"; stop and backoff")
  raise
 pages=data.get("query",{}).get("pages",{})
 by_title={p.get("title",""):p for p in pages.values()}
 results=[]
 for row,title in zip(rows,titles):
  page=by_title.get(title,{})
  info=(page.get("imageinfo") or [{}])[0]
  ext=info.get("extmetadata") or {}
  license_label=str((ext.get("LicenseShortName") or {}).get("value","")).strip()
  license_url=str((ext.get("LicenseUrl") or {}).get("value","")).strip()
  live="missing" not in page and bool(info)
  original_label=row.get("license_label","")
  original_url=row.get("license_url","")
  mismatch=(bool(original_label and license_label and original_label!=license_label) or bool(original_url and license_url and original_url!=license_url))
  results.append({"source_id":row["source_id"],"source_page":row["source_page"],"dedup_status":row["full_index_dedup_status"],"source_page_live_verified":live,"provider_mime":info.get("mime"),"license_label_current":license_label,"license_url_current":license_url,"license_metadata_changed":mismatch,"license_verified_for_youtube":False,"status":"SOURCE_NOT_FOUND" if not live else "LICENSE_METADATA_CHANGED_REVIEW" if mismatch else "SOURCE_METADATA_VERIFIED_RIGHTS_PENDING"})
 summary={"schema":"wnc_ws3_source_verification_v1","checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_candidates":len(rows),"source_page_live_verified":sum(x["source_page_live_verified"] for x in results),"source_page_missing":sum(not x["source_page_live_verified"] for x in results),"license_metadata_changed":sum(x["license_metadata_changed"] for x in results),"exact_duplicates":sum(x["dedup_status"]=="EXACT_MATCH" for x in results),"no_exact_match":sum(x["dedup_status"]=="NO_EXACT_MATCH_IN_COMPARABLE_COLUMNS" for x in results),"youtube_license_verified":0,"audio_downloads":0,"next_stage":"manual_rights_review_and_coverage_gap_prioritization"}
 fingerprint=hashlib.sha256(json.dumps({"parent":prior["checkpoint_key"],"rows":results},sort_keys=True).encode()).hexdigest()
 key=ROOT+"source-verification/"+fingerprint[:24]+".json"
 body=json.dumps({"summary":summary,"rows":results},ensure_ascii=False).encode()
 try:s3.head_object(Bucket=BUCKET,Key=key)
 except s3.exceptions.ClientError as e:
  if e.response.get("Error",{}).get("Code") not in ("404","NoSuchKey","NotFound"):raise
  s3.put_object(Bucket=BUCKET,Key=key,Body=body,ContentType="application/json",CacheControl="private,no-store")
  if s3.head_object(Bucket=BUCKET,Key=key)["ContentLength"]!=len(body):raise RuntimeError("R2 HEAD mismatch")
 summary["checkpoint_key"]=key
 s3.put_object(Bucket=BUCKET,Key=ROOT+"source-verification/latest-summary.json",Body=json.dumps(summary).encode(),ContentType="application/json",CacheControl="private,no-store")
 print("WS3_SOURCE_VERIFICATION "+json.dumps({k:v for k,v in summary.items() if k!="checkpoint_key"}))
if __name__=="__main__":main()
