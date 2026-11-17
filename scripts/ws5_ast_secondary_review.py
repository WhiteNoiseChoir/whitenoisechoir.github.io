#!/usr/bin/env python3
"""Independent AST AudioSet evidence for six flagged WS5 CLAP pilot items.

PRIVATE diagnostic evidence only. Not truth, no source or Studio mutation,
no publication approval, no audio in public artifacts or GitHub logs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile

import boto3
import numpy as np
from botocore.config import Config
from botocore.exceptions import ClientError

import ws5_acoustic_intelligence as base
import ws5_semantic_intelligence as semantic
import ws5_semantic_review as qa

SCHEMA = "wnc_ws5_ast_secondary_v1"
MODEL_ID = "MIT/ast-finetuned-audioset-10-10-0.4593"
MODEL_REVISION = "f826b80d28226b62986cc218e5cec390b1096902"
PREFIX = semantic.PREFIX + "secondary-audioset/v1/"
MAX_FILES = 6
MAX_BYTES = base.MAX_BYTES
RATE = 16000
MAX_WINDOWS = 3
TOP_K = 12

# These only indicate possible AudioSet label families. They are NOT ground truth.
EVENT_FAMILIES = {
    "speech": ("speech", "conversation", "narration", "babbling", "shout", "scream", "whisper"),
    "music": ("music", "singing", "piano", "guitar", "instrument"),
    "rain": ("rain", "thunder"),
    "freshwater": ("stream", "waterfall", "gurgling"),
    "ocean": ("ocean", "waves", "surf"),
    "wildlife": ("bird", "owl", "hoot", "cricket", "insect", "frog", "croak", "wolf"),
    "wind_fire": ("wind", "fire", "crackle", "rustling leaves", "fan", "air conditioning"),
    "traffic": ("traffic", "vehicle", "car", "siren", "engine"),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def chosen_rows(report):
    if report.get("schema") != qa.SCHEMA:
        raise ValueError("unexpected private CLAP QA report schema")
    if report.get("analysis_method") != "METADATA_HINT_VS_CLAP_RELATIVE_SIMILARITY_NOT_GROUND_TRUTH":
        raise ValueError("unexpected comparison methodology")
    items = report.get("private_review_queue")
    if not isinstance(items, list) or len(items) != qa.MAX_INSPECT:
        raise ValueError("pilot report must contain eight records")
    selected = []
    seen = set()
    for entry in items:
        digest = entry.get("source_sha256")
        if not isinstance(digest, str) or not base.DIGEST.fullmatch(digest) or digest in seen:
            raise ValueError("invalid or repeated SHA in private QA")
        seen.add(digest)
        if entry.get("audit_status") != "AUDITED":
            raise ValueError("private QA contains invalid source")
        review = entry.get("assessment")
        if not isinstance(review, dict) or review.get("human_reference_label") != "UNKNOWN" or review.get("human_listening_pass") != "NOT_RUN":
            raise ValueError("review improperly cleared")
        flags = review.get("review_flags")
        if not isinstance(flags, list) or not all(isinstance(v, str) for v in flags):
            raise ValueError("unrecognized review flags")
        if flags:
            selected.append(entry)
    if not 1 <= len(selected) <= MAX_FILES:
        raise ValueError("unexpected flagged item count: refuse broad scan")
    return selected


def windows_for_duration(duration):
    return semantic.sample_windows(duration)[:MAX_WINDOWS]


def event_families_from_labels(top):
    out = set()
    for item in top:
        label = str(item["label"]).lower()
        for family, keywords in EVENT_FAMILIES.items():
            if any(kw in label for kw in keywords):
                out.add(family)
    return sorted(out)


def summarize_outputs(score_by_window):
    if not score_by_window:
        raise ValueError("missing AST scores")
    labels = set(score_by_window[0])
    if len(labels) < 100:
        raise ValueError("not a full AudioSet output")
    for row in score_by_window:
        if set(row) != labels:
            raise ValueError("inconsistent AudioSet labels")
        for v in row.values():
            if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError("nonfinite or invalid AudioSet score")
    maxscore = {label: max(float(row[label]) for row in score_by_window) for label in labels}
    ordered = sorted(maxscore.items(), key=lambda z: (-z[1], z[0]))
    top = [{"label": name, "uncalibrated_sigmoid": round(score, 6)}
           for name, score in ordered[:TOP_K]]
    per_window = [
        [{"label": name, "uncalibrated_sigmoid": round(score, 6)}
         for name, score in sorted(row.items(), key=lambda z: (-z[1], z[0]))[:6]]
        for row in score_by_window
    ]
    speech_hints = event_families_from_labels(top)
    return {
        "top_event_hints": top,
        "per_window_event_hints": per_window,
        "event_families_possible_not_verified": speech_hints,
        "speaker_detection": "NOT_VERIFIED",
        "sound_identity_verified": False,
        "model_accuracy_verified": False,
        "scores_are_calibrated_probabilities": False,
        "human_listening_pass": "NOT_RUN",
        "license_approval": "NOT_CHECKED",
        "sleep_approval": "NOT_APPROVED",
        "publication_approved": False,
    }


class ASTScorer:
    def __init__(self):
        import torch
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        torch.set_num_threads(2)
        self.torch = torch
        self.extractor = AutoFeatureExtractor.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION)
        self.model = AutoModelForAudioClassification.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, use_safetensors=True).eval()
        self.labels = self.model.config.id2label
        if len(self.labels) < 100:
            raise RuntimeError("unexpected AudioSet model label count")
        if int(getattr(self.extractor, "sampling_rate", 0)) != RATE:
            raise RuntimeError("unexpected AudioSet input sample rate")

    def score(self, samples):
        if len(samples) < RATE // 2 or not np.isfinite(samples).all():
            raise ValueError("invalid audio input")
        features = self.extractor(samples, sampling_rate=RATE, return_tensors="pt")
        with self.torch.inference_mode():
            output = self.model(**features)
            raw = self.torch.sigmoid(output.logits).squeeze(0).tolist()
        if len(raw) != len(self.labels):
            raise RuntimeError("unexpected AST output label count")
        return {self.labels[i]: float(raw[i]) for i in range(len(raw))}


def inspect_source(s3, source, folder, scorer):
    digest = source["source_sha256"]
    key = source.get("source_r2_key_private")
    result = {
        "schema": SCHEMA,
        "sha256": digest,
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "analyzed_at_utc": now(),
        "source": "PRIVATE_R2_SHA256_VERIFIED",
        "review_only": True,
        "human_reference_label": "UNKNOWN",
        "human_listening_pass": "NOT_RUN",
        "publication_approved": False,
        "status": "ERROR",
    }
    try:
        m = base.KEY_RE.fullmatch(str(key))
        if not m or m[1].lower() != digest:
            raise ValueError("source R2 key/sha mismatch")
        h = s3.head_object(Bucket=base.BUCKET, Key=key)
        count = int(h["ContentLength"])
        if count < 100 or count > MAX_BYTES:
            result.update(status="SKIPPED_SIZE_BUDGET", file_bytes=count)
            return result
        f = Path(folder) / (digest + "." + key.rsplit(".", 1)[-1])
        s3.download_file(base.BUCKET, key, str(f))
        if base.digest_file(f) != digest:
            raise ValueError("SOURCE_SHA256_MISMATCH")
        probe = base.command(["ffprobe", "-v", "error", "-select_streams", "a:0",
                              "-show_entries", "format=duration", "-of", "json", str(f)], timeout=35)
        duration = float(json.loads(probe.stdout)["format"]["duration"])
        if not math.isfinite(duration) or not 0 < duration <= 604800:
            raise ValueError("INVALID_DURATION")
        windows = windows_for_duration(duration)
        scores, ranges = [], []
        for offset, seconds in windows:
            x = base.waveform(f, offset, seconds)  # original v1 decoder: 16k mono
            scores.append(scorer.score(x))
            ranges.append({"start_seconds": offset, "decoded_seconds": round(len(x)/RATE, 3)})
        result.update(summarize_outputs(scores))
        result.update(status="SECOND_MODEL_EVENT_HINTS_UNVERIFIED",
                      source_sha256_verified=True, duration_seconds=round(duration, 3),
                      source_r2_key_private=key, sample_windows=ranges)
    except Exception as exc:
        result["reason"] = type(exc).__name__ + ": " + str(exc)[:85]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-files", type=int, default=MAX_FILES)
    args = parser.parse_args()
    if args.max_files != MAX_FILES:
        raise ValueError("one fixed six-record pilot only")

    s3 = boto3.client("s3", region_name="auto", endpoint_url=base.ENDPOINT,
                      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                      config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                                    retries={"max_attempts": 3, "mode": "standard"}))
    pointer = base.jsonget(s3, base.WS1)
    sha = str(pointer.get("index_sha256", "")).lower()
    if not base.DIGEST.fullmatch(sha):
        raise ValueError("invalid WS1 pointer")
    review_key = (semantic.DIVERSITY_PREFIX + "source-" + sha[:16] +
                  "/qa/v1/report-000000-000008.json")
    report = base.jsonget(s3, review_key, limit=200000)
    selected = chosen_rows(report)

    target_prefix = PREFIX + "source-" + sha[:16] + "/"
    # Check all preexisting records first. Successfully analyzed SHAs are immutable/idempotent.
    outstanding = []
    existing = {}
    for row in selected:
        digest = row["source_sha256"]
        rkey = target_prefix + "records/" + digest + ".json"
        try:
            prev = base.jsonget(s3, rkey, limit=200000)
            if prev.get("schema") != SCHEMA or prev.get("sha256") != digest:
                raise ValueError("existing record schema/source mismatch")
            if prev.get("status") == "SECOND_MODEL_EVENT_HINTS_UNVERIFIED":
                existing[digest] = prev
                continue
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in ("NoSuchKey", "404", "NotFound"):
                raise
        outstanding.append(row)

    records = dict(existing)
    with tempfile.TemporaryDirectory() as wd:
        # Skip model download entirely if all records were already completed.
        scorer = ASTScorer() if outstanding else None
        for row in outstanding:
            rec = inspect_source(s3, row, wd, scorer)
            digest = row["source_sha256"]
            base.jsonput(s3, target_prefix + "records/" + digest + ".json", rec)
            records[digest] = rec

    counts = Counter(rec["status"] for rec in records.values())
    family_counts = Counter()
    for rec in records.values():
        if rec.get("status") == "SECOND_MODEL_EVENT_HINTS_UNVERIFIED":
            family_counts.update(rec["event_families_possible_not_verified"])
    summary = {
        "schema": SCHEMA,
        "source_index_sha256": sha,
        "review_source": "PRIVATE_CLAP_QA_REPORT",
        "source_review_key_private": review_key,
        "created_at_utc": now(),
        "selected_flagged": len(selected),
        "status_counts": dict(counts),
        "possible_event_family_counts_not_truth": dict(family_counts),
        "review_required": len(selected),
        "human_labeled": 0,
        "human_verified_accuracy": None,
        "publication_approved": 0,
        "no_public_artifacts": True,
        "no_originals_modified": True,
    }
    base.jsonput(s3, target_prefix + "summary.json", summary)
    # Only aggregate counts leave the private bucket.
    print("WS5_AST_SECONDARY", json.dumps({
        "selected_flagged": len(selected), "status_counts": dict(counts),
        "possible_event_family_counts_not_truth": dict(family_counts),
        "human_verified_accuracy": "NOT_MEASURED",
        "private_source_records": True,
        "no_originals_modified": True,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
