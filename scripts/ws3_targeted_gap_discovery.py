#!/usr/bin/env python3
"""WS3 targeted discovery of five zero-lexical gaps; metadata only, private R2."""
import datetime,hashlib,json,os,urllib.parse,urllib.request,urllib.error
import boto3
from botocore.config import Config
ROOT="internal/ws3-sleep-relax-discovery/v1/"
BUCKET="whitenoisechoir-media"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
API="https://commons.wikimedia.org/w/api.php"
TERMS={
 "rain_on_roof":["rain hitting roof sound","rain on metal roof audio"],
 "rain_on_window":["rain on window sound","raindrops glass window sound"],
 "wind_in_pines":["wind pine trees sound","wind through conifers audio"],
 "air_conditioner":["air conditioner hum sound","air conditioning unit noise"],
 "cabin":["wooden cabin ambience sound","cabin room tone sound"],
}
def main():
 s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",retries={"max_attempts":2,"mode":"standard"}))
 p=json.loads(s3.get_object(Bucket=BUCKET,Key=ROOT+"gap-priority/latest-summary.json")["Body"].read())
 if p.get("schema")!="wnc_ws3_gap_priority_v1" or p.get("indexed_total")!=22239:raise ValueError("Baseline changed; do not crawl")
 wanted={r["sound_identity"] for r in p["top_priorities"] if r["gap"]=="NO_LEXICAL_CANDIDATE"}
 if not wanted.intersection(TERMS):raise ValueError("Priority queue changed; nothing to target")
 rows={};attempts=0;hits=0;duplicates=0;blocker=None
 for identity,terms in TERMS.items():
  if identity not in wanted:continue
  for term in terms:
   params={"action":"query","generator":"search","gsrsearch":"filetype:audio "+term,"gsrnamespace":"6","gsrlimit":"15","prop":"imageinfo","iiprop":"extmetadata|mime|size","iiextmetadatalanguage":"en","format":"json","formatversion":"2"}
   req=urllib.request.Request(API+"?"+urllib.parse.urlencode(params),headers={"User-Agent":"WhiteNoiseChoirMetadataDiscovery/1.0 (metadata-only; contact github.com/WhiteNoiseChoir/whitenoisechoir.github.io)","Accept":"application/json"})
   try:
    with urllib.request.urlopen(req,timeout=25) as response:data=json.load(response)
    attempts+=1
   except urllib.error.HTTPError as exc:
    blocker="provider_http_"+str(exc.code);break
   except (urllib.error.URLError,TimeoutError,ValueError):
    blocker="provider_transient_error";break
   for page in data.get("query",{}).get("pages",[]):
    info=(page.get("imageinfo") or [{}])[0]
    if not str(info.get("mime","")).startswith("audio/"):continue
    hits+=1
    pid=page.get("pageid")
    if not isinstance(pid,int):continue
    sid="wikimedia-commons:"+str(pid)
    if sid in rows:
     duplicates+=1
     if identity not in rows[sid]["target_gaps"]:rows[sid]["target_gaps"].append(identity)
     continue
    ext=info.get("extmetadata") or {}
    def field(name):
     v=ext.get(name,{})
     return v.get("value","") if isinstance(v,dict) else ""
    rows[sid]={"source_id":sid,"provider":"wikimedia_commons","source_page":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(page.get("title","").replace(" ","_"),safe="():_"),"title":page.get("title"),"mime":info.get("mime"),"size_bytes":info.get("size"),"target_gaps":[identity],"query_term":term,"license_short_name":field("LicenseShortName"),"license_url":field("LicenseUrl"),"license_verified_for_youtube":False,"has_r2_audio":False,"status":"CANDIDATE_UNVERIFIED"}
  if blocker:break
 # Never claim global dedup or rights verification. Do not publish private rows in logs.
 payload={"schema":"wnc_ws3_targeted_gap_candidates_v1","source_priority_checkpoint":p["checkpoint_key"],"provider":"wikimedia_commons","metadata_only":True,"rights_verified":False,"cross_index_dedup_done":False,"audio_downloads":0,"candidates":[rows[k] for k in sorted(rows)]}
 raw=json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()
 digest=hashlib.sha256(raw).hexdigest()
 key=ROOT+"targeted-gap-candidates/"+digest[:24]+".json"
 if rows:
  try:s3.head_object(Bucket=BUCKET,Key=key)
  except s3.exceptions.ClientError as exc:
   if exc.response.get("Error",{}).get("Code") not in ("404","NotFound","NoSuchKey"):raise
   s3.put_object(Bucket=BUCKET,Key=key,Body=raw,ContentType="application/json",CacheControl="private,no-store")
   if s3.head_object(Bucket=BUCKET,Key=key)["ContentLength"]!=len(raw):raise RuntimeError("R2 checkpoint mismatch")
 summary={"schema":payload["schema"],"priority_checkpoint":p["checkpoint_key"],"checkpoint_key":key if rows else None,"queries_attempted":attempts,"audio_hits":hits,"unique_candidates":len(rows),"duplicates_within_batch":duplicates,"target_gaps":sorted(wanted.intersection(TERMS)),"provider_blocker":blocker,"rights_verified":0,"cross_index_dedup_done":False,"audio_downloads":0}
 s3.put_object(Bucket=BUCKET,Key=ROOT+"targeted-gap-candidates/latest-summary.json",Body=json.dumps(summary,sort_keys=True).encode(),ContentType="application/json",CacheControl="private,no-store")
 print("WS3_TARGETED_GAPS "+json.dumps({k:v for k,v in summary.items() if k not in ("checkpoint_key","priority_checkpoint")},sort_keys=True))
if __name__=="__main__":main()
