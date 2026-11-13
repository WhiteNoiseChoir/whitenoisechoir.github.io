#!/usr/bin/env python3
"""WS3 bounded Wikimedia Commons metadata discovery; no audio download.
Private R2 candidate records only. Respect provider 429/403; stop without retry storms.
"""
import datetime, hashlib, json, os, urllib.parse, urllib.request, urllib.error
import boto3
from botocore.config import Config

ROOT="internal/ws3-sleep-relax-discovery/v1/"
BUCKET="whitenoisechoir-media"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
API="https://commons.wikimedia.org/w/api.php"
QUERIES={
 "continuous_beds":["field recording rain ambience","stream water sound","ocean waves sound"],
 "weather_material":["rain on roof sound","rain on leaves sound"],
 "cozy_interiors":["fireplace crackling sound","electric fan sound"],
}
def get_json(url):
 req=urllib.request.Request(url,headers={"User-Agent":"WhiteNoiseChoirMetadataDiscovery/1.0 (noncommercial metadata indexing; contact via github.com/WhiteNoiseChoir/whitenoisechoir.github.io)","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=25) as response:
  return json.load(response)
def s3():
 return boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",retries={"max_attempts":2,"mode":"standard"}))
def main():
 client=s3()
 # WS3 must have a completed coverage baseline before discovering.
 checkpoint=json.loads(client.get_object(Bucket=BUCKET,Key=ROOT+"current.json")["Body"].read())
 if checkpoint.get("next_stage")!="provider_metadata_gap_discovery":raise RuntimeError("Coverage checkpoint not ready")
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
 results={};calls=0;blocked=None;audio_hits=0;duplicate_hits=0
 for category,queries in QUERIES.items():
  for term in queries:
   params={"action":"query","generator":"search","gsrsearch":'filetype:audio '+term,"gsrnamespace":"6","gsrlimit":"12","prop":"imageinfo","iiprop":"extmetadata|mime|size|url","iiextmetadatalanguage":"en","format":"json","formatversion":"2"}
   try:data=get_json(API+"?"+urllib.parse.urlencode(params));calls+=1
   except urllib.error.HTTPError as exc:
    if exc.code in (403,429):blocked=f"provider_http_{exc.code}";break
    blocked=f"provider_http_{exc.code}";break
   except (TimeoutError,urllib.error.URLError,ValueError) as exc:
    blocked="provider_transient_error";break
   for page in data.get("query",{}).get("pages",[]):
    info=(page.get("imageinfo") or [{}])[0]
    if not str(info.get("mime","")).startswith("audio/"):continue
    audio_hits+=1
    ext=info.get("extmetadata") or {}
    def field(k):
     value=ext.get(k,{})
     return value.get("value","") if isinstance(value,dict) else ""
    pageid=page.get("pageid")
    if not isinstance(pageid,int):continue
    identity="wikimedia-commons:"+str(pageid)
    if identity in results:
     duplicate_hits+=1
     continue
    url="https://commons.wikimedia.org/wiki/"+urllib.parse.quote(page.get("title","").replace(" ","_"),safe="():_")
    results[identity]={"source_id":identity,"provider":"wikimedia_commons","source_page":url,"title":page.get("title"),
     "mime":info.get("mime"),"size_bytes":info.get("size"),"category":category,
     "query_term":term,"license_short_name":field("LicenseShortName"),"license_url":field("LicenseUrl"),
     "artist_html":field("Artist"),"attribution_html":field("Attribution"),
     "license_verified_for_youtube":False,"has_r2_audio":False,
     "status":"CANDIDATE_UNVERIFIED","retrieved_at":stamp}
  if blocked:break
 # Avoid writing a new version on exact duplicate results. No public artifacts with private metadata.
 keys=sorted(results)
 fingerprint=hashlib.sha256(json.dumps([{k:v for k,v in results[x].items() if k!="retrieved_at"} for x in keys],sort_keys=True).encode()).hexdigest()
 target=ROOT+"provider-candidates/wikimedia-commons/"+fingerprint[:24]+".json"
 report={"schema":"wnc_ws3_provider_candidates_v1","provider":"wikimedia_commons","source":"Wikimedia Commons MediaWiki API",
  "retrieved_at":stamp,"queries_attempted":calls,"unique_candidates":len(results),"audio_hits":audio_hits,"dedup_within_batch":duplicate_hits,
  "provider_blocker":blocked,"metadata_only":True,"audio_downloads":0,"license_verified_for_youtube":False,
  "baseline_coverage_version":checkpoint["version"],"candidates":[results[k] for k in keys]}
 # Avoid re-uploading identical candidate content on repeat scheduled runs.
 already_present=False
 if results:
  try:
   client.head_object(Bucket=BUCKET,Key=target)
   already_present=True
  except client.exceptions.ClientError as exc:
   if exc.response.get("ResponseMetadata",{}).get("HTTPStatusCode")!=404 and exc.response.get("Error",{}).get("Code") not in ("404","NoSuchKey","NotFound"):
    raise
 if results and not already_present:
  client.put_object(Bucket=BUCKET,Key=target,Body=json.dumps(report,ensure_ascii=False).encode(),ContentType="application/json",CacheControl="private,no-store")
  client.head_object(Bucket=BUCKET,Key=target)
 summary={k:v for k,v in report.items() if k!="candidates"}
 summary["candidate_sha256"]=fingerprint
 summary["checkpoint_key"]=target if results else None
 client.put_object(Bucket=BUCKET,Key=ROOT+"provider-candidates/latest-summary.json",Body=json.dumps(summary).encode(),ContentType="application/json",CacheControl="private,no-store")
 print("WS3_PROVIDER_DISCOVERY "+json.dumps({"queries_attempted":calls,"unique_candidates":len(results),
  "provider_blocker":blocked,"checkpoint_written":bool(results),"reused_existing_checkpoint":already_present,"audio_hits":audio_hits,"duplicate_hits":duplicate_hits,"audio_downloads":0,"license_verified_for_youtube":False}))
if __name__=="__main__":main()
