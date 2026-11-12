#!/usr/bin/env python3
"""Read-only R2 inventory of potential finalized V4 release files."""
import os,json,sys
import boto3
from botocore.config import Config
bucket="whitenoisechoir-media"
account="7483501ad8365fe26b0448b96b54fb9"
s3=boto3.session.Session().client("s3",endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
 region_name="auto",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
 aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",s3={"addressing_style":"path"}))
paginator=s3.get_paginator("list_objects_v2")
matches=[];scanned=0;prefix_totals={}
for page in paginator.paginate(Bucket=bucket,PaginationConfig={"PageSize":1000,"MaxItems":4500}):
 for item in page.get("Contents",[]):
  scanned+=1
  key=item["Key"];lower=key.lower()
  if any(token in lower for token in ("living","forest-creek","/v4","release","exports","output","final","mixed","_mix","/video","studio-mix","rendered","/thumb","poster")) and (lower.endswith((".mp4",".webm",".wav",".mp3",".m4a",".jpg",".jpeg",".png",".webp"))):
   matches.append({"key":key,"bytes":item["Size"],"updated":item["LastModified"].isoformat()})
  prefix=key.split("/")[0]
  prefix_totals[prefix]=prefix_totals.get(prefix,0)+1
matches=sorted(matches,key=lambda x:x["updated"],reverse=True)
print("V4_R2_INVENTORY",json.dumps({"scanned":scanned,"roots":prefix_totals,"candidates":matches[:100]},ensure_ascii=False),flush=True)
with open("v4-r2-inventory.json","w") as handle:
 json.dump({"scanned":scanned,"roots":prefix_totals,"candidates":matches},handle,indent=2)
