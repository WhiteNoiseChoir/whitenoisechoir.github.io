#!/usr/bin/env python3
"""Read an existing R2 wildlife intake run and output Studio-safe catalog metadata."""
import boto3,json,os,re,urllib.request
from botocore.config import Config

ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
BUCKET="whitenoisechoir-media"
MEDIA="https://media.whitenoisechoir.com/"
run=os.environ.get("TROPICAL_INTAKE_RUN_ID","43156908467")
s3=boto3.client("s3",endpoint_url=f"https://{ACCOUNT}.r2.cloudflarestorage.com",region_name="auto",
  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
  config=Config(signature_version="s3v4",request_checksum_calculation="when_required",response_checksum_validation="when_required"))
def get(key):
  obj=s3.get_object(Bucket=BUCKET,Key=key)
  try: return json.load(obj["Body"])
  finally: obj["Body"].close()
record=get(f"asset-library/sources/tropical-wildlife/runs/{run}-1.json")
result=[];errors=[]
for row in record["assets"]:
  if row.get("state") not in ("new","reused") or not row.get("key"):continue
  key=row["key"]
  sha=re.search(r"/([0-9a-f]{64})\.[a-z0-9]+$",key).group(1)
  meta=get(f"asset-library/records/sha256/{sha[:2]}/{sha}.json")
  data={"name":meta.get("title") or meta.get("scientific_name") or meta.get("original_filename"),
        "key":key,"group":"wildlife","aliases":" ".join(filter(None,[
          str(meta.get("scientific_name") or ""),str(meta.get("group_hint") or ""),
          str(meta.get("source_provider") or ""),str(meta.get("original_filename") or "")])),
        "duration":round(float(meta.get("duration_seconds") or 0),3),
        "source":meta.get("source_page"),"license":meta.get("license"),
        "scientific_name":meta.get("scientific_name"),
        "recorded_at":meta.get("recorded_date"),"source_group":meta.get("group_hint"),
        "sha256":sha,"qa_status":"QA_LISTENING_PENDING",
        "assetStatus":"STORED_R2_TECHNICAL_PASS_LISTENING_PENDING"}
  head=s3.head_object(Bucket=BUCKET,Key=key)
  if head["ContentLength"]!=meta.get("file_bytes") or head.get("Metadata",{}).get("sha256")!=sha:
    errors.append(key+": R2 metadata mismatch");continue
  if data["duration"]<=0:
    errors.append(key+": unknown duration");continue
  # Public byte range + identity check for Studio source URL.
  try:
    req=urllib.request.Request(MEDIA+key,headers={"Range":"bytes=0-15","User-Agent":"WhiteNoiseChoir-StudioQA/1.0"})
    with urllib.request.urlopen(req,timeout=15) as resp:
      if resp.status not in (200,206) or not resp.read(16):
        raise RuntimeError("No accessible media bytes")
  except Exception as exc: errors.append(key+": public preview "+str(exc)[:160]);continue
  result.append(data)
  print("TROPICAL_STUDIO_ASSET_JSON "+json.dumps(data,ensure_ascii=False),flush=True)
print("TROPICAL_STUDIO_SUMMARY "+json.dumps({"checked":len(record["assets"]),"ready":len(result),"errors":errors[:30]},ensure_ascii=False),flush=True)
with open("tropical-studio-assets.json","w") as out:json.dump({"assets":result,"errors":errors},out,ensure_ascii=False,indent=2)
if errors:raise SystemExit("One or more items failed R2 Studio accessibility")
