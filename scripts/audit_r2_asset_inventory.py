#!/usr/bin/env python3
"""Read-only R2 object inventory for actual harvested SHA-256 audio assets."""
import datetime
import json
import os
import re
import boto3
from botocore.config import Config

ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
BUCKET="whitenoisechoir-media"
PREFIXES={
 "commons":"asset-library/commons/sha256/",
 "kenney_direct":"asset-library/kenney/sha256/",
 "cc0_github_mirror":"asset-library/cc0-github-mirror/sha256/"}
SHA=re.compile(r"/([0-9a-f]{64})\.[a-z0-9]+$")
def audit(s3):
    kinds={}
    total={}
    all_sha=set()
    duplicated_sha=0
    for label,prefix in PREFIXES.items():
        assets=[]
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET,Prefix=prefix):
            for obj in page.get("Contents",[]):
                m=SHA.search(obj["Key"])
                if m:
                    assets.append((m.group(1),obj["Size"]))
        kinds[label]={"objects":len(assets),"bytes":sum(x[1] for x in assets),
                      "unique_sha256":len(set(x[0] for x in assets))}
        for digest,bytesize in assets:
            if digest in all_sha:
                duplicated_sha+=1
            all_sha.add(digest)
            total.setdefault(digest,bytesize)
    return {"checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "bucket":BUCKET,"by_prefix":kinds,
            "unique_sha256_across_intake":len(all_sha),
            "unique_asset_bytes":sum(total.values()),
            "duplicate_sha_across_prefixes":duplicated_sha}
def main():
    s3=boto3.session.Session().client(
        "s3",region_name="auto",
        endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
                      retries={"max_attempts":5,"mode":"standard"}))
    print("R2_INVENTORY "+json.dumps(audit(s3),ensure_ascii=False),flush=True)
if __name__=="__main__":
    main()
