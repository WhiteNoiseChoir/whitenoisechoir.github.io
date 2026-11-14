#!/usr/bin/env python3
"""Private ONLY canonical WS1 + WS2 metadata index sync into GitHub via existing bridge.
Not a live query API; the index becomes ChatGPT-readable after Private repo setup.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
import requests
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import sync_r2_metadata_private_github as common

SOURCE="internal/ai-metadata-index/v1/current.json"
WS2="internal/ws2-sleep-relax-enrichment/v1/"
MIN_ROWS=15000

def get_json(s3,key,cap=9000000):
    with s3.get_object(Bucket=common.BUCKET,Key=key)["Body"] as f:
        data=f.read(cap+1)
    if len(data)>cap:raise RuntimeError("Private R2 JSON exceeds limit")
    return json.loads(data)

def ws2_roles(s3,digest,total):
    root=WS2+"source-"+digest[:16]+"/"
    try:checkpoint=get_json(s3,root+"checkpoint.json")
    except ClientError as exc:
        if exc.response.get("Error",{}).get("Code") in ("404","NoSuchKey","NotFound"):
            return {},{"processed":0,"status":"NOT_AVAILABLE"}
        raise
    if checkpoint.get("source_index_sha256")!=digest:
        raise RuntimeError("WS2 checkpoint and canonical WS1 index do not match")
    end=int(checkpoint.get("processed",0))
    if end<0 or end>total or (end%500 and end!=total) or int(checkpoint.get("errors",0))!=0:
        raise RuntimeError("WS2 checkpoint is inconsistent")
    hints={}
    for start in range(0,end,500):
        stop=min(start+500,end)
        chunk=get_json(s3,root+"batches/"+f"{start:06d}-{stop:06d}.json")
        if chunk.get("schema")!="wnc_ws2_batch_v1" or chunk.get("source_index_sha256")!=digest or int(chunk.get("offset",-1))!=start:
            raise RuntimeError("WS2 batch provenance mismatch")
        data=chunk.get("records",[])
        if len(data)!=stop-start:raise RuntimeError("WS2 batch is incomplete")
        for x in data:
            rid=str(x.get("id") or "")
            role=(x.get("composition") or {}).get("role_hint","UNKNOWN")
            if not rid or rid in hints or role not in ("CONTINUOUS_BED","TEXTURE","EVENT","UNKNOWN"):
                raise RuntimeError("WS2 duplicate id or invalid role")
            hints[rid]=role
    if len(hints)!=end:raise RuntimeError("WS2 overlay missing records")
    return hints,{"processed":end,"status":"COMPLETE" if end==total else "PARTIAL"}

def export(s3,where):
    manifest=get_json(s3,SOURCE)
    digest=str(manifest.get("index_sha256") or "").lower()
    key=str(manifest.get("index_r2_key") or "")
    if not re.fullmatch(r"[a-f0-9]{64}",digest) or not key.startswith("internal/ai-metadata-index/v1/versions/") or not key.endswith(".sqlite"):
        raise RuntimeError("Invalid canonical WS1 index pointer")
    database=Path(where)/"source.sqlite"
    s3.download_file(common.BUCKET,key,str(database))
    if hashlib.sha256(database.read_bytes()).hexdigest()!=digest:
        raise RuntimeError("Private R2 canonical SQLite SHA mismatch")
    db=sqlite3.connect("file:"+str(database)+"?mode=ro",uri=True)
    db.row_factory=sqlite3.Row
    required={"id","source_class","name","description","scientific_name","sound_family","habitat","region","provider","source_page","license","duration","r2_key","tags","taxon","qa_status"}
    cols={x["name"] for x in db.execute("PRAGMA table_info(assets)")}
    if not required.issubset(cols):raise RuntimeError("Canonical WS1 SQLite schema mismatch")
    n=db.execute("SELECT count(*) FROM assets").fetchone()[0]
    if n!=int(manifest.get("indexed_total",0)) or n<MIN_ROWS:
        raise RuntimeError("Canonical WS1 SQLite row count mismatch")
    overlay,ws2=ws2_roles(s3,digest,n)
    media=defaultdict(dict)
    for obj in common.objects(s3,common.AUDIO_PREFIXES):
        m=common.AUDIO.search(obj["Key"])
        if m and obj["Size"]>0:media[m[1].lower()][obj["Key"]]=int(obj["Size"])
    groups=defaultdict(list)
    classes=Counter()
    status=Counter()
    for r in db.execute("SELECT * FROM assets ORDER BY id"):
        rid=str(r["id"] or "")
        cls=str(r["source_class"] or "")
        if cls not in ("nature","music"):raise RuntimeError("Unexpected canonical source class")
        h=rid[7:] if cls=="nature" and rid.startswith("nature:") else ""
        if cls=="nature" and not re.fullmatch(r"[a-f0-9]{64}",h):
            raise RuntimeError("Unexpected nature SHA")
        key=str(r["r2_key"] or "")
        ok=bool(h and key.startswith(common.AUDIO_PREFIXES) and key in media.get(h,{}))
        license_name=common.clean(r["license"],70)
        family=common.group_name(r["sound_family"])
        role=overlay.get(rid,"UNKNOWN")
        duration=r["duration"]
        try:
            duration=float(duration)
            if duration<=0 or duration>604800:duration=None
        except (ValueError,TypeError):duration=None
        item={
            "id":"r2-"+h if ok else rid,
            "source_id":rid,"class":cls,
            "name":common.clean(r["name"],180),
            "description":common.clean(r["description"],350),
            "family":common.clean(r["sound_family"],100),
            "species":common.clean(r["scientific_name"],140),
            "taxon":common.clean(r["taxon"],100),
            "habitat":common.clean(r["habitat"],150),
            "region":common.clean(r["region"],90),
            "tags":common.clean(r["tags"],250),
            "provider":common.clean(r["provider"],90),
            "source_url":common.safe_url(r["source_page"]),
            "license":license_name,
            "duration_s":round(duration,3) if duration is not None else None,
            "r2_key":key if ok else None,
            "r2_bytes":media[h][key] if ok else None,
            "availability":"R2_OBJECT_LISTED" if ok else "METADATA_ONLY",
            "playback":"UNVERIFIED",
            "rights":"LICENSE_DECLARED_REVIEW" if license_name.upper() in ("CC0","CC0-1.0","PUBLIC DOMAIN","PUBLIC-DOMAIN","CC-BY-3.0","CC-BY-4.0") else "NEEDS_RIGHTS_REVIEW",
            "qa_status":common.clean(r["qa_status"],50),
            "composition_role":role,
            "role_evidence":"LEXICAL_UNVERIFIED" if rid in overlay and role!="UNKNOWN" else "UNKNOWN_OR_UNENRICHED",
            "sleep_suitability":"UNVERIFIED",
            "relaxation_suitability":"UNVERIFIED"
        }
        groups[(cls,family)].append(item)
        classes[cls]+=1
        status[item["availability"]]+=1
    db.close()
    index=Path(where)/"index"
    index.mkdir(parents=True,exist_ok=True)
    folders=[]
    for (cls,family),items in sorted(groups.items()):
        items.sort(key=lambda x:(x["name"].lower(),x["source_id"]))
        paths=[]
        for start in range(0,len(items),100):
            rel=f"index/groups/{cls}/{family}/part-{start//100+1:03d}.jsonl"
            out=Path(where)/rel
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text("".join(json.dumps(v,ensure_ascii=False,separators=(",",":"))+"\n" for v in items[start:start+100]),encoding="utf8")
            paths.append(rel)
        folders.append({"class":cls,"family":family,"count":len(items),"files":paths})
    report={
        "schema_version":2,"generated_utc":datetime.now(timezone.utc).isoformat(),
        "source":"Private canonical WS1 SQLite FTS5; WS2 lexical role overlay",
        "ws1_sha256":digest,"ws1_total":n,"index_unique_records":sum(classes.values()),
        "source_class_counts":dict(classes),"availability":dict(status),
        "ws2_role_overlay":ws2,"groups":folders,
        "caveats":["R2_OBJECT_LISTED != checksum verified, WebAudio playable or approved",
                   "Music candidates may not have an R2 audio object",
                   "Role and sleep suitability have NOT been acoustically verified",
                   "WS3 new discoveries are not included until canonical WS1 is refreshed"]
    }
    if report["index_unique_records"]!=n:raise RuntimeError("Export loss")
    (index/"manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    (Path(where)/"README.md").write_text(
        "# WhiteNoiseChoir private canonical metadata search index\n\n"
        "Read index/manifest.json and then selected index/groups/CLASS/FAMILY/part-NNN.jsonl shards.\n"
        "Source is the verified R2 WS1 index, with checked WS2 role hints.\n"
        "No audio copied. Rights, playback, acoustic properties and sleep suitability are not certified.\n"
        "NEVER make this repository public.\n",encoding="utf8")
    return report

def main():
    import sys
    local="--local-only" in sys.argv
    token=os.environ.get("WNC_METADATA_REPO_TOKEN","")
    if not local:
        if not token:raise RuntimeError("Missing WNC_METADATA_REPO_TOKEN; nothing synchronized")
        response=requests.get("https://api.github.com/repos/"+common.DEST,
            headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json"},timeout=25)
        if response.status_code!=200 or not response.json().get("private"):
            raise RuntimeError("SECURITY BLOCK: expected private GitHub repository not accessible")
    s3=boto3.client("s3",region_name="auto",endpoint_url=common.ENDPOINT,
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",s3={"addressing_style":"path"},retries={"max_attempts":5,"mode":"standard"}))
    with tempfile.TemporaryDirectory() as d:
        result=export(s3,d)
        if local:updated=False
        else:updated=common.publish(d,token)
        print("PRIVATE_CANONICAL_INDEX_OK",json.dumps({
            "records":result["index_unique_records"],
            "classes":result["source_class_counts"],
            "r2_listed":result["availability"].get("R2_OBJECT_LISTED",0),
            "ws2_processed":result["ws2_role_overlay"]["processed"],
            "private_sync_done":not local,"updated":updated
        },ensure_ascii=False))
if __name__=="__main__":main()
