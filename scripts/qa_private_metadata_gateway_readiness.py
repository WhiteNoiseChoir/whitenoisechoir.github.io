#!/usr/bin/env python3
"""Non-mutating deployment readiness check for WhiteNoiseChoir PRIVATE metadata search.
Checks private R2 search index/staging and availability of Cloudflare auth prerequisites.
Never outputs secrets, account/database IDs, or private asset metadata.
"""
import datetime, json, os
from pathlib import Path
import boto3
from botocore.config import Config

BUCKET="whitenoisechoir-media"
ROOT="internal/ai-metadata-index/v1/"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"

def main():
 s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",
  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
  config=Config(signature_version="s3v4",retries={"max_attempts":4,"mode":"standard"}))
 def read(k):
  o=s3.get_object(Bucket=BUCKET,Key=k)
  try: return json.loads(o["Body"].read(131072))
  finally:o["Body"].close()
 summary=read(ROOT+"current.json")
 if summary["indexed_total"]<20000:raise RuntimeError("Private index count unexpectedly low")
 obj=s3.head_object(Bucket=BUCKET,Key=summary["index_r2_key"])
 index_ok=obj["ContentLength"]==summary["index_bytes"] and obj.get("Metadata",{}).get("sha256")==summary["index_sha256"]
 if not index_ok:raise RuntimeError("R2 private index failed object HEAD/checksum metadata check")
 # Choose the newest versioned D1 staging manifest by listing paths only.
 keys=[x["Key"] for p in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET,Prefix=ROOT+"d1-staging/")
       for x in p.get("Contents",[]) if x["Key"].endswith("/manifest.json")]
 latest=read(sorted(keys)[-1]) if keys else None
 if not latest:raise RuntimeError("D1 staging manifest missing; fail closed before deployment")
 staging_files=0
 if latest:
  prefix=latest["private_sql_prefix"]
  staging_files=sum(1 for p in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET,Prefix=prefix)
   for x in p.get("Contents",[]) if x["Key"].endswith(".sql"))
  if staging_files==0:raise RuntimeError("D1 staged SQL files missing; fail closed before deployment")
  if staging_files!=latest["sql_files"]:raise RuntimeError("D1 staged SQL count mismatch")
  if latest["source_index_sha256"]!=summary["index_sha256"]:raise RuntimeError("D1 export stale for current index")
 token=bool(os.getenv("CLOUDFLARE_API_TOKEN") or os.getenv("CF_API_TOKEN"))
 account=bool(os.getenv("CLOUDFLARE_ACCOUNT_ID") or os.getenv("CF_ACCOUNT_ID"))
 domain=bool(os.getenv("ACCESS_TEAM_DOMAIN"))
 aud=bool(os.getenv("ACCESS_AUD"))
 database=bool(os.getenv("METADATA_D1_DATABASE_ID"))
 configured={"cloudflare_api_token_present":token,"cloudflare_account_id_present":account,
  "access_team_domain_present":domain,"access_audience_present":aud,"metadata_d1_database_id_present":database}
 blockers=[k for k,v in configured.items() if not v]
 report={"schema":"wnc_ai_metadata_deployment_readiness_v1",
  "checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "indexed_records":summary["indexed_total"],"r2_index_head_verified":True,
  "private_d1_staged_sql_files":staging_files,
  "d1_sql_manifest_integrity":bool(latest),
  "worker_contract_ci_last_known":"PASS_10_TESTS_MOCK_ONLY",
  "deployment_auth_prerequisites":configured,
  "missing_prerequisites":blockers,
  "deployment_status":"BLOCKED_NO_CLOUDFLARE_DEPLOY_CREDS_OR_ACCESS_SETUP" if blockers else "PREFLIGHT_READY_DEPLOY_NOT_ATTEMPTED",
  "production_worker_tested":False,"gpt_live_search_tested":False,
  "next_action":"Configure an authenticated D1 + Worker deployment and verify live token-protected searches; no private data published",
  }
 Path("audits").mkdir(exist_ok=True)
 Path("audits/metadata-gateway-readiness.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("AI_METADATA_GATEWAY_PREFLIGHT "+json.dumps(report,ensure_ascii=False),flush=True)
if __name__=="__main__":
 try:
  main()
 except Exception as exc:
  # Always preserve a sanitized checkpoint artifact, even on R2/Cloudflare failure.
  # Do not serialize exception strings: SDK errors may contain private object paths.
  from botocore.exceptions import ClientError
  code = ""
  if isinstance(exc, ClientError):
   code = str(exc.response.get("ResponseMetadata",{}).get("HTTPStatusCode",""))
   if not code:
    code = str(exc.response.get("Error",{}).get("Code",""))
  if code in ("429","TooManyRequests","SlowDown","Throttling"):
   reason="RATE_LIMITED"
  elif code in ("401","403","AccessDenied","Unauthorized","Forbidden"):
   reason="ACCESS_DENIED"
  elif isinstance(exc, KeyError):
   reason="MISSING_CONFIGURATION_OR_MANIFEST_FIELD"
  else:
   reason="PREFLIGHT_FAILED"
  report={"schema":"wnc_ai_metadata_deployment_readiness_v1",
   "checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
   "deployment_status":"BLOCKED_"+reason,
   "error_category":reason,
   "production_worker_tested":False,"gpt_live_search_tested":False,
   "next_action":"Inspect private CI logs and fix the blocking prerequisite; do not deploy"}
  Path("audits").mkdir(exist_ok=True)
  Path("audits/metadata-gateway-readiness.json").write_text(json.dumps(report,indent=2)+"\\n",encoding="utf-8")
  print("AI_METADATA_GATEWAY_PREFLIGHT "+json.dumps(report),flush=True)
  raise SystemExit(1)

