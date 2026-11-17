#!/usr/bin/env python3
"""WS5: private, non-approving CLAP + AudioSet review-priority synthesis.

Read only eight-file QA + six SHA AST records; output a private listening plan.
Never downloads audio, asserts AI accuracy, changes publication state or logs IDs.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os

import boto3
from botocore.config import Config

import ws5_acoustic_intelligence as base
import ws5_semantic_intelligence as semantic
import ws5_semantic_review as clapqa
import ws5_ast_secondary_review as ast

SCHEMA = "wnc_ws5_cross_model_triage_v1"


def triage_item(source, secondary):
    digest = source.get("source_sha256")
    if not isinstance(digest, str) or not base.DIGEST.fullmatch(digest):
        raise ValueError("invalid private SHA")
    key = source.get("source_r2_key_private")
    match = base.KEY_RE.fullmatch(str(key))
    if not match or match[1].lower() != digest:
        raise ValueError("source key must be canonical SHA-addressed audio")

    review = source.get("assessment")
    if source.get("audit_status") != "AUDITED" or not isinstance(review, dict):
        raise ValueError("unaudited source")
    flags = review.get("review_flags")
    if not isinstance(flags, list) or any(not isinstance(f, str) for f in flags) or not flags:
        raise ValueError("not an outstanding review case")
    if review.get("human_listening_pass") != "NOT_RUN" or review.get("human_reference_label") != "UNKNOWN":
        raise ValueError("human review already modified")

    if secondary.get("schema") != ast.SCHEMA or secondary.get("sha256") != digest or (
        secondary.get("model") != ast.MODEL_ID or
        secondary.get("model_revision") != ast.MODEL_REVISION or
        secondary.get("status") != "SECOND_MODEL_EVENT_HINTS_UNVERIFIED" or
        secondary.get("source_sha256_verified") is not True
    ):
        raise ValueError("secondary inference/identity not verified")
    if secondary.get("human_listening_pass") != "NOT_RUN" or secondary.get("publication_approved") is not False:
        raise ValueError("secondary result incorrectly cleared for release")

    families = secondary.get("event_families_possible_not_verified")
    if not isinstance(families, list) or any(f not in ast.EVENT_FAMILIES for f in families):
        raise ValueError("invalid secondary AudioSet family")
    windows = secondary.get("sample_windows")
    if not isinstance(windows, list) or not 1 <= len(windows) <= 3:
        raise ValueError("missing proposed listening windows")
    for win in windows:
        if not isinstance(win, dict) or not 0 <= float(win.get("start_seconds", -1)) or not 0 < float(win.get("decoded_seconds", 0)) <= 10.1:
            raise ValueError("invalid window geometry")

    # Review PRIORITY is not a probability, detection, or accuracy claim.
    clap_contamination = "POSSIBLE_CONTAMINATION_UNVERIFIED" in flags
    speech_hint = "speech" in families
    traffic_hint = "traffic" in families
    if speech_hint and clap_contamination:
        priority, reasons = 1, ["MULTI_MODEL_POSSIBLE_VOICE_REVIEW"]
    elif speech_hint or traffic_hint:
        priority, reasons = 2, ["SECOND_MODEL_POSSIBLE_SPEECH_OR_TRAFFIC"]
    elif clap_contamination or "WINDOW_TOP1_VARIATION" in flags:
        priority, reasons = 2, ["CLAP_CONTAMINATION_OR_TEMPORAL_VARIATION"]
    elif "METADATA_CLAP_DISAGREEMENT" in flags:
        priority, reasons = 3, ["POSSIBLE_METADATA_MODEL_DISAGREEMENT"]
    else:
        priority, reasons = 4, ["WEAK_OR_UNKNOWN_METADATA_HINT"]

    return {
        "source_sha256_private": digest,
        "source_title_private": source.get("source_title_private"),
        "original_r2_key_private": key,
        "review_priority_ordinal_only": priority,
        "priority_reasons_unverified": reasons,
        "clap_review_flags_unverified": flags,
        "clap_ranked_labels_unverified": review.get("top_matches", [])[:6],
        "ast_ranked_events_unverified": secondary.get("top_event_hints", [])[:12],
        "ast_possible_event_families_unverified": families,
        "audition_windows": [
            {"start_seconds": win["start_seconds"],
             "duration_seconds": win["decoded_seconds"],
             "reviewed_by_human": False}
            for win in windows
        ],
        "human_reference_labels": [],
        "listening_result": "NOT_RUN",
        "label_accuracy": "NOT_MEASURED",
        "speech_presence": "NOT_VERIFIED",
        "license_clearance": "NOT_VERIFIED",
        "sleep_approval": "NOT_APPROVED",
        "publication_approved": False,
    }


def synthesize(clap_report, ast_records):
    selected = ast.chosen_rows(clap_report)
    keys = {row["source_sha256"] for row in selected}
    if not isinstance(ast_records, dict) or set(ast_records) != keys:
        raise ValueError("secondary record identities don't match flagged QA list")
    queue = [triage_item(row, ast_records[row["source_sha256"]]) for row in selected]
    queue.sort(key=lambda row: (row["review_priority_ordinal_only"], row["source_sha256_private"]))
    counts = Counter(x["review_priority_ordinal_only"] for x in queue)
    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HUMAN_LISTENING_NOT_STARTED",
        "comparison": "UNVERIFIED_CLAP_VS_AST_EVIDENCE",
        "source_count": len(selected),
        "priority_counts": {str(key): counts[key] for key in sorted(counts)},
        "audition_total_windows": sum(len(x["audition_windows"]) for x in queue),
        "reference_accuracy": None,
        "human_verified_count": 0,
        "publication_approved": False,
        "private_listening_queue": queue,
    }


def main():
    s3 = boto3.client(
        "s3", region_name="auto", endpoint_url=base.ENDPOINT,
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      retries={"max_attempts": 3, "mode": "standard"})
    )
    pointer = base.jsonget(s3, base.WS1)
    sha = str(pointer.get("index_sha256", "")).lower()
    if not base.DIGEST.fullmatch(sha):
        raise ValueError("WS1 canonical index missing")
    clap_prefix = semantic.DIVERSITY_PREFIX + "source-" + sha[:16] + "/"
    secondary_prefix = ast.PREFIX + "source-" + sha[:16] + "/"
    report = base.jsonget(s3, clap_prefix + "qa/v1/report-000000-000008.json", limit=200000)
    selected = ast.chosen_rows(report)
    records = {}
    for row in selected:
        digest = row["source_sha256"]
        records[digest] = base.jsonget(s3, secondary_prefix + "records/" + digest + ".json", limit=200000)

    out = synthesize(report, records)
    target = secondary_prefix + "human-review/v1/queue.json"
    # Only output to PRIVATE R2; no public artifacts or source audio.
    base.jsonput(s3, target, out)
    print("WS5_CROSS_MODEL_TRIAGE", json.dumps({
        "source_count": out["source_count"],
        "priority_counts": out["priority_counts"],
        "audition_total_windows": out["audition_total_windows"],
        "reference_accuracy": "NOT_MEASURED",
        "human_verified_count": 0,
        "report_storage": "PRIVATE_R2",
        "audio_downloads": 0,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
