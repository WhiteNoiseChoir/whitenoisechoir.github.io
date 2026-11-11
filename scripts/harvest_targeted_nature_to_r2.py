#!/usr/bin/env python3
"""Collect nature recordings by related metadata queries and Commons categories."""
import argparse
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re

import harvest_commons_cc0_to_r2 as commons
from harvest_nature_diversity_to_r2 import (
    ROOT, Intake, category_pages, commons_media_downloader, emit, now, put_json,
)

MAX_BYTES = 160 * 1024**2
GROUPS = {
    "rain": (
        ("Sounds of rain",),
        ("rain drizzle", "rain heavy", "rain on roof", "rain on window", "rain on leaves",
         "rain tent", "rain car", "rain puddles", "rain umbrella"),
        r"\b(rain|raining|rainfall|drizzle|regen|lluvia|pluie|raindrops?)\b",
    ),
    "thunder-and-weather": (
        ("Sounds of thunder",),
        ("thunderstorm", "distant thunder", "rolling thunder", "thunder and rain", "hail storm"),
        r"\b(thunder|thunderstorms?|thunderclap|lightning|hail|donner|tonnerre|tormenta)\b",
    ),
    "streams-and-lakes": (
        ("Sounds of rivers and streams",),
        ("mountain stream", "brook babbling", "river rapids", "creek water", "lake shore waves",
         "pond ambience", "river flowing", "water trickling rocks"),
        r"\b(streams?|rivers?|brooks?|creeks?|rapids|lakes?|ponds?|rivulet|bach|riviere|rivière)\b",
    ),
    "waterfalls": (
        ("Audio files of waterfalls",),
        ("waterfall field recording", "waterfall sound", "cascade water", "wasserfall"),
        r"\b(waterfalls?|cataract|cascade|wasserfall|cascada)\b",
    ),
    "wind": (
        (),
        ("wind in trees", "wind gust", "wind rustling leaves", "wind in grass", "wind on mountain",
         "wind in reeds", "wind on beach", "forest wind ambience"),
        r"\b(wind|winds|windy|gusts?|breeze|windgeräusch|vent|viento)\b",
    ),
    "coast": (
        ("Sounds of sea waves",),
        ("ocean surf", "waves rocky shore", "pebble beach waves", "waves washing shore",
         "sea waves wind", "waves sandy beach", "coastal ambience"),
        r"\b(ocean|sea waves|surf|shore|shoreline|beach|coast|seaside|mare|meer)\b",
    ),
    "forest": (
        ("Rainforest sounds",),
        ("forest ambience", "forest dawn chorus", "night forest soundscape", "rainforest sounds",
         "woodland soundscape", "jungle ambience", "forest morning sounds", "meadow soundscape"),
        r"\b(forest|rainforest|woodland|woods|jungle|meadow|dawn chorus)\b",
    ),
}
EXCLUDED = re.compile(
    r"^(?:[a-z]{2,3}-(?:us|uk|gb|au)-|nl-|de-|fr-|es-|ru-)"
    r"|\b(?:pronunciation|phonetic|lingua libre|wiktionary|dictionary|consonant|"
    r"piano|guitar|musical instrument|song by|track from|video game|wind instrument)\b",
    re.I,
)


def candidates_for_group(intake, group, spec, report):
    categories, queries, topic = spec
    found = {}
    seen_urls = set()
    lookups = [(name, category_pages(name, 0)) for name in categories]
    for query in queries:
        try:
            rows = commons.candidates(query, 0, 28)
            lookups.append((query, [(page, query) for page in rows]))
        except Exception as exc:
            report["errors"].append({"group": group, "query": query, "error": str(exc)[:350]})
    for name, pages in lookups:
        try:
            for page, hint in pages:
                row = commons.decide(page, group, MAX_BYTES, allow_cc_by=True)
                if row["state"] != "ELIGIBLE" or row["direct_file_url"] in seen_urls:
                    continue
                info = page["imageinfo"][0]
                fields = info.get("extmetadata", {})
                description = commons.plain(commons.val(fields, "ImageDescription"))
                tags = commons.val(fields, "Categories").split("|")[:40]
                name_and_description = row["file_name"] + " " + description
                if EXCLUDED.search(name_and_description):
                    continue
                if hint not in categories and not re.search(topic, name_and_description, re.I):
                    continue
                seen_urls.add(row["direct_file_url"])
                revision = info.get("sha1") or str(row["size"])
                identity = row["direct_file_url"] + "\n" + revision
                if identity in report["cached_ids"] or intake.cached(identity):
                    report["cached_ids"].add(identity)
                    continue
                found[row["direct_file_url"]] = {
                    **row, "identity": identity, "description": description, "tags": tags, "hint": hint,
                    "copyright_notice": commons.plain(commons.val(fields, "Copyright")),
                }
        except Exception as exc:
            report["errors"].append({"group": group, "query": name, "error": str(exc)[:350]})
    rows = sorted(found.values(), key=lambda row: row["source_license"] != "CC0-1.0")
    emit("TARGETED_DISCOVERY", {"group": group, "eligible": len(rows)})
    return deque(rows)


def collect(intake, download, row):
    path, _, digest, duration, audio = download(row)
    try:
        meta = {
            "source_provider": "Wikimedia Commons", "source_page": row["source_url"],
            "license_evidence_url": row["rights_evidence_url"], "download_url": row["direct_file_url"],
            "license": row["source_license"], "license_url": row["license_url"],
            "creator": row["author"], "attribution": row["attribution"],
            "copyright_notice": row["copyright_notice"],
            "original_filename": row["file_name"], "title": row["title"],
            "description": row["description"], "source_tags": row["tags"],
            "group_hint": row["category"], "discovery_hint": row["hint"],
        }
        result = intake.save(path, row["identity"], meta, audio, duration, digest)
        if result["state"] == "new":
            emit("TARGETED_ASSET", {
                **result, **meta, "sha256": digest, "duration_seconds": duration,
                "codec": audio.get("codec_name"), "sample_rate_hz": audio.get("sample_rate"),
                "channels": audio.get("channels"), "description": meta["description"][:1000],
            })
        return result | {"license": row["source_license"]}
    finally:
        path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=180)
    args = parser.parse_args()
    intake = Intake()
    report = {"started_at": now(), "assets": [], "errors": [], "cached_ids": set()}
    queues = [candidates_for_group(intake, group, spec, report) for group, spec in GROUPS.items()]
    picked = {}
    while any(queues) and len(picked) < args.batch_size:
        for queue in queues:
            if queue and len(picked) < args.batch_size:
                row = queue.popleft()
                picked.setdefault(row["direct_file_url"], row)
    download = commons_media_downloader()
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {pool.submit(collect, intake, download, row): row for row in picked.values()}
        for future in as_completed(jobs):
            try:
                report["assets"].append(future.result())
            except Exception as exc:
                report["errors"].append({"file": jobs[future]["file_name"], "error": str(exc)[:350]})
    fresh = [row for row in report["assets"] if row["state"] == "new"]
    report.update(
        finished_at=now(), selected=len(picked), cached=len(report.pop("cached_ids")),
        counts=Counter(row["state"] for row in report["assets"]),
        groups=Counter(row["group"] for row in fresh),
        licenses=Counter(row["license"] for row in fresh),
        bytes_added=sum(row["bytes"] for row in fresh),
    )
    key = f"{ROOT}runs/targeted/{os.environ['GITHUB_RUN_ID']}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}.json"
    put_json(intake.s3, key, report)
    emit("TARGETED_FINAL", {k: report[k] for k in ("selected", "counts", "groups", "licenses", "cached", "bytes_added")}
         | {"report_key": key, "errors": len(report["errors"]), "first_errors": report["errors"][:6]})


if __name__ == "__main__":
    main()
