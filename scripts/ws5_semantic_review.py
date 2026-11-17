#!/usr/bin/env python3
"""WS5 v2 post-inference audit: compare private CLAP evidence with metadata hints.

No audio download, CLAP inference, publishing, source modifications or license approval.
Outputs a private review queue for human reference labeling. Source metadata is NOT truth.
GitHub logs only contain aggregate counters, never raw titles, SHA or R2 keys.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

import ws5_acoustic_intelligence as base
import ws5_semantic_intelligence as semantic

SCHEMA = "wnc_ws5_semantic_review_v1"
EXPECTED = {
    "rain_storm": {"rain", "thunder"},
    "freshwater": {"river_stream", "waterfall"},
    "ocean": {"ocean_waves"},
    "wildlife": {"forest_birds", "owl_call", "frogs", "crickets_insects"},
    "wind_fire_fan": {"wind_trees", "fireplace", "fan_air"},
    "other": set(),
}
MAX_INSPECT = 8


def _safe_similarity(entry):
    if not isinstance(entry, dict) or entry.get("label") not in semantic.PROMPTS:
        raise ValueError("invalid CLAP category")
    score = entry.get("cosine_similarity")
    if isinstance(score, bool) or not isinstance(score, (float, int)):
        raise ValueError("missing model similarity")
    if not math.isfinite(score) or not -1.0001 <= score <= 1.0001:
        raise ValueError("invalid model similarity")
    return float(score)


def inspect_record(record, group):
    """Heuristic consistency checks only; NEVER a ground-truth accuracy verdict."""
    if group not in EXPECTED:
        raise ValueError("unknown metadata stratum")
    if record.get("status") != "SEMANTIC_SCORED_UNCALIBRATED":
        raise ValueError("source has no successful CLAP result")
    if record.get("schema") != semantic.SCHEMA:
        raise ValueError("unknown source record schema")
    if record.get("source_sha256_verified") is not True:
        raise ValueError("original SHA verification missing")
    if record.get("model") != semantic.MODEL_ID or record.get("model_revision") != semantic.MODEL_REVISION:
        raise ValueError("model identity mismatch")
    if record.get("vocabulary_version") != semantic.LABEL_VERSION:
        raise ValueError("CLAP prompt vocabulary version mismatch")
    if record.get("sleep_approval") != "NOT_APPROVED":
        raise ValueError("unexpected sleep approval")
    if record.get("license_approval") != "NOT_CHECKED":
        raise ValueError("unexpected rights approval")
    if record.get("suitability_score") is not None:
        raise ValueError("unsupported suitability score")
    if record.get("speech_detection") != "NOT_VERIFIED":
        raise ValueError("unexpected speech clearance")

    top = record.get("top_matches")
    windows = record.get("window_top_matches")
    if not isinstance(top, list) or len(top) < 3 or len(top) > 6:
        raise ValueError("invalid CLAP ranking")
    if not isinstance(windows, list) or not 1 <= len(windows) <= 3:
        raise ValueError("invalid model windows")
    if len({x["label"] for x in top}) != len(top):
        raise ValueError("duplicate model category")
    for match in top:
        _safe_similarity(match)
    if any(_safe_similarity(top[i]) < _safe_similarity(top[i+1]) for i in range(len(top)-1)):
        raise ValueError("unsorted CLAP top ranking")
    for w in windows:
        if not isinstance(w, list) or not 1 <= len(w) <= 4:
            raise ValueError("invalid window ranking")
        for entry in w:
            _safe_similarity(entry)

    expected = EXPECTED[group]
    top_three = [item["label"] for item in top[:3]]
    six = [item["label"] for item in top]
    rank = next((i + 1 for i, label in enumerate(six) if label in expected), None)
    # Similarity margins describe rank separation only, never predictive confidence.
    separation = round(_safe_similarity(top[0]) - _safe_similarity(top[1]), 5)
    top_window_labels = [w[0]["label"] for w in windows]

    review_flags = []
    if not expected:
        review_flags.append("METADATA_CATEGORY_UNKNOWN")
    elif rank is None:
        review_flags.append("METADATA_CLAP_DISAGREEMENT")
    elif rank > 3:
        review_flags.append("WEAK_METADATA_CLAP_ALIGNMENT")
    if len(set(top_window_labels)) > 1:
        review_flags.append("WINDOW_TOP1_VARIATION")
    contamination = record.get("possible_contamination_review", [])
    if not isinstance(contamination, list) or any(x not in semantic.REVIEW_LABELS for x in contamination):
        raise ValueError("invalid contamination review signals")
    if contamination:
        review_flags.append("POSSIBLE_CONTAMINATION_UNVERIFIED")

    # All human judgments stay UNKNOWN. Strong metadata agreement is NOT truth.
    return {
        "metadata_group": group,
        "expected_clap_categories_unverified": sorted(expected),
        "best_expected_rank": rank,
        "top_similarity_margin_not_confidence": separation,
        "top_matches": top[:6],
        "window_top_matches": windows,
        "review_flags": review_flags,
        "human_reference_label": "UNKNOWN",
        "human_listening_pass": "NOT_RUN",
        "semantic_accuracy_verified": False,
        "publication_approved": False,
    }


def summarize(rows):
    counts = Counter()
    for item in rows:
        state = item["audit_status"]
        counts["audited_records"] += 1
        counts[state] += 1
        if state != "AUDITED":
            continue
        assessment = item["assessment"]
        counts["metadata_group_" + assessment["metadata_group"]] += 1
        if assessment["best_expected_rank"] is not None and assessment["best_expected_rank"] <= 3:
            counts["metadata_agreement_top3_not_truth"] += 1
        else:
            counts["metadata_agreement_not_established"] += 1
        if assessment["review_flags"]:
            counts["items_for_human_review"] += 1
        for flag in assessment["review_flags"]:
            counts["flag_" + flag] += 1
    return dict(sorted(counts.items()))


def read_pilot(s3):
    """Find pilot from its private versioned checkpoint; don't download audio."""
    pointer = base.jsonget(s3, base.WS1)
    sha = str(pointer.get("index_sha256", "")).lower()
    if not base.DIGEST.fullmatch(sha):
        raise ValueError("canonical source SHA missing")
    prefix = semantic.DIVERSITY_PREFIX + "source-" + sha[:16] + "/"
    checkpoint = base.jsonget(s3, prefix + "checkpoint.json")
    if checkpoint.get("schema") != semantic.SCHEMA or checkpoint.get("source_index_sha256") != sha:
        raise ValueError("private pilot checkpoint schema/source mismatch")
    if not 0 <= int(checkpoint.get("cursor", -1)) <= int(checkpoint.get("candidate_count", 0)):
        raise ValueError("invalid cursor")
    batch_key = prefix + "batches/000000-000008.json"
    batch = base.jsonget(s3, batch_key, limit=150000)
    if batch.get("schema") != semantic.SCHEMA or batch.get("source_index_sha256") != sha:
        raise ValueError("private pilot batch mismatch")
    if batch.get("start") != 0 or batch.get("end") != 8:
        raise ValueError("expected bounded 8-record pilot")
    if not isinstance(batch.get("rows"), list) or len(batch["rows"]) != MAX_INSPECT:
        raise ValueError("pilot batch record count mismatch")
    if int(checkpoint.get("cursor", 0)) < MAX_INSPECT:
        raise ValueError("R2 checkpoint is before pilot completion")
    return prefix, batch["rows"]


def build_report(s3, prefix, rows):
    reviewed = []
    visited = set()
    for row in rows:
        digest = row.get("sha256")
        if not isinstance(digest, str) or not base.DIGEST.fullmatch(digest) or digest in visited:
            raise ValueError("invalid or repeated R2 SHA")
        visited.add(digest)
        group = row.get("metadata_hint_group")
        if group not in EXPECTED:
            raise ValueError("missing stratification metadata")
        record_key = prefix + "records/" + digest + ".json"
        record = base.jsonget(s3, record_key, limit=150000)
        if record.get("sha256") != digest:
            raise ValueError("record SHA identity mismatch")
        if record.get("status") != row.get("status"):
            raise ValueError("batch/record status disagreement")
        if not isinstance(record.get("r2_key"), str) or not base.KEY_RE.fullmatch(record["r2_key"]):
            raise ValueError("record source key invalid")
        if base.KEY_RE.fullmatch(record["r2_key"])[1].lower() != digest:
            raise ValueError("R2 original SHA mismatch")
        detail = {
            "source_sha256": digest,
            "source_title_private": record.get("title"),
            "source_r2_key_private": record["r2_key"],
            "metadata_family_private": record.get("family_hint"),
        }
        try:
            assessment = inspect_record(record, group)
            detail.update(audit_status="AUDITED", assessment=assessment)
        except ValueError as exc:
            detail.update(audit_status="INVALID_MODEL_RESULT", invalid_reason=str(exc)[:90])
        reviewed.append(detail)
    counts = summarize(reviewed)
    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "PRIVATE_R2_VERIFIED_WS5_CLAP_DIVERSITY_PILOT",
        "analysis_method": "METADATA_HINT_VS_CLAP_RELATIVE_SIMILARITY_NOT_GROUND_TRUTH",
        "human_reference_accuracy": None,
        "sleep_suitability_verified": False,
        "rights_verified": False,
        "counts": counts,
        "private_review_queue": reviewed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Read all pilot records, write nothing")
    args = parser.parse_args()
    s3 = boto3.client("s3", region_name="auto", endpoint_url=base.ENDPOINT,
                      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                      config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                                    retries={"max_attempts": 3, "mode": "standard"}))
    prefix, rows = read_pilot(s3)
    report = build_report(s3, prefix, rows)
    if not args.dry_run:
        # The report and source identifiers stay PRIVATE in R2. No public CI artifacts.
        base.jsonput(s3, prefix + "qa/v1/report-000000-000008.json", report)
    print("WS5_SEMANTIC_QA", json.dumps({
        "records": len(rows),
        "counts": report["counts"],
        "report_storage": "PRIVATE_R2" if not args.dry_run else "DRY_RUN",
        "accuracy": "NOT_MEASURED_NO_HUMAN_GROUND_TRUTH",
        "audio_downloads": 0,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
