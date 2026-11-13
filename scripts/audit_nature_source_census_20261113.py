#!/usr/bin/env python3
"""Strictly read-only census of existing nature-diversity source JSON on R2."""
import collections,datetime,json,os,re,time
from concurrent.futures import ThreadPoolExecutor,as_completed
import boto3
from botocore.config import Config
BUCKET="whitenoisechoir-media"
ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
ROOT="asset-library/sources/nature-diversity/records/"
def fetch(s3,key):
 obj=s3.get_object(Bucket=BUCKET,Key=key)
 try:body=obj["Body"].read(64_000)
 finally:obj["Body"].close()
 return json.loads(body)
def main():
 s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",max_pool_connections=20,retries={"max_attempts":5,"mode":"standard"}))
 keys=[x["Key"] for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET,Prefix=ROOT) for x in page.get("Contents",[]) if x["Key"].endswith(".json")]
 providers=collections.Counter();groups=collections.Counter();licenses=collections.Counter();schema=collections.Counter();filled=collections.Counter();durations=collections.Counter();types=collections.Counter();sha=set();source_ids=set();errors=collections.Counter();done=0;start=time.monotonic()
 def mark(d):
  nonlocal done
  providers[str(d.get("source_provider") or "unknown")]+=1
  groups[str(d.get("group_hint") or d.get("group") or "unknown")]+=1
  licenses[str(d.get("license") or "unknown")]+=1
  schema[str(d.get("schema_version") or "unknown")]+=1
  for k in ("audio_sha256","audio_storage_key","source_page","source_provider","license","creator","attribution","duration_seconds","scientific_name","common_name","recorded_at","recorded_date","group_hint","description","source_tags","source_file_bytes","channels","sample_rate"):
   if d.get(k) not in (None,"",[],{}):filled[k]+=1
  if d.get("audio_sha256"):sha.add(str(d["audio_sha256"]))
  sec=d.get("duration_seconds")
  if isinstance(sec,(int,float)):
   k=("under_10s" if sec<10 else "10_to_60s" if sec<60 else "1_to_5min" if sec<300 else "over_5min")
   durations[k]+=1
  else:durations["unknown"]+=1
  for k in ("scientific_name","taxon_name","taxon","common_name"):
   if d.get(k): source_ids.add(str(d[k]));break
  done+=1
 with ThreadPoolExecutor(max_workers=12) as pool:
  futures={pool.submit(fetch,s3,k):k for k in keys}
  for f in as_completed(futures):
   try:mark(f.result())
   except Exception as exc:errors[type(exc).__name__]+=1
   if (done+sum(errors.values()))%4000==0:
    print("NATURE_CENSUS_PROGRESS "+json.dumps({"done":done,"errors":sum(errors.values()),"total":len(keys)}),flush=True)
 report={"schema":"nature_source_metadata_full_census_v1","completed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"prefix":ROOT,"objects":len(keys),"read_success":done,"read_errors":dict(errors),"all_records_read":done==len(keys),"unique_audio_sha256_in_source_records":len(sha),"distinct_species_or_taxon_labels_if_present":len(source_ids),"providers":dict(providers.most_common()),"group_hints":dict(groups.most_common()),"licenses":dict(licenses.most_common()),"schema_versions":dict(schema.most_common()),"populated_fields":dict(filled),"duration_bins":dict(durations),"note":"One JSON source-record per source identity, not one distinct animal species or recording type. Group hints may represent regions, taxa or acoustic families; do not merge without taxonomy normalization."}
 os.makedirs("audits",exist_ok=True)
 open("audits/nature-source-metadata-census-20261113.json","w",encoding="utf-8").write(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
 print("NATURE_CENSUS_FINAL "+json.dumps(report,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
