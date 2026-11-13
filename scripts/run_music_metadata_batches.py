#!/usr/bin/env python3
"""Automated bounded follow-on music metadata batches, private R2 progress gates.

Runs only on a separate feature-branch GitHub Actions job. Waits for the preceding
Openverse run; then launches fresh search waves in sequence, stopping at a
VERIFIED R2 candidate-object count >= target or when blocked/exhausted.
No audio downloads, no main merge, no Studio writes.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time

from botocore.exceptions import ClientError
import requests

import scan_music_candidate_metadata as core
import scan_openverse_music_metadata as openverse

KEY_PATTERN = re.compile(
    r"^internal/music-candidates/v1/[a-f0-9]{2}/([a-f0-9]{64})\.json$")
CHECKPOINT = "internal/music-candidates/control/openverse-auto-v1/"
DEFAULT_WAIT_FOR_RUN = 43378869855
RUN_STATUS_URL = (
    "https://api.github.com/repos/WhiteNoiseChoir/"
    "whitenoisechoir.github.io/actions/runs/"
)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def candidate_keys(s3):
    """Count unique, present candidate-object keys, excluding reports and audio."""
    found = set()
    pages = s3.get_paginator("list_objects_v2").paginate(
        Bucket=core.BUCKET, Prefix=core.PRIVATE_ROOT + "v1/")
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if KEY_PATTERN.fullmatch(key) and int(obj.get("Size", 0)) > 0:
                found.add(key)
    return found


def checkpoint_waves(s3):
    used = set()
    pages = s3.get_paginator("list_objects_v2").paginate(
        Bucket=core.BUCKET, Prefix=CHECKPOINT)
    for page in pages:
        for obj in page.get("Contents", []):
            name = obj["Key"].removeprefix(CHECKPOINT)
            if re.fullmatch(r"wave-[1-9]\.json", name):
                used.add(int(name[5]))
    return used


def save_checkpoint(s3, wave, outcome):
    key = f"{CHECKPOINT}wave-{wave}.json"
    payload = json.dumps(outcome, ensure_ascii=False, sort_keys=True).encode()
    try:
        s3.put_object(Bucket=core.BUCKET, Key=key, Body=payload,
                      ContentType="application/json", CacheControl="private,no-store",
                      IfNoneMatch="*")
    except ClientError as exc:
        if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 412:
            raise
    return key


def wait_for_prior_run(run_id, max_wait_seconds=2700, pause=25):
    """Require prior wave to finish; never run overlapping uncapped API sweeps."""
    if not run_id:
        return "skipped"
    headers = {"Accept": "application/vnd.github+json"}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    deadline = time.monotonic() + max_wait_seconds
    while time.monotonic() < deadline:
        response = requests.get(RUN_STATUS_URL + str(run_id),
                                headers=headers, timeout=(8, 25))
        response.raise_for_status()
        doc = response.json()
        if doc.get("status") == "completed":
            return doc.get("conclusion", "unknown")
        print("AUTOBATCH_WAIT_PREVIOUS " +
              json.dumps({"run_id": run_id, "status": doc.get("status")}), flush=True)
        time.sleep(pause)
    raise TimeoutError("Prior music metadata workflow did not finish within cap")


def verify_candidate(s3, key):
    """Inspect one persisted JSON's stable identity; never trust filename alone."""
    response = s3.get_object(Bucket=core.BUCKET, Key=key)
    data = json.loads(response["Body"].read())
    digest = KEY_PATTERN.fullmatch(key).group(1)
    return (
        data.get("candidate_id") == "music-candidate-" + digest
        and data.get("schema") == "music_source_candidate_v1"
        and data.get("status") == "candidate_only_not_downloaded"
        and isinstance(data.get("source_page"), str)
        and bool(data.get("source_page"))
    )


def verify_full_index(s3, keys, workers=8):
    invalid = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futs = {executor.submit(verify_candidate, s3, k): k for k in keys}
        for fut in as_completed(futs):
            try:
                if not fut.result():
                    invalid.append(futs[fut])
            except Exception:
                invalid.append(futs[fut])
    return {"objects_seen": len(keys), "valid": len(keys) - len(invalid),
            "invalid": len(invalid), "invalid_example_count": min(len(invalid), 5)}


def report_write(path, data):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    line = "AUTOBATCH_FINAL " + json.dumps({
        "state": data["state"], "stored_candidate_objects": data["candidate_objects"],
        "target": data["target"], "batches": len(data["batches"]),
        "finished_at": utcnow(),
    }, ensure_ascii=False)
    print(line, flush=True)
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf8") as f:
            f.write(f"## Music Candidate Index: {data['state']}\n\n")
            f.write(f"**{data['candidate_objects']}/{data['target']}** private R2 candidate JSON objects\n\n")
            f.write(f"Successful new batches: {len(data['batches'])}; *audio downloads 0*\n\n")
            f.write("Records are **unverified metadata**, not audio or copyright-cleared music.\n")
    return data


def run(args):
    if not 1 <= args.target <= 10000:
        raise ValueError("Unsafe target")
    if not 1 <= args.max_batches <= 9:
        raise ValueError("Max waves limited to 1..9")
    report = {
        "schema": "auto_music_metadata_batches_v1",
        "started_at": utcnow(), "target": args.target, "candidate_objects": 0,
        "state": "INITIALIZING", "previous_run": args.wait_for_run,
        "batches": [], "downloaded": 0, "audio_uploaded": 0,
        "rights_status": "unverified-source-license-and-composition-pending",
    }
    try:
        conclusion = wait_for_prior_run(args.wait_for_run, args.wait_seconds)
        report["previous_run_conclusion"] = conclusion
        if conclusion not in ("success", "skipped"):
            report["state"] = "BLOCKED_PRIOR_RUN_" + conclusion.upper()
            return report_write(args.output, report)
        s3 = core.s3_client()
        keys = candidate_keys(s3)
        report["candidate_objects"] = len(keys)
        report["baseline_objects"] = len(keys)
        core.emit("AUTOBATCH_BASELINE", {"stored_candidate_objects": len(keys),
                                        "target": args.target, "count_method": "private_R2_objects"})
        if len(keys) >= args.target:
            verification = verify_full_index(s3, keys)
            report["verification"] = verification
            report["state"] = "TARGET_REACHED" if verification["valid"] >= args.target else "BLOCKED_INVALID_METADATA"
            return report_write(args.output, report)

        completed = checkpoint_waves(s3)
        report["previously_completed_waves"] = sorted(completed)
        consecutive_empty = 0
        budget_start = time.monotonic()
        for wave in range(1, min(args.max_batches, 9) + 1):
            if wave in completed:
                continue
            if time.monotonic() - budget_start > args.budget_seconds:
                report["state"] = "BUDGET_PAUSED"
                break
            # Distinct search terms per wave; avoid repeatedly hitting identical pages.
            run_id = os.getenv("GITHUB_RUN_ID", "manual")
            original_id = os.getenv("GITHUB_RUN_ID")
            os.environ["GITHUB_RUN_ID"] = f"{run_id}-wave{wave}"
            try:
                sub_args = argparse.Namespace(
                    persist=True, shard_index=0, shard_count=1,
                    batch_index=wave, per_group=25, pages=2,
                    max_candidates=min(350, max(120, args.target - len(keys) + 20)),
                    output=f"audits/music-auto-wave-{wave}.json",
                )
                result = openverse.scan(sub_args)
            finally:
                if original_id is None:
                    os.environ.pop("GITHUB_RUN_ID", None)
                else:
                    os.environ["GITHUB_RUN_ID"] = original_id
            stats = result["storage"]
            api_errors = sum(d.get("api_errors", 0)
                             for d in result.get("family_diagnostics", {}).values())
            keys = candidate_keys(s3)
            report["candidate_objects"] = len(keys)
            detail = {
                "wave": wave, "finished_at": utcnow(),
                "found_candidates": result["found_unique_in_shard"],
                "persisted_new": stats["created"],
                "persisted_existing": stats["existing"],
                "write_errors": stats["errors"],
                "api_errors": api_errors,
                "stored_candidate_objects": len(keys),
                "github_run_id": run_id,
            }
            report["batches"].append(detail)
            checkpoint_key = save_checkpoint(s3, wave, detail)
            detail["checkpoint_key"] = checkpoint_key
            core.emit("AUTOBATCH_PROGRESS", detail)
            if stats["errors"]:
                report["state"] = "BLOCKED_R2_WRITE_ERRORS"
                break
            if api_errors >= 8:
                report["state"] = "BLOCKED_PROVIDER_API_ERRORS"
                break
            if len(keys) >= args.target:
                verification = verify_full_index(s3, keys)
                report["verification"] = verification
                report["state"] = "TARGET_REACHED" if verification["valid"] >= args.target else "BLOCKED_INVALID_METADATA"
                break
            consecutive_empty = consecutive_empty + 1 if stats["created"] == 0 else 0
            if consecutive_empty >= 3:
                report["state"] = "NO_NEW_METADATA_3_WAVES"
                break
        else:
            report["state"] = "QUERY_WAVES_EXHAUSTED"
    except Exception as exc:
        report["state"] = "FAILED"
        report["error"] = type(exc).__name__ + ": " + str(exc)[:220]
    return report_write(args.output, report)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--max-batches", type=int, default=9)
    ap.add_argument("--wait-for-run", type=int, default=DEFAULT_WAIT_FOR_RUN)
    ap.add_argument("--wait-seconds", type=int, default=2700)
    ap.add_argument("--budget-seconds", type=int, default=6000)
    ap.add_argument("--output", default="audits/music-auto-progress.json")
    res = run(ap.parse_args())
    # Emit a failed job for real faults so reviewers cannot mistake it for success.
    if res["state"].startswith(("FAILED", "BLOCKED_")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
