#!/usr/bin/env python3
"""Import public-domain USFWS wildlife audio from the Internet Archive originals."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os
from pathlib import Path, PurePosixPath
import tempfile
from urllib.parse import quote, urlsplit

import requests

from harvest_commons_cc0_to_r2 import EXT, USER_AGENT
from harvest_nature_diversity_to_r2 import Intake, emit, file_digest, now, probe, put_json

ITEM = "animalsounds1"
PAGE = f"https://archive.org/details/{ITEM}"
LICENSE = "https://creativecommons.org/licenses/publicdomain/"
HEADERS = {"User-Agent": USER_AGENT}


def originals():
    with requests.get(f"https://archive.org/metadata/{ITEM}", headers=HEADERS, timeout=(15, 50)) as response:
        response.raise_for_status()
        payload = response.json()
    declared = urlsplit(payload["metadata"].get("licenseurl", ""))
    if declared.hostname != "creativecommons.org" or declared.path.rstrip("/") != "/licenses/publicdomain":
        raise ValueError("The item no longer declares the public-domain license")
    return [file for file in payload["files"]
            if file.get("source") == "original" and not file.get("private")
            and PurePosixPath(file["name"]).suffix.lower() in EXT
            and "creativecommons.org/licenses/publicdomain" in file.get("license", "")]


def save_file(intake, original):
    filename = original["name"]
    url = f"https://archive.org/download/{ITEM}/{quote(filename, safe='')}"
    identity = f"internet-archive:{ITEM}:{filename}:{original['sha1']}"
    group = "wildlife-field-recording"
    if intake.cached(identity):
        return {"state": "cached", "bytes": 0, "group": group}
    declared_size = int(original["size"])
    if not 0 < declared_size <= 160 * 1024**2:
        raise ValueError("Unexpected archive file size")
    with tempfile.TemporaryDirectory(prefix="wnc-usfws-") as folder:
        path = Path(folder) / ("source" + PurePosixPath(filename).suffix.lower())
        sha1 = hashlib.sha1()
        size = 0
        with requests.get(url, headers=HEADERS, stream=True, timeout=(15, 90)) as response, path.open("wb") as output:
            response.raise_for_status()
            hostname = urlsplit(response.url).hostname or ""
            if hostname != "archive.org" and not hostname.endswith(".archive.org"):
                raise ValueError("Unexpected Internet Archive download host")
            for block in response.iter_content(256 * 1024):
                size += len(block)
                if size > declared_size:
                    raise ValueError("Download exceeds the published byte count")
                output.write(block)
                sha1.update(block)
        if size != declared_size or sha1.hexdigest() != original["sha1"]:
            raise ValueError("Download does not match Internet Archive's original")
        audio, duration = probe(path)
        return intake.save(path, identity, {
            "source_provider": "Internet Archive / U.S. Fish and Wildlife Service",
            "source_page": PAGE, "license_evidence_url": PAGE, "license_url": LICENSE,
            "license": "Public Domain", "credit": "U.S. Fish and Wildlife Service",
            "download_url": url, "title": original.get("title") or filename,
            "original_filename": filename, "original_sha1": original["sha1"], "group_hint": group,
        }, audio, duration, file_digest(path))


def main():
    intake = Intake()
    candidates = originals()
    report = {"source": "Internet Archive USFWS", "started_at": now(), "candidates": len(candidates),
              "assets": [], "errors": []}
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(save_file, intake, file): file["name"] for file in candidates}
        for future in as_completed(jobs):
            try:
                report["assets"].append(future.result())
            except Exception as exc:
                report["errors"].append({"file": jobs[future], "error": str(exc)[:350]})
    report.update(finished_at=now(), counts=Counter(row["state"] for row in report["assets"]),
                  bytes_added=sum(row["bytes"] for row in report["assets"]))
    key = f"asset-library/sources/internet-archive-usfws/runs/{os.environ.get('GITHUB_RUN_ID', 'local')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}.json"
    put_json(intake.s3, key, report)
    emit("ARCHIVE_FINAL", {k: report[k] for k in ("candidates", "counts", "bytes_added", "errors")} | {"report_key": key})
    if not report["assets"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
