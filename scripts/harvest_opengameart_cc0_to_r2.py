#!/usr/bin/env python3
"""Original CC0 sound intake from OpenGameArt. No transcoding or listening gate."""
from __future__ import annotations
import argparse, concurrent.futures as cf, datetime as dt, hashlib, io, json, os
import pathlib, re, shutil, subprocess, tempfile, threading, time, urllib.parse, zipfile
from collections import deque
import boto3, requests
from bs4 import BeautifulSoup
from botocore.config import Config
from harvest_cc0_github_mirror_to_r2 import BUCKET, ACCOUNT_ID, EXTENSIONS, head, sha256, digest_map

ORIGIN = "https://opengameart.org"
RAW = "asset-library/raw/sha256/"
ROOT = "asset-library/sources/opengameart/"
EXTS = {**EXTENSIONS, ".au":"audio/basic", ".wma":"audio/x-ms-wma"}
ARCHIVES = {".zip", ".7z", ".tar", ".tgz", ".gz"}
SEEDS = [
 "animal-sounds", "nature-sounds-cc0", "cc0-sounds-library",
 "ambient-bird-sounds", "bird-chirping-sounds", "park-ambiences",
 "water-waves", "sea-and-river-wave-sounds", "skippy-fish-water-sound-collection",
 "water-splash-and-sand-footsteps", "creature-sounds",
]
UA = "WhiteNoiseChoirAssetIntake/2.0 (+https://whitenoisechoir.com; CC0 audio archive)"
def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()
def emit(label, obj):
    print(label+" "+json.dumps(obj, ensure_ascii=False), flush=True)
def ident(value):
    return hashlib.sha256(value.encode()).hexdigest()
def safe_url(url, asset=False):
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or p.hostname not in {"opengameart.org", "www.opengameart.org"}:
        raise ValueError("Unexpected source host")
    if asset and not p.path.startswith("/sites/default/files/"):
        raise ValueError("Not a publisher file URL")
    return url
def request(url, stream=False):
    safe_url(url)
    for attempt in range(4):
        r = requests.get(url, headers={"User-Agent":UA}, timeout=(15,90),
                         stream=stream, allow_redirects=True)
        safe_url(r.url)
        if r.status_code in {429,500,502,503,504} and attempt < 3:
            delay = r.headers.get("Retry-After","")
            r.close()
            time.sleep(min(45, int(delay) if delay.isdigit() else 2**attempt+1))
            continue
        r.raise_for_status()
        return r
    raise RuntimeError("Source retries exhausted")
def json_get(s3, key):
    try:
        return json.loads(s3.get_object(Bucket=BUCKET,Key=key)["Body"].read())
    except s3.exceptions.NoSuchKey:
        return None
def json_put(s3, key, obj):
    data = (json.dumps(obj,ensure_ascii=False,sort_keys=True)+"\n").encode()
    s3.put_object(Bucket=BUCKET,Key=key,Body=data,ContentType="application/json")
def parse_page(url, text):
    soup = BeautifulSoup(text,"html.parser")
    main = soup.select_one("#content") or soup
    files = main.select_one(".field-name-field-art-files")
    licence = main.select_one(".field-name-field-art-licenses")
    # The submission's own file and licence fields are mandatory.
    cc0 = bool(licence and (
        licence.select_one('img[src*="license_images/cc0"]') or
        licence.select_one('a[href*="creativecommons.org/publicdomain/zero/1.0"]') or
        re.search(r"\bCC0\b",licence.get_text(" ",strip=True))))
    author = main.select_one(".field-name-field-art-author")
    description = main.select_one(".field-name-body")
    title = main.select_one("h1") or soup.select_one("h1")
    tags = [x.get_text(" ",strip=True) for x in main.select(".field-name-field-art-tags a")]
    info = {"source_page":url,"title":title.get_text(" ",strip=True) if title else url,
            "creator":author.get_text(" ",strip=True) if author else None,
            "description":description.get_text(" ",strip=True)[:16000] if description else "",
            "source_tags":tags,"license":"CC0-1.0","license_evidence_url":url,
            "license_checked_at":now()}
    downloads=[]
    if files and cc0:
        for a in files.select("a[href]"):
            u=urllib.parse.urljoin(url,a["href"])
            ext=pathlib.PurePosixPath(urllib.parse.unquote(urllib.parse.urlsplit(u).path)).suffix.lower()
            if ext in EXTS or ext in ARCHIVES:
                try: safe_url(u,asset=True)
                except ValueError: continue
                if u not in downloads: downloads.append(u)
    # Only collections expand to child pages; submission related-links are ignored.
    children=[]
    if not files and "Collected Art" in main.get_text(" ",strip=True):
        for a in main.select('a[href*="/content/"]'):
            u=urllib.parse.urljoin(ORIGIN,a["href"]).split("#",1)[0].split("?",1)[0]
            p=urllib.parse.urlsplit(u)
            if p.hostname in {"opengameart.org","www.opengameart.org"} and p.path.startswith("/content/"):
                u=ORIGIN+p.path
                if u not in children and u != url: children.append(u)
    return info,downloads,children,{"file_field":bool(files),"license_field":bool(licence),"cc0":cc0}
def audio_info(path):
    r=subprocess.run(["ffprobe","-v","error","-show_entries",
        "format=duration:stream=codec_type,codec_name,sample_rate,channels",
        "-of","json",str(path)],capture_output=True,text=True,timeout=30)
    if r.returncode: raise ValueError("Unreadable audio: "+r.stderr[-120:])
    x=json.loads(r.stdout)
    stream=next((v for v in x.get("streams",[]) if v.get("codec_type")=="audio"),None)
    if not stream: raise ValueError("No audio stream")
    duration=x.get("format",{}).get("duration")
    return stream,float(duration) if duration else None
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--max-pages",type=int,default=140)
    ap.add_argument("--max-files",type=int,default=5000)
    ap.add_argument("--max-total-mb",type=int,default=4096)
    ap.add_argument("--report",default="audits/opengameart-harvest.json")
    args=ap.parse_args()
    s3=boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",max_pool_connections=16,
            retries={"max_attempts":5,"mode":"standard"},request_checksum_calculation="when_required",
            response_checksum_validation="when_required"))
    known=digest_map(s3)
    before=len(known)
    lock=threading.Lock()
    gates={}
    report={"started_at":now(),"classification_status":"pending","counts":
        {"new":0,"reused":0,"source_cached":0,"failed":0,"skipped_budget":0},
        "new_bytes":0,"pages":[],"errors":[],"source":"OpenGameArt CC0"}
    reserved=[0,0]
    def ingest(path, original_name, direct_url, meta):
        size=path.stat().st_size
        if not size: raise ValueError("Empty source file")
        digest=sha256(path)
        with lock: gate=gates.setdefault(digest,threading.Lock())
        with gate:
            stream,duration=audio_info(path)
            ext=path.suffix.lower()
            key=known.get(digest)
            state="reused" if key else "new"
            if key is None:
                with lock:
                    if reserved[0]>=args.max_files or reserved[1]+size>args.max_total_mb*1024**2:
                        report["counts"]["skipped_budget"]+=1
                        return None
                    reserved[0]+=1; reserved[1]+=size
                key=RAW+digest[:2]+"/"+digest+ext
                try:
                    with path.open("rb") as f:
                        s3.put_object(Bucket=BUCKET,Key=key,Body=f,ContentLength=size,
                            ContentType=EXTS[ext],Metadata={"sha256":digest,"license":"cc0-1.0"})
                    h=head(s3,key)
                    if not h or h["ContentLength"]!=size or h.get("Metadata",{}).get("sha256")!=digest:
                        raise ValueError("R2 object confirmation failed")
                    with lock: known[digest]=key
                except Exception:
                    with lock: reserved[0]-=1;reserved[1]-=size
                    raise
            row={**meta,"schema_version":2,"audio_sha256":digest,"audio_storage_key":key,
                "original_filename":original_name,"download_url":direct_url,"file_bytes":size,
                "codec":stream.get("codec_name"),"sample_rate_hz":stream.get("sample_rate"),
                "channels":stream.get("channels"),"duration_seconds":duration,
                "classification_status":"pending","classification_labels":[],
                "original_extension":ext,"ingested_at":now(),"bytes_unchanged":True}
            # A source alias preserves every original page even when payloads are reused.
            source_id=ident(meta["source_page"]+"\n"+direct_url+"\n"+original_name)
            record_key=ROOT+"records/"+source_id+".json"
            json_put(s3,record_key,row)
            canonical="asset-library/records/sha256/"+digest[:2]+"/"+digest+".json"
            if not head(s3,canonical): json_put(s3,canonical,row)
            with lock:
                report["counts"][state]+=1
                if state=="new": report["new_bytes"]+=size
                n=report["counts"]["new"]
            if n and n%50==0: emit("INTAKE_PROGRESS",{"new":n,"new_bytes":report["new_bytes"]})
            return {"sha256":digest,"key":key,"record_key":record_key}
    def download_one(url,meta):
        ledger=ROOT+"downloads/"+ident(url)+".json"
        cached=json_get(s3,ledger)
        if cached and cached.get("complete") and all(head(s3,x["key"]) for x in cached.get("assets",[])):
            with lock: report["counts"]["source_cached"]+=1
            return
        with tempfile.TemporaryDirectory(prefix="wnc-oga-") as folder:
            tmp=pathlib.Path(folder)
            name=pathlib.PurePosixPath(urllib.parse.unquote(urllib.parse.urlsplit(url).path)).name
            payload=tmp/("payload"+pathlib.Path(name).suffix.lower())
            total=0
            with request(url,stream=True) as r,payload.open("wb") as f:
                for block in r.iter_content(1024*512):
                    total+=len(block)
                    if total>768*1024**2: raise ValueError("Source package exceeds 768 MiB intake limit")
                    f.write(block)
            ext=payload.suffix.lower()
            local=[]
            if ext in EXTS:
                local=[(payload,name)]
            elif ext==".zip":
                with zipfile.ZipFile(payload) as z:
                    unpacked=0
                    for n,entry in enumerate(z.infolist()):
                        e=pathlib.PurePosixPath(entry.filename)
                        if e.suffix.lower() not in EXTS or e.name.startswith("._") or "__MACOSX" in e.parts: continue
                        unpacked+=entry.file_size
                        if entry.file_size>768*1024**2 or unpacked>4096*1024**2:
                            raise ValueError("Package exceeds unpacked intake budget")
                        p=tmp/(str(n)+e.suffix.lower())
                        with z.open(entry) as src,p.open("wb") as out: shutil.copyfileobj(src,out)
                        local.append((p,entry.filename))
            elif ext==".7z":
                import py7zr
                dest=tmp/"unpacked"; dest.mkdir()
                with py7zr.SevenZipFile(payload,"r") as z:
                    for name_in_zip in z.getnames():
                        candidate=(dest/name_in_zip).resolve()
                        if not candidate.is_relative_to(dest.resolve()): raise ValueError("Unsafe archive member")
                    z.extractall(path=dest)
                for p in dest.rglob("*"):
                    if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(dest.resolve()) and p.suffix.lower() in EXTS:
                        local.append((p,p.relative_to(dest).as_posix()))
            else:
                raise ValueError("Unsupported package format "+ext)
            if not local: raise ValueError("No supported audio in source payload")
            futures=[audio_pool.submit(ingest,p,n,url,meta) for p,n in local]
            assets=[]; failures=[]
            for f in cf.as_completed(futures):
                try:
                    row=f.result()
                    if row: assets.append(row)
                    else: failures.append("budget")
                except Exception as e: failures.append(str(e)[:200])
            json_put(s3,ledger,{"complete":not failures,"download_url":url,"source_page":meta["source_page"],
                "payload_sha256":sha256(payload),"assets":assets,"errors":failures,"updated_at":now()})
            if failures: raise ValueError(str(failures[:3]))
    queue=deque(ORIGIN+"/content/"+s for s in SEEDS)
    visited=set()
    with cf.ThreadPoolExecutor(max_workers=8) as audio_pool,cf.ThreadPoolExecutor(max_workers=2) as download_pool:
        while queue and len(visited)<args.max_pages:
            url=queue.popleft()
            if url in visited: continue
            visited.add(url)
            try:
                with request(url) as r: page=r.text
                meta,files,children,flags=parse_page(url,page)
                queue.extend(x for x in children if x not in visited)
                if files:
                    evidence=ROOT+"pages/"+ident(url)+"/"+ident(page)+".html"
                    s3.put_object(Bucket=BUCKET,Key=evidence,Body=page.encode(),ContentType="text/html")
                    meta["license_snapshot_key"]=evidence
                row={"url":url,"files":len(files),"discovered":len(children),**flags}
                report["pages"].append(row)
                emit("SOURCE_PAGE",row)
                futures={download_pool.submit(download_one,u,meta):u for u in files}
                for f in cf.as_completed(futures):
                    try: f.result()
                    except Exception as e:
                        report["counts"]["failed"]+=1
                        report["errors"].append({"url":futures[f],"error":str(e)[:250]})
                        emit("SOURCE_ERROR",report["errors"][-1])
            except Exception as e:
                report["errors"].append({"url":url,"error":str(e)[:250]})
                emit("SOURCE_ERROR",report["errors"][-1])
            if report["counts"]["new"]>=args.max_files or reserved[1]>=args.max_total_mb*1024**2: break
    after=digest_map(s3)
    report.update(finished_at=now(),unique_before=before,unique_after=len(after),
        status="COMPLETE" if report["counts"]["new"] else "NO_NEW_FILES")
    output=pathlib.Path(args.report); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    key=ROOT+"runs/"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%f")+".json"
    json_put(s3,key,report)
    emit("HARVEST_FINAL",{"counts":report["counts"],"new_bytes":report["new_bytes"],
        "unique_before":before,"unique_after":len(after),"pages":len(visited),"report_key":key})
    if not report["counts"]["new"] and not report["counts"]["reused"] and not report["counts"]["source_cached"]:
        raise SystemExit(3)
if __name__=="__main__":
    main()
