#!/usr/bin/env python3
"""Read-only QA of eight imported music files, Cloudflare media Range and CORS.

This validates technical accessibility for the private Studio trial; it is
NOT a subjective listening test or clearance of commercial music rights.
"""
import json
from pathlib import Path
import os
import sys
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config

ORIGIN = "https://whitenoisechoir.com"
MEDIA = "https://media.whitenoisechoir.com/"
ACCOUNT_ID = "86bcd68281bc9476cbeeefffd7fe071d"
BUCKET = "whitenoisechoir-media"


def sources():
    raw = Path("studio-catalog.js").read_text()
    assets = json.loads(raw[raw.index("["):raw.rindex("]")+1])
    tracks = json.loads(Path("data/studio-trials.json").read_text())
    trial = next(row for row in tracks if row.get("slug") ==
                 "music-eight-source-preview-20261113")
    assert trial["project"]["length"] == 600
    refs = {row["assetRef"] for row in trial["project"]["tracks"]}
    music = [a for a in assets if a.get("group") == "music"
             and "r2-" + a.get("sha256", "") in refs]
    assert len(music) == len(refs) == 8
    for asset in music:
        assert asset["key"].startswith("asset-library/raw/sha256/")
        assert not asset["publicationApproved"]
    return music


def r2():
    return boto3.client("s3",region_name="auto",
        endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",
            s3={"addressing_style":"path"},retries={"max_attempts":3,"mode":"standard"}))


def verify(s3, asset):
    key=asset["key"]
    obj=s3.head_object(Bucket=BUCKET,Key=key)
    size=int(obj.get("ContentLength",0))
    if size<=2048:raise RuntimeError("R2 object is unexpectedly small")
    if obj.get("Metadata",{}).get("sha256") != asset["sha256"]:
        raise RuntimeError("R2 SHA metadata mismatch")
    request=Request(MEDIA+key,headers={
       "Origin":ORIGIN,
       "Range":"bytes=0-2047",
       "User-Agent":"WhiteNoiseChoir-MusicTrial-TechnicalSmoke/1.0",
    })
    with urlopen(request,timeout=40) as r:
        code=r.status
        content=r.read(2048)
        typ=r.headers.get("Content-Type","")
        cors=r.headers.get("Access-Control-Allow-Origin","")
        range_=r.headers.get("Content-Range","")
    if code!=206 or len(content)!=2048 or not range_.startswith("bytes 0-2047/"):
        raise RuntimeError(f"Media Range failed: {code}, {range_}, {len(content)}")
    if cors not in ("*", ORIGIN):
        raise RuntimeError("Media CORS does not allow owner Studio")
    if not (typ.startswith("audio/") or typ.startswith("application/ogg") or typ.startswith("application/octet-stream")):
        raise RuntimeError("Unexpected media Content-Type: "+typ)
    return {"key_sha_prefix":asset["sha256"][:10],
        "r2_bytes":size, "http_range_status":code,
        "media_type":typ,"cors":cors,"state":"HTTP_RANGE_R2_HEAD_PASS"}


def main():
    assets=sources()
    client=r2()
    passed=0
    failures=[]
    for a in assets:
        try:
            item=verify(client,a)
            passed+=1
            print("MUSIC_TRIAL_SOURCE_QA "+json.dumps(item),flush=True)
        except Exception as exc:
            failures.append({"sha_prefix":a["sha256"][:10],
                             "error":str(exc)[:190]})
            print("MUSIC_TRIAL_SOURCE_QA_FAIL "+json.dumps(failures[-1]),flush=True)
    print("MUSIC_TRIAL_R2_FINAL "+json.dumps({
        "sources":len(assets),"http_r2_access_passed":passed,
        "failed":len(failures),"failures":failures,
        "subjective_audio_listening_tested":False,
        "browser_studio_playback_tested":False,
        "rights_to_youtube_export_verified":False,
    }),flush=True)
    if failures:sys.exit(1)


if __name__=="__main__":
    main()
