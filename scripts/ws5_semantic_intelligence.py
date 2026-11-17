#!/usr/bin/env python3
"""WS5 v2: bounded CLAP semantic evidence from SHA-verified R2 originals.

Independent, opt-in pilot. Does not replace v1 DSP, approve licenses, or edit audio.
All candidate names, keys and results stay in private R2; no public artifact export.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

import boto3
import numpy as np
from botocore.config import Config
from botocore.exceptions import ClientError

import ws5_acoustic_intelligence as base

SCHEMA = "wnc_ws5_semantic_v2_pilot"
PREFIX = "internal/ws5-acoustic-intelligence/v2-clap/"
MODEL_ID = "laion/clap-htsat-unfused"
# Pinned to a published model commit, not floating main.
MODEL_REVISION = "84bcbbd1d619e407a8216371ddef36e458d95d93"
RATE = 48000  # CLAP expects 48 kHz, unlike the 16 kHz v1 DSP features.
WINDOW_S = 10
MAX_FILES = 3
MAX_SCAN = 12

# Fixed, versioned vocabulary. Similarity is NOT a class probability.
PROMPTS = {
    "rain": "The sound of continuous rain falling outside.",
    "river_stream": "The sound of a gentle flowing stream or river.",
    "waterfall": "The sound of a rushing waterfall.",
    "ocean_waves": "The sound of ocean surf and waves washing ashore.",
    "wind_trees": "The sound of wind rustling through trees and leaves.",
    "forest_birds": "The sound of wild birds singing in a forest.",
    "owl_call": "The sound of an owl hooting in the distance.",
    "frogs": "The sound of frogs croaking near water.",
    "crickets_insects": "The sound of crickets and insects chirping at night.",
    "thunder": "The sound of thunder rumbling in the distance.",
    "fireplace": "The sound of a fire crackling in a fireplace.",
    "fan_air": "The steady hum of a fan or air conditioner.",
    "piano_music": "The sound of solo piano instrumental music.",
    "guitar_music": "The sound of acoustic guitar instrumental music.",
    "other_music": "The sound of instrumental background music.",
    "human_speech": "The sound of people talking or human speech.",
    "singing_voice": "The sound of a person singing.",
    "traffic": "The sound of road traffic and passing vehicles.",
    "siren_alarm": "The sound of a siren or loud warning alarm.",
    "sharp_impact": "The sound of a sudden loud bang or sharp impact.",
}
ROLE_GROUPS = {
    "bed_candidate": {"rain", "river_stream", "waterfall", "ocean_waves", "wind_trees", "fan_air", "fireplace"},
    "event_candidate": {"forest_birds", "owl_call", "frogs", "crickets_insects", "thunder", "sharp_impact"},
    "music_candidate": {"piano_music", "guitar_music", "other_music"},
}
REVIEW_LABELS = {"human_speech", "singing_voice", "traffic", "siren_alarm", "sharp_impact"}
LABEL_VERSION = "wnc_clap_scene_labels_20261117_1"


def now():
    return datetime.now(timezone.utc).isoformat()


def sample_windows(duration):
    """Deterministic start, middle and end windows; no random sampling."""
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("invalid duration")
    length = min(WINDOW_S, duration)
    if duration <= WINDOW_S:
        return [(0.0, round(length, 3))]
    start_points = [0.0, max(0.0, (duration - length) / 2), max(0.0, duration - length)]
    return [(round(s, 3), round(length, 3)) for s in dict.fromkeys(start_points)]


def decode_48k(path, start, seconds):
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-ss", str(start),
           "-i", str(path), "-t", str(seconds), "-vn", "-map", "0:a:0",
           "-ac", "1", "-ar", str(RATE), "-f", "f32le", "pipe:1"]
    result = subprocess.run(cmd, capture_output=True, timeout=75, check=False)
    if result.returncode:
        raise RuntimeError("FFmpeg decode failed")
    samples = np.frombuffer(result.stdout, dtype="<f4")
    if len(samples) < RATE // 2 or not np.isfinite(samples).all():
        raise ValueError("invalid decoded PCM")
    return samples


def ranking(window_scores):
    """Keep raw cosine similarities, not a misleading softmax/probability."""
    if not window_scores:
        raise ValueError("no semantic windows")
    if any(set(row) != set(PROMPTS) for row in window_scores):
        raise ValueError("model scores missing vocabulary labels")
    aggregate = {}
    for label in PROMPTS:
        vals = [float(row[label]) for row in window_scores]
        if not all(math.isfinite(x) and -1.0001 <= x <= 1.0001 for x in vals):
            raise ValueError("invalid cosine similarity")
        aggregate[label] = round(float(np.median(vals)), 5)
    order = sorted(aggregate, key=lambda k: (-aggregate[k], k))
    top = [{"label": k, "cosine_similarity": aggregate[k]} for k in order[:6]]
    window_top = [
        [{"label": k, "cosine_similarity": round(float(row[k]), 5)}
         for k in sorted(row, key=lambda x: (-row[x], x))[:4]]
        for row in window_scores
    ]
    review = sorted({
        hit["label"] for hits in window_top for hit in hits[:3]
        if hit["label"] in REVIEW_LABELS
    })
    role_hints = [
        role for role, labels in ROLE_GROUPS.items()
        if set(order[:4]) & labels
    ]
    return {"top_matches": top, "window_top_matches": window_top,
            "role_hints_unverified": role_hints,
            "possible_contamination_review": review,
            "scores_are_probabilities": False,
            "classifier_confidence": "UNCALIBRATED",
            "speech_detection": "NOT_VERIFIED",
            "music_detection": "NOT_VERIFIED",
            "sleep_approval": "NOT_APPROVED",
            "license_approval": "NOT_CHECKED"}


class ClapScorer:
    def __init__(self):
        import torch
        from transformers import ClapModel, ClapProcessor
        torch.set_num_threads(2)
        self.torch = torch
        self.processor = ClapProcessor.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
        self.model = ClapModel.from_pretrained(MODEL_ID, revision=MODEL_REVISION).eval()
        texts = self.processor.tokenizer(list(PROMPTS.values()), padding=True, return_tensors="pt")
        with torch.inference_mode():
            vectors = self.model.get_text_features(**texts)
        self.text_vectors = torch.nn.functional.normalize(vectors, dim=-1)

    def score(self, samples):
        feature = self.processor.feature_extractor(samples, sampling_rate=RATE, return_tensors="pt")
        with self.torch.inference_mode():
            vec = self.model.get_audio_features(**feature)
            vec = self.torch.nn.functional.normalize(vec, dim=-1)
            similarities = (vec @ self.text_vectors.T).squeeze(0).tolist()
        if len(similarities) != len(PROMPTS):
            raise RuntimeError("unexpected model output shape")
        return dict(zip(PROMPTS, (float(x) for x in similarities)))


def inspect_one(s3, item, folder, scorer):
    sha = item["sha256"]
    key = item["r2_key"]
    record = {
        "schema": SCHEMA, "sha256": sha, "r2_key": key,
        "title": item["title"], "family_hint": item["family"],
        "analyzed_at_utc": now(), "source": "SHA256_VERIFIED_R2_ORIGINAL",
        "model": MODEL_ID, "model_revision": MODEL_REVISION,
        "vocabulary_version": LABEL_VERSION, "sample_rate_hz": RATE,
        "status": "ERROR", "analysis_scope": "THREE_SAMPLED_10S_WINDOWS_MAX",
        "sleep_approval": "NOT_APPROVED", "license_approval": "NOT_CHECKED",
        "speech_detection": "NOT_VERIFIED", "music_detection": "NOT_VERIFIED",
        "suitability_score": None
    }
    try:
        head = s3.head_object(Bucket=base.BUCKET, Key=key)
        count = int(head["ContentLength"])
        record["file_bytes"] = count
        if count > base.MAX_BYTES:
            record.update(status="SKIPPED_LARGE", reason="over 16MB v2 pilot budget")
            return record
        if count < 100:
            record.update(status="SKIPPED_INVALID", reason="too small")
            return record
        target = Path(folder) / (sha + "." + key.rsplit(".", 1)[-1])
        s3.download_file(base.BUCKET, key, str(target))
        if base.digest_file(target) != sha:
            raise ValueError("SHA256_MISMATCH")
        result = base.command(["ffprobe", "-v", "error", "-select_streams", "a:0",
                               "-show_entries", "format=duration", "-of", "json",
                               str(target)], timeout=35)
        duration = float(json.loads(result.stdout)["format"]["duration"])
        if not math.isfinite(duration) or duration <= 0 or duration > 604800:
            raise ValueError("INVALID_DURATION")
        windows = sample_windows(duration)
        scores = []
        coverage = []
        for offset, length in windows:
            audio = decode_48k(target, offset, length)
            scores.append(scorer.score(audio))
            coverage.append({"start_seconds": offset, "decoded_seconds": round(len(audio)/RATE, 3)})
        record.update(ranking(scores))
        record.update(status="SEMANTIC_SCORED_UNCALIBRATED",
                      source_sha256_verified=True,
                      duration_seconds=round(duration, 3),
                      sampled_windows=coverage,
                      sampled_seconds=round(sum(x["decoded_seconds"] for x in coverage), 3))
    except Exception as exc:
        record["reason"] = type(exc).__name__ + ": " + str(exc)[:75]
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-files", type=int, default=MAX_FILES)
    parser.add_argument("--max-scan", type=int, default=MAX_SCAN)
    args = parser.parse_args()
    if not 1 <= args.max_files <= 4 or not args.max_files <= args.max_scan <= 12:
        raise ValueError("v2 pilot maximum four files, twelve scan rows")

    s3 = boto3.client("s3", region_name="auto", endpoint_url=base.ENDPOINT,
                     aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                     aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                     config=Config(signature_version="s3v4",
                                   s3={"addressing_style": "path"},
                                   retries={"max_attempts": 4, "mode": "standard"}))

    with tempfile.TemporaryDirectory() as wd:
        pointer = base.jsonget(s3, base.WS1)
        index_sha = str(pointer["index_sha256"]).lower()
        index_key = str(pointer["index_r2_key"])
        if not base.DIGEST.fullmatch(index_sha) or not index_key.startswith(
                "internal/ai-metadata-index/v1/versions/"):
            raise RuntimeError("unexpected canonical WS1 index pointer")
        index_path = Path(wd) / "ws1.sqlite"
        s3.download_file(base.BUCKET, index_key, str(index_path))
        if base.digest_file(index_path) != index_sha:
            raise RuntimeError("WS1_INDEX_SHA256_MISMATCH")

        candidates, total = base.media_sources(index_path)
        prefix = PREFIX + "source-" + index_sha[:16] + "/"
        checkpoint_key = prefix + "checkpoint.json"
        try:
            cp = base.jsonget(s3, checkpoint_key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in ("NoSuchKey", "404", "NotFound"):
                raise
            cp = {"schema": SCHEMA, "source_index_sha256": index_sha,
                  "cursor": 0, "status_counts": {}, "batch_keys": [], "started_at": now()}
        if cp.get("schema") != SCHEMA or cp.get("source_index_sha256") != index_sha:
            raise RuntimeError("semantic checkpoint mismatch")
        start = int(cp.get("cursor", 0))
        if not 0 <= start <= len(candidates):
            raise RuntimeError("invalid checkpoint cursor")
        stop = min(len(candidates), start + args.max_scan)
        if start == len(candidates):
            print("WS5_V2_COMPLETE", json.dumps({"processed": start, "total": len(candidates)}))
            return

        # Model errors stop the run; no checkpoint advances on a model download/load failure.
        scorer = ClapScorer()
        statuses = Counter(cp.get("status_counts", {}))
        rows = []
        cursor = start
        for idx in range(start, stop):
            if len(rows) >= args.max_files:
                break
            item = candidates[idx]
            key = prefix + "records/" + item["sha256"] + ".json"
            try:
                rec = base.jsonget(s3, key, limit=150000)
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") not in ("NoSuchKey", "404", "NotFound"):
                    raise
                rec = inspect_one(s3, item, wd, scorer)
                base.jsonput(s3, key, rec)
            if rec.get("schema") != SCHEMA or rec.get("sha256") != item["sha256"]:
                raise RuntimeError("record identity mismatch")
            statuses[rec["status"]] += 1
            rows.append({"sha256": item["sha256"], "status": rec["status"],
                         "top_matches": rec.get("top_matches", [])[:3],
                         "possible_contamination_review": rec.get("possible_contamination_review", [])})
            cursor = idx + 1

        if rows:
            batch_key = prefix + f"batches/{start:06d}-{cursor:06d}.json"
            base.jsonput(s3, batch_key, {"schema": SCHEMA,
                        "source_index_sha256": index_sha, "start": start, "end": cursor,
                        "rows": rows, "generated_at_utc": now()})
            cp.setdefault("batch_keys", []).append(batch_key)
        cp.update(cursor=cursor, attempted=cursor, status_counts=dict(statuses),
                  canonical_ws1_count=total, candidate_count=len(candidates),
                  completed=cursor >= len(candidates), updated_at_utc=now())
        base.jsonput(s3, checkpoint_key, cp)
        # Never print private titles, keys, model label predictions, or individual SHA values.
        print("WS5_V2_PILOT", json.dumps({"start": start, "end": cursor,
               "attempted": len(rows), "status_counts": dict(statuses),
               "completed": cp["completed"]}), flush=True)


if __name__ == "__main__":
    main()
