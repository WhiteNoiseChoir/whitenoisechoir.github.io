#!/usr/bin/env python3
"""Sample original CC0 wildlife sounds via the public iNaturalist API."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path, PurePosixPath
import tempfile
import time
from urllib.parse import unquote, urlsplit

import requests

import harvest_commons_cc0_to_r2 as commons
from harvest_nature_diversity_to_r2 import Intake, emit, file_digest, now, probe, put_json

API = "https://api.inaturalist.org/v1/observations"
HOSTS = {"static.inaturalist.org", "inaturalist-open-data.s3.amazonaws.com"}
MAX_BYTES = 160 * 1024**2
REGIONS = {
    "southeast-asia": (-12, 91, 29, 142),
    "east-asia": (18, 105, 57, 155),
    "south-asia": (5, 60, 37, 92),
    "oceania": (-56, 112, -10, 180),
    "africa": (-36, -19, 38, 53),
    "europe": (34, -26, 72, 43),
    "central-america-caribbean": (5, -119, 25, -58),
    "south-america": (-57, -82, 13, -33),
    "north-america": (25, -168, 83, -53),
}
TAXA = ("Aves", "Amphibia", "Insecta", "Mammalia", "Reptilia")
SPECIFIC_TAXA = ("Orthoptera", "Cicadidae", "Strigiformes", "Cuculidae", "Anura")
HEADERS = {"User-Agent": commons.USER_AGENT}


def parameters():
    for region, (south, west, north, east) in REGIONS.items():
        yield region, {"swlat": south, "swlng": west, "nelat": north, "nelng": east}
    for name in TAXA:
        yield name, {"iconic_taxa": name}
    for name in SPECIFIC_TAXA:
        yield name, {"taxon_name": name}


def api_results(session, query, endpoint=API):
    for attempt in range(4):
        with session.get(endpoint, params=query, timeout=(12, 50)) as response:
            if response.status_code not in (429, 500, 502, 503, 504):
                response.raise_for_status()
                return response.json()["results"]
            if attempt == 3:
                response.raise_for_status()
            retry_after = response.headers.get("Retry-After", "")
        time.sleep(max(2, int(retry_after)) if retry_after.isdigit() else 4 * 2**attempt)


def candidates(page, per_group, report):
    seen_sounds = set()
    species_counts = Counter()
    with requests.Session() as session:
        session.headers.update(HEADERS)
        for group, params in parameters():
            time.sleep(1.15)
            try:
                if "taxon_name" in params:
                    matches = api_results(session, {"q": group, "is_active": "true", "per_page": 12},
                                          endpoint="https://api.inaturalist.org/v1/taxa")
                    taxon = next((item for item in matches if item.get("name") == group), None)
                    if not taxon:
                        raise ValueError(f"iNaturalist did not resolve taxon {group}")
                    params = {"taxon_id": taxon["id"]}
                    time.sleep(1.15)
                rows = api_results(session, {
                    "sounds": "true", "sound_license": "cc0", "quality_grade": "research",
                    "order_by": "id", "order": "desc", "per_page": 100, "page": page, **params,
                })
            except (ValueError, KeyError, requests.RequestException) as exc:
                report["errors"].append({"group": group, "error": str(exc)[:350]})
                continue
            accepted = 0
            for row in rows:
                taxon = row.get("taxon") or {}
                name = taxon.get("name")
                species = taxon.get("min_species_taxon_id") or taxon.get("id")
                if not name or not species or species_counts[species] >= 4:
                    continue
                for sound in row.get("sounds") or []:
                    sound_id = sound.get("id")
                    url = sound.get("file_url") or ""
                    if (not sound_id or sound_id in seen_sounds or sound.get("hidden")
                            or sound.get("secret_token") or sound.get("license_code") != "cc0"):
                        continue
                    parts = urlsplit(url)
                    filename = PurePosixPath(unquote(parts.path)).name
                    if (parts.scheme != "https" or parts.hostname not in HOSTS
                            or not parts.path.startswith("/sounds/")
                            or PurePosixPath(filename).suffix.lower() not in commons.EXT):
                        continue
                    seen_sounds.add(sound_id)
                    species_counts[species] += 1
                    accepted += 1
                    yield url, {
                        "source_provider": "iNaturalist",
                        "source_page": f"https://www.inaturalist.org/observations/{row['id']}",
                        "license_evidence_url": f"https://www.inaturalist.org/sounds/{sound_id}",
                        "source_sound_id": sound_id, "source_observation_id": row["id"],
                        "original_filename": filename, "title": taxon.get("preferred_common_name") or name,
                        "scientific_name": name, "species_taxon_id": species,
                        "iconic_taxon": taxon.get("iconic_taxon_name"),
                        "source_quality_grade": row.get("quality_grade"),
                        "credit": sound.get("attribution"), "group_hint": group,
                        "recorded_date": row.get("observed_on"), "download_url": url,
                    }
                    break
                if accepted >= per_group:
                    break
            report["candidates"][group] = accepted
            emit("INAT_SELECTION", {"group": group, "selected": accepted})


def ingest(intake, url, meta):
    identity = f"inaturalist:{meta['source_sound_id']}:{url}"
    if intake.cached(identity):
        return {"state": "cached", "bytes": 0, "group": meta["group_hint"]}
    extension = PurePosixPath(meta["original_filename"]).suffix.lower()
    with tempfile.TemporaryDirectory(prefix="wnc-inaturalist-") as folder:
        path = Path(folder) / ("recording" + extension)
        with requests.get(url, headers=HEADERS, stream=True, timeout=(12, 90)) as response, path.open("wb") as output:
            response.raise_for_status()
            if urlsplit(response.url).hostname not in HOSTS:
                raise ValueError("Unexpected iNaturalist media host")
            size = 0
            for block in response.iter_content(512 * 1024):
                size += len(block)
                if size > MAX_BYTES:
                    raise ValueError("Recording exceeds 160 MiB")
                output.write(block)
        audio, duration = probe(path)
        result = intake.save(path, identity, meta, audio, duration, file_digest(path))
        return {**result, "species": meta["scientific_name"], "iconic_taxon": meta["iconic_taxon"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", type=int, default=1, choices=range(1, 101))
    parser.add_argument("--per-group", type=int, default=22, choices=range(1, 61))
    args = parser.parse_args()
    intake = Intake()
    report = {"source": "iNaturalist", "page": args.page, "started_at": now(), "candidates": {}, "errors": []}
    records = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        jobs = {pool.submit(ingest, intake, url, meta): meta for url, meta in candidates(args.page, args.per_group, report)}
        for future in as_completed(jobs):
            try:
                records.append(future.result())
            except Exception as exc:
                report["errors"].append({"sound_id": jobs[future]["source_sound_id"], "error": str(exc)[:350]})
    fresh = [row for row in records if row["state"] == "new"]
    report.update(
        finished_at=now(), assets=records, counts=Counter(row["state"] for row in records),
        groups=Counter(row["group"] for row in fresh), distinct_taxa=len({row["species"] for row in fresh}),
        bytes_added=sum(row["bytes"] for row in fresh),
    )
    key = "asset-library/sources/inaturalist/runs/" + os.environ.get("GITHUB_RUN_ID", "local") + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1") + f"-page-{args.page}.json"
    put_json(intake.s3, key, report)
    emit("INAT_FINAL", {name: report[name] for name in ("counts", "groups", "candidates", "distinct_taxa", "bytes_added")}
         | {"report_key": key, "errors": len(report["errors"]), "first_errors": report["errors"][:5]})
    if not records and report["errors"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
