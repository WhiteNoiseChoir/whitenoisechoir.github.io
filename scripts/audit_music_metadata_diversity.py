#!/usr/bin/env python3
"""Read-only private R2 music candidate coverage audit.

No source URLs, titles, candidate IDs, or object keys appear in the report.
All records are metadata candidates, NOT licensed or downloaded audio.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit, unquote

import boto3
from botocore.config import Config

import scan_music_candidate_metadata as core

KEY_RE = re.compile(r"^internal/music-candidates/v1/([a-f0-9]{2})/([a-f0-9]{64})\.json$")
EXPECTED = {x[0] for x in core.FAMILIES}
SPARSE_THRESHOLD = 10
MAX_OBJECTS = 25000
MAX_BYTES = 256 * 1024


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def normalized_url(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        p = urlsplit(value.strip())
        if p.scheme.lower() not in ("https", "http") or not p.hostname:
            return None
        host = p.hostname.lower()
        port = ":" + str(p.port) if p.port and p.port not in (80, 443) else ""
        path = unquote(p.path).rstrip("/") or "/"
        return urlunsplit((p.scheme.lower(), host + port, path, "", ""))
    except (ValueError, UnicodeError):
        return None


def list_candidate_keys(s3):
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(
        Bucket=core.BUCKET, Prefix=core.PRIVATE_ROOT + "v1/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            match = KEY_RE.fullmatch(key)
            if match and int(obj.get("Size", 0)) > 0:
                keys.append((key, int(obj["Size"])))
            if len(keys) > MAX_OBJECTS:
                raise ValueError("Exceeded safe audit object cap")
    return keys


def read_candidate(s3, key, listed_size):
    if listed_size > MAX_BYTES:
        raise ValueError("Candidate JSON exceeds safe byte cap")
    response = s3.get_object(Bucket=core.BUCKET, Key=key)
    try:
        raw = response["Body"].read(MAX_BYTES + 1)
    finally:
        response["Body"].close()
    if len(raw) > MAX_BYTES:
        raise ValueError("Candidate JSON exceeds safe byte cap")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("Candidate JSON is not an object")
    return obj


def audit_records(records, keys=None):
    """Audit arbitrary (object_key, parsed_candidate) pairs without leaking identifiers."""
    providers, licenses, rights, families = (Counter() for _ in range(4))
    ages, kinds, gaps = Counter(), Counter(), Counter()
    missing = Counter()
    candidate_ids = Counter()
    media_urls, source_pages = defaultdict(set), defaultdict(set)
    invalid = Counter()
    multiple_groups = 0
    total = 0
    for key, row in records:
        total += 1
        m = KEY_RE.fullmatch(key)
        if not m:
            invalid["invalid_key"] += 1
            continue
        digest = m.group(2)
        if m.group(1) != digest[:2]:
            invalid["shard_mismatch"] += 1
        if row.get("schema") != "music_source_candidate_v1":
            invalid["invalid_schema"] += 1
        ident = row.get("candidate_id")
        if ident != "music-candidate-" + digest:
            invalid["candidate_id_key_mismatch"] += 1
        if isinstance(ident, str):
            candidate_ids[ident] += 1
        else:
            missing["candidate_id"] += 1
        providers[str(row.get("provider") or "UNKNOWN")] += 1
        licenses[str(row.get("license") or "UNKNOWN")] += 1
        rights[str(row.get("rights_review_status") or "UNKNOWN")] += 1
        if row.get("status") != "candidate_only_not_downloaded":
            invalid["unexpected_status"] += 1
        cls = row.get("classification") or {}
        if not isinstance(cls, dict):
            cls = {}
            invalid["invalid_classification"] += 1
        raw_groups = cls.get("instrument_hints")
        if not isinstance(raw_groups, list):
            raw_groups = []
        groups = sorted(set(x for x in raw_groups if isinstance(x, str) and x))
        if not groups:
            missing["instrument_hints"] += 1
        if len(groups) > 1:
            multiple_groups += 1
        for group in groups:
            families[group] += 1
        kinds[str(cls.get("audio_kind") or "UNKNOWN")] += 1
        for field in ("source_page", "source_media_url", "creator", "license_evidence_url",
                      "source_file_bytes", "source_license_verified_at"):
            if row.get(field) in (None, "", []):
                missing[field] += 1
        for field in ("tempo_bpm", "musical_key", "loopable"):
            if cls.get(field) is None:
                missing[field] += 1
        technical = row.get("technical") or {}
        if not isinstance(technical, dict):
            technical = {}
        for field in ("duration_seconds", "codec", "sample_rate_hz"):
            if technical.get(field) is None:
                missing[field] += 1
        for field, dest in (("source_media_url", media_urls), ("source_page", source_pages)):
            url = normalized_url(row.get(field))
            if url:
                dest[url].add(ident if isinstance(ident, str) else key)
        observed = row.get("source_license_claim_observed_at") or row.get("source_license_verified_at")
        if isinstance(observed, str):
            try:
                dt = datetime.fromisoformat(observed.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    ages["timestamp_no_timezone"] += 1
                else:
                    days = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).days
                    ages["future"] += int(days < 0)
                    if days >= 0:
                        ages["0-7d" if days <= 7 else "8-30d" if days <= 30 else "31-365d" if days <= 365 else "older"] += 1
            except ValueError:
                ages["timestamp_invalid"] += 1
        else:
            ages["timestamp_missing"] += 1
    def overlap(group):
        return {
            "normalized_keys_with_multiple_candidate_ids": sum(len(v) > 1 for v in group.values()),
            "candidate_ids_in_overlapping_keys": sum(len(v) for v in group.values() if len(v) > 1),
        }
    sparse = {name: families.get(name, 0) for name in EXPECTED if families.get(name, 0) < SPARSE_THRESHOLD}
    priority = sorted(sparse, key=lambda name: (families.get(name, 0), name))[:10]
    provider_count = max(providers.values(), default=0)
    report = {
        "schema": "music_candidate_diversity_audit_v1",
        "generated_at": utcnow(),
        "privacy": "aggregate_counts_only_no_private_source_urls_or_ids",
        "scope": "private_R2_candidate_JSON_not_downloaded_audio",
        "objects_read": total,
        "valid_core_records": total - sum(1 for key, row in records if not (
            (m := KEY_RE.fullmatch(key))
            and m.group(1) == m.group(2)[:2]
            and row.get("schema") == "music_source_candidate_v1"
            and row.get("candidate_id") == "music-candidate-" + m.group(2)
            and row.get("status") == "candidate_only_not_downloaded")),
        "invalid_checks": dict(sorted(invalid.items())),
        "duplicate_candidate_id_excess": sum(v - 1 for v in candidate_ids.values() if v > 1),
        "providers": dict(sorted(providers.items())),
        "provider_dominance_percent": round(100 * provider_count / total, 2) if total else 0,
        "license_claims_not_clearance": dict(sorted(licenses.items())),
        "rights_review_status": dict(sorted(rights.items())),
        "instrument_family_hint_counts_not_audio_verified": dict(sorted(families.items())),
        "families_expected": len(EXPECTED),
        "families_covered": sum(families.get(name, 0) > 0 for name in EXPECTED),
        "families_missing": sorted(x for x in EXPECTED if not families.get(x)),
        "families_sparse_below_10": dict(sorted(sparse.items())),
        "priority_gap_families": priority,
        "records_with_multiple_family_hints": multiple_groups,
        "audio_kind_hints": dict(sorted(kinds.items())),
        "missing_field_counts": dict(sorted(missing.items())),
        "source_record_age": dict(sorted(ages.items())),
        "possible_source_media_url_overlaps": overlap(media_urls),
        "possible_source_page_overlaps": overlap(source_pages),
        "audio_downloads_performed": 0,
        "commercial_rights_cleared_by_audit": False,
    }
    return report


def audit_r2(s3, workers=8):
    listed = list_candidate_keys(s3)
    records = []
    errors = Counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(read_candidate, s3, key, size): key for key, size in listed}
        for future in as_completed(futures):
            try:
                records.append((futures[future], future.result()))
            except Exception as exc:
                errors[type(exc).__name__] += 1
    report = audit_records(records)
    report["objects_listed"] = len(listed)
    report["objects_failed_to_read"] = len(listed) - len(records)
    report["read_error_types"] = dict(sorted(errors.items()))
    report["complete_read"] = len(listed) == len(records)
    return report


def output_report(report, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf8")
    print("MUSIC_DIVERSITY_AUDIT_FINAL " + json.dumps({
        "objects_listed": report["objects_listed"],
        "objects_read": report["objects_read"],
        "valid_core_records": report["valid_core_records"],
        "read_errors": report["objects_failed_to_read"],
        "families_covered": report["families_covered"],
        "families_expected": report["families_expected"],
        "missing_families": len(report["families_missing"]),
        "duplicate_id_excess": report["duplicate_candidate_id_excess"],
        "possible_media_url_overlap_keys": report["possible_source_media_url_overlaps"]["normalized_keys_with_multiple_candidate_ids"],
        "priority_gap_families": report["priority_gap_families"],
    }, ensure_ascii=False), flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf8") as f:
            f.write("## Private R2 music candidate diversity audit\n\n")
            f.write(f"- Objects listed/read: **{report['objects_listed']}/{report['objects_read']}**\n")
            f.write(f"- Valid core schema/key/ID/status: **{report['valid_core_records']}**\n")
            f.write(f"- Families covered: **{report['families_covered']}/{report['families_expected']}**\n")
            f.write(f"- Missing families: **{len(report['families_missing'])}**; sparse families: **{len(report['families_sparse_below_10'])}**\n")
            f.write(f"- Duplicate candidate IDs beyond first: **{report['duplicate_candidate_id_excess']}**\n")
            f.write(f"- Possible normalized media URL overlaps: **{report['possible_source_media_url_overlaps']['normalized_keys_with_multiple_candidate_ids']}**\n")
            f.write("- These are **source metadata only**, not validated audio or composition-rights clearance.\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="audits/music-diversity-audit.json")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.workers <= 12:
        parser.error("workers must be 1..12")
    result = output_report(audit_r2(core.s3_client(), args.workers), args.output)
    if not result["complete_read"] or result["valid_core_records"] != result["objects_read"]:
        raise SystemExit("Audit incomplete or core schema validation failed")


if __name__ == "__main__":
    main()
