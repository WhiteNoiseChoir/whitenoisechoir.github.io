#!/usr/bin/env python3
"""WS3 conservative cross-index dedup; metadata only, private R2 output."""
import datetime,hashlib,json,os,sqlite3,tempfile
from pathlib import Path
import boto3
from botocore.config import Config
BUCKET="whitenoisechoir-media"
ROOT="internal/ws3-sleep-relax-discovery/v1/"
INDEX="internal/ai-metadata-index/v1/current.json"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
def load(s3,key):
 obj=s3.get_object(Bucket=BUCKET,Key=key)
 try:return json.loads(obj["Body"].read())
 finally:obj["Body"].close()
def main():
 s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",retries={"max_attempts":2,"mode":"standard"}))
 triage=load(s3,ROOT+"rights-triage/latest-summary.json")
 if triage.get("schema")!="wnc_ws3_rights_triage_summary_v2":raise RuntimeError("WS3 rights triage V2 required")
 source=load(s3,triage["triage_checkpoint"])
 rows=source["rows"]
 index=load(s3,INDEX)
 with tempfile.TemporaryDirectory() as tmp:
  path=Path(tmp)/"index.sqlite"
  s3.download_file(BUCKET,index["index_r2_key"],str(path))
  digest=hashlib.sha256(path.read_bytes()).hexdigest()
  if digest!=index["index_sha256"]:raise RuntimeError("index SHA mismatch")
  db=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
  columns=[x[1] for x in db.execute("PRAGMA table_info(assets)")]
  count=db.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
  if count!=index["indexed_total"]:raise RuntimeError("index row count mismatch")
  # Only compare exact stable identifiers, never approximate text similarity.
  fields=[x for x in ("source_id","source_url","source_page","canonical_url","url","original_url","provider_id") if x in columns]
  if not fields:
   results=[dict(row,full_index_dedup_status="UNVERIFIED_NO_COMPARABLE_COLUMNS") for row in rows]
  else:
   query="SELECT "+",".join('"'+x+'"' for x in fields)+" FROM assets"
   values=set()
   for record in db.execute(query):
    for val in record:
     if val is not None and str(val).strip():values.add(str(val).strip())
   results=[]
   for row in rows:
    identifiers=(row["source_id"],row["source_page"])
    matched=[x for x in identifiers if x in values]
    results.append(dict(row,full_index_dedup_status="EXACT_MATCH" if matched else "NO_EXACT_MATCH_IN_COMPARABLE_COLUMNS",matched_identifiers=matched))
  db.close()
 summary={"schema":"wnc_ws3_cross_index_dedup_v1","checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"index_sha256":digest,"indexed_total":count,"source_candidates":len(rows),"compared_columns":fields,"exact_duplicates":sum(x["full_index_dedup_status"]=="EXACT_MATCH" for x in results),"no_exact_match":sum(x["full_index_dedup_status"]=="NO_EXACT_MATCH_IN_COMPARABLE_COLUMNS" for x in results),"unverified":sum(x["full_index_dedup_status"].startswith("UNVERIFIED") for x in results),"youtube_license_verified":0,"source_page_live_verified":0,"audio_downloads":0,"note":"Exact identifier comparison only. No match is not proof of uniqueness across all representations."}
 fingerprint=hashlib.sha256(json.dumps({"index":digest,"source":triage["triage_checkpoint"],"results":results},sort_keys=True).encode()).hexdigest()
 key=ROOT+"cross-index-dedup/"+fingerprint[:24]+".json"
 body=json.dumps({"summary":summary,"rows":results},ensure_ascii=False).encode()
 try:s3.head_object(Bucket=BUCKET,Key=key)
 except s3.exceptions.ClientError as e:
  if e.response.get("Error",{}).get("Code") not in ("404","NoSuchKey","NotFound"):raise
  s3.put_object(Bucket=BUCKET,Key=key,Body=body,ContentType="application/json",CacheControl="private,no-store")
  if s3.head_object(Bucket=BUCKET,Key=key)["ContentLength"]!=len(body):raise RuntimeError("R2 checkpoint size mismatch")
 summary["checkpoint_key"]=key
 s3.put_object(Bucket=BUCKET,Key=ROOT+"cross-index-dedup/latest-summary.json",Body=json.dumps(summary).encode(),ContentType="application/json",CacheControl="private,no-store")
 print("WS3_CROSS_INDEX_DEDUP "+json.dumps({k:v for k,v in summary.items() if k!="checkpoint_key"}))
if __name__=="__main__":main()
