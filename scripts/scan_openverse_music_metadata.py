#!/usr/bin/env python3
"""Openverse official API music candidate metadata intake.

Only openly indexed source references are discovered. No scraping, audio
downloads, attribution clearance, composition clearance or Studio writes.
Anonymous API rate limits are respected. Source license claims are unverified.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import scan_music_candidate_metadata as core

API = "https://api.openverse.org/v1/audio/"
LICENSES = {
    "https://creativecommons.org/publicdomain/zero/1.0": ("cc0", "CC0-1.0"),
    **{f"https://creativecommons.org/licenses/by/{v}": ("by", f"CC-BY-{v}")
       for v in ("2.0", "2.5", "3.0", "4.0")},
}
SKIP = re.compile(r"\b(?:bootleg|karaoke|copyright infringement|soundtrack rip|pirated)\b", re.I)
EXCLUDE_SOURCES = ("wikimedia", "internet_archive", "internetarchive", "internet archive")


def now():
    return datetime.now(timezone.utc).isoformat()


def https_url(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        return None
    return value


def license_claim(row):
    code = row.get("license", "").lower() if isinstance(row.get("license"), str) else ""
    raw = row.get("license_url")
    if not isinstance(raw, str):
        return None
    url = urlsplit(raw.strip())
    if url.scheme != "https" or url.hostname != "creativecommons.org":
        return None
    path = f"https://{url.hostname}{url.path.rstrip('/').lower()}"
    expected = LICENSES.get(path)
    if expected and expected[0] == code:
        return expected[1]
    return None


def stable_id(page_url):
    parts = urlsplit(page_url)
    canonical = urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                            parts.path.rstrip("/"), parts.query, ""))
    return "music-candidate-" + hashlib.sha256(("openverse\n" + canonical).encode()).hexdigest()


def reported_number(value):
    if isinstance(value, bool):
        return None
    try:
        converted = float(value)
    except (ValueError, TypeError):
        return None
    return converted if math.isfinite(converted) and converted >= 0 else None


def build_candidate(row, group, query):
    source_page = https_url(row.get("foreign_landing_url"))
    if not source_page:
        return None, "skip_no_https_source_page"
    source = str(row.get("source") or row.get("provider") or "").lower()
    if any(x in source for x in EXCLUDE_SOURCES):
        return None, "skip_existing_provider"
    if "archive.org" in urlsplit(source_page).hostname or "wikimedia.org" in urlsplit(source_page).hostname:
        return None, "skip_existing_provider"
    license_name = license_claim(row)
    if not license_name:
        return None, "skip_license_not_cc0_or_by"
    if row.get("mature"):
        return None, "skip_mature"
    title = str(row.get("title") or "")
    if SKIP.search(title):
        return None, "skip_unsuitable"
    ident = str(row.get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,90}", ident):
        return None, "skip_missing_openverse_id"
    tags = [str(t.get("name")).strip() for t in (row.get("tags") or [])
            if isinstance(t, dict) and isinstance(t.get("name"), str)][:50]
    ext = row.get("filetype")
    if not isinstance(ext, str) or not re.fullmatch(r"[A-Za-z0-9]{2,5}", ext):
        ext = None
    creator = row.get("creator")
    if not isinstance(creator, str):
        creator = None
    duration = reported_number(row.get("duration"))
    bits = reported_number(row.get("bit_rate"))
    rate = reported_number(row.get("sample_rate"))
    size = reported_number(row.get("filesize"))
    return {
        "schema": "music_source_candidate_v1",
        "candidate_id": stable_id(source_page),
        "status": "candidate_only_not_downloaded",
        "asset_id": None, "content_sha256": None, "audio_storage_key": None,
        "provider": "Openverse / " + source,
        "source_page": source_page,
        "source_media_url": https_url(row.get("url")),
        "source_revision_sha1": None,
        "source_revision_hint": str(row.get("indexed_on") or ""),
        "title": title or None,
        "file_name": None, "extension": ("." + ext.lower()) if ext else None,
        "mime_type": None, "source_file_bytes": int(size) if size else None,
        "source_description": None, "source_categories": tags,
        "creator": creator, "attribution": row.get("attribution"),
        "license": license_name,
        "license_url": row.get("license_url"),
        "license_evidence_url": f"{API}{ident}/",
        "source_license_verified_at": None,
        "source_license_claim_observed_at": now(),
        "license_evidence_type": "openverse_indexed_claim_unverified",
        "rights_review_status": "source_claim_and_composition_rights_pending",
        "indexed_source_name": source,
        "openverse_id": ident,
        "source_reported_audio_metadata": {
            "duration_seconds": duration,
            "bit_rate": int(bits) if bits else None,
            "sample_rate_hz": int(rate) if rate else None,
            "file_size_bytes": int(size) if size else None,
            "provenance": "Openverse API metadata; not independently validated",
        },
        "classification": {
            "instrument_hints": [group], "hint_origin": [query],
            "instrument_verified_by_audio": False, "audio_kind": "unclassified",
            "tempo_bpm": None, "musical_key": None, "chords": None,
            "time_signature": None, "loopable": None,
            "mood": None, "musical_role": None, "energy": None,
        },
        "technical": {
            "duration_seconds": None, "codec": None, "sample_rate_hz": None,
            "channels": None, "integrated_lufs": None, "true_peak_dbtp": None,
        },
    }, None


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": "WhiteNoiseChoir-MetadataResearch/1.0 (official Openverse API; no media downloads)",
                      "Accept": "application/json"})
    retry = Retry(total=3, status_forcelist=[429, 500, 502, 503, 504],
                  backoff_factor=2, respect_retry_after_header=True)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def query_api(client, query, page, stats):
    # Two concurrent shards, each <= 1 request/2.8 s; shared anonymous budget.
    time.sleep(2.8)
    response = client.get(API,
        params={"q": query, "license": "cc0,by", "page_size": 20, "page": page,
                "mature": "false", "filter_dead": "true"},
        timeout=(10, 35))
    response.raise_for_status()
    stats["api_requests"] += 1
    data = response.json()
    return data.get("results", []), int(data.get("page_count", 1))


def scan(args):
    if not 1 <= args.shard_count <= 4 or not 0 <= args.shard_index < args.shard_count:
        raise ValueError("Invalid shard")
    if not 1 <= args.max_candidates <= 1500 or not 1 <= args.per_group <= 60:
        raise ValueError("Invalid caps")
    if not 1 <= args.pages <= 4:
        raise ValueError("Invalid pages")
    client = session()
    rows = {}
    group_report = {}
    core.emit("OPENVERSE_METADATA_BEGIN", {
        "shard": args.shard_index, "groups": len(core.FAMILIES[args.shard_index::args.shard_count]),
        "persist": args.persist, "provider": "Openverse official API"})
    for slug, cats, queries, pattern in core.FAMILIES[args.shard_index::args.shard_count]:
        stats = Counter()
        found_group = 0
        terms = list(dict.fromkeys([slug.replace("-", " "), queries[0]]))
        for term in terms:
            if found_group >= args.per_group or len(rows) >= args.max_candidates:
                break
            for page in range(1, args.pages + 1):
                if found_group >= args.per_group or len(rows) >= args.max_candidates:
                    break
                try:
                    found, total_pages = query_api(client, term, page, stats)
                except Exception as exc:
                    stats["api_errors"] += 1
                    core.emit("OPENVERSE_METADATA_ERROR", {
                        "family": slug, "query": term, "error": str(exc)[:160]})
                    break
                if not isinstance(found, list):
                    stats["bad_result"] += 1
                    break
                for r in found:
                    stats["results_examined"] += 1
                    if not isinstance(r, dict):
                        stats["bad_result"] += 1
                        continue
                    candidate, reason = build_candidate(r, slug, term)
                    if reason:
                        stats[reason] += 1
                        continue
                    cid = candidate["candidate_id"]
                    if cid in rows:
                        core.merge_candidate(rows[cid], candidate)
                        stats["skip_duplicate_source"] += 1
                        continue
                    rows[cid] = candidate
                    found_group += 1
                    stats["eligible"] += 1
                    if found_group >= args.per_group or len(rows) >= args.max_candidates:
                        break
                if not found or page >= total_pages:
                    break
        group_report[slug] = dict(stats)
        core.emit("OPENVERSE_METADATA_GROUP", {
            "family": slug, "new_candidates": found_group,
            "total_unique": len(rows), "diagnostics": dict(stats)})
        if len(rows) >= args.max_candidates:
            break
    client.close()
    report = {"schema": "openverse_candidate_discovery_report_v1",
              "generated_at": now(), "provider": "Openverse",
              "shard": args.shard_index, "families_scanned": len(group_report),
              "found_unique_in_shard": len(rows), "mode": "persist" if args.persist else "read_only",
              "family_diagnostics": group_report, "candidates": list(rows.values())}
    counts = Counter()
    errors = []
    if args.persist:
        s3 = core.s3_client()
        for candidate in rows.values():
            try:
                result, key = core.persist(s3, candidate)
                counts[result] += 1
            except Exception as exc:
                counts["error"] += 1
                errors.append({"candidate_id": candidate["candidate_id"], "error": str(exc)[:160]})
        run_id = re.sub(r"[^A-Za-z0-9_-]", "", os.getenv("GITHUB_RUN_ID", "local"))
        report_key = f"{core.PRIVATE_ROOT}runs/openverse-{run_id}-{args.shard_index}.json"
        report_data = {k: v for k, v in report.items() if k != "candidates"}
        report_data["candidate_ids"] = list(rows)
        from botocore.exceptions import ClientError
        try:
            s3.put_object(Bucket=core.BUCKET, Key=report_key, Body=json.dumps(report_data).encode(),
                          IfNoneMatch="*", ContentType="application/json", CacheControl="private,no-store")
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 412:
                raise
    report["storage"] = {"created": counts["created"], "existing": counts["existing"],
                         "errors": counts["error"]}
    report["write_errors"] = errors[:20]
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    core.emit("OPENVERSE_METADATA_FINAL", {
        "shard": args.shard_index, "candidate_unique": len(rows),
        "persisted_new": counts["created"], "persisted_existing": counts["existing"],
        "write_errors": counts["error"], "downloads": 0, "audio_uploaded": 0,
        "report_path": str(path),
    })
    if counts["error"]:
        raise RuntimeError(f"Failed {counts['error']} private candidate writes")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--persist", action="store_true")
    p.add_argument("--shard-index", type=int, default=0)
    p.add_argument("--shard-count", type=int, default=2)
    p.add_argument("--max-candidates", type=int, default=500)
    p.add_argument("--per-group", type=int, default=32)
    p.add_argument("--pages", type=int, default=2)
    p.add_argument("--output", default="audits/music-openverse-candidates.json")
    scan(p.parse_args())


if __name__ == "__main__":
    main()
