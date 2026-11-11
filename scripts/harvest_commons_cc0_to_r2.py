#!/usr/bin/env python3
"""Fast Commons CC0 sound ingest -> existing R2. No listening, no recoding, no SEO.

Real source bytes are kept in the existing R2 bucket, under asset-library/commons/.
Only sound files whose individual Wikimedia Commons extmetadata explicitly declares
CC0 1.0 are accepted. No other claimed license is inferred. GitHub stays metadata-only.
"""
from __future__ import annotations
import argparse, concurrent.futures, datetime, hashlib, html, json, os, pathlib, re, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

API="https://commons.wikimedia.org/w/api.php"
ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
BUCKET="whitenoisechoir-media"
USER_AGENT="WhiteNoiseChoirSoundArchive/1.0 (https://whitenoisechoir.com; audio-asset-library; respectful Wikimedia API client)"
PREFIX="asset-library/commons/sha256/"
EXT={".ogg":"audio/ogg",".oga":"audio/ogg",".opus":"audio/ogg",".wav":"audio/wav",".mp3":"audio/mpeg",".flac":"audio/flac",".m4a":"audio/mp4",".aiff":"audio/aiff"}
# Distinct queries; each is an audio-concept seed, NOT an SEO page target.
QUERIES=[
 ("rain","rain sound"),("rain-window","rain window"),("thunder","thunder sound"),
 ("river","river sound"),("stream","stream water"),("waterfall","waterfall sound"),
 ("ocean","ocean waves sound"),("wind","wind sound"),("forest","forest ambience"),
 ("birdsong","birds singing sound"),("cuckoo","cuckoo call"),("owl","owl call"),
 ("crickets","crickets sound"),("cicadas","cicada sound"),("frogs","frog call"),
 ("wolves","wolf howling"),("dog","dog barking"),("cats","cat purring"),
 ("farm","rooster crowing"),("horse","horse sound"),("train","train passing sound"),
 ("rail","railway locomotive audio"),("aircraft","airplane sound"),("car","car driving sound"),
 ("boat","boat ship sound"),("fire","fire crackling sound"),("clock","clock ticking sound"),
 ("footsteps","footsteps sound"),("fan","fan noise"),("machine","machine running sound"),
 ("bell","bell sound"),("insects","insect sound"),("underwater","underwater sound"),
 ("door","door creaking sound"),("woods","wood creaking sound"),("traffic","traffic ambience"),
 ("nature","nature sounds"),("animals","animal sound"),("bird-calls","bird call")
]
def get_json(params):
    q=urllib.parse.urlencode({**params,"action":"query","format":"json","formatversion":"2","maxlag":"5"})
    request=urllib.request.Request(API+"?"+q,headers={"User-Agent":USER_AGENT,"Api-User-Agent":USER_AGENT,"Accept":"application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request,timeout=45) as response:
                value=json.load(response)
            if value.get("error"):
                code=value["error"].get("code","")
                if code=="maxlag":
                    time.sleep(min(20,2+attempt*3));continue
                raise RuntimeError("MediaWiki API: "+str(value["error"])[:300])
            return value
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==4:raise
            time.sleep(min(30,int(exc.headers.get("Retry-After","0") or 0) or (2**attempt+2)))
        except (TimeoutError,urllib.error.URLError):
            if attempt==4:raise
            time.sleep(2**attempt+1)
    raise RuntimeError("MediaWiki retry exhaustion")
def val(metadata,key):
    v=metadata.get(key,{})
    return html.unescape(str(v.get("value",""))).strip() if isinstance(v,dict) else ""
def plain(s):
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",s)).strip()[:250]
def candidates(query,offset,page_size):
    data=get_json({"generator":"search","gsrsearch":query+" filetype:audio","gsrnamespace":"6","gsroffset":str(offset),
       "gsrlimit":str(page_size),"prop":"imageinfo","iiprop":"url|mime|size|extmetadata|user"})
    return data.get("query",{}).get("pages",[])
def decide(p,category,max_bytes,*,allow_cc_by=False):
    result={"title":p.get("title"),"category":category}
    ii=(p.get("imageinfo") or [{}])[0]
    filename=str(p.get("title","")).removeprefix("File:")
    # Cheap semantic exclusion, NOT subjective listening QA: Commons search can
    # match a *spoken dictionary word* ("frog", "stream", "owl") instead of its sound.
    # Never bulk-store Lingua Libre/Wiktionary pronunciations as wildlife ambience.
    if (re.match(r"^(?:LL-Q\d+|Kcg-|Lingua[ _-]?Libre|Wiktionary)",filename,re.IGNORECASE)
        or re.search(r"\b(?:pronunciation|spoken[ _-]word|how[ _-]to[ _-]say)\b",filename,re.IGNORECASE)
        or re.fullmatch(r"[A-Za-z][A-Za-z ]{1,23} \([a-z]{2,3}\)\.(?:ogg|oga|wav|mp3)",filename)):
        result["state"]="SKIP_SPOKEN_DICTIONARY";return result
    ext=pathlib.Path(filename).suffix.lower()
    if ext not in EXT:
        result["state"]="SKIP_NOT_SUPPORTED_AUDIO";return result
    if not str(ii.get("mime","")).startswith(("audio/","application/ogg")):
        result["state"]="SKIP_NOT_AUDIO";return result
    size=int(ii.get("size") or 0)
    if size<1200 or size>max_bytes:
        result.update(state="SKIP_SIZE_LIMIT",size=size);return result
    meta=ii.get("extmetadata") or {}
    license_name=val(meta,"LicenseShortName").lower().replace(" ","").replace("-","")
    license_url=val(meta,"LicenseUrl").lower().rstrip("/")
    attribution=plain(val(meta,"Attribution")) or plain(val(meta,"Artist"))
    cc_url=urllib.parse.urlsplit(license_url)
    cc_by=re.fullmatch(r"/licenses/by/(3\.0|4\.0)",cc_url.path)
    if (license_name in {"cc0","cc01.0","cczero","creativecommonzero"}
            and cc_url.hostname=="creativecommons.org" and cc_url.path=="/publicdomain/zero/1.0"):
        source_license="CC0-1.0"
    elif (allow_cc_by and cc_url.hostname=="creativecommons.org" and cc_by and attribution
          and license_name=="ccby"+cc_by.group(1)):
        source_license="CC-BY-"+cc_by.group(1)
    else:
        result.update(state="SKIP_LICENSE_NOT_CC0",license_name=val(meta,"LicenseShortName"));return result
    restrictions=val(meta,"Restrictions")
    if restrictions:
        result.update(state="SKIP_RESTRICTIONS",restrictions=plain(restrictions));return result
    url=str(ii.get("url") or "")
    if not url.startswith("https://upload.wikimedia.org/"):
        result["state"]="SKIP_UNEXPECTED_ORIGIN";return result
    original_page=str(ii.get("descriptionurl") or ("https://commons.wikimedia.org/wiki/"+urllib.parse.quote(p["title"].replace(" ","_"))))
    result.update(state="ELIGIBLE",source_url=original_page,direct_file_url=url,
      size=size,mime=ii.get("mime"),extension=ext,source_license=source_license,attribution=attribution or None,
      license_url=val(meta,"LicenseUrl"),license_short=val(meta,"LicenseShortName"),
      author=plain(val(meta,"Artist")) or None,uploader=ii.get("user"),
      rights_evidence_url=original_page,license_checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      source_provider="Wikimedia Commons",file_name=filename)
    return result
def head(s3,key):
    try:return s3.head_object(Bucket=BUCKET,Key=key)
    except ClientError as exc:
        if str(exc.response.get("Error",{}).get("Code","")) in ("404","NoSuchKey","NotFound"):return None
        raise
def download(row,max_bytes):
    req=urllib.request.Request(row["direct_file_url"],headers={"User-Agent":USER_AGENT,"Accept":"audio/*,application/ogg,*/*"})
    with tempfile.NamedTemporaryFile(prefix="wnc-commons-",suffix=row["extension"],delete=False) as f:
        path=pathlib.Path(f.name)
    try:
        hasher=hashlib.sha256();total=0
        with urllib.request.urlopen(req,timeout=90) as response,path.open("wb") as out:
            if response.geturl().startswith("https://upload.wikimedia.org/") is False:
                raise ValueError("redirected outside Wikimedia upload host")
            while True:
                chunk=response.read(1024*512)
                if not chunk:break
                total+=len(chunk)
                if total>max_bytes:raise ValueError("source exceeded byte cap")
                out.write(chunk);hasher.update(chunk)
        if total!=row["size"]:raise ValueError("source byte count mismatched API metadata")
        probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,codec_name,sample_rate,channels",
          "-of","json",str(path)],capture_output=True,text=True,timeout=45)
        if probe.returncode:raise ValueError("ffprobe error: "+probe.stderr[-200:])
        info=json.loads(probe.stdout)
        sec=float(info.get("format",{}).get("duration") or 0)
        audio=next((x for x in info.get("streams",[]) if x.get("codec_type")=="audio"),None)
        if not audio or not 0.05<=sec<=86400:raise ValueError("invalid audio stream/duration")
        return path,total,hasher.hexdigest(),round(sec,3),audio
    except BaseException:
        path.unlink(missing_ok=True);raise
def upload(s3,row,path,size,digest,dur,stream):
    key=PREFIX+digest[:2]+"/"+digest+row["extension"]
    h=head(s3,key)
    if h:
        if int(h["ContentLength"])!=size or h.get("Metadata",{}).get("sha256")!=digest:
            raise ValueError("existing object checksum/size mismatch; refuse overwrite")
        state="REUSED_R2"
    else:
        with path.open("rb") as data:
            s3.put_object(Bucket=BUCKET,Key=key,Body=data,ContentLength=size,ContentType=EXT[row["extension"]],
              Metadata={"sha256":digest,"license":"cc0-1.0","provider":"wikimedia-commons"},
              CacheControl="public, max-age=31536000, immutable")
        state="UPLOADED_R2"
    h2=head(s3,key)
    if not h2 or int(h2.get("ContentLength",0))!=size or h2.get("Metadata",{}).get("sha256")!=digest:
        raise ValueError("R2 write/readback verification failed")
    # Durable per-file provenance, not an expiring CI artifact. Each source may
    # be retrieved by SHA ID from this small JSON sidecar without rescanning.
    metadata_key="asset-library/commons/records/"+digest[:2]+"/"+digest+".json"
    meta={
      "schema_version":1,"audio_sha256":digest,"audio_storage_key":key,
      "file_title":row["title"],"source_page":row["source_url"],
      "original_filename":row["file_name"],"uploader":row.get("uploader"),
      "creator":row.get("author"),"taxonomy_query_category":row["category"],
      "license":"CC0-1.0","license_evidence_url":row["rights_evidence_url"],
      "license_checked_at":row["license_checked_at"],"file_bytes":size,
      "duration_seconds":dur,"codec":stream.get("codec_name"),
      "sample_rate_hz":stream.get("sample_rate"),"channels":stream.get("channels"),
      "source_metadata_not_subjectively_listened":True,
      "ready_for_public_website":False,"ready_for_mixer":False
    }
    if not head(s3,metadata_key):
        encoded=(json.dumps(meta,ensure_ascii=False,sort_keys=True)+"\n").encode("utf-8")
        s3.put_object(Bucket=BUCKET,Key=metadata_key,Body=encoded,
          ContentType="application/json",Metadata={"sha256":digest,"kind":"source-provenance"})
    if not head(s3,metadata_key):
        raise ValueError("R2 provenance sidecar missing after upload")
    return {"state":state,"storage_key":key,"metadata_storage_key":metadata_key,
      "sha256":digest,"duration_seconds":dur,
      "codec":stream.get("codec_name"),"sample_rate_hz":stream.get("sample_rate"),"channels":stream.get("channels")}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--max-files",type=int,default=40)
    ap.add_argument("--per-query",type=int,default=50)
    ap.add_argument("--offset",type=int,default=0)
    ap.add_argument("--max-file-mb",type=int,default=20)
    ap.add_argument("--max-total-mb",type=int,default=250)
    ap.add_argument("--report",default="audits/commons-first-harvest-report.json")
    args=ap.parse_args()
    assert 1<=args.max_files<=200 and 1<=args.per_query<=50 and 0<=args.offset<=950
    assert 1<=args.max_file_mb<=50 and 1<=args.max_total_mb<=1200
    assert os.getenv("R2_ACCESS_KEY_ID") and os.getenv("R2_SECRET_ACCESS_KEY"),"Missing approved R2 credentials"
    s3=boto3.session.Session().client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",s3={"addressing_style":"path"},retries={"max_attempts":5,"mode":"standard"},
          connect_timeout=15,read_timeout=100,request_checksum_calculation="when_required",
          response_checksum_validation="when_required"))
    report={"status":"RUNNING","source":"Wikimedia Commons CC0 audio","bucket":BUCKET,
      "object_prefix":PREFIX,"public_api_page_license_filter":"CC0 1.0 only","no_listening_qa":True,
      "no_existing_production_changes":True,"max_files":args.max_files,"per_query":args.per_query,
      "offset":args.offset,"queried":[],"files":[],"counts":{},"errors":[]}
    count=0;remote_bytes=0;seen_urls=set();seen_hashes=set()
    max_bytes=args.max_file_mb*1024**2
    start=time.time()
    for cat,query in QUERIES:
        if count>=args.max_files:break
        if time.time()-start>2400:break
        try:pages=candidates(query,args.offset,args.per_query)
        except Exception as exc:
            report["errors"].append({"query":query,"error":repr(exc)[:180]});continue
        candidates_count=0
        for p in pages:
            record=decide(p,cat,max_bytes)
            status=record["state"];report["counts"][status]=report["counts"].get(status,0)+1
            if status!="ELIGIBLE":continue
            url=record["direct_file_url"]
            if url in seen_urls:continue
            seen_urls.add(url);candidates_count+=1
            if count>=args.max_files:break
            if remote_bytes+record["size"]>args.max_total_mb*1024**2:continue
            local=None
            try:
                local,size,digest,duration,stream=download(record,max_bytes)
                if digest in seen_hashes:
                    report["counts"]["SAME_RUN_DUPLICATE"]=report["counts"].get("SAME_RUN_DUPLICATE",0)+1
                    continue
                seen_hashes.add(digest)
                result=upload(s3,record,local,size,digest,duration,stream)
                if result["state"]=="UPLOADED_R2":
                    remote_bytes+=size
                    count+=1
                row={**{k:v for k,v in record.items() if k!="direct_file_url"},**result,"size_bytes":size}
                report["files"].append(row)
                report["counts"][result["state"]]=report["counts"].get(result["state"],0)+1
                print("ASSET_IN_R2 "+json.dumps({"category":cat,"title":row["title"],"state":result["state"],"bytes":size,"seconds":duration,"key":result["storage_key"]},ensure_ascii=False),flush=True)
            except Exception as exc:
                report["errors"].append({"title":record["title"],"error":str(exc)[:190]})
            finally:
                if local:local.unlink(missing_ok=True)
        report["queried"].append({"category":cat,"query":query,"candidates":len(pages),"eligible_distinct":candidates_count})
        print("CATEGORY_SCAN "+json.dumps({"category":cat,"pages":len(pages),"eligible_distinct":candidates_count,"stored_or_reused":count},ensure_ascii=False),flush=True)
    report.update(status="COMPLETE" if count else ("NO_NEW_FILES" if report["counts"].get("REUSED_R2",0) else "ZERO_FILES"),r2_stored_or_reused=report["counts"].get("UPLOADED_R2",0)+report["counts"].get("REUSED_R2",0),
      r2_new_uploads=report["counts"].get("UPLOADED_R2",0),r2_preexisting_verified=report["counts"].get("REUSED_R2",0),
      bytes_verified=remote_bytes,elapsed_seconds=int(time.time()-start),generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    out=pathlib.Path(args.report);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    # Store full run provenance durably in R2; Actions artifacts expire.
    run_key="asset-library/commons/runs/"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")+".json"
    s3.put_object(Bucket=BUCKET,Key=run_key,Body=out.read_bytes(),
      ContentType="application/json",Metadata={"kind":"source-harvest-report"})
    assert head(s3,run_key),"R2 run-report object not saved"
    print("R2_REPORT_SAVED "+run_key,flush=True)
    print("HARVEST_FINAL "+json.dumps({"status":report["status"],"r2_new_uploads":report["r2_new_uploads"],"r2_preexisting_verified":report["r2_preexisting_verified"],
      "bytes_verified":remote_bytes,"queried_count":len(report["queried"]),"errors":len(report["errors"])},ensure_ascii=False),flush=True)
    if not report["r2_stored_or_reused"]:sys.exit(3)
if __name__=="__main__":main()
