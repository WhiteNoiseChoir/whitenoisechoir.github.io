#!/usr/bin/env python3
"""Read-only, no outbound discovery/download, current R2 source record inventory."""
import collections, datetime, json, os, re
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.config import Config

ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
BUCKET="whitenoisechoir-media"
PREFIXES={
"nature_diversity_source_records":"asset-library/sources/nature-diversity/records/",
"opengameart_source_records":"asset-library/sources/opengameart/records/",
"cc0_mirror_provenance_records":"asset-library/cc0-github-mirror/records/",
"canonical_audio_metadata":"asset-library/records/sha256/",
"music_candidate_metadata":"internal/music-candidates/v1/",
"tropical_wildlife_runs":"asset-library/sources/tropical-wildlife/runs/",
"inaturalist_runs":"asset-library/sources/inaturalist/runs/",
"nature_diversity_runs":"asset-library/sources/nature-diversity/runs/",
"noaa_pmel_runs":"asset-library/sources/noaa-pmel/runs/",
"usfws_runs":"asset-library/sources/internet-archive-usfws/runs/",
"opengameart_runs":"asset-library/sources/opengameart/runs/",
"audio_raw_objects":"asset-library/raw/sha256/",
"audio_commons_objects":"asset-library/commons/sha256/",
"audio_cc0_mirror_objects":"asset-library/cc0-github-mirror/sha256/",
"audio_kenney_objects":"asset-library/kenney/sha256/"
}
def s3_client():
 return boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",max_pool_connections=20,retries={"max_attempts":4,"mode":"standard"}))
def main():
 s3=s3_client()
 data={"schema":"nature_metadata_r2_inventory_v1","checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"bucket":BUCKET,"counts":{},"source_record_classification_sample":{},"warnings":[]}
 for name,prefix in PREFIXES.items():
  cnt=0;bytes_sum=0;examples=[]
  for p in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET,Prefix=prefix):
   for x in p.get("Contents",[]):
    if not x["Key"].endswith(".json") and "metadata" in name:continue
    cnt+=1;bytes_sum+=x["Size"]
    if len(examples)<4:examples.append(x["Key"])
  data["counts"][name]={"objects":cnt,"bytes":bytes_sum,"examples":examples[:2]}
  print("NATURE_INVENTORY_PREFIX "+json.dumps({"name":name,"count":cnt,"bytes":bytes_sum}),flush=True)
 # Inspect 100 canonical asset metadata documents to characterize whether they are all nature;
 # this sample must NEVER be presented as a full population count.
 prefix=PREFIXES["canonical_audio_metadata"]; keys=[]
 for p in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET,Prefix=prefix):
  for x in p.get("Contents",[]):
   if x["Key"].endswith(".json"):
    keys.append(x["Key"])
    if len(keys)>=160:break
  if len(keys)>=160:break
 def fetch(k):
  x=s3.get_object(Bucket=BUCKET,Key=k)
  try:doc=json.loads(x["Body"].read(64_000))
  finally:x["Body"].close()
  return doc
 groups=collections.Counter();providers=collections.Counter();errors=0
 with ThreadPoolExecutor(max_workers=8) as pool:
  fut=[pool.submit(fetch,k) for k in keys]
  for f in as_completed(fut):
   try:
    doc=f.result()
    groups[str(doc.get("group_hint") or doc.get("group") or "unspecified")]+=1
    providers[str(doc.get("source_provider") or "unspecified")]+=1
   except Exception:
    errors+=1
 data["source_record_classification_sample"]={"sample_count":len(keys),"classified_count":sum(groups.values()),"read_errors":errors,"group_hints":dict(groups.most_common(25)),"providers":dict(providers.most_common(20)),"warning":"This sample is NOT an exhaustive semantic classification of all canonical records."}
 if data["counts"]["canonical_audio_metadata"]["objects"]:
  data["warnings"].append("Canonical records correspond to real audio files, not all nature-only metadata; do not add counts across overlapping prefixes.")
 if data["counts"]["nature_diversity_source_records"]["objects"]:
  data["warnings"].append("Nature diversity source records correspond to audio source identities imported by that pipeline, not a corpus of all candidate metadata.")
 os.makedirs("audits",exist_ok=True)
 open("audits/nature-metadata-readonly-20261113.json","w",encoding="utf-8").write(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
 print("NATURE_INVENTORY_FINAL "+json.dumps(data,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
