#!/usr/bin/env python3
"""WS2: bounded private music candidate metadata expansion to 5,000 objects.

Only metadata, never media. Provider searches use official Openverse and Internet
Archive adapters; source-license claims and search hints are not rights clearance.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

import scan_music_candidate_metadata as core
import scan_openverse_music_metadata as ov
import scan_archive_music_metadata as ia
from run_music_metadata_batches import candidate_keys, verify_full_index

CONTROL = "internal/music-candidates/control/ws2-5k-v1/"
# The 0-9 Openverse waves are handled by the earlier controller. These are
# deliberately new language/role combinations and nonidentical query surfaces.
WAVES = (
    ("openverse", ("one shot", "single hit")),
    ("archive", ("solo", "sample")),
    ("openverse", ("drone", "sustained tone")),
    ("archive", ("traditional", "instrument")),
    ("openverse", ("plucked", "bowed")),
    ("archive", ("loop", "improvisation")),
    ("openverse", ("world music", "ethnic instrument")),
    ("archive", ("acoustic", "solo")),
    ("openverse", ("sound effect", "percussion")),
    ("archive", ("ambient", "soundscape")),
    ("openverse", ("melody", "phrase")),
    ("archive", ("short", "recording")),
    ("openverse", ("arpeggiated", "musical texture")),
    ("archive", ("folk", "instrumental")),
    ("openverse", ("woodwind", "brass")),
    ("archive", ("string", "keyboard")),
    ("openverse", ("ritual", "ceremonial")),
    ("archive", ("handpan", "kalimba")),
)
# Additional taxonomy for culturally diverse instrument candidates. Search
# labels remain hints, never verified instrumentation.
EXTRA_FAMILIES = (
    "oud", "ney", "qanun", "duduk", "santoor", "sarangi", "tabla",
    "djembe", "balafon", "kora", "berimbau", "bansuri", "shamisen",
    "sanshin", "gayageum", "geomungo", "pipa", "sheng", "suona",
    "hulusi", "dan bau", "dan tranh", "dan nguyet", "dan nhi",
    "guitar harmonics", "singing bowl", "celesta", "vibraphone",
    "bassoon", "piccolo", "tuba", "bass clarinet", "dulcimer",
    "nyckelharpa", "hurdy gurdy", "ocarina", "recorder", "jaw harp",
)


def now():
    return datetime.now(timezone.utc).isoformat()


def checkpoint(s3, index):
    return CONTROL + f"wave-{index:02d}.json"


def is_done(s3, index):
    try:
        s3.head_object(Bucket=core.BUCKET, Key=checkpoint(s3, index))
        return True
    except Exception as exc:
        response = getattr(exc, "response", {})
        if response.get("ResponseMetadata", {}).get("HTTPStatusCode") in (404,):
            return False
        if response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def save(s3, index, data):
    from botocore.exceptions import ClientError
    try:
        s3.put_object(Bucket=core.BUCKET, Key=checkpoint(s3, index),
                      Body=json.dumps(data, sort_keys=True).encode("utf8"),
                      ContentType="application/json", IfNoneMatch="*",
                      CacheControl="private,no-store")
    except ClientError as exc:
        if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 412:
            raise


def families(index):
    provider, terms = WAVES[index]
    # All 44 baseline families plus 37 additional regional/instrument families,
    # alternating per wave to avoid repeating the same first-page queries.
    base = [(slug, slug.replace("-", " ")) for slug, *_ in core.FAMILIES]
    extra = [(slug.replace(" ", "-"), slug) for slug in EXTRA_FAMILIES]
    if index % 2:
        selected = extra + base
    else:
        selected = base + extra
    return provider, [(slug, (f"{label} {terms[0]}", f"{label} {terms[1]}"))
                      for slug, label in selected]


def collect_wave(s3, index, budget_requests=125, budget_seconds=1200,
                 max_new=250, per_family=10):
    provider, queries = families(index)
    stats = Counter()
    created = existing = 0
    start = time.monotonic()
    if provider == "openverse":
        client = ov.session()
    else:
        client = ia.make_session()
    try:
        for family, terms in queries:
            if (stats["requests"] >= budget_requests
                    or time.monotonic() - start >= budget_seconds
                    or created >= max_new):
                break
            found = {}
            for term in terms:
                if len(found) >= per_family or stats["requests"] >= budget_requests:
                    break
                if time.monotonic() - start >= budget_seconds:
                    break
                # Providers each have their own throttling and retry policy.
                # 429/503 repeated errors terminate the wave conservatively.
                try:
                    if provider == "openverse":
                        rows, _ = ov.query_api(client, term, 1, stats)
                    else:
                        rows = ia.search_items(client, term, stats, page=1)
                    stats["requests"] += 1
                except Exception as exc:
                    stats["api_errors"] += 1
                    stats["requests"] += 1
                    if stats["api_errors"] >= 5:
                        return {"provider": provider, "created": created,
                                "existing": existing, "api_errors": stats["api_errors"],
                                "requests": stats["requests"], "state": "API_BLOCKED"}
                    continue
                if provider == "openverse":
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        record, reason = ov.build_candidate(row, family, term)
                        if record:
                            found[record["candidate_id"]] = record
                        elif reason:
                            stats[reason] += 1
                        if len(found) >= per_family:
                            break
                else:
                    # IA's item search only returns item-level results; the
                    # existing adapter validates original-file metadata and
                    # explicit CC license claims before producing candidates.
                    # Do not bypass its rights/size/source filtering.
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        identifier = row.get("identifier")
                        if not ia.valid_identifier(identifier):
                            continue
                        try:
                            item = ia.fetch_json(client, f"{ia.ARCHIVE}/metadata/{identifier}")
                            stats["requests"] += 1
                        except Exception:
                            stats["api_errors"] += 1
                            if stats["api_errors"] >= 5:
                                break
                            continue
                        meta = item.get("metadata") or {}
                        claim = ia.license_claim(meta.get("licenseurl"))
                        if not claim:
                            stats["skip_rights"] += 1
                            continue
                        files = ia.parse_original_files(item, stats)
                        for fileinfo in files[:per_family]:
                            record = ia.build_candidate(identifier, fileinfo, meta,
                                                        family, term, claim,
                                                        meta.get("licenseurl"))
                            found[record["candidate_id"]] = record
                            if len(found) >= per_family:
                                break
                        if len(found) >= per_family or stats["requests"] >= budget_requests:
                            break
                if stats["api_errors"] >= 5:
                    break
            for record in found.values():
                try:
                    result, _ = core.persist(s3, record)
                    if result == "created":
                        created += 1
                    else:
                        existing += 1
                except Exception:
                    stats["write_errors"] += 1
                    break
                if created >= max_new:
                    break
            if stats["write_errors"] or stats["api_errors"] >= 5:
                break
    finally:
        client.close()
    state = ("R2_BLOCKED" if stats["write_errors"] else
             "API_BLOCKED" if stats["api_errors"] >= 5 else "COMPLETED")
    return {"provider": provider, "created": created, "existing": existing,
            "api_errors": stats["api_errors"], "write_errors": stats["write_errors"],
            "requests": stats["requests"], "state": state}


def run(args):
    s3 = core.s3_client()
    initial = candidate_keys(s3)
    report = {"schema": "ws2_music_5k_report_v1", "started_at": now(),
              "target": args.target, "baseline_objects": len(initial),
              "current_objects": len(initial), "batches": [],
              "media_downloaded": 0, "audio_uploaded": 0,
              "rights": "unverified_source_and_composition"}
    if len(initial) >= args.target:
        v = verify_full_index(s3, initial)
        report["verification"] = v
        report["state"] = "TARGET_REACHED" if v["valid"] >= args.target else "INVALID_INDEX"
        return report
    begin = time.monotonic()
    consecutive_empty = 0
    report["state"] = "WAVES_EXHAUSTED"
    for index in range(min(args.max_waves, len(WAVES))):
        if time.monotonic() - begin > args.total_seconds:
            report["state"] = "BUDGET_PAUSED"
            break
        if is_done(s3, index):
            report["batches"].append({"wave": index, "state": "CHECKPOINT_SKIPPED"})
            continue
        outcome = collect_wave(s3, index, args.requests_per_wave,
                               args.seconds_per_wave, args.new_per_wave)
        count = len(candidate_keys(s3))
        report["current_objects"] = count
        outcome["wave"] = index
        outcome["stored_candidate_objects"] = count
        report["batches"].append(outcome)
        core.emit("WS2_WAVE", outcome)
        # Only completed waves are checkpointed; partial/failed waves may
        # safely retry because writes use immutable create-only candidate IDs.
        if outcome["state"] == "COMPLETED":
            save(s3, index, outcome)
        else:
            report["state"] = outcome["state"]
            break
        if count >= args.target:
            v = verify_full_index(s3, candidate_keys(s3))
            report["verification"] = v
            report["state"] = "TARGET_REACHED" if v["valid"] >= args.target else "INVALID_INDEX"
            break
        consecutive_empty = consecutive_empty + 1 if outcome["created"] == 0 else 0
        if consecutive_empty >= 3:
            report["state"] = "THREE_EMPTY_WAVES"
            break
    report["missing"] = max(0, args.target - report["current_objects"])
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", type=int, default=5000)
    p.add_argument("--max-waves", type=int, default=4)
    p.add_argument("--requests-per-wave", type=int, default=125)
    p.add_argument("--seconds-per-wave", type=int, default=1200)
    p.add_argument("--total-seconds", type=int, default=4500)
    p.add_argument("--new-per-wave", type=int, default=250)
    p.add_argument("--output", default="audits/ws2-5k.json")
    args = p.parse_args()
    if not 1000 <= args.target <= 5000 or not 1 <= args.max_waves <= len(WAVES):
        p.error("unsafe target or wave count")
    if not 1 <= args.requests_per_wave <= 150 or not 1 <= args.new_per_wave <= 350:
        p.error("unsafe request or new-record budget")
    result = run(args)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    core.emit("WS2_FINAL", {"state": result["state"], "target": args.target,
                           "stored_candidate_objects": result["current_objects"],
                           "missing": result.get("missing", 0),
                           "created": sum(x.get("created", 0) for x in result["batches"]),
                           "existing": sum(x.get("existing", 0) for x in result["batches"]),
                           "api_errors": sum(x.get("api_errors", 0) for x in result["batches"]),
                           "media_downloaded": 0})
    if result["state"] in ("R2_BLOCKED", "API_BLOCKED", "INVALID_INDEX"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
