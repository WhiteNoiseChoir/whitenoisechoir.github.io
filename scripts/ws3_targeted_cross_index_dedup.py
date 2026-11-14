#!/usr/bin/env python3
"""WS3 targeted candidates vs private AI index, exact-identifier dedup only."""
import hashlib,json,os,sqlite3,tempfile,urllib.parse
from pathlib import Path
import boto3
from botocore.config import Config
BUCKET="whitenoisechoir-media"
ROOT="internal/ws3-sleep-relax-discovery/v1/"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
def load(s3,key):
 obj=s3.get_object(Bucket=BUCKET,Key=key)
 try:return json.load(obj["Body"])
 finally:obj["Body"].close()
def canonical(s):
 if not s:return ""
 p=urllib.parse.urlsplit(str(s).strip())
 if p.hostname=="commons.wikimedia.org" and p.path.startswith("/wiki/"):
  return "https://commons.wikimedia.org/wiki/"+urllib.parse.unquote(p.path).replace(" ","_")
 return str(s).strip()
def main():
 s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",retries={"max_attempts":2,"mode":"standard"}))
 source=load(s3,ROOT+"targeted-gap-candidates/latest-summary.json")
 if source.get("schema")!="wnc_ws3_targeted_gap_candidates_v1" or not source.get("checkpoint_key"):raise ValueError("Targeted discovery checkpoint missing")
 payload=load(s3,source["checkpoint_key"])
 if payload.get("schema")!=source["schema"] or payload.get("audio_downloads")!=0:raise ValueError("Invalid source manifest")
 rows=payload["candidates"]
 if len(rows)!=source["unique_candidates"]:raise ValueError("Source count mismatch")
 idx=load(s3,"internal/ai-metadata-index/v1/current.json")
 if idx.get("indexed_total")!=22239:raise ValueError("Baseline changed")
 with tempfile.TemporaryDirectory() as tmp:
  path=Path(tmp)/"index.sqlite"
  s3.download_file(BUCKET,idx["index_r2_key"],str(path))
  sha=hashlib.sha256(path.read_bytes()).hexdigest()
  if sha!=idx["index_sha256"]:raise ValueError("Index SHA mismatch")
  db=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
  if db.execute("SELECT COUNT(*) FROM assets").fetchone()[0]!=22239:raise ValueError("Row count mismatch")
  cols={r[1] for r in db.execute("PRAGMA table_info(assets)")}
  fields=sorted(cols.intersection({"source_id","source_url","source_page","canonical_url","url","original_url","provider_id"}))
  if not fields:raise ValueError("No comparable identifier fields")
  known=set()
  for record in db.execute("SELECT "+",".join('"'+f+'"' for f in fields)+" FROM assets"):
   for val in record:
    if val is not None and str(val).strip():known.add(canonical(val))
  results=[]
  for row in rows:
   sid=str(row.get("source_id",""))
   page=canonical(row.get("source_page",""))
   if not sid or not page:raise ValueError("Missing candidate identifier")
   exact=sid in known or page in known
   results.append({"source_id":sid,"source_page":page,"target_gaps":row.get("target_gaps",[]),"status":"EXACT_MATCH" if exact else "NO_EXACT_MATCH_UNVERIFIED","rights_verified":False,"has_r2_audio":False})
  db.close()
 summary={"schema":"wnc_ws3_targeted_cross_index_dedup_v1","index_sha256":sha,"indexed_total":22239,"source_checkpoint":source["checkpoint_key"],"source_candidates":len(rows),"compared_columns":fields,"exact_duplicates":sum(r["status"]=="EXACT_MATCH" for r in results),"no_exact_match_unverified":sum(r["status"]=="NO_EXACT_MATCH_UNVERIFIED" for r in results),"stale_sources":None,"validated_sources":0,"rights_verified":0,"audio_downloads":0,"coverage_change_verified":0}
 digest=hashlib.sha256(json.dumps({"index":sha,"source":source["checkpoint_key"],"results":results},sort_keys=True).encode()).hexdigest()
 key=ROOT+"targeted-cross-index-dedup/"+digest[:24]+".json"
 body=json.dumps({"summary":summary,"rows":results},sort_keys=True,ensure_ascii=False).encode()
 try:s3.head_object(Bucket=BUCKET,Key=key)
 except s3.exceptions.ClientError as e:
  if e.response.get("Error",{}).get("Code") not in ("404","NotFound","NoSuchKey"):raise
  s3.put_object(Bucket=BUCKET,Key=key,Body=body,ContentType="application/json",CacheControl="private,no-store")
 if s3.head_object(Bucket=BUCKET,Key=key)["ContentLength"]!=len(body):raise ValueError("R2 checkpoint mismatch")
 summary["checkpoint_key"]=key
 s3.put_object(Bucket=BUCKET,Key=ROOT+"targeted-cross-index-dedup/latest-summary.json",Body=json.dumps(summary,sort_keys=True).encode(),ContentType="application/json",CacheControl="private,no-store")
 print("WS3_TARGETED_DEDUP "+json.dumps({k:v for k,v in summary.items() if k not in ("checkpoint_key","source_checkpoint","index_sha256")},sort_keys=True))
if __name__=="__main__":main()
