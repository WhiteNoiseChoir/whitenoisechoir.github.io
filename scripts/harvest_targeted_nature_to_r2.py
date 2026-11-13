#!/usr/bin/env python3
"""Collect nature recordings by related metadata queries and Commons categories."""
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

MAX_BYTES = 160 * 1024**2
GROUPS = {
    "rain": (
        ("Sounds of rain",),
        ("rain drizzle", "rain heavy", "rain on roof", "rain on window", "rain on leaves",
         "rain tent", "rain car", "rain puddles", "rain umbrella", "intitle:rain", "intitle:pluie", "intitle:regen"),
        r"\b(rain|raining|rainfall|drizzle|regen|lluvia|pluie|raindrops?)\b",
    ),
    "thunder-and-weather": (
        ("Sounds of thunder",),
        ("thunderstorm", "distant thunder", "rolling thunder", "thunder and rain", "hail storm", "intitle:thunder", "intitle:gewitter"),
        r"\b(thunder|thunderstorms?|thunderclap|lightning|hail|donner|tonnerre|tormenta)\b",
    ),
    "streams-and-lakes": (
        ("Sounds of rivers and streams",),
        ("mountain stream", "brook babbling", "river rapids", "creek water", "lake shore waves",
         "pond ambience", "river flowing", "water trickling rocks", "intitle:brook", "intitle:creek", "intitle:rapids"),
        r"\b(streams?|rivers?|brooks?|creeks?|rapids|lakes?|ponds?|rivulet|bach|riviere|rivière)\b",
    ),
    "waterfalls": (
        ("Audio files of waterfalls",),
        ("waterfall field recording", "waterfall sound", "cascade water", "wasserfall", "intitle:waterfall", "intitle:cascade"),
        r"\b(waterfalls?|cataract|cascade|wasserfall|cascada)\b",
    ),
    "wind": (
        (),
        ("wind in trees", "wind gust", "wind rustling leaves", "wind in grass", "wind on mountain",
         "wind in reeds", "wind on beach", "forest wind ambience", "intitle:wind ambience", "intitle:windgeräusch"),
        r"\b(wind|winds|windy|gusts?|breeze|windgeräusch|vent|viento)\b",
    ),
    "coast": (
        ("Sounds of sea waves",),
        ("ocean surf", "waves rocky shore", "pebble beach waves", "waves washing shore",
         "sea waves wind", "waves sandy beach", "coastal ambience", "intitle:waves", "intitle:shoreline"),
        r"\b(ocean|sea waves|surf|shore|shoreline|beach|coast|seaside|mare|meer)\b",
    ),
    "forest": (
        ("Rainforest sounds",),
        ("forest ambience", "forest dawn chorus", "night forest soundscape", "rainforest sounds",
         "woodland soundscape", "jungle ambience", "forest morning sounds", "meadow soundscape", "intitle:soundscape forest"),
        r"\b(forest|rainforest|woodland|woods|jungle|meadow|dawn chorus)\b",
    ),
}
EXCLUDED = re.compile(
    r"^(?:[a-z]{2,3}-(?:us|uk|gb|au)-|nl-|de-|fr-|es-|ru-)"
    r"|^.+ - \d{1,2} - "
    r"|\b(?:pronunciation|phonetic|lingua libre|wiktionary|dictionary|consonant|"
    r"piano|guitar|musical instrument|song by|track from|video game|wind instrument|"
    r"isrc|future bass|surf rock|soundtrack|royalty.free music|background music|"
    r"alma mater|talk nation radio|radio broadcast|news report|thunderstorm watch|weather alert|"
    r"folk song|vocal performance)\b",
    re.I,
)


# Expand beyond first-page results without overwhelming Commons.  This is a
# discovery bound, NOT a relaxation of rights, content, or audio-format checks.
QUERY_PAGE_SIZE = 50
QUERY_OFFSETS = (0, 50, 100)
MAX_CATEGORY_ROWS = 200
MAX_ELIGIBLE_PER_GROUP = 45


def candidates_for_group(intake, group, spec, report):
    categories, queries, topic = spec
    found = {}
    seen_urls = set()
    stats = Counter()

    def consider(page, hint):
        stats["examined"] += 1
        try:
            row = commons.decide(page, group, MAX_BYTES, allow_cc_by=True)
            if row["state"] != "ELIGIBLE":
                stats[row["state"]] += 1
                return
            info = (page.get("imageinfo") or [{}])[0]
            fields = info.get("extmetadata") or {}
            description = commons.plain(commons.val(fields, "ImageDescription"))
            tags = commons.val(fields, "Categories").split("|")[:40]
            name_and_description = row["file_name"] + " " + description
            category_is_music = any(
                re.search(r"^(?:music$|audio files of .*music\b|.* \(song\)$)", tag, re.I)
                for tag in tags
            )
            artist_pack_without_context = "Audio files by Antti Luode" in tags and not re.search(
                r"\b(?:field recording|recorded at|recorded in)\b", description, re.I,
            )
            if EXCLUDED.search(name_and_description) or category_is_music or artist_pack_without_context:
                stats["SKIP_NON_NATURE_OR_MUSIC"] += 1
                return
            if hint not in categories and not re.search(topic, name_and_description, re.I):
                stats["SKIP_TOPIC_MISMATCH"] += 1
                return
            url = row["direct_file_url"]
            if url in seen_urls:
                stats["SKIP_RUN_DUPLICATE_URL"] += 1
                return
            seen_urls.add(url)
            revision = info.get("sha1") or str(row["size"])
            identity = url + "\n" + revision
            if identity in report["cached_ids"] or intake.cached(identity):
                report["cached_ids"].add(identity)
                stats["SKIP_CACHED"] += 1
                return
            found[url] = {
                **row, "identity": identity, "description": description, "tags": tags, "hint": hint,
                "copyright_notice": commons.plain(commons.val(fields, "Copyright")),
            }
            stats["new_eligible"] += 1
        except Exception as exc:
            stats["candidate_errors"] += 1
            report["errors"].append({"group": group, "query": hint, "error": str(exc)[:350]})

    # Include direct child categories: relevant recordings may sit entirely in
    # subcategories, not in the parent category's first 100 file entries.
    for category in categories:
        try:
            for page, hint in islice(category_pages(category, 1), MAX_CATEGORY_ROWS):
                consider(page, hint)
                if len(found) >= MAX_ELIGIBLE_PER_GROUP:
                    break
            stats["categories_visited"] += 1
        except Exception as exc:
            stats["category_errors"] += 1
            report["errors"].append({"group": group, "query": category, "error": str(exc)[:350]})
        if len(found) >= MAX_ELIGIBLE_PER_GROUP:
            break

    # Paginate per search query.  The old crawler only read offset 0, so one
    # saturated first page could make all seven categories appear exhausted.
    for query in queries:
        if len(found) >= MAX_ELIGIBLE_PER_GROUP:
            break
        for offset in QUERY_OFFSETS:
            if len(found) >= MAX_ELIGIBLE_PER_GROUP:
                break
            stats["search_requests"] += 1
            try:
                pages = commons.candidates(query, offset, QUERY_PAGE_SIZE)
            except Exception as exc:
                stats["search_errors"] += 1
                report["errors"].append({"group": group, "query": query, "offset": offset,
                                         "error": str(exc)[:350]})
                break
            for page in pages:
                consider(page, query)
                if len(found) >= MAX_ELIGIBLE_PER_GROUP:
                    break
            if len(pages) < QUERY_PAGE_SIZE:
                break

    rows = sorted(found.values(), key=lambda row: row["source_license"] != "CC0-1.0")
    report.setdefault("discovery_details", {})[group] = dict(stats)
    emit("TARGETED_DISCOVERY", {"group": group, "eligible": len(rows),
                              "diagnostics": dict(stats)})
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
    parser.add_argument("--discovery-only", action="store_true", help="Read-only discovery; do not download or write R2")
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
    if args.discovery_only:
        emit("TARGETED_DISCOVERY_ONLY", {
            "selected": len(picked), "cached": len(report["cached_ids"]),
            "groups": {name: details for name, details in report["discovery_details"].items()},
            "errors": len(report["errors"]), "writes_to_r2": 0, "downloads": 0,
        })
        return
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
