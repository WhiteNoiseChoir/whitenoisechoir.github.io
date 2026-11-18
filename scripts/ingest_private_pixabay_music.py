#!/usr/bin/env python3
"""Private Pixabay music ingestion. Explicitly reviewed sources only; never publishes music."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import boto3
import requests
from botocore.config import Config

BUCKET = "wnc-music-private"
ENDPOINT = "https://7483501ad8365fe26b0448b96b54fb9f.r2.cloudflarestorage.com"
MAX_BYTES = 60_000_000
MAX_REDIRECTS = 4
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
PAGE_RE = re.compile(r"^https://pixabay\.com/music/[a-z0-9-]+/?(?:\?.*)?$", re.I)
ALLOWED_DOWNLOAD_HOSTS = {"cdn.pixabay.com", "pixabay.com", "www.pixabay.com"}


def validate_page(url):
    if not PAGE_RE.fullmatch(url):
        raise ValueError("Source must be a specific Pixabay music page")
    return url


def validate_download_url(url):
    p = urlparse(url)
    if (p.scheme != "https" or p.hostname not in ALLOWED_DOWNLOAD_HOSTS
            or p.username or p.password or p.port not in (None, 443)):
        raise ValueError("Download URL must be HTTPS on an approved Pixabay host")
    if not p.path.lower().endswith(".mp3") and "/download/audio/" not in p.path.lower():
        raise ValueError("Download URL must point to Pixabay MP3 audio")
    return url


def download(url, target):
    with requests.Session() as session:
        for _ in range(MAX_REDIRECTS + 1):
            validate_download_url(url)
            with session.get(url, stream=True, allow_redirects=False, timeout=(10, 45)) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = response.headers.get("Location", "")
                    if not url.startswith("https://"):
                        raise ValueError("Unsafe download redirect")
                    continue
                response.raise_for_status()
                size = 0
                with open(target, "wb") as out:
                    for block in response.iter_content(128 * 1024):
                        if not block:
                            continue
                        size += len(block)
                        if size > MAX_BYTES:
                            raise ValueError("Music file exceeds 60MB cap")
                        out.write(block)
                if size < 4096:
                    raise ValueError("Music file too small")
                return size
    raise ValueError("Too many redirects")


def probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_name,codec_type,sample_rate,channels",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=35, check=True)
    data = json.loads(result.stdout)
    audio = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if len(audio) != 1 or audio[0].get("codec_name") != "mp3":
        raise ValueError("Expected one MP3 audio stream")
    duration = float(data["format"]["duration"])
    if not 5 <= duration <= 7200:
        raise ValueError("Invalid music duration")
    return duration, audio[0]


def main():
    parser = argparse.ArgumentParser()
    for name in ("source_page", "title", "creator", "license_evidence_url"):
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--download-url")
    source.add_argument("--input-file", type=Path,
                        help="Previously approved MP3 file supplied by the owner; avoid refetching Pixabay")
    args = parser.parse_args()
    validate_page(args.source_page)
    if args.download_url:
        validate_download_url(args.download_url)
    if not args.license_evidence_url.startswith("https://pixabay.com/"):
        raise ValueError("Provide a Pixabay license evidence URL")
    if not 1 <= len(args.title.strip()) <= 180 or not 1 <= len(args.creator.strip()) <= 180:
        raise ValueError("Invalid title or creator")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "music.mp3"
        if args.input_file is not None:
            if not args.input_file.is_file() or args.input_file.is_symlink():
                raise ValueError("Input must be a regular MP3 file")
            size = args.input_file.stat().st_size
            if size < 4096 or size > MAX_BYTES:
                raise ValueError("Music file size outside permitted range")
            # Copy into a private bounded temporary workspace; source file stays untouched.
            with args.input_file.open("rb") as inp, path.open("wb") as out:
                while block := inp.read(128 * 1024):
                    out.write(block)
        else:
            size = download(args.download_url, path)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        assert SHA_RE.fullmatch(sha)
        duration, stream = probe(path)
        key = f"internal/licensed-music/v1/sha256/{sha[:2]}/{sha}.mp3"
        metadata_key = f"internal/licensed-music/v1/metadata/{sha}.json"
        client = boto3.client("s3", region_name="auto", endpoint_url=ENDPOINT,
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
        try:
            existing = client.head_object(Bucket=BUCKET, Key=key)
            if existing["ContentLength"] != size:
                raise ValueError("Existing SHA-key object size mismatch")
        except client.exceptions.ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in ("404", "NoSuchKey", "NotFound"):
                raise
            client.upload_file(str(path), BUCKET, key, ExtraArgs={"ContentType": "audio/mpeg"})
        record = {
            "schema": "wnc_private_music_ingest_v1",
            "sha256": sha, "assetRef": "r2-" + sha,
            "r2_bucket": BUCKET, "r2_key": key,
            "group": "music", "name": args.title.strip(), "creator": args.creator.strip(),
            "source_url": args.source_page, "download_origin": "Pixabay",
            "input_method": "OWNER_APPROVED_FILE" if args.input_file else "PIXABAY_HTTPS",
            "license": "Pixabay Content License",
            "license_evidence_url": args.license_evidence_url,
            "license_review": "PENDING_HUMAN_PUBLICATION_REVIEW",
            "attribution": args.creator.strip() + " – " + args.title.strip() + " (Pixabay)",
            "duration_seconds": round(duration, 3), "bytes": size,
            "codec": "mp3", "sample_rate_hz": int(stream.get("sample_rate", 0)),
            "channels": stream.get("channels"),
            "technical_status": "DECODED_NOT_LISTENING_APPROVED",
            "playback_status": "PRIVATE_AUTH_GATEWAY_REQUIRED",
            "studio_ready": False, "publication_approved": False,
            "ingested_utc": datetime.now(timezone.utc).isoformat()
        }
        client.put_object(Bucket=BUCKET, Key=metadata_key,
            Body=json.dumps(record, ensure_ascii=False, indent=2).encode(),
            ContentType="application/json")
        print(json.dumps({"status": "PRIVATE_INGESTED_NOT_PUBLISHED",
                          "assetRef": record["assetRef"], "metadata_key": metadata_key,
                          "duration_seconds": record["duration_seconds"]}))


if __name__ == "__main__":
    main()
