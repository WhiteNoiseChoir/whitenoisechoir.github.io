#!/usr/bin/env python3
"""Verify staged listening QA without silently promoting unapproved audio.

This gate validates 12 DSP masters plus four CC0 audition assets, their original
manifest checksums, relative spectral-shape screening, and the production hold.
It explicitly DOES NOT substitute for human listening or iPhone playback QA.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def check(condition, message):
    if not condition:
        raise AssertionError(message)

queue = read("audio/review-queue-20261108.json")
extended = read("audio/extended-dsp-manifest.json")
field = read("signature/field-review/manifest.json")
hls = read("audio/continuous/manifest.json")
field_audit = read("audio/field-source-audit.json")

check(queue["state"] == "TECHNICAL_QA_COMPLETE_HUMAN_LISTENING_INCOMPLETE", "Review incorrectly marked completed")
check(queue["production_change_authorized_by_listening"] is False, "Production promotion requires actual listening approval")
check(len(queue["dsp"]) == 12 and len(queue["cc0_field"]) == 4, "Expected twelve DSP plus four CC0 candidates")
check(len(hls["records"]) == 22, "Unexpected main-site HLS inventory")
check(sum(x["original_source_length_category"] == "LEGACY_CC0_SHORT_DEMO" for x in hls["records"]) == 4, "Four legacy field recordings must remain untouched")
check(sum(x["original_source_length_category"] == "10_MINUTE_MASTER" for x in hls["records"]) == 18, "Unexpected 10-minute production count")

ids = [r["id"] for r in queue["dsp"] + queue["cc0_field"]]
check(len(ids) == len(set(ids)) == 16, "Duplicate candidate ID")
source_dsp = {r["id"]: r for r in extended["tracks"]}
source_field = {r["id"]: r for r in field["records"]}
audit_field = {r["id"]: r for r in field_audit["tracks"]}
check(set(source_dsp) == {r["id"] for r in queue["dsp"]}, "DSP list differs from source manifest")
check(set(source_field) == {r["id"] for r in queue["cc0_field"]}, "Field audition list differs from source manifest")

for item in queue["dsp"]:
    ident = item["id"]
    src = source_dsp[ident]
    check(item["technical_status"] == src["qa"]["technical_status"] == "PASS", ident + " technical QA")
    check(item["human_listening"] == "PENDING", ident + " human listening was not approved")
    check(item["source_sha256"] == src["file_sha256"], ident + " unexpected master checksum")
    check(item["duration_seconds"] == src["qa"]["duration_seconds"] == 600, ident + " duration changed")
    check(item["file"] == src["file"], ident + " unexpected source filename")
    check(item["spectral_bands_db"] == src["qa"]["spectral_band_amplitude_dbfs"], ident + " spectral data changed")
    check(digest(ROOT / item["file"]) == item["source_sha256"], ident + " file differs from manifest")
    check(src["qa"]["stereo_mode"] == "centered_dual_mono", ident + " changed stereo implementation")
    print("DSP_MASTER_PASS", ident, flush=True)

for item in queue["cc0_field"]:
    ident = item["id"]
    src = source_field[ident]
    audit = audit_field[ident]
    check(item["technical_status"] == src["qa"]["status"] == "PASS", ident + " candidate QA")
    check(item["human_listening"] == "PENDING", ident + " not human-approved")
    check(item["production_policy"] == "KEEP_LEGACY_54_SECOND_MASTER_UNTIL_LISTENING_APPROVAL", ident + " promotion hold")
    check(item["file"] == src["preview_file"], ident + " candidate path changed")
    check(item["source_sha256"] == src["sha256"], ident + " candidate hash changed")
    check(digest(ROOT / item["file"]) == item["source_sha256"], ident + " file differs from audition manifest")
    check(src["license"] == item["license"] == audit["declared_source_license"] == "CC0-1.0", ident + " license mismatch")
    check(item["independent_source_seconds"] == src["independent_recording_seconds"], ident + " independent duration mismatch")
    check(item["duration_seconds"] == src["qa"]["seconds"], ident + " candidate duration mismatch")
    for research in item["longer_cc0_research_candidates"]:
        check(research["source_page_checked"] is True, ident + " unverified research reference")
        check(research["actual_media_audited"] is False, ident + " cannot claim media audit")
        check(research["license"] == "CC0-1.0" and research["url"].startswith("https://freesound.org/people/"), ident + " research link invalid")
    print("CC0_CANDIDATE_PASS", ident, flush=True)

threshold = queue["spectral_screening_threshold_db"]
def distance(a, b):
    aa = [v - a[0] for v in a]
    bb = [v - b[0] for v in b]
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(aa, bb)) / len(aa))

expected = {}
for i, a in enumerate(queue["dsp"]):
    for b in queue["dsp"][i+1:]:
        score = round(distance(a["spectral_bands_db"], b["spectral_bands_db"]), 2)
        if score < threshold:
            expected.setdefault(a["id"], []).append((b["id"], score))
            expected.setdefault(b["id"], []).append((a["id"], score))
for item in queue["dsp"]:
    found = sorted((r["compare_to"], r["spectral_shape_rmse_db"]) for r in item["distinctiveness_attention"])
    check(found == sorted(expected.get(item["id"], [])), "Spectral screening drift: " + item["id"])

print("LISTENING_READINESS_GATE_PASS", json.dumps({
    "technical_dsp": 12,
    "technical_cc0_candidates": 4,
    "human_approved": 0,
    "main_site_HLS_unchanged": 22,
    "flagged_spectral_pairs": sum(len(v) for v in expected.values()) // 2,
    "result": "REVIEW_READY_NOT_PRODUCTION_APPROVED"
}), flush=True)
