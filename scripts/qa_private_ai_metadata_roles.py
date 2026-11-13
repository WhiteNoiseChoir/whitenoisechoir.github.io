#!/usr/bin/env python3
"""Private QA of role-aware multi-layer search. No media download or public results."""
import datetime, hashlib, json, os, sqlite3, tempfile
from pathlib import Path
import boto3
from botocore.config import Config
from build_private_ai_metadata_index import BUCKET,ACCOUNT,INDEX_ROOT,query
SCENARIOS={
 "rainforest_evening":{"roles":["rainforest birds","frogs","crickets"],"nature_only":True},
 "forest_stream":{"roles":["stream river","birds forest","wind leaves"],"nature_only":True},
 "winter_cabin":{"roles":["wind winter","fireplace crackling","snow"],"nature_only":True},
 "tropical_dawn":{"roles":["rainforest morning","birds dawn","waterfall"],"nature_only":True},
 "soft_piano":{"roles":["piano ambient","rain background"],"nature_only":False},
}
def main():
 s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",
  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
  config=Config(signature_version="s3v4",retries={"max_attempts":4,"mode":"standard"}))
 manifest=json.loads(s3.get_object(Bucket=BUCKET,Key=INDEX_ROOT+"current.json")["Body"].read())
 with tempfile.TemporaryDirectory() as tmp:
  path=Path(tmp)/"source.sqlite"
  s3.download_file(BUCKET,manifest["index_r2_key"],str(path))
  if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest["index_sha256"]:raise RuntimeError("Index checksum mismatch")
  db=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
  counts=dict(db.execute("SELECT source_class,count(*) FROM assets GROUP BY source_class"))
  verified=db.execute("SELECT count(*) FROM assets WHERE has_r2_audio=1").fetchone()[0]
  scenarios={}
  for name,scenario in SCENARIOS.items():
   roles={}
   for role in scenario["roles"]:
    rows=query(db,role,30,"nature" if scenario["nature_only"] else None)
    # Filter to actual audio when selecting a layer. Candidates remain discoverable separately.
    playable=[x for x in rows if x["has_r2_audio"]]
    roles[role]={"hits":len(rows),"audio_hits_top30":len(playable),
      "first_audio_rank":next((i+1 for i,x in enumerate(rows) if x["has_r2_audio"]),None),
      "top3":[{"id":x["id"],"name":x["name"],"source":x["source"],"license":x["license"],
        "qa_status":x["qa_status"],"has_r2_audio":x["has_r2_audio"]} for x in rows[:3]]}
   scenarios[name]=roles
  db.close()
  report={"schema":"wnc_private_composition_retrieval_qa_v1",
    "created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "index_sha256":manifest["index_sha256"],"total_indexed":sum(counts.values()),
    "source_class_counts":counts,"records_with_r2_audio":verified,
    "method":"lexical FTS5 OR across roles; top-30 each; no acoustic verification; no evidence of semantic understanding",
    "scenarios":scenarios}
  # Private R2 only; public GitHub log prints aggregate metrics, never private records.
  key=INDEX_ROOT+"qa/composition-role-qa-"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".json"
  s3.put_object(Bucket=BUCKET,Key=key,Body=json.dumps(report,ensure_ascii=False).encode(),
   ContentType="application/json",CacheControl="private,no-store")
  summary={"total":report["total_indexed"],"classes":counts,"r2_audio":verified,
   "scenarios":{name:{role:{"hits":v["hits"],"audio_hits_top30":v["audio_hits_top30"],
    "first_audio_rank":v["first_audio_rank"]} for role,v in roles.items()} for name,roles in scenarios.items()},
   "private_report_key":key}
  print("AI_METADATA_ROLE_QA_FINAL "+json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
