#!/usr/bin/env python3
"""Breadth-first music metadata discovery and PRIVATE candidate-index persistence.

Every candidate is a SOURCE RECORD, not a downloaded audio file or a validated
musical stem. Underlying composition, BPM, key, chords, instruments, loopability
and commercial-export rights remain unverified until independent validation.
No interaction with the protected Studio catalog, mixer, or production source
assets. --persist writes only internal/music-candidates/v1 and runs/ prefixes.

Usage:
  python scripts/scan_music_candidate_metadata.py --shard-index 0 --shard-count 2
  python scripts/scan_music_candidate_metadata.py --persist --shard-index 0 --shard-count 2

The source is Wikimedia Commons audio metadata (licenses CC0 or CC-BY 3/4
verified by the existing commons.decide gate). No audio download is performed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

import harvest_commons_cc0_to_r2 as commons
from harvest_nature_diversity_to_r2 import category_pages, emit
from harvest_cc0_github_mirror_to_r2 import ACCOUNT_ID, BUCKET

PRIVATE_ROOT = "internal/music-candidates/"
VERSION = 1
MAX_AUDIO_BYTES = 100 * 1024**2
PER_GROUP = 38
QUERY_PAGE_SIZE = 50
OFFSETS = (0, 50, 100)
CATEGORY_MAX = 120
SKIP = re.compile(
    r"\b(?:lingua libre|wiktionary|pronunciation|spoken word|dictation|karaoke|"
    r"soundtrack rip|bootleg|pirated|copyright infringement|"
    r"video game rip|film score rip|music video|not licensed|all rights reserved)\b",
    re.I,
)

# These are classification HINTS, not claims about the actual sound.
# (slug, Commons categories, Commons audio searches, local topic terms)
FAMILIES = [
 ("grand-piano", ("Sounds of pianos", "Audio files of piano music"),
   ("grand piano solo", "soft piano recording"), r"\b(?:piano|pianoforte|pianist)\b"),
 ("electric-piano", ("Sounds of electric pianos",),
   ("electric piano sound", "rhodes piano"), r"\b(?:rhodes|electric piano|piano)\b"),
 ("organ", ("Sounds of organs", "Audio files of organ music"),
   ("organ instrument", "pipe organ audio"), r"\b(?:pipe organ|organ music|organ recital)\b"),
 ("harpsichord", ("Sounds of harpsichords",),
   ("harpsichord recording", "harpsichord solo"), r"\b(?:harpsichord|cembalo|clavichord)\b"),
 ("acoustic-guitar", ("Sounds of guitars", "Audio files of guitar music"),
   ("acoustic guitar fingerstyle", "classical guitar solo"), r"\b(?:guitar|fingerstyle|strumming)\b"),
 ("electric-guitar", ("Sounds of electric guitars",),
   ("electric guitar clean sound", "electric guitar sample"), r"\b(?:electric guitar|guitar)\b"),
 ("bass-guitar", ("Sounds of bass guitars",),
   ("bass guitar solo", "bass guitar string"), r"\b(?:bass guitar|electric bass)\b"),
 ("ukulele", ("Sounds of ukuleles",),
   ("ukulele strum", "ukulele instrument"), r"\b(?:ukulele|uke strumming)\b"),
 ("mandolin", ("Sounds of mandolins",),
   ("mandolin picking", "mandolin solo"), r"\b(?:mandolin)\b"),
 ("banjo", ("Sounds of banjos",),
   ("banjo picking", "banjo solo"), r"\b(?:banjo)\b"),
 ("harp", ("Sounds of harps", "Audio files of harp music"),
   ("harp arpeggio", "harp solo"), r"\b(?:harp|harps)\b"),
 ("violin", ("Sounds of violins", "Audio files of violin music"),
   ("violin solo", "fiddle sound"), r"\b(?:violin|fiddle)\b"),
 ("cello", ("Sounds of cellos", "Audio files of cello music"),
   ("cello solo", "violoncello sound"), r"\b(?:cello|violoncello)\b"),
 ("viola", ("Sounds of violas",),
   ("viola instrument recording", "viola solo"), r"\b(?:viola|violas)\b"),
 ("string-ensemble", ("Audio files of string quartets",),
   ("string quartet recording", "string ensemble"), r"\b(?:string quartet|string ensemble|strings)\b"),
 ("flute", ("Sounds of flutes", "Audio files of flute music"),
   ("flute solo", "flute instrument"), r"\b(?:flute|flautist|flauta)\b"),
 ("clarinet", ("Sounds of clarinets",),
   ("clarinet solo", "clarinet sound"), r"\b(?:clarinet)\b"),
 ("saxophone", ("Sounds of saxophones",),
   ("saxophone solo", "saxophone instrument"), r"\b(?:saxophone|sax)\b"),
 ("oboe", ("Sounds of oboes",),
   ("oboe solo", "oboe instrument"), r"\b(?:oboe)\b"),
 ("trumpet", ("Sounds of trumpets",),
   ("trumpet sound", "trumpet solo"), r"\b(?:trumpet)\b"),
 ("trombone", ("Sounds of trombones",),
   ("trombone solo", "trombone sound"), r"\b(?:trombone)\b"),
 ("french-horn", ("Sounds of French horns",),
   ("french horn solo", "french horn instrument"), r"\b(?:french horn|horn section)\b"),
 ("harmonica", ("Sounds of harmonicas",),
   ("harmonica solo", "mouth organ instrument"), r"\b(?:harmonica|mouth organ)\b"),
 ("accordion", ("Sounds of accordions",),
   ("accordion solo", "accordion instrument"), r"\b(?:accordion)\b"),
 ("drum-kit", ("Sounds of drums", "Audio files of drumming"),
   ("drum kit sample", "drum solo recording"), r"\b(?:drum kit|drums|drumming)\b"),
 ("percussion", ("Sounds of percussion instruments",),
   ("percussion sample", "percussion instrument"), r"\b(?:percussion|shaker|tambourine)\b"),
 ("handpan", ("Sounds of handpans",),
   ("handpan music", "hang drum sound"), r"\b(?:handpan|hang drum)\b"),
 ("kalimba", ("Sounds of thumb pianos",),
   ("kalimba sound", "kalimba solo"), r"\b(?:kalimba|thumb piano|mbira)\b"),
 ("marimba", ("Sounds of marimbas",),
   ("marimba sound", "marimba solo"), r"\b(?:marimba)\b"),
 ("xylophone", ("Sounds of xylophones",),
   ("xylophone sound", "xylophone solo"), r"\b(?:xylophone)\b"),
 ("bells-chimes", ("Sounds of bells", "Sounds of chimes"),
   ("wind chimes sound", "tubular bells recording"), r"\b(?:bells?|chimes?|carillon)\b"),
 ("steel-pan", ("Sounds of steelpans",),
   ("steelpan sound", "steel drum music"), r"\b(?:steelpan|steel drum)\b"),
 ("synthesizer", ("Sounds of synthesizers",),
   ("synthesizer sound", "analog synth sound"), r"\b(?:synthesizer|synth|electronic keyboard)\b"),
 ("ambient-pads", ("Electronic music audio files",),
   ("ambient synthesizer pad", "synth drone sound"), r"\b(?:ambient synth|synth pad|drone|electronic ambience)\b"),
 ("sitar", ("Sounds of sitars",),
   ("sitar instrument recording", "sitar solo"), r"\b(?:sitar)\b"),
 ("koto", ("Sounds of kotos",),
   ("koto instrument solo", "koto music"), r"\b(?:koto)\b"),
 ("guzheng", ("Sounds of guzhengs",),
   ("guzheng solo", "chinese zither recording"), r"\b(?:guzheng|chinese zither)\b"),
 ("erhu", ("Sounds of erhus",),
   ("erhu solo", "erhu music"), r"\b(?:erhu)\b"),
 ("shakuhachi", ("Sounds of shakuhachis",),
   ("shakuhachi solo", "shakuhachi flute"), r"\b(?:shakuhachi)\b"),
 ("pan-flute", ("Sounds of pan flutes",),
   ("pan flute instrument", "panpipes music"), r"\b(?:pan ?flute|panpipes)\b"),
 ("didgeridoo", ("Sounds of didgeridoos",),
   ("didgeridoo sound", "didgeridoo instrument"), r"\b(?:didgeridoo)\b"),
 ("gamelan", ("Sounds of gamelan instruments",),
   ("gamelan music recording", "gamelan instrument"), r"\b(?:gamelan)\b"),
 ("bagpipes", ("Sounds of bagpipes",),
   ("bagpipes solo", "bagpipe instrument"), r"\b(?:bagpipes?)\b"),
 ("taiko", ("Sounds of taiko drums",),
   ("taiko drums sound", "japanese taiko"), r"\b(?:taiko|wadaiko)\b"),
]
FAMILY_COUNT = len(FAMILIES)


def now():
    return datetime.now(timezone.utc).isoformat()


def stable_candidate_id(source_page, revision):
    """A source-reference digest; never call this an audio content SHA256."""
    payload = "wikimedia-commons\n" + source_page.strip() + "\n" + str(revision)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_record(row, group, revision, hint, description, categories):
    digest = stable_candidate_id(row["source_url"], revision)
    return {
        "schema": "music_source_candidate_v1",
        "candidate_id": "music-candidate-" + digest,
        "status": "candidate_only_not_downloaded",
        "asset_id": None,
        "content_sha256": None,
        "audio_storage_key": None,
        "provider": "Wikimedia Commons",
        "source_page": row["source_url"],
        "source_revision_sha1": revision if re.fullmatch(r"[0-9a-f]{40}", str(revision), re.I) else None,
        "source_revision_hint": str(revision),
        "source_media_url": row["direct_file_url"],
        "title": row["title"],
        "file_name": row["file_name"],
        "mime_type": row["mime"],
        "source_file_bytes": row["size"],
        "extension": row["extension"],
        "source_description": description,
        "source_categories": categories,
        "creator": row["author"],
        "attribution": row["attribution"],
        "license": row["source_license"],
        "license_url": row["license_url"],
        "license_evidence_url": row["rights_evidence_url"],
        "source_license_verified_at": row["license_checked_at"],
        "rights_review_status": "composition_and_reuse_rights_pending",
        "classification": {
            "instrument_hints": [group],
            "hint_origin": [hint],
            "instrument_verified_by_audio": False,
            "audio_kind": "unclassified",
            "tempo_bpm": None, "musical_key": None, "chords": None,
            "time_signature": None, "loopable": None,
            "mood": None, "musical_role": None, "energy": None,
        },
        "technical": {
            "duration_seconds": None, "codec": None, "sample_rate_hz": None,
            "channels": None, "integrated_lufs": None, "true_peak_dbtp": None,
        },
    }


def discover_family(slug, categories, queries, pattern, stats, args):
    topic = re.compile(pattern, re.I)
    found = {}
    seen_urls = set()

    def consider(page, hint, known_category=False):
        stats["examined"] += 1
        result = commons.decide(page, slug, MAX_AUDIO_BYTES, allow_cc_by=True)
        if result["state"] != "ELIGIBLE":
            stats[result["state"]] += 1
            return
        meta = (page.get("imageinfo") or [{}])[0]
        fields = meta.get("extmetadata") or {}
        description = commons.plain(commons.val(fields, "ImageDescription"))
        categories_found = commons.val(fields, "Categories").split("|")[:40]
        title_and_desc = result["file_name"] + " " + description
        if SKIP.search(title_and_desc):
            stats["skip_unsuitable"] += 1
            return
        if not known_category and not topic.search(title_and_desc):
            stats["skip_topic_mismatch"] += 1
            return
        media = result["direct_file_url"]
        if media in seen_urls:
            stats["skip_duplicate_url"] += 1
            return
        seen_urls.add(media)
        revision = meta.get("sha1") or str(result["size"])
        candidate = source_record(result, slug, revision, hint, description, categories_found)
        if candidate["candidate_id"] not in found:
            found[candidate["candidate_id"]] = candidate
            stats["eligible"] += 1

    for cat in categories:
        if len(found) >= args.per_group or stats["api_requests"] >= args.per_group_api_requests:
            break
        try:
            stats["api_requests"] += 1
            for page, _hint in category_pages(cat, 0):
                consider(page, cat, known_category=True)
                if len(found) >= args.per_group or stats["examined"] >= CATEGORY_MAX * 3:
                    break
        except Exception as exc:
            stats["category_errors"] += 1
            emit("MUSIC_METADATA_ERROR", {"group": slug, "stage": "category", "error": str(exc)[:160]})

    for query in queries:
        if len(found) >= args.per_group or stats["api_requests"] >= args.per_group_api_requests:
            break
        for offset in OFFSETS:
            if len(found) >= args.per_group or stats["api_requests"] >= args.per_group_api_requests:
                break
            try:
                stats["api_requests"] += 1
                pages = commons.candidates(query, offset, QUERY_PAGE_SIZE)
                for page in pages:
                    consider(page, query)
                    if len(found) >= args.per_group:
                        break
                if len(pages) < QUERY_PAGE_SIZE:
                    break
            except Exception as exc:
                stats["search_errors"] += 1
                emit("MUSIC_METADATA_ERROR", {"group": slug, "stage": "search",
                                              "query": query, "error": str(exc)[:160]})
                break
    return list(found.values())


def merge_candidate(master, candidate):
    """Preserve all relevant groups/hints when the same file appears in multiple categories."""
    if master["candidate_id"] != candidate["candidate_id"]:
        raise ValueError("Cannot merge different sources")
    cls = master["classification"]
    for group in candidate["classification"]["instrument_hints"]:
        if group not in cls["instrument_hints"]:
            cls["instrument_hints"].append(group)
    for hint in candidate["classification"]["hint_origin"]:
        if hint not in cls["hint_origin"]:
            cls["hint_origin"].append(hint)


def s3_client():
    if not os.getenv("R2_ACCESS_KEY_ID") or not os.getenv("R2_SECRET_ACCESS_KEY"):
        raise ValueError("Missing approved R2 credentials")
    return boto3.client(
        "s3", region_name="auto",
        endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",
                      max_pool_connections=8,
                      retries={"max_attempts": 5, "mode": "standard"}),
    )


def persist(s3, candidate):
    digest = candidate["candidate_id"].removeprefix("music-candidate-")
    key = f"{PRIVATE_ROOT}v1/{digest[:2]}/{digest}.json"
    payload = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    try:
        s3.put_object(Bucket=BUCKET, Key=key, Body=payload, IfNoneMatch="*",
                      ContentType="application/json", CacheControl="private,no-store")
        return "created", key
    except ClientError as exc:
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        code = exc.response.get("Error", {}).get("Code")
        if status == 412 or code in {"PreconditionFailed", "ConditionalRequestConflict"}:
            return "existing", key
        raise


def scan(args):
    if not 1 <= args.shard_count <= 4 or not 0 <= args.shard_index < args.shard_count:
        raise ValueError("Invalid shard configuration")
    if not 1 <= args.per_group <= 80 or not 1 <= args.max_candidates <= 2000:
        raise ValueError("Invalid candidate limits")
    if not 1 <= args.per_group_api_requests <= 15:
        raise ValueError("Invalid request limit")
    records = {}
    family_stats = {}
    family_list = FAMILIES[args.shard_index::args.shard_count]
    emit("MUSIC_METADATA_BEGIN", {"shard": args.shard_index, "shards": args.shard_count,
                                  "families_in_shard": len(family_list),
                                  "max_candidates": args.max_candidates,
                                  "mode": "persist" if args.persist else "read_only"})
    for slug, categories, queries, regex in family_list:
        stats = Counter()
        candidates = discover_family(slug, categories, queries, regex, stats, args)
        family_stats[slug] = dict(stats)
        for candidate in candidates:
            candidate_id = candidate["candidate_id"]
            if candidate_id not in records and len(records) >= args.max_candidates:
                continue
            if candidate_id in records:
                merge_candidate(records[candidate_id], candidate)
            else:
                records[candidate_id] = candidate
        emit("MUSIC_METADATA_GROUP", {"group": slug, "found": len(candidates),
                                      "total_candidates": len(records), "diagnostics": dict(stats)})
        if len(records) >= args.max_candidates:
            break
    output = {
        "schema": "music_candidate_discovery_report_v1",
        "generated_at": now(), "shard_index": args.shard_index,
        "shard_count": args.shard_count, "families_scanned": len(family_stats),
        "families_total": FAMILY_COUNT, "found_unique_in_shard": len(records),
        "mode": "persist" if args.persist else "read_only",
        "family_diagnostics": family_stats,
        "candidates": list(records.values()),
    }
    if args.persist:
        s3 = s3_client()
        counts = Counter()
        errors = []
        # Metadata-only writes; no MP3, conversion or Studio publishing.
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = {pool.submit(persist, s3, candidate): candidate["candidate_id"]
                    for candidate in records.values()}
            for future in as_completed(jobs):
                try:
                    outcome, key = future.result()
                    counts[outcome] += 1
                except Exception as exc:
                    counts["error"] += 1
                    errors.append({"id": jobs[future], "error": str(exc)[:160]})
        output["storage"] = {"created": counts["created"], "existing": counts["existing"],
                             "errors": counts["error"], "private_prefix": PRIVATE_ROOT + "v1/"}
        output["write_errors"] = errors[:20]
        run_id = re.sub(r"[^A-Za-z0-9_-]", "", os.getenv("GITHUB_RUN_ID", "local"))
        report_key = f"{PRIVATE_ROOT}runs/{run_id}-{args.shard_index}.json"
        report_for_r2 = {k: v for k, v in output.items() if k != "candidates"}
        report_for_r2["candidate_ids"] = list(records)
        report_bytes = json.dumps(report_for_r2, ensure_ascii=False).encode()
        try:
            s3.put_object(Bucket=BUCKET, Key=report_key, Body=report_bytes,
                          ContentType="application/json", IfNoneMatch="*",
                          CacheControl="private,no-store")
            output["storage"]["report_key"] = report_key
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 412:
                raise
            output["storage"]["report_key"] = report_key
        if counts["error"]:
            raise RuntimeError(f"Failed to store {counts['error']} candidate records")
    else:
        output["storage"] = {"created": 0, "existing": 0, "errors": 0}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    emit("MUSIC_METADATA_FINAL", {
        "shard": args.shard_index, "families_scanned": output["families_scanned"],
        "candidate_unique": output["found_unique_in_shard"],
        "persisted_new": output["storage"]["created"],
        "persisted_existing": output["storage"]["existing"],
        "write_errors": output["storage"]["errors"],
        "downloads": 0, "audio_uploaded": 0,
        "report_path": str(path),
    })
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--max-candidates", type=int, default=500)
    parser.add_argument("--per-group", type=int, default=38)
    parser.add_argument("--per-group-api-requests", type=int, default=9)
    parser.add_argument("--output", default="audits/music-candidates.json")
    args = parser.parse_args()
    scan(args)


if __name__ == "__main__":
    main()
