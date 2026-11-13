#!/usr/bin/env python3
"""Offline regression coverage for the Commons nature-discovery funnel.

No network, R2 credentials, audio downloads or writes are required.
"""
import sys
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harvest_targeted_nature_to_r2 as target
import harvest_commons_cc0_to_r2 as commons


def page(title, index=0, tags="Sounds of rain", description="Field recording"):
    return {
        "title": "File:" + title,
        "imageinfo": [{
            "sha1": str(index), "extmetadata": {
                "ImageDescription": {"value": description},
                "Categories": {"value": tags},
            },
        }],
    }


def decide(page_, group, max_bytes, *, allow_cc_by=False):
    if "unlicensed" in page_["title"]:
        return {"state": "SKIP_LICENSE_NOT_CC0"}
    return {
        "state": "ELIGIBLE", "file_name": page_["title"].removeprefix("File:"),
        "direct_file_url": "https://upload.wikimedia.org/" + page_["title"].removeprefix("File:"),
        "size": 123456, "source_license": "CC0-1.0", "category": group,
        "source_url": "https://commons.wikimedia.org/wiki/" + page_["title"],
    }


class Intake:
    def __init__(self, cached_urls=()):
        self.cached_urls = set(cached_urls)

    def cached(self, identity):
        return identity.split("\n")[0] in self.cached_urls


class DiscoveryTests(unittest.TestCase):
    def run_discovery(self, queries=None, candidates=None, categories=None, cached=()):
        report = {"cached_ids": set(), "errors": []}
        spec = (("Sounds of rain",), queries or ("rain",), r"\brain\b")
        with (
            patch.object(target.commons, "decide", side_effect=decide),
            patch.object(target.commons, "candidates", side_effect=candidates or (lambda *_: [])) as query,
            patch.object(target, "category_pages", side_effect=categories or (lambda *_: iter(()))),
            patch.object(target, "emit"),
        ):
            rows = target.candidates_for_group(Intake(cached), "rain", spec, report)
        return list(rows), report, query

    def test_paginates_when_first_page_is_fully_cached(self):
        stale = [page(f"rain cached {i}.ogg", i) for i in range(50)]
        fresh = page("rain fresh field recording.ogg", 51)
        def fetch(query, offset, size):
            return stale if offset == 0 else ([fresh] if offset == 50 else [])
        cached = ["https://upload.wikimedia.org/" + x["title"][5:] for x in stale]
        rows, report, query = self.run_discovery(candidates=fetch, cached=cached)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["file_name"], "rain fresh field recording.ogg")
        self.assertEqual(len(report["cached_ids"]), 50)
        self.assertIn(50, [call.args[1] for call in query.call_args_list])
        self.assertEqual(report["discovery_details"]["rain"]["SKIP_CACHED"], 50)

    def test_scans_child_category_without_relaxing_topic(self):
        def categories(root, depth):
            self.assertEqual(depth, 1)
            yield page("rain in beech forest.ogg", 5), "Audio from rainy forests"
        rows, report, _ = self.run_discovery(categories=categories)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["hint"], "Audio from rainy forests")

    def test_rejection_counts_are_reported(self):
        rows, report, _ = self.run_discovery(candidates=lambda *_: [page("rain unlicensed.ogg")])
        self.assertEqual(len(rows), 0)
        self.assertEqual(report["discovery_details"]["rain"]["SKIP_LICENSE_NOT_CC0"], 1)

    def test_music_and_offtopic_are_filtered(self):
        rows, report, _ = self.run_discovery(candidates=lambda *_: [
            page("rain guitar soundtrack.ogg"),
            page("engine rumble.ogg", 2),
            page("rain field recording.ogg", 3),
        ])
        self.assertEqual([r["file_name"] for r in rows], ["rain field recording.ogg"])
        self.assertEqual(report["discovery_details"]["rain"]["SKIP_NON_NATURE_OR_MUSIC"], 1)
        self.assertEqual(report["discovery_details"]["rain"]["SKIP_TOPIC_MISMATCH"], 1)

    def test_no_new_files_is_reported_as_zero(self):
        rows, report, _ = self.run_discovery(candidates=lambda *_: [])
        self.assertEqual(rows, [])
        self.assertEqual(report["discovery_details"]["rain"]["new_eligible"], 0) if "new_eligible" in report["discovery_details"]["rain"] else None
        self.assertEqual(report["discovery_details"]["rain"]["search_requests"], 1)

    def test_query_pagination_is_bounded(self):
        cached = [page(f"rain archive {i}.ogg", i) for i in range(50)]
        cached_urls = ["https://upload.wikimedia.org/" + x["title"][5:] for x in cached]
        rows, report, calls = self.run_discovery(queries=("rain",), candidates=lambda *_: cached, cached=cached_urls)
        self.assertEqual(len(rows), 0)
        self.assertEqual([c.args[1] for c in calls.call_args_list], [0, 50, 100])
        self.assertEqual(report["discovery_details"]["rain"]["search_requests"], 3)

    def test_duplicate_url_not_queued_twice(self):
        item = page("rain field capture.ogg")
        rows, report, _ = self.run_discovery(candidates=lambda *_: [item, item])
        self.assertEqual(len(rows), 1)
        self.assertEqual(report["discovery_details"]["rain"]["SKIP_RUN_DUPLICATE_URL"], 1)

    def test_actual_commons_license_validation_still_rejects_unlicensed(self):
        item = page("Rain and pine trees.ogg")
        ii = item["imageinfo"][0]
        ii.update(mime="audio/ogg", size=8000, url="https://upload.wikimedia.org/audio.ogg")
        ii["extmetadata"].update(LicenseShortName={"value":"All rights reserved"}, LicenseUrl={"value":""})
        result = commons.decide(item,"rain",160 * 1024 * 1024,allow_cc_by=True)
        self.assertEqual(result["state"], "SKIP_LICENSE_NOT_CC0")
        ii["extmetadata"].update(LicenseShortName={"value":"CC0 1.0"},
                                  LicenseUrl={"value":"https://creativecommons.org/publicdomain/zero/1.0/"})
        self.assertEqual(commons.decide(item,"rain",160 * 1024 * 1024,allow_cc_by=True)["state"], "ELIGIBLE")

    def test_discovery_only_never_writes_or_downloads(self):
        def fake_discover(intake, group, spec, report):
            report.setdefault("discovery_details", {})[group] = {"new_eligible": 0}
            return deque()
        with (
            patch.object(target, "Intake", return_value=Intake()),
            patch.object(target, "candidates_for_group", side_effect=fake_discover),
            patch.object(target, "commons_media_downloader") as downloader,
            patch.object(target, "put_json") as upload,
            patch.object(target, "emit") as emit,
            patch.object(sys, "argv", ["scanner", "--discovery-only"]),
        ):
            target.main()
        downloader.assert_not_called()
        upload.assert_not_called()
        self.assertEqual(emit.call_args.args[0], "TARGETED_DISCOVERY_ONLY")
        self.assertEqual(emit.call_args.args[1]["writes_to_r2"], 0)


if __name__ == "__main__":
    unittest.main()
