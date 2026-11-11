#!/usr/bin/env python3
"""Save WAV examples as published by the NOAA PMEL Acoustics Program."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

import requests

from harvest_commons_cc0_to_r2 import USER_AGENT
from harvest_nature_diversity_to_r2 import Intake, emit, file_digest, now, probe, put_json

PMEL = "https://www.pmel.noaa.gov/acoustics/"
POLICY = "https://www.omao.noaa.gov/image-licensing-usage-info"
WHALE_AUDIO = "whales/sounds/whalewav/"
WHALE_PAGES = "whales/sounds/"
CLIPS = [
    ("Northeast Pacific blue whale", WHALE_PAGES + "sounds_nepblue.html",
     WHALE_AUDIO + "nepblue24s10x.wav", "marine-mammals", 10),
    ("Western Pacific blue whale", WHALE_PAGES + "sounds_wpacblue.html",
     WHALE_AUDIO + "wblue26s10x.wav", "marine-mammals", 10),
    ("South Pacific blue whale", WHALE_PAGES + "sounds_spacblue.html",
     WHALE_AUDIO + "etpb3_10xc-BlueWhaleSouthPacific-10x.wav", "marine-mammals", 10),
    ("Atlantic blue whale", WHALE_PAGES + "sounds_atlblu.html",
     WHALE_AUDIO + "atlblue_512_64_0-50_10x.wav", "marine-mammals", 10),
    ("Atlantic fin whale", WHALE_PAGES + "sounds_atlfin.html",
     WHALE_AUDIO + "atlfin_128_64_0-50-FinWhaleAtlantic-10x.wav", "marine-mammals", 10),
    ("Alaska humpback whale", WHALE_PAGES + "sounds_akhump.html",
     WHALE_AUDIO + "akhumphi1x.wav", "marine-mammals", None),
    ("52 Hz whale-like call", WHALE_PAGES + "sounds_52blue.html",
     WHALE_AUDIO + "ak52_10x.wav", "marine-mammals", 10),
    ("Atlantic minke whale", WHALE_PAGES + "sounds_atlminke.html",
     WHALE_AUDIO + "atlmin_512_64_0-50_10x.wav", "marine-mammals", 10),
    ("Iceberg calving", "sounds_cryogenic.html", "sounds/A53JD33Calving_3x.wav", "underwater-ice", 3),
    ("Iceberg harmonic tremor", "sounds_cryogenic.html",
     "sounds/HarmonicTremor2006_215_09_20UsedOnBloopWebsite.wav", "underwater-ice", 3),
    ("Bloop icequake", "sounds_cryogenic.html", "sounds/bloop.wav", "underwater-ice", 16),
    ("Iceberg grounding", "sounds_cryogenic.html", "sounds/noise97139.wav", "underwater-ice", 16),
    ("Ocean earthquake", "sounds_seismic.html", "pioneer/sounds/pio_eq_244_1159.wav", "underwater-geology", 10),
    ("Ocean tremor", "sounds_seismic.html", "sounds/tremorx16.wav", "underwater-geology", 16),
    ("Ocean eruption", "sounds_seismic.html", "sounds/whistle16x.wav", "underwater-geology", 16),
]


def import_clip(intake, clip):
    title, page, source, group, speed = clip
    url = PMEL + source
    if intake.cached(url):
        return {"state": "cached", "bytes": 0, "group": group}
    with tempfile.TemporaryDirectory(prefix="wnc-noaa-") as folder:
        path = Path(folder) / "published.wav"
        with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=(15, 50)) as response, path.open("wb") as output:
            response.raise_for_status()
            if urlsplit(response.url).hostname not in {"www.pmel.noaa.gov", "pmel.noaa.gov"}:
                raise ValueError("Unexpected NOAA media host")
            size = 0
            for block in response.iter_content(256 * 1024):
                size += len(block)
                if size > 50 * 1024**2:
                    raise ValueError("Audio example exceeds 50 MiB")
                output.write(block)
        audio, duration = probe(path)
        return intake.save(path, url, {
            "source_provider": "NOAA PMEL Acoustics Program", "source_page": PMEL + page,
            "license_evidence_url": POLICY, "license": "Public Domain", "license_url": POLICY,
            "credit": "NOAA Pacific Marine Environmental Laboratory", "download_url": url,
            "title": title, "original_filename": source.rsplit("/", 1)[-1], "group_hint": group,
            "source_playback_speed_factor": speed,
            "source_version_note": (
                "NOAA publication speed differs between its index and detail page."
                if speed is None else f"Published WAV example, source signal sped up {speed}x."
            ),
        }, audio, duration, file_digest(path))


def main():
    intake = Intake()
    report = {"source": "NOAA PMEL", "started_at": now(), "assets": [], "errors": []}
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(import_clip, intake, clip): clip[0] for clip in CLIPS}
        for future in as_completed(jobs):
            try:
                report["assets"].append(future.result())
            except Exception as exc:
                report["errors"].append({"title": jobs[future], "error": str(exc)[:350]})
    report.update(
        finished_at=now(), counts=Counter(row["state"] for row in report["assets"]),
        groups=Counter(row["group"] for row in report["assets"] if row["state"] == "new"),
        bytes_added=sum(row["bytes"] for row in report["assets"]),
    )
    key = f"asset-library/sources/noaa-pmel/runs/{os.environ.get('GITHUB_RUN_ID', 'local')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}.json"
    put_json(intake.s3, key, report)
    emit("NOAA_FINAL", {k: report[k] for k in ("counts", "groups", "bytes_added", "errors")} | {"report_key": key})
    if not report["assets"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
