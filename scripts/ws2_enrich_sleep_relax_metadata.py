#!/usr/bin/env python3
"""WS2 private, resumable metadata enrichment. Never downloads audio or modifies source/index."""
import collections,datetime,hashlib,json,os,sqlite3,tempfile
from pathlib import Path
import boto3
from botocore.config import Config

BUCKET="whitenoisechoir-media"; ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
INDEX="internal/ai-metadata-index/v1/"; OUT="internal/ws2-sleep-relax-enrichment/v1/"
BATCH=500
# Only lexical cues; never claim verified acoustic quality, loopability or suitability.
BED={"rain","rainfall","drizzle","stream","creek","river","brook","ocean","sea","wave","waves","wind","breeze","waterfall","fan","noise","water"}
TEXTURE={"forest","woodland","jungle","fireplace","fire","leaves","rustling","crackle","crackling","snow"}
EVENT={"bird","birds","owl","frog","frogs","cricket","crickets","cicada","cicadas","wolf","wolves","thunder","train","horn","call","song"}
def infer(row):
 name,family,habitat,tags,description=(str(row[k] or "") for k in ("name","sound_family","habitat","tags","description"))
 s=" ".join((name,family,habitat,tags,description)).lower()
 words=set(s.replace("-"," ").replace("_"," ").split())
 # Ambiguous mixtures must not be forced into a single verified role.
 hits=[role for role,v in (("CONTINUOUS_BED",BED),("TEXTURE",TEXTURE),("EVENT",EVENT)) if words&v]
 role=hits[0] if len(hits)==1 else "UNKNOWN"
 return {
  "id":row["id"],"source_class":row["source_class"],"sound_identity":{"name":name,"family":family or None,
   "species":row["scientific_name"] or None,"taxon":row["taxon"] or None},
  "context":{"habitat":habitat or None,"region":row["region"] or None},
  "source":{"provider":row["provider"] or None,"page":row["source_page"] or None,
   "license_raw":row["license"] or None,"credit":row["credit"] or None},
  "duration_seconds":row["duration"] if row["duration"] and row["duration"]>0 else None,
  "audio":{"has_r2_key":bool(row["r2_key"]),"r2_object_verified":False,
   "acoustic_measurements":"UNVERIFIED","loopability":"UNKNOWN","loudness":"UNKNOWN",
   "transients":"UNKNOWN","speech":"UNKNOWN"},
  "composition":{"role_hint":role,"role_evidence":"LEXICAL_UNVERIFIED" if role!="UNKNOWN" else "INSUFFICIENT_OR_AMBIGUOUS",
   "sleep_suitability":"UNVERIFIED","relaxation_suitability":"UNVERIFIED"},
  "provenance":{"schema":"wnc_ws2_enrichment_v1","source":"private_index_sqlite",
   "source_classification_status":row["qa_status"] or "UNKNOWN"}
 }
def main():
 s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",
  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
  config=Config(signature_version="s3v4",retries={"max_attempts":4,"mode":"standard"}))
 def read(key):
  x=s3.get_object(Bucket=BUCKET,Key=key)
  try:return json.loads(x["Body"].read())
  finally:x["Body"].close()
 def put(key,data):
  s3.put_object(Bucket=BUCKET,Key=key,Body=json.dumps(data,ensure_ascii=False,separators=(",",":")).encode(),
   ContentType="application/json",CacheControl="private,no-store")
 manifest=read(INDEX+"current.json")
 digest=manifest["index_sha256"];root=OUT+"source-"+digest[:16]+"/"
 try:checkpoint=read(root+"checkpoint.json")
 except s3.exceptions.NoSuchKey:checkpoint={"offset":0,"processed":0,"enriched":0,"errors":0,"role_counts":{}}
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/"index.sqlite"
  s3.download_file(BUCKET,manifest["index_r2_key"],str(path))
  if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise RuntimeError("Index checksum mismatch")
  db=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True);db.row_factory=sqlite3.Row
  total=db.execute("SELECT count(*) FROM assets").fetchone()[0]
  if total!=manifest["indexed_total"]:raise RuntimeError("Index count mismatch")
  # Three read-only SQLite audits; aggregate counts only, no private rows in logs.
  audits={
   "source_class_counts":dict(db.execute("SELECT source_class,COUNT(*) FROM assets GROUP BY source_class").fetchall()),
   "missing_sound_family":db.execute("SELECT COUNT(*) FROM assets WHERE sound_family IS NULL OR TRIM(sound_family)=''").fetchone()[0],
   "audio_key_present":db.execute("SELECT COUNT(*) FROM assets WHERE r2_key IS NOT NULL AND TRIM(r2_key)<>''").fetchone()[0],
   "missing_name":db.execute("SELECT COUNT(*) FROM assets WHERE name IS NULL OR TRIM(name)=''").fetchone()[0],
   "missing_habitat":db.execute("SELECT COUNT(*) FROM assets WHERE habitat IS NULL OR TRIM(habitat)=''").fetchone()[0],
   "missing_provider":db.execute("SELECT COUNT(*) FROM assets WHERE provider IS NULL OR TRIM(provider)=''").fetchone()[0],
   "missing_license":db.execute("SELECT COUNT(*) FROM assets WHERE license IS NULL OR TRIM(license)=''").fetchone()[0],
   "missing_duration":db.execute("SELECT COUNT(*) FROM assets WHERE duration IS NULL OR duration<=0").fetchone()[0],
   "missing_species":db.execute("SELECT COUNT(*) FROM assets WHERE scientific_name IS NULL OR TRIM(scientific_name)=''").fetchone()[0]
  }
  # Read-only retrieval smoke tests: check cardinality without exposing private records.
  query_checks={
   "unique_ids":db.execute("SELECT COUNT(DISTINCT id) FROM assets").fetchone()[0]==total,
   "nature_inventory":db.execute("SELECT COUNT(*) FROM assets WHERE source_class='nature'").fetchone()[0]==audits["source_class_counts"].get("nature",0),
   "duration_audit":db.execute("SELECT COUNT(*) FROM assets WHERE duration>0").fetchone()[0]+audits["missing_duration"]==total
  }
  # Three realistic read-only discovery probes; report counts, never private rows.
  # This validates SQL retrieval plumbing, not acoustic or semantic suitability.
  retrieval_probes={
   "forest_stream":("forest","stream"),
   "night_rain":("night","rain"),
   "ambient_piano":("ambient","piano")
  }
  retrieval_counts={}
  for probe,terms in retrieval_probes.items():
   predicates=["(LOWER(COALESCE(name,'')) LIKE ? OR LOWER(COALESCE(sound_family,'')) LIKE ? OR LOWER(COALESCE(description,'')) LIKE ?)" for _ in terms]
   params=[f"%{term}%" for term in terms for _ in range(3)]
   retrieval_counts[probe]=db.execute("SELECT COUNT(*) FROM assets WHERE "+" AND ".join(predicates),params).fetchone()[0]
  query_checks["retrieval_probe_counts_valid"]=all(0<=n<=total for n in retrieval_counts.values())
  if not all(query_checks.values()):
   raise RuntimeError("Read-only retrieval smoke tests failed")
  if sum(audits["source_class_counts"].values())!=total:
   raise RuntimeError("Source class audit count mismatch")
  if int(checkpoint.get("offset",0))>0 and checkpoint.get("schema")!="wnc_ws2_checkpoint_v1":
   raise RuntimeError("Checkpoint schema mismatch")
  offset=int(checkpoint["offset"])
  # Reject corrupt/stale checkpoints rather than silently skipping records.
  if checkpoint.get("source_index_sha256",digest)!=digest:
   raise RuntimeError("Checkpoint source hash mismatch")
  if offset<0 or offset>total or int(checkpoint.get("processed",offset))!=offset:
   raise RuntimeError("Checkpoint offset/processed inconsistent")
  if checkpoint.get("complete",False)!=(offset==total) and offset>0:
   raise RuntimeError("Checkpoint completion flag inconsistent")
  if offset>0:
   prior=checkpoint.get("last_batch")
   if not prior or not prior.startswith(root+"batches/"):
    raise RuntimeError("Missing or foreign previous batch reference")
   s3.head_object(Bucket=BUCKET,Key=prior)
   previous=read(prior)
   if previous.get("source_index_sha256")!=digest or previous.get("schema")!="wnc_ws2_batch_v1":
    raise RuntimeError("Previous batch provenance/schema mismatch")
   prev_records=previous.get("records")
   if not isinstance(prev_records,list) or int(previous.get("offset",-1))<0 or int(previous["offset"])+len(prev_records)!=offset:
    raise RuntimeError("Previous batch range does not match checkpoint")
   ids=[x.get("id") for x in prev_records]
   if not all(ids) or len(ids)!=len(set(ids)):
    raise RuntimeError("Previous batch IDs invalid or duplicate")
  if sum(int(n) for n in checkpoint.get("role_counts",{}).values())!=offset:
   raise RuntimeError("Checkpoint role-count sum does not match processed offset")
  if int(checkpoint.get("enriched",offset))!=offset or int(checkpoint.get("errors",0))!=0:
   raise RuntimeError("Checkpoint enriched/error totals inconsistent")
  if offset>=total:
   print("WS2_ENRICHMENT_FINAL "+json.dumps({"state":"COMPLETE","processed":offset,"total":total,"checkpoint":True}));return
  rows=db.execute("SELECT * FROM assets ORDER BY id LIMIT ? OFFSET ?",(BATCH,offset)).fetchall()
  results=[infer(r) for r in rows]
  if len(results)!=len({r["id"] for r in results}):raise RuntimeError("Duplicate IDs in batch")
  # Fail closed on unsupported source classes, missing provenance, or acoustic claims.
  allowed_classes={"nature","music"}
  for r in results:
   if r["source_class"] not in allowed_classes or not r["id"]:
    raise RuntimeError("Invalid source classification or ID")
   if not r["source"]["provider"] or not r["source"]["license_raw"]:
    raise RuntimeError("Missing required source provenance")
   if r["audio"]["r2_object_verified"] is not False or r["audio"]["acoustic_measurements"]!="UNVERIFIED":
    raise RuntimeError("Unsupported audio verification claim")
   if r["composition"]["sleep_suitability"]!="UNVERIFIED" or r["composition"]["relaxation_suitability"]!="UNVERIFIED":
    raise RuntimeError("Unsupported suitability claim")
  roles=collections.Counter(r["composition"]["role_hint"] for r in results)
  batch_key=root+"batches/"+f"{offset:06d}-{offset+len(results):06d}.json"
  put(batch_key,{"schema":"wnc_ws2_batch_v1","source_index_sha256":digest,"offset":offset,"records":results})
  # Commit checkpoint only after batch object upload/HEAD verified.
  s3.head_object(Bucket=BUCKET,Key=batch_key)
  cumulative=collections.Counter(checkpoint.get("role_counts",{}));cumulative.update(roles)
  checkpoint={"schema":"wnc_ws2_checkpoint_v1","source_index_sha256":digest,
   "offset":offset+len(results),"processed":offset+len(results),"enriched":offset+len(results),
   "errors":0,"role_counts":dict(cumulative),"total":total,
   "last_batch":batch_key,"updated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
   "complete":offset+len(results)==total}
  # Detect checkpoint advancement by another writer before publishing this offset.
  # This is a best-effort stale-writer guard, not an atomic R2 compare-and-swap.
  try:latest=read(root+"checkpoint.json")
  except s3.exceptions.NoSuchKey:latest={"offset":0,"source_index_sha256":digest}
  if int(latest.get("offset",-1))!=offset or latest.get("source_index_sha256",digest)!=digest:
   raise RuntimeError("Checkpoint advanced during batch; refusing stale checkpoint write")
  put(root+"checkpoint.json",checkpoint)
  print("WS2_ENRICHMENT_FINAL "+json.dumps({"processed_this_run":len(results),
   "processed_total":checkpoint["processed"],"remaining":total-checkpoint["processed"],
   "roles_this_run":dict(roles),"errors":0,"sleep_audio_verified":0,
   "audio_downloaded":False,"source_mutated":False,"sqlite_audit":audits,"query_checks":query_checks,"retrieval_probe_counts":retrieval_counts,"complete":checkpoint["complete"]}),flush=True)
if __name__=="__main__":main()
