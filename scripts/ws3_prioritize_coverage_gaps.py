#!/usr/bin/env python3
"""WS3 deterministic coverage-gap queue, private R2 only. No audio or rights clearance."""
import datetime,hashlib,json,os
import boto3
from botocore.config import Config
ROOT="internal/ws3-sleep-relax-discovery/v1/"
BUCKET="whitenoisechoir-media"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
# Higher values prioritize missing continuous beds and distinctive soundscapes.
WEIGHTS={"continuous_beds":6,"weather_material":5,"habitats":4,"cozy_interiors":4,"wildlife_events":3,"gentle_music":2}
def read(s3,key):
    obj=s3.get_object(Bucket=BUCKET,Key=key)
    try:return json.load(obj["Body"])
    finally:obj["Body"].close()
def main():
    s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",
      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
      config=Config(signature_version="s3v4",retries={"max_attempts":2,"mode":"standard"}))
    current=read(s3,ROOT+"current.json")
    coverage=read(s3,current["coverage_key"])
    verified=read(s3,ROOT+"source-verification/latest-summary.json")
    vrows=read(s3,verified["checkpoint_key"])["rows"]
    if coverage["schema"]!="wnc_ws3_coverage_v1" or verified["schema"]!="wnc_ws3_source_verification_v1":raise ValueError("Unexpected parent schema")
    if coverage["indexed_total"]!=22239:raise ValueError("Index changed: rebuild coverage first")
    queue=[]
    for r in coverage["coverage"]:
        zero=r["lexical_candidates"]==0
        no_audio=r["r2_audio_flagged"]==0
        # Lexical hits are not equivalent to rights-cleared assets or validated sleep quality.
        score=WEIGHTS[r["category"]]*10+(30 if zero else 0)+(15 if no_audio else 0)
        queue.append({"category":r["category"],"sound_identity":r["sound_identity"],"score":score,
          "lexical_candidates":r["lexical_candidates"],"r2_audio_flagged":r["r2_audio_flagged"],
          "gap":"NO_LEXICAL_CANDIDATE" if zero else "NO_R2_AUDIO_FLAG" if no_audio else "UNVERIFIED_AUDIO_SUITABILITY",
          "youtube_license_verified":False,"source_quality_verified":False})
    queue.sort(key=lambda x:(-x["score"],x["category"],x["sound_identity"]))
    status={"schema":"wnc_ws3_gap_priority_v1","indexed_total":coverage["indexed_total"],
      "source_coverage_version":coverage["version"],"source_verification_checkpoint":verified["checkpoint_key"],
      "gap_count":len(queue),"zero_lexical_count":sum(x["gap"]=="NO_LEXICAL_CANDIDATE" for x in queue),
      "no_r2_audio_count":sum(x["r2_audio_flagged"]==0 for x in queue),
      "provider_candidates":len(vrows),"provider_source_live":sum(bool(x.get("source_page_live_verified")) for x in vrows),
      "provider_exact_duplicates":sum(x.get("dedup_status")=="EXACT_MATCH" for x in vrows),
      "provider_no_exact_match":sum(x.get("dedup_status")=="NO_EXACT_MATCH_IN_COMPARABLE_COLUMNS" for x in vrows),
      "provider_rights_verified_for_youtube":0,"new_external_sources":0,"audio_downloads":0,
      "top_priorities":queue[:10],"next_stage":"source-specific rights review and provider gap discovery"}
    # Content-addressed immutable checkpoint; latest pointer is allowed to update.
    digest=hashlib.sha256(json.dumps({"version":coverage["version"],"verification":verified["checkpoint_key"],"queue":queue},sort_keys=True).encode()).hexdigest()
    key=ROOT+"gap-priority/"+digest[:24]+".json"
    body=json.dumps({"summary":status,"queue":queue},ensure_ascii=False,sort_keys=True).encode()
    try:s3.head_object(Bucket=BUCKET,Key=key)
    except s3.exceptions.ClientError as e:
        if e.response.get("Error",{}).get("Code") not in ("404","NoSuchKey","NotFound"):raise
        s3.put_object(Bucket=BUCKET,Key=key,Body=body,ContentType="application/json",CacheControl="private,no-store")
        if s3.head_object(Bucket=BUCKET,Key=key)["ContentLength"]!=len(body):raise RuntimeError("Checkpoint R2 mismatch")
    status["checkpoint_key"]=key
    s3.put_object(Bucket=BUCKET,Key=ROOT+"gap-priority/latest-summary.json",Body=json.dumps(status).encode(),ContentType="application/json",CacheControl="private,no-store")
    print("WS3_GAP_PRIORITY "+json.dumps({k:v for k,v in status.items() if k not in ("checkpoint_key","top_priorities")}))
    print("WS3_TOP_GAPS "+json.dumps([{"category":r["category"],"sound_identity":r["sound_identity"],"gap":r["gap"]} for r in queue[:10]]))
if __name__=="__main__":main()
