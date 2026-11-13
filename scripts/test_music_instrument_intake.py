#!/usr/bin/env python3
"""Offline tests: no network access, R2 writes, or audio download."""
import sys
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harvest_music_instruments_to_r2 as music
import harvest_commons_cc0_to_r2 as commons


def page(filename, n=1, description="Instrument recorded in studio"):
    return {
        "title": "File:" + filename,
        "imageinfo": [{
            "sha1": str(n),
            "extmetadata": {
                "ImageDescription": {"value": description},
                "Categories": {"value": "Audio files of piano music|Music"},
            },
        }],
    }


def decision(p, group, size, *, allow_cc_by=False):
    if p["title"].startswith("File:unlicensed"):
        return {"state": "SKIP_LICENSE_NOT_CC0"}
    assert allow_cc_by is True
    name = p["title"].removeprefix("File:")
    return {
        "state": "ELIGIBLE", "file_name": name, "title": p["title"],
        "direct_file_url": "https://upload.wikimedia.org/" + name,
        "size": 200000, "source_license": "CC0-1.0",
        "source_url": "https://commons.wikimedia.org/wiki/" + p["title"],
        "rights_evidence_url": "https://commons.wikimedia.org/wiki/" + p["title"],
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "author": "Author", "attribution": "Author", "category": group,
    }


class StubIntake:
    def __init__(self, cached_urls=()):
        self.cached_urls = set(cached_urls)

    def cached(self, identity):
        return identity.split("\n")[0] in self.cached_urls


class MusicDiscoveryTests(unittest.TestCase):
    def discover(self, spec=None, category_provider=None, search_provider=None, cached=()):
        spec = spec if spec is not None else (
            ("Audio files of piano music",), ("piano sample",), )
        report = {"errors": [], "cached_ids": set()}
        with (
            patch.object(music.commons, "decide", side_effect=decision),
            patch.object(music, "category_pages", side_effect=category_provider or (lambda *_: iter(()))),
            patch.object(music.commons, "candidates", side_effect=search_provider or (lambda *_: [])) as search,
            patch.object(music, "emit"),
        ):
            result = list(music.discover_group(StubIntake(cached), "piano", spec, report))
        return result, report, search

    def test_category_instrument_demonstration(self):
        def category_provider(name, depth):
            self.assertEqual(depth, 0)
            yield page("Grand piano single note.ogg"), "Sounds of pianos"
        rows, report, _ = self.discover(
            spec=(("Sounds of pianos",), ()), category_provider=category_provider)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["music_kind_hint"], "instrument_demonstration")
        self.assertEqual(rows[0]["group"], "piano")

    def test_pagination_beyond_cached_first_page(self):
        old = [page(f"Piano cached {i}.ogg", i) for i in range(50)]
        fresh = page("Piano soft recording.ogg", 51)
        def search(query, offset, limit):
            return old if offset == 0 else ([fresh] if offset == 50 else [])
        cached = ["https://upload.wikimedia.org/" + p["title"][5:] for p in old]
        rows, report, search_mock = self.discover(search_provider=search, cached=cached)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["file_name"], "Piano soft recording.ogg")
        self.assertEqual(report["discovery_details"]["piano"]["SKIP_CACHED"], 50)
        self.assertIn(50, [c.args[1] for c in search_mock.call_args_list])

    def test_license_rejection_stats(self):
        rows, report, _ = self.discover(search_provider=lambda *_: [page("unlicensed piano.ogg")])
        self.assertEqual(rows, [])
        self.assertEqual(report["discovery_details"]["piano"]["SKIP_LICENSE_NOT_CC0"], 1)

    def test_offtopic_search_rejected(self):
        rows, report, _ = self.discover(search_provider=lambda *_: [page("car engine.ogg")])
        self.assertEqual(rows, [])
        self.assertEqual(report["discovery_details"]["piano"]["SKIP_TOPIC_MISMATCH"], 1)

    def test_cover_unsafe_rejected(self):
        rows, report, _ = self.discover(search_provider=lambda *_: [page("Piano soundtrack rip.ogg")])
        self.assertEqual(rows, [])
        self.assertEqual(report["discovery_details"]["piano"]["SKIP_UNSUITABLE"], 1)

    def test_global_duplicate_url(self):
        item = page("Piano soft demo.ogg")
        rows, report, _ = self.discover(search_provider=lambda *_: [item, item])
        self.assertEqual(len(rows), 1)
        self.assertEqual(report["discovery_details"]["piano"]["SKIP_DUPLICATE_URL"], 1)

    def test_cc0_prioritized_over_cc_by(self):
        rows1 = [page("Piano CC-BY.ogg"), page("Piano CC0.ogg")]
        def license_order(page_, *args, **kwargs):
            x = decision(page_, *args, **kwargs)
            if "BY" in x["file_name"]:
                x["source_license"] = "CC-BY-4.0"
            return x
        with patch.object(music.commons, "decide", side_effect=license_order):
            with patch.object(music.commons, "candidates", return_value=rows1), patch.object(music, "category_pages", return_value=iter(())), patch.object(music, "emit"):
                report = {"errors": [], "cached_ids": set()}
                found = list(music.discover_group(StubIntake(), "piano", ((), ("piano",)), report))
        self.assertEqual(found[0]["source_license"], "CC0-1.0")
        self.assertEqual(found[1]["source_license"], "CC-BY-4.0")

    def test_music_metadata_keeps_unmeasured_values_null(self):
        candidate = decision(page("Soft Piano.ogg"), "piano", music.MAX_BYTES, allow_cc_by=True)
        candidate.update(group="piano", hint="Audio files of piano music", description="",
                         tags=[], music_kind_hint="musical_performance")
        meta = music.candidate_metadata(candidate)
        for k in ("music_bpm", "music_key", "music_chords",
                  "music_time_signature", "music_loopable"):
            self.assertIsNone(meta[k])
        self.assertEqual(meta["music_classification_status"], "pending_audio_analysis")
        self.assertNotIn("mix_ready", meta.values())

    def test_existing_commons_license_gate(self):
        item = page("Piano scale.ogg")
        info = item["imageinfo"][0]
        info.update(mime="audio/ogg", size=20000, url="https://upload.wikimedia.org/piano.ogg")
        info["extmetadata"].update(LicenseShortName={"value": "All rights reserved"},
                                   LicenseUrl={"value": ""})
        self.assertEqual(commons.decide(item, "piano", music.MAX_BYTES, allow_cc_by=True)["state"],
                         "SKIP_LICENSE_NOT_CC0")
        info["extmetadata"].update(LicenseShortName={"value": "CC0 1.0"},
                                   LicenseUrl={"value": "https://creativecommons.org/publicdomain/zero/1.0/"})
        self.assertEqual(commons.decide(item, "piano", music.MAX_BYTES, allow_cc_by=True)["state"],
                         "ELIGIBLE")

    def test_discovery_only_never_downloads_or_writes(self):
        def discovery(intake, group, spec, report):
            report.setdefault("discovery_details", {})[group] = {"new_eligible": 0}
            return deque()
        with (
            patch.object(music, "Intake", return_value=StubIntake()),
            patch.object(music, "discover_group", side_effect=discovery),
            patch.object(music, "commons_media_downloader") as downloader,
            patch.object(music, "put_json") as write,
            patch.object(music, "emit") as log,
            patch.object(sys, "argv", ["music", "--discovery-only"]),
        ):
            music.main()
        downloader.assert_not_called()
        write.assert_not_called()
        self.assertEqual(log.call_args.args[0], "MUSIC_DISCOVERY_ONLY")
        self.assertEqual(log.call_args.args[1]["writes_to_R2"], 0)

    def test_invalid_batch_and_workers_rejected(self):
        with (
            patch.object(music, "Intake") as intake,
            patch.object(sys, "argv", ["music", "--ingest", "--workers", "32"]),
        ):
            with self.assertRaises(SystemExit):
                music.main()
        intake.assert_not_called()


if __name__ == "__main__":
    unittest.main()
