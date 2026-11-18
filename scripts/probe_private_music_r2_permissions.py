#!/usr/bin/env python3
"""Non-destructive permission probe. No credentials or bucket contents printed."""
import json
import os
import sys
from datetime import datetime,timezone
from uuid import uuid4

def main():
    a=os.environ.get("R2_ACCESS_KEY_ID", "")
    b=os.environ.get("R2_SECRET_ACCESS_KEY", "")
    if not a or not b:
        print("MUSIC_R2_PROBE "+json.dumps({"status":"MISSING_GITHUB_SECRETS"}),flush=True)
        return 2
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    s3=boto3.client(
        "s3",region_name="auto",
        endpoint_url="https://7483501ad8365fe26b0448b96b54fb9f.r2.cloudflarestorage.com",
        aws_access_key_id=a,aws_secret_access_key=b,
        config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
                      retries={"mode":"standard","max_attempts":2}))
    bucket="wnc-music-private"
    key="internal/licensed-music/v1/diagnostics/permission-probe-"+uuid4().hex+".json"
    body=json.dumps({"schema":"wnc_permission_probe_v1","time":datetime.now(timezone.utc).isoformat()}).encode()
    wrote=False
    try:
        s3.put_object(Bucket=bucket,Key=key,Body=body,ContentType="application/json")
        wrote=True
        meta=s3.head_object(Bucket=bucket,Key=key)
        if meta["ContentLength"]!=len(body):
            raise RuntimeError("Probe object HEAD size mismatch")
        print("MUSIC_R2_PROBE "+json.dumps({"bucket":bucket,"status":"WRITE_AND_READ_OK"}),flush=True)
        return 0
    except ClientError as exc:
        code=exc.response.get("Error",{}).get("Code","Unknown")
        # Codes only: no signed URL, response headers or credentials.
        print("MUSIC_R2_PROBE "+json.dumps({"bucket":bucket,"status":"BLOCKED","error_code":code}),flush=True)
        return 1
    except Exception as exc:
        print("MUSIC_R2_PROBE "+json.dumps({"bucket":bucket,"status":"ERROR","exception_type":type(exc).__name__}),flush=True)
        return 1
    finally:
        if wrote:
            try:
                s3.delete_object(Bucket=bucket,Key=key)
                print("MUSIC_R2_PROBE_CLEANUP DELETED",flush=True)
            except Exception:
                print("MUSIC_R2_PROBE_CLEANUP NEEDS_REVIEW",flush=True)

if __name__=="__main__":
    sys.exit(main())
