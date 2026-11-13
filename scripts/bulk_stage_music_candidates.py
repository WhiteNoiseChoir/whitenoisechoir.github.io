#!/usr/bin/env python3
"""WS3: bounded, repeatable metadata -> private audio staging (NOT publication).

Only original Wikimedia Commons CC0 / CC-BY candidates with freshly rechecked
license/size/revision are downloaded. Source permission is NOT a determination
that every underlying composition / performance right is cleared. Objects in
this prefix are for INTERNAL AUDITION / MIX TESTS ONLY. R2 receipts persist
per-candidate progress and batches chain within a single Actions job.

Provider adapters for Openverse and Internet Archive must be separately
implemented and tested; they are explicitly not treated as exhausted here.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from botocore.exceptions import ClientError
import requests

import scan_music_candidate_metadata as core
import pilot_import_music_candidates as pilot
import prepare_music_rights_review as review

ROOT = "internal/music-audio-staging/v1/"
AUDIO_ROOT = ROOT + "sha256/"
RECEIPT_ROOT = ROOT + "receipts/"
PROVENANCE_ROOT = ROOT + "provenance/"
RUNS_ROOT = ROOT + "runs/"
SHA_RE = re.compile(r"^music-candidate-([0-9a-f]{64})$")
AUDIO_BYTES_MAX = 32 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def receipt_key(candidate_id):
    match = SHA_RE.fullmatch(candidate_id)
    if not match:
        raise ValueError("Invalid candidate id")
    digest = match.group(1)
    return f"{RECEIPT_ROOT}{digest[:2]}/{digest}.json"


def head(s3, key):
    try:
        return s3.head_object(Bucket=core.BUCKET, Key=key)
    except ClientError as exc:
        if str(exc.response.get("Error", {}).get("Code")) in (
                "NoSuchKey", "NotFound", "404"):
            return None
        raise


def create_json(s3, key, doc):
    body = (json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n").encode()
    try:
        s3.put_object(Bucket=core.BUCKET, Key=key, Body=body,
                      ContentType="application/json", CacheControl="private,no-store",
                      IfNoneMatch="*")
    except ClientError as exc:
        if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 412:
            raise
    result = head(s3, key)
    if result is None or int(result.get("ContentLength", 0)) <= 0:
        raise RuntimeError("R2 JSON persistence cannot be verified")


def existing_receipts(s3):
    completed = set()
    pages = s3.get_paginator("list_objects_v2").paginate(
        Bucket=core.BUCKET, Prefix=RECEIPT_ROOT)
    for page in pages:
        for item in page.get("Contents", []):
            match = re.fullmatch(
                re.escape(RECEIPT_ROOT) + r"[0-9a-f]{2}/([0-9a-f]{64})\.json",
                item["Key"])
            if match:
                completed.add("music-candidate-" + match.group(1))
    return completed


def read_candidates(s3, max_records, processed):
    keys = pilot.candidate_keys(s3, max_records)
    eligible = []
    diagnostics = Counter()
    pending = [key for key in keys
               if "music-candidate-" + pilot.KEY_RE.fullmatch(key).group(2)
               not in processed]
    def read_one(key):
        return key, pilot.load_json(s3, key)
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {pool.submit(read_one, key): key for key in pending}
        for job in as_completed(jobs):
            try:
                key, row = job.result()
                digest = pilot.KEY_RE.fullmatch(key).group(2)
                if not isinstance(row, dict) or row.get("candidate_id") != (
                        "music-candidate-" + digest):
                    diagnostics["BAD_CANDIDATE_ID"] += 1
                    continue
                status = review.candidate_review_basics(row)
                diagnostics[status] += 1
                if status == "REVIEWABLE_CLAIM":
                    eligible.append(row)
            except Exception as exc:
                diagnostics["R2_READ_ERRORS"] += 1
                print("WS3_STAGE_READ_ERROR " + json.dumps({
                    "type": type(exc).__name__}), flush=True)
    if diagnostics["R2_READ_ERRORS"]:
        raise RuntimeError("R2 candidate reads failed. Fail closed.")
    eligible.sort(key=review.candidate_priority)
    return eligible, diagnostics, len(keys)


def validate_audio(path):
    technical = pilot.ffprobe(path)
    run = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-i", str(path),
         "-f", "null", "-"],
        capture_output=True, text=True, timeout=120, check=False)
    if run.returncode:
        raise ValueError("ffmpeg full decode failed")
    return technical


def store_staging(s3, candidate, evidence, digest, size, source, technical):
    # All archived binaries remain PRIVATE and rights-review-pending.
    ext = Path(candidate["source_media_url"].split("?", 1)[0]).suffix.lower()
    key = f"{AUDIO_ROOT}{digest[:2]}/{digest}{ext}"
    existing = head(s3, key)
    if existing is None:
        with source.open("rb") as fh:
            try:
                s3.put_object(
                    Bucket=core.BUCKET, Key=key, Body=fh, ContentLength=size,
                    ContentType=mimetypes.guess_type(key)[0] or "application/octet-stream",
                    CacheControl="private,no-store", IfNoneMatch="*",
                    Metadata={"sha256": digest, "state": "rights-review-pending",
                              "license": candidate["license"].lower()})
            except ClientError as exc:
                if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 412:
                    raise
    verified = head(s3, key)
    if not verified or int(verified.get("ContentLength", -1)) != size:
        raise RuntimeError("R2 HEAD size mismatch")
    if (verified.get("Metadata") or {}).get("sha256") != digest:
        raise RuntimeError("R2 HEAD sha256 metadata mismatch")
    provenance = {
        "schema": "music_audio_staging_provenance_v1",
        "state": "STORED_R2_RIGHTS_QA_PENDING",
        "public_or_commercial_export_approved": False,
        "studio_ready": False, "cataloged": False, "listening_qa": "pending",
        "candidate_id": candidate["candidate_id"],
        "license_source_claim": candidate["license"],
        "rights_review_status": "underlying_recording_and_composition_pending",
        "source_page": candidate["source_page"],
        "source_media_url": candidate["source_media_url"],
        "creator": candidate.get("creator"),
        "attribution": candidate.get("attribution"),
        "license_url": candidate.get("license_url"),
        "current_source_check": evidence,
        "content_sha256": digest, "audio_storage_key": key,
        "file_bytes": size, "technical": technical, "downloaded_at": now(),
    }
    create_json(s3, f"{PROVENANCE_ROOT}{digest[:2]}/{digest}.json", provenance)
    return key


def save_receipt(s3, row, state, digest=None, stored_key=None, reason=None):
    receipt = {
        "schema": "music_audio_staging_receipt_v1",
        "candidate_id": row["candidate_id"],
        "state": state,
        "content_sha256": digest,
        "audio_storage_key": stored_key,
        "reason": reason,
        "approved_for_publication": False,
        "studio_ready": False,
        "finished_at": now(),
    }
    create_json(s3, receipt_key(row["candidate_id"]), receipt)


def ingest(s3, rows, args, previous_digests, start_time):
    stats = Counter()
    batch_stats = Counter()
    total_bytes = 0
    total_files = 0
    pages_checked = 0
    session = requests.Session()
    session.headers["User-Agent"] = (
        "WhiteNoiseChoir-Private-Music-Staging/1.0 (Wikimedia license recheck)")
    session.headers["Accept"] = "application/json"
    batch_no = 0
    run = re.sub(r"[^A-Za-z0-9_-]", "", os.getenv("GITHUB_RUN_ID", "manual"))
    with tempfile.TemporaryDirectory(prefix="wnc-music-staging-") as tmp:
        try:
            for row in rows:
                if (total_files >= args.max_files or
                        pages_checked >= args.max_source_queries or
                        time.monotonic() - start_time > args.max_seconds):
                    break
                estimate = row["source_file_bytes"]
                if total_bytes + estimate > args.max_total_mib * 1024**2:
                    stats["SKIP_TRANSFER_BUDGET"] += 1
                    continue
                if pages_checked > 0:
                    time.sleep(args.request_delay)
                pages_checked += 1
                try:
                    state, evidence = review.revalidate_source(session, row)
                except (requests.RequestException, RuntimeError, ValueError) as exc:
                    stats["SOURCE_API_ERROR"] += 1
                    print("WS3_STAGE_SOURCE_ERROR " +
                          json.dumps({"kind": type(exc).__name__}), flush=True)
                    if stats["SOURCE_API_ERROR"] >= 3:
                        stats["STOP_REPEATED_SOURCE_ERRORS"] += 1
                        break
                    continue
                if state != "SOURCE_CLAIM_RECHECKED":
                    stats["SOURCE_REJECTED_" + state] += 1
                    continue
                dest = Path(tmp) / (row["candidate_id"] +
                                    Path(row.get("file_name") or
                                         row["source_media_url"]).suffix.lower())
                try:
                    digest, size = pilot.stream_safe_media(row, dest)
                    total_bytes += size
                    stats["DOWNLOADED"] += 1
                    if digest in previous_digests:
                        # Existing file may already be in the shared raw asset library.
                        save_receipt(s3, row, "DUPLICATE_SHA256_REUSE_EXISTING",
                                     digest=digest, reason="asset_sha256_preexists")
                        stats["DUPLICATE_SHA256"] += 1
                    else:
                        tech = validate_audio(dest)
                        stats["AUDIO_VALIDATED"] += 1
                        key = store_staging(s3, row, evidence, digest, size, dest, tech)
                        save_receipt(s3, row, "STORED_R2_RIGHTS_QA_PENDING",
                                     digest=digest, stored_key=key)
                        stats["STORED_R2"] += 1
                        previous_digests.add(digest)
                    total_files += 1
                    batch_stats["candidates_processed"] += 1
                    if batch_stats["candidates_processed"] >= args.batch_size:
                        batch_no += 1
                        save_checkpoint(s3, run, batch_no, total_files, total_bytes,
                                        pages_checked, stats)
                        batch_stats.clear()
                except Exception as exc:
                    stats["IMPORT_ERROR"] += 1
                    print("WS3_STAGE_IMPORT_ERROR " + json.dumps({
                        "type": type(exc).__name__,
                        "detail": str(exc)[:120]}), flush=True)
                    if stats["IMPORT_ERROR"] >= args.max_errors:
                        stats["STOP_IMPORT_ERRORS"] += 1
                        break
                finally:
                    dest.unlink(missing_ok=True)
        finally:
            session.close()
        if batch_stats["candidates_processed"] or batch_no == 0:
            batch_no += 1
            save_checkpoint(s3, run, batch_no, total_files, total_bytes,
                            pages_checked, stats)
    return stats, total_bytes, pages_checked, total_files, batch_no


def save_checkpoint(s3, run, batch, files, bytes_transferred, pages, stats):
    data = {
        "schema": "music_audio_staging_checkpoint_v1",
        "run": run, "batch": batch, "at": now(),
        "processed_files": files, "downloaded_bytes": bytes_transferred,
        "source_pages_checked": pages, "states": dict(stats),
    }
    key = f"{RUNS_ROOT}{run}-{os.getenv('GITHUB_RUN_ATTEMPT','1')}-batch{batch}.json"
    create_json(s3, key, data)
    print("WS3_CHAIN_BATCH " + json.dumps(data, ensure_ascii=False), flush=True)


def run(args):
    start = time.monotonic()
    s3 = core.s3_client()
    already = existing_receipts(s3)
    rows, discovery, count = read_candidates(s3, args.max_records, already)
    previous_digests = pilot.existing_digest_set(s3)
    for page in s3.get_paginator("list_objects_v2").paginate(
            Bucket=core.BUCKET, Prefix=AUDIO_ROOT):
        for item in page.get("Contents", []):
            match = re.search(r"/([a-f0-9]{64})\.[a-z0-9]+$", item["Key"])
            if match:
                previous_digests.add(match.group(1))
    states, total_bytes, pages_checked, files, batches = ingest(
        s3, rows, args, previous_digests, start)
    result = {
        "schema": "music_audio_staging_chain_report_v1",
        "timestamp": now(),
        "r2_candidate_json_objects_listed": count,
        "previously_processed_candidate_receipts": len(already),
        "current_source_claims_eligible_for_recheck": len(rows),
        "scope": "Wikimedia Commons CC0/CC-BY, private staging; other providers not yet eligible",
        "discovery": dict(discovery),
        "batches_completed": batches,
        "source_pages_checked": pages_checked,
        "downloaded_or_deduped_files": files,
        "downloaded_bytes_this_run": total_bytes,
        "new_private_staged_audio_files_this_run": states["STORED_R2"],
        "duplicate_audio_sha256_this_run": states["DUPLICATE_SHA256"],
        "public_commercial_release_rights_cleared_by_this_run": 0,
        "studio_ready_by_this_run": 0,
        "states": dict(states),
        "remaining_eligible_commons_claims_before_recheck": max(0, len(rows)-pages_checked),
        "completed_all_providers": False,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("WS3_CHAIN_FINAL " + json.dumps(result, ensure_ascii=False), flush=True)
    if states["STOP_REPEATED_SOURCE_ERRORS"] or states["STOP_IMPORT_ERRORS"]:
        raise RuntimeError("WS3 chained intake halted after bounded errors")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-files", type=int, default=48)
    parser.add_argument("--max-records", type=int, default=10000)
    parser.add_argument("--max-source-queries", type=int, default=72)
    parser.add_argument("--max-total-mib", type=int, default=250)
    parser.add_argument("--max-seconds", type=int, default=7800)
    parser.add_argument("--max-errors", type=int, default=5)
    parser.add_argument("--request-delay", type=float, default=1.0)
    parser.add_argument("--output", default="audits/music-audio-staging-chain-summary.json")
    args = parser.parse_args()
    if not (1 <= args.batch_size <= 16 and
            args.batch_size <= args.max_files <= 96 and
            1 <= args.max_records <= 10000 and
            1 <= args.max_source_queries <= 144 and
            1 <= args.max_total_mib <= 500 and
            60 <= args.max_seconds <= 14400 and
            1 <= args.max_errors <= 10 and
            0.5 <= args.request_delay <= 5):
        parser.error("Batch limits exceed approved safe bounds")
    run(args)


if __name__ == "__main__":
    main()
