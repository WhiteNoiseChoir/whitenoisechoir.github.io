#!/usr/bin/env python3
"""WS3 targeted source revalidation; metadata only; private checkpoints."""
import hashlib,json,os,urllib.parse,urllib.request,urllib.error
import boto3
from botocore.config import Config
ROOT="internal/ws3-sleep-relax-discovery/v1/"
BUCKET="whitenoisechoir-media"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
API="https://commons.wikimedia.org/w/api.php"
def load(s3,key):
    obj=s3.get_object(Bucket=BUCKET,Key=key)
    try:return json.load(obj["Body"])
    finally:obj["Body"].close()
def main():
    s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",retries={"max_attempts":1}))
    dedup=load(s3,ROOT+"targeted-cross-index-dedup/latest-summary.json")
    if dedup.get("schema")!="wnc_ws3_targeted_cross_index_dedup_v1" or dedup.get("indexed_total")!=22239:raise ValueError("Dedup baseline changed")
    manifest=load(s3,dedup["checkpoint_key"])
    candidates=load(s3,dedup["source_checkpoint"])
    byid={r["source_id"]:r for r in candidates["candidates"]}
    rows=[];blocker=None;checked=0
    for row in manifest["rows"]:
        sid=row["source_id"]; original=byid[sid]
        if row["status"]=="EXACT_MATCH":
            rows.append({"source_id":sid,"status":"EXACT_DUPLICATE","rights_verified":False})
            continue
        pageid=sid.split(":")[-1]
        params={"action":"query","pageids":pageid,"prop":"imageinfo","iiprop":"extmetadata|mime","format":"json","formatversion":"2"}
        req=urllib.request.Request(API+"?"+urllib.parse.urlencode(params),headers={"User-Agent":"WhiteNoiseChoirMetadataDiscovery/1.0 (metadata-only; contact github.com/WhiteNoiseChoir/whitenoisechoir.github.io)","Accept":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=25) as response:data=json.load(response)
            checked+=1
        except urllib.error.HTTPError as exc:
            blocker="HTTP_"+str(exc.code)
            break
        except (urllib.error.URLError,TimeoutError,ValueError):
            blocker="TRANSIENT_PROVIDER_ERROR"
            break
        pages=data.get("query",{}).get("pages",[])
        p=pages[0] if pages else {}
        info=(p.get("imageinfo") or [{}])[0]
        ext=info.get("extmetadata") or {}
        def field(name):
            v=ext.get(name,{})
            return v.get("value","") if isinstance(v,dict) else ""
        mime=info.get("mime","")
        license_name=field("LicenseShortName")
        license_url=field("LicenseUrl")
        valid_url=urllib.parse.urlsplit(license_url).scheme=="https" and bool(urllib.parse.urlsplit(license_url).hostname)
        state="SOURCE_VALID_METADATA_ONLY" if p and not p.get("missing") and mime.startswith("audio/") else "STALE_OR_NOT_AUDIO"
        rows.append({"source_id":sid,"source_page":original["source_page"],"status":state,"mime_matches":mime==original.get("mime"),"license_claim_matches":license_name==original.get("license_short_name") and license_url==original.get("license_url"),"license_url_https":valid_url,"rights_verified":False,"has_r2_audio":False,"target_gaps":original.get("target_gaps",[])})
    summary={"schema":"wnc_ws3_targeted_source_verification_v1","dedup_checkpoint":dedup["checkpoint_key"],"source_total":len(manifest["rows"]),"checked":checked,"exact_duplicate":sum(x["status"]=="EXACT_DUPLICATE" for x in rows),"source_valid_metadata_only":sum(x["status"]=="SOURCE_VALID_METADATA_ONLY" for x in rows),"stale":sum(x["status"]=="STALE_OR_NOT_AUDIO" for x in rows),"license_claim_changed":sum(x.get("license_claim_matches") is False for x in rows),"provider_blocker":blocker,"rights_verified":0,"coverage_change_verified":0,"audio_downloads":0}
    body=json.dumps({"summary":summary,"rows":rows},sort_keys=True,ensure_ascii=False).encode()
    key=ROOT+"targeted-source-verification/"+hashlib.sha256(body).hexdigest()[:24]+".json"
    try:s3.head_object(Bucket=BUCKET,Key=key)
    except s3.exceptions.ClientError as exc:
        if exc.response.get("Error",{}).get("Code") not in ("404","NotFound","NoSuchKey"):raise
        s3.put_object(Bucket=BUCKET,Key=key,Body=body,ContentType="application/json",CacheControl="private,no-store")
    if s3.head_object(Bucket=BUCKET,Key=key)["ContentLength"]!=len(body):raise RuntimeError("Checkpoint size mismatch")
    summary["checkpoint_key"]=key
    s3.put_object(Bucket=BUCKET,Key=ROOT+"targeted-source-verification/latest-summary.json",Body=json.dumps(summary,sort_keys=True).encode(),ContentType="application/json",CacheControl="private,no-store")
    print("WS3_TARGETED_SOURCE_VERIFICATION "+json.dumps({k:v for k,v in summary.items() if k not in ("checkpoint_key","dedup_checkpoint")},sort_keys=True))
if __name__=="__main__":main()
