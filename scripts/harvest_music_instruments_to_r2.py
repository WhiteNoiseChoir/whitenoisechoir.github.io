#!/usr/bin/env python3
"""Independent musical-instrument intake from Wikimedia Commons.

Two modes:
  --discovery-only  read-only source/R2 discovery; NO downloads/writes
  --ingest          download verified CC0/CC-BY original audio into the
                    EXISTING content-addressed R2 asset library

This is a separate lane from nature intake. Instrument labels are SEARCH HINTS,
not verified source separation; tempo/key/chords must be measured later.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice
import os
import re

import harvest_commons_cc0_to_r2 as commons
from harvest_nature_diversity_to_r2 import (
    ROOT, Intake, category_pages, commons_media_downloader, emit, now, put_json,
)

# Categories include both real musical performances and individual sound samples.
# These are never assumed to be editable stems.
GROUPS = {
    "piano": (
        ("Sounds of pianos", "Audio files of piano music"),
        ("piano improvisation", "piano solo", "soft piano"),
    ),
    "acoustic-guitar": (
        ("Sounds of guitars", "Audio files of guitar music"),
        ("acoustic guitar", "fingerstyle guitar", "guitar chord"),
    ),
    "strings": (
        ("Audio files of harp music", "Audio files of cello music", "Sounds of violins"),
        ("harp plucked", "cello solo", "violin bowed"),
    ),
    "flute-and-winds": (
        ("Audio files of flute music", "Sounds of wind instruments"),
        ("flute solo", "wooden flute", "pan flute"),
    ),
    "percussion": (
        ("Sounds of percussion instruments", "Audio files of drum music"),
        ("handpan", "percussion sample", "shaker percussion"),
    ),
    "synth-and-keys": (
        ("Synthesizer sound", "Sounds of keyboard instruments"),
        ("synthesizer pad", "ambient synth", "electric piano"),
    ),
}
MAX_BYTES = 64 * 1024**2
PAGE_SIZE = 50
SEARCH_OFFSETS = (0, 50)
CATEGORY_CAP = 90
PER_GROUP_CAP = 12
MAX_BATCH = 40

# These are cheap first-pass flags, not a content rights audit.
UNSUITABLE = re.compile(
    r"\b(?:lingua libre|wiktionary|spoken word|pronunciation|karaoke|"
    r"bootleg|cover version|soundtrack rip|copyright infringement|"
    r"not licensed|all rights reserved)\b",
    re.I,
)
TOPIC = {
    "piano": re.compile(r"\b(?:piano|keyboard|rhodes|pianoforte)\b", re.I),
    "acoustic-guitar": re.compile(r"\b(?:guitar|fingerstyle|strumming|acoustic)\b", re.I),
    "strings": re.compile(r"\b(?:harp|cello|violin|strings?|fiddle)\b", re.I),
    "flute-and-winds": re.compile(r"\b(?:flute|woodwind|clarinet|panpipe)\b", re.I),
    "percussion": re.compile(r"\b(?:drum|percussion|handpan|shaker|rhythm)\b", re.I),
    "synth-and-keys": re.compile(r"\b(?:synth|keyboard|electronic|rhodes)\b", re.I),
}


def candidate_metadata(row):
    """Preserve provenance and mark unmeasured music features explicitly unknown."""
    return {
        "source_provider": "Wikimedia Commons",
        "source_page": row["source_url"],
        "license_evidence_url": row["rights_evidence_url"],
        "download_url": row["direct_file_url"],
        "license": row["source_license"],
        "license_url": row["license_url"],
        "creator": row["author"],
        "attribution": row["attribution"],
        "original_filename": row["file_name"],
        "title": row["title"],
        "description": row["description"],
        "source_tags": row["tags"],
        "group_hint": "music/" + row["group"],
        "discovery_hint": row["hint"],
        "music_instrument_hint": row["group"],
        "music_instrument_evidence": "source_category_or_search_query_unverified",
        "music_asset_kind_hint": row["music_kind_hint"],
        "music_classification_status": "pending_audio_analysis",
        "music_rights_review_status": "underlying_composition_not_independently_verified",
        "music_bpm": None,
        "music_key": None,
        "music_chords": None,
        "music_time_signature": None,
        "music_loopable": None,
    }


def discover_group(intake, group, spec, report):
    categories, queries = spec
    found = {}
    seen = set()
    stats = Counter()

    def consider(page, hint, from_category=False):
        stats["examined"] += 1
        try:
            row = commons.decide(page, group, MAX_BYTES, allow_cc_by=True)
            if row["state"] != "ELIGIBLE":
                stats[row["state"]] += 1
                return
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            description = commons.plain(commons.val(meta, "ImageDescription"))
            tags = commons.val(meta, "Categories").split("|")[:40]
            text = row["file_name"] + " " + description
            if UNSUITABLE.search(text):
                stats["SKIP_UNSUITABLE"] += 1
                return
            if not from_category and not TOPIC[group].search(text):
                stats["SKIP_TOPIC_MISMATCH"] += 1
                return
            url = row["direct_file_url"]
            if url in seen:
                stats["SKIP_DUPLICATE_URL"] += 1
                return
            seen.add(url)
            revision = info.get("sha1") or str(row["size"])
            identity = url + "\n" + revision
            if identity in report["cached_ids"] or intake.cached(identity):
                report["cached_ids"].add(identity)
                stats["SKIP_CACHED"] += 1
                return
            kind = ("instrument_demonstration" if hint.startswith("Sounds of ")
                    else "musical_performance" if hint.startswith("Audio files of ")
                    else "unclassified_music_audio")
            found[url] = {
                **row, "group": group, "identity": identity, "hint": hint,
                "description": description, "tags": tags, "music_kind_hint": kind,
            }
            stats["new_eligible"] += 1
        except Exception as exc:
            stats["candidate_errors"] += 1
            report["errors"].append({"group": group, "hint": hint, "error": str(exc)[:240]})

    for category in categories:
        if len(found) >= PER_GROUP_CAP:
            break
        stats["category_requests"] += 1
        try:
            for page, hint in islice(category_pages(category, 0), CATEGORY_CAP):
                consider(page, category, from_category=True)
                if len(found) >= PER_GROUP_CAP:
                    break
        except Exception as exc:
            stats["category_errors"] += 1
            report["errors"].append({"group": group, "category": category, "error": str(exc)[:240]})

    for query in queries:
        if len(found) >= PER_GROUP_CAP:
            break
        for offset in SEARCH_OFFSETS:
            if len(found) >= PER_GROUP_CAP:
                break
            stats["search_requests"] += 1
            try:
                pages = commons.candidates(query, offset, PAGE_SIZE)
            except Exception as exc:
                stats["search_errors"] += 1
                report["errors"].append({"group": group, "query": query,
                                         "offset": offset, "error": str(exc)[:240]})
                break
            for page in pages:
                consider(page, query)
                if len(found) >= PER_GROUP_CAP:
                    break
            if len(pages) < PAGE_SIZE:
                break

    rows = sorted(found.values(), key=lambda x: x["source_license"] != "CC0-1.0")
    report.setdefault("discovery_details", {})[group] = dict(stats)
    emit("MUSIC_DISCOVERY", {"group": group, "eligible": len(rows),
                             "diagnostics": dict(stats)})
    return deque(rows)


def store(intake, downloader, row):
    path, size, digest, duration, audio = downloader(row)
    try:
        output = intake.save(path, row["identity"], candidate_metadata(row), audio, duration, digest)
        return output | {"license": row["source_license"], "music_group": row["group"],
                         "sha256": digest, "duration_seconds": duration, "bytes_source": size}
    finally:
        path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--workers", type=int, default=2)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--discovery-only", action="store_true")
    mode.add_argument("--ingest", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.batch_size <= MAX_BATCH or not 1 <= args.workers <= 3:
        parser.error("batch size 1..40, workers 1..3")
    intake = Intake()
    report = {"started_at": now(), "source": "Wikimedia Commons music",
              "mode": "read_only" if args.discovery_only else "original_audio_to_R2",
              "assets": [], "errors": [], "cached_ids": set()}
    queues = [discover_group(intake, group, spec, report) for group, spec in GROUPS.items()]
    selected = {}
    while any(queues) and len(selected) < args.batch_size:
        for queue in queues:
            if queue and len(selected) < args.batch_size:
                row = queue.popleft()
                selected.setdefault(row["direct_file_url"], row)
    cached = len(report.pop("cached_ids"))
    if args.discovery_only:
        emit("MUSIC_DISCOVERY_ONLY", {"selected": len(selected), "cached": cached,
                                     "groups": report["discovery_details"],
                                     "errors": len(report["errors"]),
                                     "downloads": 0, "writes_to_R2": 0})
        return
    downloader = commons_media_downloader()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(store, intake, downloader, row): row for row in selected.values()}
        for future in as_completed(futures):
            try:
                result = future.result()
                report["assets"].append(result)
                emit("MUSIC_ASSET", result)
            except Exception as exc:
                report["errors"].append({"file": futures[future]["file_name"],
                                         "error": str(exc)[:240]})
    new = [row for row in report["assets"] if row["state"] == "new"]
    report.update(finished_at=now(), selected=len(selected), cached=cached,
                  counts=dict(Counter(row["state"] for row in report["assets"])),
                  music_groups=dict(Counter(row["music_group"] for row in new)),
                  bytes_added=sum(row["bytes"] for row in new))
    key = f"{ROOT}runs/music/{os.environ.get('GITHUB_RUN_ID', 'local')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}.json"
    put_json(intake.s3, key, report)
    emit("MUSIC_FINAL", {"selected": report["selected"], "cached": cached,
                         "counts": report["counts"], "groups": report["music_groups"],
                         "bytes_added": report["bytes_added"], "errors": len(report["errors"]),
                         "report_key": key})


if __name__ == "__main__":
    main()
