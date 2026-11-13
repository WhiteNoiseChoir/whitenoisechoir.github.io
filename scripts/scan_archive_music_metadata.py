#!/usr/bin/env python3
"""Metadata-only Internet Archive music discovery (no audio downloads).

Independent, conservative second-provider adapter for WhiteNoiseChoir.
All candidate records represent unverified source metadata. An IA item's
license claim is evidence, NOT independent clearance of a composition.
Writes only private internal/music-candidates/ objects, create-only.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import time
from urllib.parse import quote, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import scan_music_candidate_metadata as core

ARCHIVE = "https://archive.org"
AUDIO_EXT = {".wav", ".flac", ".mp3", ".ogg", ".opus", ".m4a", ".aif", ".aiff"}
MAX_SOURCE_SIZE = 2 * 1024**3
LICENSE_URLS = {
    "https://creativecommons.org/publicdomain/zero/1.0": "CC0-1.0",
    "https://creativecommons.org/licenses/by/4.0": "CC-BY-4.0",
    "https://creativecommons.org/licenses/by/3.0": "CC-BY-3.0",
}
SKIP = re.compile(
    r"\b(?:bootleg|pirated|soundtrack rip|karaoke|video rip|"
    r"copyright infringement|spoken word|audiobook|remix of commercial)\b", re.I,
)


def now():
    return datetime.now(timezone.utc).isoformat()


def license_claim(raw):
    """Accept an explicit recognized Creative Commons URL; never infer rights."""
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    parsed = urlparse(raw)
    if parsed.scheme != "https" or parsed.hostname != "creativecommons.org":
        return None
    normalized = parsed.scheme + "://" + parsed.hostname + parsed.path.rstrip("/").lower()
    return LICENSE_URLS.get(normalized)


def stable_id(identifier, filename):
    """Source locator ID, not checksum of downloaded bytes."""
    canonical = "internet-archive\n" + identifier + "\n" + filename
    return "music-candidate-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def text_field(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " | ".join(x.strip() for x in value if isinstance(x, str) and x.strip())
    return ""


def valid_identifier(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{1,140}", value))


def parse_original_files(payload, stats):
    files = payload.get("files", [])
    if not isinstance(files, list):
        return []
    out = []
    for file in files:
        if not isinstance(file, dict):
            stats["skip_malformed_file"] += 1
            continue
        name = file.get("name", "")
        ext = Path(name).suffix.lower() if isinstance(name, str) else ""
        if (not name or name.startswith("/") or ".." in Path(name).parts
                or ext not in AUDIO_EXT):
            stats["skip_non_audio"] += 1
            continue
        if file.get("source", "original") != "original":
            stats["skip_derivative"] += 1
            continue
        try:
            size = int(file.get("size", 0))
        except (ValueError, TypeError):
            size = 0
        if not 0 < size <= MAX_SOURCE_SIZE:
            stats["skip_bad_size"] += 1
            continue
        out.append((name, ext, size, file.get("sha1")))
    return out


def build_candidate(identifier, fileinfo, metadata, group, query, rights, license_url):
    filename, ext, size, source_sha1 = fileinfo
    digest = stable_id(identifier, filename)
    source_url = f"{ARCHIVE}/details/{quote(identifier)}"
    file_url = f"{ARCHIVE}/download/{quote(identifier)}/{quote(filename, safe='/')}"
    title = text_field(metadata.get("title")) or identifier
    creator = text_field(metadata.get("creator"))
    description = text_field(metadata.get("description"))[:1800]
    source_sha1 = source_sha1 if isinstance(source_sha1, str) and re.fullmatch(r"[a-fA-F0-9]{40}", source_sha1) else None
    return {
        "schema": "music_source_candidate_v1",
        "candidate_id": digest, "status": "candidate_only_not_downloaded",
        "asset_id": None, "content_sha256": None, "audio_storage_key": None,
        "provider": "Internet Archive",
        "source_page": source_url, "source_revision_sha1": source_sha1,
        "source_revision_hint": source_sha1,
        "source_media_url": file_url, "title": title,
        "file_name": filename, "mime_type": mimetypes.guess_type(filename)[0],
        "source_file_bytes": size, "extension": ext,
        "source_description": description, "source_categories": [text_field(metadata.get("subject"))[:1000]],
        "creator": creator or None, "attribution": creator or None,
        "license": rights, "license_url": license_url,
        "license_evidence_url": source_url,
        "source_license_verified_at": None,
        "source_license_claim_observed_at": now(),
        "license_evidence_type": "internet_archive_uploader_metadata_unverified",
        "rights_review_status": "source_claim_and_composition_rights_pending",
        "classification": {
            "instrument_hints": [group], "hint_origin": [query],
            "instrument_verified_by_audio": False, "audio_kind": "unclassified",
            "tempo_bpm": None, "musical_key": None, "chords": None,
            "time_signature": None, "loopable": None,
            "mood": None, "musical_role": None, "energy": None,
        },
        "technical": {
            "duration_seconds": None, "codec": None, "sample_rate_hz": None,
            "channels": None, "integrated_lufs": None, "true_peak_dbtp": None,
        },
    }


def make_session():
    session = requests.Session()
    retry = Retry(total=3, connect=3, read=2, backoff_factor=1,
                  status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "WhiteNoiseChoir-MetadataResearch/1.0 (internal catalog; no file downloads)",
                            "Accept": "application/json"})
    return session


def fetch_json(session, url, params=None):
    # Bounded requests, with modest pacing across both shards.
    time.sleep(0.35)
    res = session.get(url, params=params, timeout=(10, 35))
    res.raise_for_status()
    return res.json()


def search_items(session, term, stats, page=1):
    # Archive Advanced Search uses Lucene-like queries; no raw user strings.
    cleaned = re.sub(r"[^A-Za-z0-9 -]", " ", term).strip()
    if not cleaned:
        return []
    expression = f'mediatype:audio AND (title:"{cleaned}" OR subject:"{cleaned}")'
    params = [("q", expression), ("output", "json"), ("rows", "35"),
              ("page", str(page))]
    for fld in ("identifier", "title", "creator", "licenseurl", "subject", "description", "mediatype"):
        params.append(("fl[]", fld))
    response = fetch_json(session, f"{ARCHIVE}/advancedsearch.php", params)
    stats["search_api_requests"] += 1
    return response.get("response", {}).get("docs", [])


def discover_family(session, group, queries, args, stats):
    found = {}
    seen_items = set()
    examined_items = 0
    for term in queries:
        if len(found) >= args.per_group:
            break
        for page in range(1, args.pages + 1):
            try:
                docs = search_items(session, term, stats, page=page)
            except Exception as exc:
                stats["search_errors"] += 1
                core.emit("ARCHIVE_METADATA_ERROR", {"family": group, "stage": "search",
                                                    "error": str(exc)[:160]})
                break
            if not isinstance(docs, list):
                stats["search_bad_response"] += 1
                break
            for doc in docs:
                stats["items_examined"] += 1
                identifier = doc.get("identifier") if isinstance(doc, dict) else None
                if not valid_identifier(identifier) or identifier in seen_items:
                    stats["skip_duplicate_or_invalid_identifier"] += 1
                    continue
                seen_items.add(identifier)
                if SKIP.search(text_field(doc.get("title"))):
                    stats["skip_unsuitable"] += 1
                    continue
                claim = text_field(doc.get("licenseurl"))
                if not license_claim(claim):
                    stats["skip_no_eligible_license_claim"] += 1
                    continue
                if examined_items >= args.max_item_details or len(found) >= args.per_group:
                    break
                examined_items += 1
                try:
                    item = fetch_json(session, f"{ARCHIVE}/metadata/{quote(identifier)}")
                    stats["item_detail_requests"] += 1
                except Exception as exc:
                    stats["detail_errors"] += 1
                    core.emit("ARCHIVE_METADATA_ERROR", {"family": group, "stage": "detail",
                                                        "error": str(exc)[:160]})
                    continue
                metadata = item.get("metadata", {})
                if not isinstance(metadata, dict) or text_field(metadata.get("mediatype")) != "audio":
                    stats["skip_not_audio_item"] += 1
                    continue
                actual_license = text_field(metadata.get("licenseurl"))
                rights = license_claim(actual_license)
                if not rights or rights != license_claim(claim):
                    stats["skip_license_claim_disagreement"] += 1
                    continue
                matches = parse_original_files(item, stats)
                if not matches:
                    stats["skip_no_original_audio"] += 1
                    continue
                for fileinfo in matches:
                    candidate = build_candidate(identifier, fileinfo, metadata, group, term,
                                                rights, actual_license)
                    cid = candidate["candidate_id"]
                    if cid not in found:
                        found[cid] = candidate
                        stats["eligible_metadata"] += 1
                    if len(found) >= args.per_group:
                        break
            if len(found) >= args.per_group or len(docs) < 35:
                break
    return list(found.values())


def scan(args):
    if not 1 <= args.shard_count <= 4 or not 0 <= args.shard_index < args.shard_count:
        raise ValueError("Invalid shard configuration")
    if not 1 <= args.max_candidates <= 2000 or not 1 <= args.per_group <= 100:
        raise ValueError("Invalid caps")
    if not 1 <= args.pages <= 4 or not 1 <= args.max_item_details <= 30:
        raise ValueError("Invalid search limits")
    session = make_session()
    rows = {}
    group_report = {}
    groups = core.FAMILIES[args.shard_index::args.shard_count]
    core.emit("ARCHIVE_METADATA_BEGIN", {"shard": args.shard_index,
              "groups": len(groups), "persist": args.persist, "provider": "Internet Archive"})
    for slug, categories, terms, regex in groups:
        stats = Counter()
        # One broad family search and one specific phrase from Commons taxonomy.
        queries = list(dict.fromkeys([slug.replace("-", " "), terms[0]]))
        results = discover_family(session, slug, queries, args, stats)
        group_report[slug] = dict(stats)
        for item in results:
            cid = item["candidate_id"]
            if cid in rows:
                core.merge_candidate(rows[cid], item)
            elif len(rows) < args.max_candidates:
                rows[cid] = item
        core.emit("ARCHIVE_METADATA_GROUP", {"family": slug, "candidates": len(results),
                  "total_unique": len(rows), "diagnostics": dict(stats)})
        if len(rows) >= args.max_candidates:
            break
    session.close()
    summary = {
        "schema": "archive_candidate_discovery_report_v1", "generated_at": now(),
        "shard": args.shard_index, "family_count_scanned": len(group_report),
        "source": "Internet Archive", "found_unique_in_shard": len(rows),
        "mode": "persist" if args.persist else "read_only",
        "group_diagnostics": group_report,
        "candidates": list(rows.values()),
    }
    counts = Counter()
    errors = []
    if args.persist:
        client = core.s3_client()
        for item in rows.values():
            try:
                result, _key = core.persist(client, item)
                counts[result] += 1
            except Exception as exc:
                counts["error"] += 1
                errors.append({"candidate_id": item["candidate_id"], "error": str(exc)[:160]})
        # Run reports are create-only and private; no write to audio objects.
        run_id = re.sub(r"[^0-9A-Za-z_-]", "", os.getenv("GITHUB_RUN_ID", "local"))
        report_key = f"{core.PRIVATE_ROOT}runs/archive-{run_id}-{args.shard_index}.json"
        report_data = {k: v for k, v in summary.items() if k != "candidates"}
        report_data["candidate_ids"] = list(rows)
        from botocore.exceptions import ClientError
        try:
            client.put_object(Bucket=core.BUCKET, Key=report_key, Body=json.dumps(report_data).encode(),
                              IfNoneMatch="*", ContentType="application/json", CacheControl="private,no-store")
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 412:
                raise
    summary["storage"] = {"created": counts["created"], "existing": counts["existing"],
                          "errors": counts["error"]}
    summary["write_errors"] = errors[:20]
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    core.emit("ARCHIVE_METADATA_FINAL", {
        "shard": args.shard_index, "candidate_unique": len(rows),
        "persisted_new": counts["created"], "persisted_existing": counts["existing"],
        "write_errors": counts["error"], "downloads": 0, "audio_uploaded": 0,
        "report_path": str(path),
    })
    if counts["error"]:
        raise RuntimeError(f"Failed writing {counts['error']} candidates")
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--persist", action="store_true")
    p.add_argument("--shard-index", type=int, default=0)
    p.add_argument("--shard-count", type=int, default=2)
    p.add_argument("--max-candidates", type=int, default=500)
    p.add_argument("--per-group", type=int, default=30)
    p.add_argument("--max-item-details", type=int, default=10)
    p.add_argument("--pages", type=int, default=2)
    p.add_argument("--output", default="audits/music-archive-candidates.json")
    scan(p.parse_args())


if __name__ == "__main__":
    main()
