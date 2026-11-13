#!/usr/bin/env python3
"""Build a PRIVATE source-rechecked music-audio shortlist for owner rights review.

This never grants recording/composition rights. It creates eight evidence packs
on R2, with all approval booleans NULL. Source-page licensing is a *claim*,
not proof of underlying composition/performance clearance.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time

import requests

import harvest_commons_cc0_to_r2 as commons
import pilot_import_music_candidates as pilot
import scan_music_candidate_metadata as core

REVIEW_QUEUE_PREFIX = core.PRIVATE_ROOT + "rights-review-queue/v1/"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
UNSUITABLE = re.compile(
    r"\b(?:cover|karaoke|remix|bootleg|radio broadcast|"
    r"soundtrack|song|commercial recording|orchestral performance|"
    r"film music|copyright infringement|pronunciation)\b", re.I)
SAMPLE = re.compile(r"\b(?:single|note|sample|sound|isolated|tone|"
                    r"chord|pluck|strum|glissando|arpeggio|pluck|vibration)\b", re.I)


def candidate_review_basics(row):
    if row.get("schema") != "music_source_candidate_v1":
        return "BAD_SCHEMA"
    if row.get("provider") != "Wikimedia Commons":
        return "OTHER_PROVIDER"
    if row.get("license") not in pilot.APPROVABLE_LICENSES:
        return "UNSUPPORTED_LICENSE"
    if not row.get("source_license_verified_at"):
        return "LICENSE_NOT_RECHECKABLE"
    if not pilot.safe_media_url(row.get("source_media_url")):
        return "UNTRUSTED_MEDIA_HOST"
    if not isinstance(row.get("source_file_bytes"), int) or not (
            1000 <= row["source_file_bytes"] <= pilot.MAX_SOURCE_BYTES):
        return "OUT_OF_SIZE_SCOPE"
    title = row.get("title")
    if not isinstance(title, str) or len(title) > 300 or not title.startswith("File:"):
        return "MALFORMED_COMMONS_TITLE"
    if not isinstance(row.get("source_page"), str) or not row["source_page"].startswith(
            "https://commons.wikimedia.org/wiki/File:"):
        return "UNEXPECTED_COMMONS_PAGE"
    if row["license"].startswith("CC-BY-") and not row.get("attribution"):
        return "MISSING_SOURCE_ATTRIBUTION"
    text = (title + " " + str(row.get("source_description") or ""))[:4000]
    if UNSUITABLE.search(text):
        return "UNSUITABLE_TITLE_OR_DESCRIPTION"
    return "REVIEWABLE_CLAIM"


def candidate_priority(row):
    title = str(row.get("title") or "")
    description = str(row.get("source_description") or "")
    groups = row.get("classification", {}).get("instrument_hints") or []
    return (
        0 if row.get("license") == "CC0-1.0" else 1,
        0 if SAMPLE.search(title + " " + description) else 1,
        0 if groups else 1,
        int(row.get("source_file_bytes", pilot.MAX_SOURCE_BYTES)),
        row.get("candidate_id", ""),
    )


def latest_commons_page(session, row):
    response = session.get(COMMONS_API, params={
        "action": "query", "format": "json", "formatversion": "2",
        "titles": row["title"], "prop": "imageinfo",
        "iiprop": "url|mime|size|sha1|extmetadata",
        "maxlag": "5",
    }, timeout=(8, 25))
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError("Commons API returned error: " +
                           str(payload["error"].get("code", "unknown"))[:40])
    pages = payload.get("query", {}).get("pages", [])
    if len(pages) != 1 or pages[0].get("missing"):
        return None
    return pages[0]


def revalidate_source(session, row):
    """Re-query Commons *now*; result only certifies consistency of source claims."""
    page = latest_commons_page(session, row)
    if not page:
        return "SOURCE_PAGE_MISSING", None
    result = commons.decide(page, "music-audio-review",
                            pilot.MAX_SOURCE_BYTES, allow_cc_by=True)
    if result.get("state") != "ELIGIBLE":
        return "SOURCE_NOW_INELIGIBLE", None
    if result["source_license"] != row["license"]:
        return "LICENSE_CHANGED", None
    if result["direct_file_url"] != row["source_media_url"]:
        return "MEDIA_URL_CHANGED", None
    if result["size"] != row["source_file_bytes"]:
        return "SOURCE_SIZE_CHANGED", None
    if row.get("source_revision_sha1"):
        revision = (page.get("imageinfo") or [{}])[0].get("sha1")
        if revision != row["source_revision_sha1"]:
            return "SOURCE_SHA1_CHANGED", None
    if row.get("license") != "CC0-1.0" and not result.get("attribution"):
        return "ATTRIBUTION_NOT_CONFIRMED", None
    return "SOURCE_CLAIM_RECHECKED", {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "provider": "Wikimedia Commons",
        "source_page": result["source_url"],
        "license": result["source_license"],
        "license_url": result["license_url"],
        "license_evidence_url": result["rights_evidence_url"],
        "creator": result.get("author"),
        "attribution": result.get("attribution"),
        "file_bytes": result["size"],
        "sha1": (page.get("imageinfo") or [{}])[0].get("sha1"),
        "evidence_level": "current_public_source_claim_not_composition_rights_review",
    }


def draft_review(row, evidence):
    """Every approval field is NULL; never a presigned/automatic approval."""
    return {
        "candidate_id": row["candidate_id"],
        "file_name": row.get("file_name"),
        "title": row.get("title"),
        "instrument_hints": row.get("classification", {}).get("instrument_hints", []),
        "source_media_url": row["source_media_url"],
        "source_page": row["source_page"],
        "source_revision_sha1": row.get("source_revision_sha1"),
        "source_claim": evidence,
        "approval_template": {
            "schema": "music_audio_rights_approval_v1",
            "candidate_id": row["candidate_id"],
            "source_media_url": row["source_media_url"],
            "source_revision_sha1": row.get("source_revision_sha1"),
            "license": row.get("license"),
            "attribution_text": None,
            "recording_rights_verified": None,
            "composition_rights_verified": None,
            "download_authorized": None,
            "commercial_derivative_reuse_allowed": None,
            "reviewed_by": None, "reviewed_at": None,
            "evidence_urls": [],
        },
        "approval_object_key": pilot.approval_key(row),
        "review_state": "HUMAN_RIGHTS_REVIEW_REQUIRED",
        "audio_downloaded": False,
    }


def collect(s3, limit, max_records, max_queries, wait):
    diagnostics = Counter()
    rows = []
    used_urls = set()
    keys = pilot.candidate_keys(s3, max_records)
    for key in keys:
        try:
            row = pilot.load_json(s3, key)
            match = pilot.KEY_RE.fullmatch(key)
            if not isinstance(row, dict) or row.get("candidate_id") != (
                    "music-candidate-" + match.group(2)):
                diagnostics["BAD_ID"] += 1
                continue
            reason = candidate_review_basics(row)
            diagnostics[reason] += 1
            if reason == "REVIEWABLE_CLAIM" and row["source_media_url"] not in used_urls:
                rows.append(row)
                used_urls.add(row["source_media_url"])
        except Exception as exc:
            diagnostics["READ_ERROR"] += 1
            print("MUSIC_REVIEW_SOURCE_READ_ERROR " +
                  json.dumps({"type": type(exc).__name__}), flush=True)
    if diagnostics["READ_ERROR"]:
        raise RuntimeError("Private candidate retrieval failure; cannot trust shortlist")
    rows.sort(key=candidate_priority)
    shortlist = []
    used_groups = set()
    session = requests.Session()
    session.headers.update({"User-Agent":
       "WhiteNoiseChoir-AudioRightsReview/1.0 (source claim verification; no media downloads)",
       "Accept": "application/json"})
    try:
        # First pass favors different instrument groups; second fills gaps.
        diverse = []
        repeats = []
        for row in rows:
            groups = row.get("classification", {}).get("instrument_hints") or []
            group = next((x for x in groups if x not in used_groups), None)
            if group:
                used_groups.add(group)
                diverse.append(row)
            else:
                repeats.append(row)
        attempts = 0
        for row in diverse + repeats:
            if len(shortlist) >= limit or attempts >= max_queries:
                break
            attempts += 1
            if attempts > 1:
                time.sleep(wait)
            try:
                status, evidence = revalidate_source(session, row)
            except Exception as exc:
                status, evidence = "API_ERROR", None
                print("MUSIC_REVIEW_API_ERROR " +
                      json.dumps({"type": type(exc).__name__}), flush=True)
            diagnostics[status] += 1
            if status == "SOURCE_CLAIM_RECHECKED":
                shortlist.append(draft_review(row, evidence))
    finally:
        session.close()
    return {
        "schema": "music_audio_private_rights_review_queue_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_objects_scanned": len(keys),
        "reviewable_claims": len(rows),
        "queried_current_source_pages": attempts,
        "source_rechecked_for_manual_review": len(shortlist),
        "review_approvals_created": 0,
        "audio_files_imported": 0,
        "queue": shortlist,
        "diagnostics": dict(diagnostics),
        "warning": "Commons source license is a source claim; underlying composition and recording rights need independent review",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--max-records", type=int, default=8000)
    ap.add_argument("--max-queries", type=int, default=36)
    ap.add_argument("--wait", type=float, default=1.2)
    ap.add_argument("--output", default="audits/music-audio-rights-review-summary.json")
    args = ap.parse_args()
    if not 1 <= args.limit <= 24 or not 8 <= args.max_queries <= 80:
        raise ValueError("Unsafe API budget")
    if not 1 <= args.max_records <= 10000 or not 0.4 <= args.wait <= 10:
        raise ValueError("Unsafe R2/API cap")
    s3 = core.s3_client()
    report = collect(s3, args.limit, args.max_records, args.max_queries, args.wait)
    run_id = re.sub(r"[^A-Za-z0-9_-]", "",
                    os.getenv("GITHUB_RUN_ID", "manual"))[:80]
    # PRIVATE R2 only: never upload owner-review source URLs to a public Actions artifact.
    queue_key = REVIEW_QUEUE_PREFIX + f"{run_id}-{os.getenv('GITHUB_RUN_ATTEMPT', '1')}.json"
    payload = json.dumps(report, ensure_ascii=False, indent=2).encode()
    s3.put_object(Bucket=core.BUCKET, Key=queue_key, Body=payload,
                  ContentType="application/json", CacheControl="private,no-store",
                  IfNoneMatch="*")
    head = s3.head_object(Bucket=core.BUCKET, Key=queue_key)
    if head["ContentLength"] != len(payload):
        raise RuntimeError("Private rights review queue R2 HEAD mismatch")
    safe_summary = {k: v for k, v in report.items() if k != "queue"}
    safe_summary["private_queue_key"] = queue_key
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("MUSIC_RIGHTS_REVIEW_FINAL " + json.dumps({
        "candidate_objects_scanned": safe_summary["candidate_objects_scanned"],
        "source_rechecked_for_manual_review": safe_summary["source_rechecked_for_manual_review"],
        "review_approvals_created": 0, "audio_files_imported": 0,
        "private_review_queue_key": queue_key,
        "api_errors": safe_summary["diagnostics"].get("API_ERROR", 0),
    }), flush=True)


if __name__ == "__main__":
    main()
