#!/usr/bin/env python3
"""Import official Kenney CC0 original ZIP-pack sound files to R2, unchanged.

The publisher lists CC0 for each explicitly enumerated pack. This downloader does
not crawl general catalogs, transcode, run human listening QA, or modify the site.
Keep original source provenance; mark imported sounds unreviewed/unpublished.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import mimetypes
import os
import pathlib
import re
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ACCOUNT_ID = "7483501ad8365fe26b0448b96b54fb9f"
BUCKET = "whitenoisechoir-media"
ROOT = "asset-library/kenney/"
AUDIO = {".wav", ".ogg", ".oga", ".opus", ".mp3", ".flac", ".m4a", ".aif", ".aiff"}
CONTENT_TYPES = {".wav": "audio/wav", ".ogg": "audio/ogg", ".oga": "audio/ogg",
                 ".opus": "audio/ogg", ".mp3": "audio/mpeg", ".flac": "audio/flac",
                 ".m4a": "audio/mp4", ".aif": "audio/aiff", ".aiff": "audio/aiff"}
# Explicit CC0 licenses verified on individual publisher pages on 2026-11-11.
# Counts below are publishers' pack counts, NOT previously harvested R2 files.
PACKS = [
    ("interface-sounds", "interface-ui", 100),
    ("ui-audio", "interface-ui", 50),
    ("impact-sounds", "impact-foley", 130),
    ("rpg-audio", "foley-rpg", 50),
    ("digital-audio", "synthetic-sci-fi", 60),
    ("sci-fi-sounds", "engines-sci-fi", 70),
    ("casino-audio", "cards-dice-foley", 50),
]
UA = "WhiteNoiseChoirCC0Archive/1.0 (https://whitenoisechoir.com; original pack archival)"
# Publisher-verified direct free-download links (11 Nov 2026). Pack pages are rechecked for CC0.
OFFICIAL_ZIPS = {
    "interface-sounds": "https://kenney.nl/media/pages/assets/interface-sounds/fa43c1dd4d-1677589452/kenney_interface-sounds.zip",
    "ui-audio": "https://kenney.nl/media/pages/assets/ui-audio/490d233f68-1677590494/kenney_ui-audio.zip",
    "impact-sounds": "https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip",
    "rpg-audio": "https://kenney.nl/media/pages/assets/rpg-audio/8e99002d76-1677590336/kenney_rpg-audio.zip",
    "digital-audio": "https://kenney.nl/media/pages/assets/digital-audio/216eac4753-1677590265/kenney_digital-audio.zip",
    "sci-fi-sounds": "https://kenney.nl/media/pages/assets/sci-fi-sounds/6b296f9ecf-1677589334/kenney_sci-fi-sounds.zip",
    "casino-audio": "https://kenney.nl/media/pages/assets/casino-audio/2472606a04-1721639069/kenney_casino-audio.zip"
}


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def source_page(slug):
    return "https://kenney.nl/assets/" + slug

def check_zip_url(url, slug):
    parsed = urllib.parse.urlparse(url)
    return (parsed.scheme == "https" and parsed.netloc == "kenney.nl"
            and parsed.path.startswith("/media/pages/assets/" + slug + "/")
            and parsed.path.lower().endswith(".zip"))

def pack_zip_url(slug, page_html):
    # Work only with files linked from the publisher's own explicitly CC0 page.
    plain = html.unescape(re.sub(r"<[^>]+>", " ", page_html))
    if not re.search(r"Creative\s+Commons\s+CC0", plain, re.I):
        raise ValueError("Publisher CC0 license evidence missing")
    urls = re.findall(r'href\s*=\s*["\x27]([^"\x27]+\.zip(?:\?[^"\x27]*)?)["\x27]',
                      html.unescape(page_html), re.I)
    for href in urls:
        url = urllib.parse.urljoin(source_page(slug), href)
        if check_zip_url(url, slug):
            return url
    raise ValueError("No verified original publisher ZIP download link")

def request(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    return urllib.request.urlopen(req, timeout=timeout)

def download_pack(slug, max_bytes):
    with request(source_page(slug), 45) as response:
        if response.geturl().rstrip("/") != source_page(slug):
            raise ValueError("unexpected pack page redirect")
        body = response.read(2_000_000).decode("utf-8")
    # Some Kenney pages render the ZIP link dynamically; use an individually
    # verified official free-download URL only after runtime CC0 page check.
    try:
        url = pack_zip_url(slug, body)
    except ValueError as exc:
        if str(exc) != "No verified original publisher ZIP download link":
            raise
        url = OFFICIAL_ZIPS[slug]
        if not check_zip_url(url, slug):
            raise ValueError("publisher-verified archive URL rejected")
    with tempfile.NamedTemporaryFile(prefix="wnc-kenney-", suffix=".zip", delete=False) as out:
        path = pathlib.Path(out.name)
    try:
        total = 0
        with request(url) as response, path.open("wb") as out:
            if not check_zip_url(response.geturl(), slug):
                raise ValueError("unexpected archive redirect host/path")
            while True:
                piece = response.read(1024 * 1024)
                if not piece:
                    break
                total += len(piece)
                if total > max_bytes:
                    raise ValueError("pack exceeds maximum archive size")
                out.write(piece)
        if not zipfile.is_zipfile(path):
            raise ValueError("download response is not a ZIP archive")
        return path, url, total
    except BaseException:
        path.unlink(missing_ok=True)
        raise

def sound_entry(info, max_bytes):
    name = info.filename
    parts = pathlib.PurePosixPath(name).parts
    ext = pathlib.PurePosixPath(name).suffix.lower()
    if (info.is_dir() or not parts or ".." in parts or name.startswith("/")
            or "\\" in name or "__MACOSX" in parts or ext not in AUDIO):
        return False
    if info.file_size < 200 or info.file_size > max_bytes:
        return False
    return True

def ffprobe(path):
    proc = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration:stream=codec_type,codec_name,sample_rate,channels,duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=45)
    if proc.returncode:
        raise ValueError("invalid source audio")
    obj = json.loads(proc.stdout)
    streams = [s for s in obj.get("streams", []) if s.get("codec_type") == "audio"]
    if not streams:
        raise ValueError("no audio stream")
    stream = streams[0]
    value = obj.get("format", {}).get("duration") or stream.get("duration") or 0
    duration = float(value)
    if not 0.01 <= duration <= 86400:
        raise ValueError("invalid source duration")
    return stream, round(duration, 3)

def head(s3, key):
    try:
        return s3.head_object(Bucket=BUCKET, Key=key)
    except ClientError as exc:
        if str(exc.response.get("Error", {}).get("Code")) in ("404", "NoSuchKey", "NotFound"):
            return None
        raise

def existing_hashes(s3):
    found = {}
    for prefix in ("asset-library/commons/sha256/", ROOT + "sha256/"):
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                match = re.search(r"/([0-9a-f]{64})\.[a-z0-9]+$", key)
                if match:
                    found.setdefault(match.group(1), key)
    return found

def store_sidecar(s3, digest, row):
    key = ROOT + "records/" + digest[:2] + "/" + digest + ".json"
    if not head(s3, key):
        body = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        s3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType="application/json",
                      Metadata={"kind": "original-pack-provenance", "sha256": digest})
    if not head(s3, key):
        raise RuntimeError("R2 sidecar verification failed")
    return key

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-files", type=int, default=750)
    parser.add_argument("--max-total-mb", type=int, default=900)
    parser.add_argument("--max-archive-mb", type=int, default=300)
    parser.add_argument("--max-file-mb", type=int, default=40)
    parser.add_argument("--report", default="audits/kenney-cc0-original-harvest-report.json")
    args = parser.parse_args()
    assert 1 <= args.max_files <= 1500
    assert 1 <= args.max_total_mb <= 3000
    assert 1 <= args.max_archive_mb <= 600
    assert 1 <= args.max_file_mb <= 200
    assert os.environ.get("R2_ACCESS_KEY_ID") and os.environ.get("R2_SECRET_ACCESS_KEY")
    s3 = boto3.session.Session().client(
        "s3", region_name="auto",
        endpoint_url="https://" + ACCOUNT_ID + ".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",
                      s3={"addressing_style": "path"},
                      retries={"mode": "standard", "max_attempts": 5},
                      connect_timeout=15, read_timeout=100,
                      request_checksum_calculation="when_required",
                      response_checksum_validation="when_required"))
    indexed = existing_hashes(s3)
    seen = set()
    report = {
        "source": "Kenney official CC0 audio packs", "bucket": BUCKET,
        "prefix": ROOT, "generated_at": utcnow(), "publisher_pages_checked": [],
        "files": [], "errors": [],
        "counts": {"UPLOADED_R2": 0, "REUSED_R2": 0,
                   "DUPLICATE_IN_BATCH": 0, "SKIP_ENTRY": 0, "INVALID_AUDIO": 0},
        "original_audio_unmodified": True, "subjective_audio_review": False,
        "ready_for_public_website": False, "legacy_production_untouched": True}
    total_uploaded = 0
    try:
        for slug, category, stated_count in PACKS:
            if report["counts"]["UPLOADED_R2"] >= args.max_files:
                break
            path = None
            try:
                path, zip_url, archive_size = download_pack(slug, args.max_archive_mb * 1024**2)
                package = {"page": source_page(slug), "archive_url": zip_url,
                           "category": category, "publisher_stated_files": stated_count,
                           "archive_bytes": archive_size, "sound_entries_seen": 0,
                           "uploaded": 0, "reused": 0}
                report["publisher_pages_checked"].append(package)
                with zipfile.ZipFile(path) as z:
                    for info in z.infolist():
                        if report["counts"]["UPLOADED_R2"] >= args.max_files:
                            break
                        if not sound_entry(info, args.max_file_mb * 1024**2):
                            report["counts"]["SKIP_ENTRY"] += 1
                            continue
                        package["sound_entries_seen"] += 1
                        if total_uploaded + info.file_size > args.max_total_mb * 1024**2:
                            report["counts"]["SKIP_ENTRY"] += 1
                            continue
                        with tempfile.NamedTemporaryFile(prefix="wnc-original-",
                                                         suffix=pathlib.Path(info.filename).suffix,
                                                         delete=False) as out:
                            temp = pathlib.Path(out.name)
                        try:
                            digest_obj = hashlib.sha256()
                            size = 0
                            with z.open(info, "r") as stream, temp.open("wb") as out:
                                while True:
                                    data = stream.read(512 * 1024)
                                    if not data:
                                        break
                                    size += len(data)
                                    if size > args.max_file_mb * 1024**2:
                                        raise ValueError("oversized archive member")
                                    digest_obj.update(data)
                                    out.write(data)
                            digest = digest_obj.hexdigest()
                            if digest in seen:
                                report["counts"]["DUPLICATE_IN_BATCH"] += 1
                                continue
                            seen.add(digest)
                            try:
                                audio, duration = ffprobe(temp)
                            except Exception:
                                report["counts"]["INVALID_AUDIO"] += 1
                                continue
                            extension = pathlib.Path(info.filename).suffix.lower()
                            key = indexed.get(digest)
                            state = "REUSED_R2" if key else "UPLOADED_R2"
                            if key:
                                h = head(s3, key)
                                if not h or int(h.get("ContentLength", -1)) != size:
                                    raise RuntimeError("preexisting R2 digest/size mismatch")
                                package["reused"] += 1
                            else:
                                key = ROOT + "sha256/" + digest[:2] + "/" + digest + extension
                                with temp.open("rb") as stream:
                                    s3.put_object(
                                        Bucket=BUCKET, Key=key, Body=stream,
                                        ContentLength=size,
                                        ContentType=CONTENT_TYPES[extension],
                                        Metadata={"sha256": digest, "license": "cc0-1.0",
                                                  "provider": "kenney"})
                                h = head(s3, key)
                                if not h or int(h.get("ContentLength", -1)) != size or h.get("Metadata", {}).get("sha256") != digest:
                                    raise RuntimeError("R2 audio object verification failed")
                                indexed[digest] = key
                                package["uploaded"] += 1
                                total_uploaded += size
                            row = {
                                "schema_version": 1, "audio_sha256": digest,
                                "audio_storage_key": key, "source_provider": "Kenney",
                                "source_page": source_page(slug), "archive_source_url": zip_url,
                                "original_filename": info.filename, "sound_category": category,
                                "creator": "Kenney", "license": "CC0-1.0",
                                "license_evidence_url": source_page(slug),
                                "license_checked_at": utcnow(), "file_bytes": size,
                                "duration_seconds": duration, "codec": audio.get("codec_name"),
                                "sample_rate_hz": audio.get("sample_rate"),
                                "channels": audio.get("channels"),
                                "subjective_content_not_reviewed": True,
                                "ready_for_public_website": False, "ready_for_mixer": False
                            }
                            meta_key = store_sidecar(s3, digest, row)
                            report["files"].append({"state": state, "sha256": digest,
                                                     "key": key, "metadata_key": meta_key,
                                                     "source_page": source_page(slug),
                                                     "original_filename": info.filename,
                                                     "bytes": size})
                            report["counts"][state] += 1
                            print("ASSET_IN_R2 " + json.dumps(
                                {"state": state, "pack": slug, "file": info.filename,
                                 "bytes": size, "key": key}, ensure_ascii=False), flush=True)
                        except Exception as exc:
                            report["errors"].append({"pack": slug, "file": info.filename,
                                                     "error": str(exc)[:200]})
                        finally:
                            temp.unlink(missing_ok=True)
                print("PACK_COMPLETE " + json.dumps(package), flush=True)
            except Exception as exc:
                report["errors"].append({"pack": slug, "error": str(exc)[:300]})
                print("PACK_ERROR " + slug + " " + str(exc)[:220], flush=True)
            finally:
                if path:
                    path.unlink(missing_ok=True)
    finally:
        report["r2_new_uploads"] = report["counts"]["UPLOADED_R2"]
        report["r2_preexisting_verified"] = report["counts"]["REUSED_R2"]
        report["new_file_bytes"] = total_uploaded
        report["status"] = "COMPLETE" if report["r2_new_uploads"] else "NO_NEW_FILES"
        report["finished_at"] = utcnow()
        report_path = pathlib.Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        key = ROOT + "runs/" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".json"
        s3.put_object(Bucket=BUCKET, Key=key, Body=report_path.read_bytes(),
                      ContentType="application/json", Metadata={"kind": "pack-harvest-report"})
        if not head(s3, key):
            raise RuntimeError("R2 run report missing")
        print("HARVEST_FINAL " + json.dumps({
            "new": report["r2_new_uploads"], "reused": report["r2_preexisting_verified"],
            "bytes": total_uploaded, "errors": len(report["errors"]), "report": key}), flush=True)
    if not report["r2_new_uploads"] and not report["r2_preexisting_verified"]:
        raise SystemExit(3)

if __name__ == "__main__":
    main()
