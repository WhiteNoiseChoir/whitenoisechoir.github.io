#!/usr/bin/env python3
"""Collect diverse CC0 nature recordings and retain the original source bytes."""
import argparse
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote
from zipfile import ZipFile

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import requests

import harvest_commons_cc0_to_r2 as commons
from harvest_cc0_github_mirror_to_r2 import ACCOUNT_ID, BUCKET, RAW_ROOT, digest_map, head

ROOT = "asset-library/sources/nature-diversity/"
LICENSE = "https://creativecommons.org/publicdomain/zero/1.0/"
FOREST = [(18909809, 1), (18911328, 2)]
GROUPS = {
    "forest": (["Rainforest sounds"], ["forest ambience", "woodland soundscape", "jungle ambience"]),
    "rivers": (["Sounds of rivers and streams"], ["brook stream", "river rapids", "creek water"]),
    "waterfalls": (["Audio files of waterfalls"], ["waterfall sound"]),
    "lakes-ponds": ([], ["pond ambience", "lake shore waves", "marsh soundscape"]),
    "coast": ([], ["sea surf sound", "pebble beach waves", "ocean coast ambience"]),
    "rain": ([], ["rain on leaves", "rain on roof", "rain puddles", "gentle shower"]),
    "wind": ([], ["wind in trees", "wind leaves", "wind reeds", "rustling grass"]),
    "weather": ([], ["thunderstorm ambience", "snow walking", "ice cracking"]),
    "night": ([], ["night forest ambience", "country night noise", "nocturnal soundscape"]),
    "birds": (["Audio files of Aves", "Sounds of birds"], ["bird dawn chorus", "birdsong field recording"]),
    "owls": (["Audio files of Strigiformes"], ["owl hoot", "tawny owl call"]),
    "cuckoos": ([], ["common cuckoo call", "cuckoo singing"]),
    "waterbirds": ([], ["gull calls", "duck calls", "loon call", "heron call"]),
    "amphibians": (["Audio files of Anura"], ["frog chorus", "toad call", "tree frog call"]),
    "crickets": (["Audio files of Orthoptera"], ["cricket chirping", "katydid night"]),
    "insects": (["Audio files of Insecta"], ["cicada singing", "bee buzzing", "insect night"]),
    "mammals": (["Audio files of Mammalia"], ["deer call", "wolf howl", "fox call", "gibbon call"]),
    "farm-animals": ([], ["horse sounds", "sheep bleating", "cow moo", "goat call", "rooster crow"]),
    "underwater": ([], ["underwater hydrophone", "whale song", "dolphin clicks"]),
    "other-soundscapes": (["Sounds of nature"], ["mountain ambience", "meadow sounds", "cave water drops"]),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def emit(label, data):
    print(label + " " + json.dumps(data, ensure_ascii=False), flush=True)


def file_digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def put_json(s3, key, value, create_only=False):
    kwargs = {"IfNoneMatch": "*"} if create_only else {}
    try:
        s3.put_object(
            Bucket=BUCKET, Key=key, ContentType="application/json",
            Body=(json.dumps(value, ensure_ascii=False) + "\n").encode(), **kwargs
        )
    except ClientError as exc:
        if not create_only or exc.response["ResponseMetadata"]["HTTPStatusCode"] != 412:
            raise


def source_key(identity):
    return ROOT + "records/" + hashlib.sha256(identity.encode()).hexdigest() + ".json"


class Intake:
    def __init__(self):
        self.s3 = boto3.client(
            "s3", region_name="auto", endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            config=Config(signature_version="s3v4", max_pool_connections=12,
                          retries={"max_attempts": 5, "mode": "standard"},
                          request_checksum_calculation="when_required",
                          response_checksum_validation="when_required"),
        )
        self.known = digest_map(self.s3)
        self.lock = threading.Lock()

    def cached(self, identity):
        try:
            response = self.s3.get_object(Bucket=BUCKET, Key=source_key(identity))
        except ClientError as exc:
            if exc.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
                return False
            raise
        with response["Body"] as body:
            previous = json.load(body)
        return previous["audio_sha256"] in self.known

    def save(self, path, identity, meta, audio, duration, digest):
        size = path.stat().st_size
        ext = path.suffix.lower()
        with self.lock:
            known_key = self.known.get(digest)
        key = known_key or f"{RAW_ROOT}{digest[:2]}/{digest}{ext}"
        state = "reused"
        if known_key is None:
            try:
                with path.open("rb") as data:
                    self.s3.put_object(
                        Bucket=BUCKET, Key=key, Body=data, ContentLength=size,
                        IfNoneMatch="*", ContentType=commons.EXT[ext],
                        Metadata={"sha256": digest, "license": "cc0-1.0"},
                    )
                state = "new"
            except ClientError as exc:
                if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 412:
                    raise
        current = head(self.s3, key)
        if not current or current["ContentLength"] != size or current.get("Metadata", {}).get("sha256") != digest:
            raise ValueError("R2 object does not match the downloaded audio")
        record = {
            **meta, "schema_version": 2, "audio_sha256": digest, "audio_storage_key": key,
            "file_bytes": size, "duration_seconds": duration, "codec": audio.get("codec_name"),
            "sample_rate_hz": audio.get("sample_rate"), "channels": audio.get("channels"),
            "classification_status": "pending", "classification_labels": [],
            "license": "CC0-1.0", "license_url": LICENSE, "ingested_at": now(),
        }
        put_json(self.s3, f"asset-library/records/sha256/{digest[:2]}/{digest}.json", record, True)
        put_json(self.s3, source_key(identity), record)
        with self.lock:
            self.known[digest] = key
        return {"state": state, "bytes": size if state == "new" else 0, "key": key, "group": meta["group_hint"]}


def category_pages(root, depth):
    queue = deque([(root, 0)])
    visited = set()
    while queue and len(visited) < 9:
        category, level = queue.popleft()
        if category in visited:
            continue
        visited.add(category)
        if level < depth:
            result = commons.get_json({"list": "categorymembers", "cmtitle": f"Category:{category}",
                                       "cmtype": "subcat", "cmlimit": "40"})
            queue.extend((item["title"].removeprefix("Category:"), level + 1)
                         for item in result.get("query", {}).get("categorymembers", []))
        continuation = {}
        for _ in range(2):
            result = commons.get_json({
                "generator": "categorymembers", "gcmtitle": f"Category:{category}",
                "gcmtype": "file", "gcmlimit": "50", "prop": "imageinfo",
                "iiprop": "url|mime|size|sha1|extmetadata|user", **continuation,
            })
            for item in result.get("query", {}).get("pages", []):
                yield item, category
            continuation = result.get("continue")
            if not continuation:
                break


def find_group(group, spec):
    categories, queries = spec
    streams = [iter(category_pages(category, 1 if group in {"amphibians", "crickets", "insects", "owls"} else 0))
               for category in categories]
    for query in queries:
        rows = commons.candidates(query, 0, 36)
        streams.append(iter((row, query) for row in rows))
    eligible = []
    seen = set()
    while streams and len(eligible) < 15:
        for stream in streams[:]:
            try:
                page, hint = next(stream)
            except StopIteration:
                streams.remove(stream)
                continue
            entry = commons.decide(page, group, 160 * 1024**2)
            if entry["state"] != "ELIGIBLE" or entry["direct_file_url"] in seen:
                continue
            seen.add(entry["direct_file_url"])
            info = page["imageinfo"][0]
            metadata = info.get("extmetadata", {})
            entry["hint"] = hint
            entry["description"] = commons.plain(commons.val(metadata, "ImageDescription"))
            entry["tags"] = commons.val(metadata, "Categories").split("|")[:40]
            entry["revision"] = info.get("sha1") or str(entry["size"])
            eligible.append(entry)
            if len(eligible) >= 15:
                break
    return eligible


def commons_assets(intake, report):
    # Coordinate spacing and cooldown across all Wikimedia media downloads.
    pacing_lock = threading.Lock()
    next_request = 0.0

    def paced_download(row):
        nonlocal next_request
        for attempt in range(3):
            while True:
                with pacing_lock:
                    current = time.monotonic()
                    delay = next_request - current
                    if delay <= 0:
                        next_request = current + 2.0
                        break
                time.sleep(min(delay, 5))
            try:
                return commons.download(row, 160 * 1024**2)
            except HTTPError as exc:
                if exc.code not in {429, 503}:
                    raise
                retry = exc.headers.get("Retry-After", "")
                cooldown = max(15, int(retry)) if retry.isdigit() else 30 * (attempt + 1)
                with pacing_lock:
                    next_request = max(next_request, time.monotonic() + min(cooldown, 180))
                if attempt == 2:
                    raise

    def ingest(row):
        identity = row["direct_file_url"] + "\n" + row["revision"]
        if intake.cached(identity):
            return {"state": "cached", "bytes": 0, "group": row["category"]}
        path, _, digest, duration, audio = paced_download(row)
        try:
            return intake.save(path, identity, {
                "source_provider": "Wikimedia Commons", "source_page": row["source_url"],
                "license_evidence_url": row["source_url"], "download_url": row["direct_file_url"],
                "original_filename": row["file_name"], "title": row["title"], "creator": row["author"],
                "description": row["description"], "source_tags": row["tags"],
                "group_hint": row["category"], "discovery_hint": row["hint"],
            }, audio, duration, digest)
        finally:
            path.unlink(missing_ok=True)

    with ThreadPoolExecutor(max_workers=3) as discovery, ThreadPoolExecutor(max_workers=2) as download:
        group_jobs = {discovery.submit(find_group, group, spec): group for group, spec in GROUPS.items()}
        submitted = set()
        jobs = {}
        for future in as_completed(group_jobs):
            group = group_jobs[future]
            try:
                rows = future.result()
            except Exception as exc:
                report["errors"].append({"group": group, "error": str(exc)[:350]})
                emit("SOURCE_ERROR", report["errors"][-1])
                continue
            report["candidates"][group] = len(rows)
            emit("GROUP_CANDIDATES", {"group": group, "cc0_candidates": len(rows)})
            for row in rows:
                if row["direct_file_url"] in submitted:
                    continue
                submitted.add(row["direct_file_url"])
                jobs[download.submit(ingest, row)] = (group, row["file_name"])
        for future in as_completed(jobs):
            try:
                report["assets"].append(future.result())
            except Exception as exc:
                group, name = jobs[future]
                report["errors"].append({"group": group, "file": name, "error": str(exc)[:350]})


class ZenodoZipReader(io.RawIOBase):
    """Read a public ZIP by byte range without downloading the entire archive."""
    def __init__(self, session, url):
        self.session = session
        self.url = url
        self.pos = 0
        self.start = 0
        self.data = b""
        with self.range_response(0, 0) as response:
            self.size = int(response.headers["Content-Range"].rsplit("/", 1)[1])

    def range_response(self, start, end):
        for attempt in range(4):
            response = self.session.get(self.url, stream=True, timeout=(15, 120),
                headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"})
            expected = f"bytes {start}-{end}/"
            if response.status_code == 206 and response.headers.get("Content-Range", "").startswith(expected):
                return response
            status = response.status_code
            retry = response.headers.get("Retry-After", "")
            response.close()
            if status not in {429, 500, 502, 503, 504} or attempt == 3:
                raise OSError(f"Zenodo byte range unavailable (HTTP {status})")
            time.sleep(min(60, int(retry) if retry.isdigit() else 3 * 2**attempt))

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = (0, self.pos, self.size)[whence] + offset
        if self.pos < 0:
            raise OSError("Negative archive position")
        return self.pos

    def read(self, size=-1):
        remaining = max(0, self.size - self.pos)
        size = remaining if size is None or size < 0 else min(size, remaining)
        parts = []
        while size:
            if not self.start <= self.pos < self.start + len(self.data):
                self.start = self.pos
                end = min(self.size, self.pos + 16 * 1024**2) - 1
                with self.range_response(self.pos, end) as response:
                    self.data = response.content
                if len(self.data) != end - self.start + 1:
                    raise OSError("Truncated archive byte range")
            offset = self.pos - self.start
            block = self.data[offset:offset + size]
            parts.append(block)
            self.pos += len(block)
            size -= len(block)
        return b"".join(parts)


def probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,sample_rate,channels",
         "-of", "json", str(path)], capture_output=True, text=True, timeout=30, check=True)
    info = json.loads(result.stdout)
    audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    return audio, float(info["format"]["duration"])


def forest_assets(intake, report):
    with requests.Session() as session:
        session.headers["User-Agent"] = commons.USER_AGENT
        for record_id, part in FOREST:
            page = f"https://zenodo.org/records/{record_id}"
            filename = f"42937__sensingtheforest__natural-soundscape-dataset-part-{part}.zip"
            url = f"{page}/files/{quote(filename)}?download=1"
            try:
                with ZenodoZipReader(session, url) as reader, ZipFile(reader) as archive:
                    slots = {i: [] for i in range(4)}
                    for item in sorted(archive.infolist(), key=lambda entry: entry.filename):
                        match = re.search(r"(\d{4}-\d{2}-\d{2})_([0-2]\d)([0-5]\d)\.wav$", item.filename)
                        if match and 0 < item.file_size <= 160 * 1024**2:
                            date, hour, minute = match.groups()
                            slots[min(3, int(hour) // 6)].append((item, date, hour + ":" + minute))
                    selected = []
                    for slot, entries in slots.items():
                        sample = [entries[((2 * i + 1) * len(entries)) // 6] for i in range(3)] if len(entries) >= 3 else entries
                        selected.extend((slot, *entry) for entry in sample)
                    report["candidates"][str(record_id)] = len(selected)
                    emit("FOREST_SELECTION", {"record": record_id, "archive_wav_count": sum(map(len, slots.values())),
                                              "selected": len(selected)})
                    for slot, item, date, local_time in selected:
                        group = ("00–06", "06–12", "12–18", "18–24")[slot]
                        try:
                            identity = page + "\n" + item.filename + "\n" + str(item.CRC)
                            if intake.cached(identity):
                                report["assets"].append({"state": "cached", "bytes": 0, "group": group})
                                continue
                            with tempfile.TemporaryDirectory(prefix="wnc-forest-") as folder:
                                path = Path(folder) / "source.wav"
                                with archive.open(item) as source, path.open("wb") as output:
                                    shutil.copyfileobj(source, output, 1024**2)
                                audio, duration = probe(path)
                                result = intake.save(path, identity, {
                                    "source_provider": "Sensing the Forest / Zenodo", "source_page": page,
                                    "license_evidence_url": page, "download_url": url,
                                    "original_filename": PurePosixPath(item.filename).name,
                                    "archive_member": item.filename, "archive_member_crc32": f"{item.CRC:08x}",
                                    "recording_date_from_filename": date, "time_from_filename": local_time,
                                    "location": "Alice Holt woodland, Surrey, UK",
                                    "group_hint": group, "environment_hint": "woodland soundscape",
                                }, audio, duration, file_digest(path))
                                report["assets"].append(result)
                                emit("ASSET_SAVED", {**result, "date": date, "time": local_time})
                        except Exception as exc:
                            report["errors"].append({"file": item.filename, "error": str(exc)[:350]})
                            emit("SOURCE_ERROR", report["errors"][-1])
            except Exception as exc:
                report["errors"].append({"record": record_id, "error": str(exc)[:350]})
                emit("SOURCE_ERROR", report["errors"][-1])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("commons", "forest"), required=True)
    args = parser.parse_args()
    intake = Intake()
    report = {"source": args.source, "started_at": now(), "assets": [], "candidates": {}, "errors": []}
    (commons_assets if args.source == "commons" else forest_assets)(intake, report)
    report.update(finished_at=now(), counts=Counter(row["state"] for row in report["assets"]),
                  groups=Counter(row["group"] for row in report["assets"] if row["state"] == "new"),
                  bytes_added=sum(row["bytes"] for row in report["assets"]))
    key = f"{ROOT}runs/{args.source}/{os.environ.get('GITHUB_RUN_ID', 'local')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}.json"
    put_json(intake.s3, key, report)
    emit("DIVERSITY_FINAL", {name: report[name] for name in ("source", "counts", "groups", "bytes_added", "candidates")}
         | {"report_key": key, "errors": len(report["errors"]), "first_errors": report["errors"][:5]})
    if not report["assets"] and report["errors"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
