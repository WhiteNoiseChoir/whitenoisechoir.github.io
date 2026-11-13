#!/usr/bin/env python3
"""Offline QA for metadata-only musical source index. No real network/R2 access."""
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_music_candidate_metadata as scan


def stub_rights(filename, name="piano", license="CC0-1.0"):
    return {
        "state": "ELIGIBLE",
        "title": "File:" + filename, "file_name": filename, "mime": "audio/ogg",
        "direct_file_url": "https://upload.wikimedia.org/" + filename,
        "source_url": "https://commons.wikimedia.org/wiki/File:" + filename,
        "rights_evidence_url": "https://commons.wikimedia.org/wiki/File:" + filename,
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "license_checked_at": "2026-11-13T00:00:00+00:00",
        "source_license": license, "size": 30000, "extension": ".ogg",
        "author": "Alice", "attribution": "Alice", "category": name,
    }


def stub_page(filename, n=1, description="Piano recorded in studio", tags="Musical instruments"):
    return {
        "title": "File:" + filename,
        "imageinfo": [
            {"sha1": ("a" * 39 + str(n)), "extmetadata": {
                "ImageDescription": {"value": description},
                "Categories": {"value": tags},
            }},
        ],
    }


class IndexTests(unittest.TestCase):
    def test_coverage_40_plus_distinct_families(self):
        self.assertGreaterEqual(scan.FAMILY_COUNT, 40)
        self.assertEqual(len({x[0] for x in scan.FAMILIES}), scan.FAMILY_COUNT)

    def test_same_source_revision_is_stable(self):
        a = scan.stable_candidate_id("https://commons.wikimedia.org/wiki/File:One.ogg", "aa")
        b = scan.stable_candidate_id("https://commons.wikimedia.org/wiki/File:One.ogg", "aa")
        c = scan.stable_candidate_id("https://commons.wikimedia.org/wiki/File:One.ogg", "bb")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 64)

    def test_candidate_record_not_mistaken_for_audio(self):
        row = stub_rights("piano.ogg")
        candidate = scan.source_record(row, "grand-piano", "a" * 40,
                                       "Sounds of pianos", "Piano sound", ["Piano"])
        self.assertEqual(candidate["schema"], "music_source_candidate_v1")
        self.assertEqual(candidate["status"], "candidate_only_not_downloaded")
        self.assertIsNone(candidate["asset_id"])
        self.assertIsNone(candidate["content_sha256"])
        self.assertIsNone(candidate["audio_storage_key"])
        self.assertIsNone(candidate["classification"]["tempo_bpm"])
        self.assertIsNone(candidate["classification"]["musical_key"])
        self.assertIsNone(candidate["classification"]["chords"])
        self.assertIsNone(candidate["technical"]["duration_seconds"])
        self.assertEqual(candidate["rights_review_status"], "composition_and_reuse_rights_pending")

    def test_category_discovery_keeps_license_gate(self):
        page = stub_page("Piano soft.ogg")
        def fake_decide(page_, family, *_args, **kwargs):
            self.assertTrue(kwargs["allow_cc_by"])
            return stub_rights(page_["title"][5:])
        def category(_category, _depth):
            yield page, "Sounds of pianos"
        args = SimpleNamespace(per_group=10, per_group_api_requests=5)
        stats = Counter()
        with (
            patch.object(scan.commons, "decide", side_effect=fake_decide),
            patch.object(scan, "category_pages", side_effect=category),
            patch.object(scan.commons, "candidates", return_value=[]),
            patch.object(scan, "emit"),
        ):
            result = scan.discover_family("grand-piano", ("Sounds of pianos",), (),
                                          r"\bpiano\b", stats, args)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["classification"]["instrument_hints"], ["grand-piano"])
        self.assertEqual(stats["eligible"], 1)

    def test_bad_license_is_filtered(self):
        def fake_decide(*args, **kwargs):
            return {"state": "SKIP_LICENSE_NOT_CC0"}
        args = SimpleNamespace(per_group=10, per_group_api_requests=5)
        stats = Counter()
        with (
            patch.object(scan.commons, "decide", side_effect=fake_decide),
            patch.object(scan, "category_pages", return_value=iter(())),
            patch.object(scan.commons, "candidates", return_value=[stub_page("Piano solo.ogg")]),
        ):
            result = scan.discover_family("grand-piano", (), ("piano solo",),
                                          r"\bpiano\b", stats, args)
        self.assertEqual(result, [])
        self.assertEqual(stats["SKIP_LICENSE_NOT_CC0"], 1)

    def test_reject_music_rip_keyword(self):
        def fake_decide(page_, *_args, **kwargs):
            return stub_rights(page_["title"][5:])
        args = SimpleNamespace(per_group=10, per_group_api_requests=5)
        stats = Counter()
        with (
            patch.object(scan.commons, "decide", side_effect=fake_decide),
            patch.object(scan, "category_pages", return_value=iter(())),
            patch.object(scan.commons, "candidates", return_value=[stub_page("piano soundtrack rip.ogg")]),
        ):
            result = scan.discover_family("grand-piano", (), ("piano solo",),
                                          r"\bpiano\b", stats, args)
        self.assertEqual(result, [])
        self.assertEqual(stats["skip_unsuitable"], 1)

    def test_reject_offtopic_search_match(self):
        def fake_decide(page_, *_args, **kwargs):
            return stub_rights(page_["title"][5:])
        args = SimpleNamespace(per_group=10, per_group_api_requests=5)
        stats = Counter()
        with (
            patch.object(scan.commons, "decide", side_effect=fake_decide),
            patch.object(scan, "category_pages", return_value=iter(())),
            patch.object(scan.commons, "candidates", return_value=[
                stub_page("Rainfall forest.ogg", description="Nature ambience")]),
        ):
            result = scan.discover_family("grand-piano", (), ("piano solo",),
                                          r"\bpiano\b", stats, args)
        self.assertEqual(result, [])
        self.assertEqual(stats["skip_topic_mismatch"], 1)

    def test_merge_two_instrument_hints(self):
        a = scan.source_record(stub_rights("piano.ogg"), "grand-piano", "a" * 40,
                               "Sounds of pianos", "", [])
        b = scan.source_record(stub_rights("piano.ogg"), "electric-piano", "a" * 40,
                               "Electric pianos", "", [])
        scan.merge_candidate(a, b)
        scan.merge_candidate(a, b)
        self.assertEqual(a["classification"]["instrument_hints"],
                         ["grand-piano", "electric-piano"])

    def test_r2_record_uses_if_none_match(self):
        client = Mock()
        item = scan.source_record(stub_rights("piano.ogg"), "grand-piano", "a" * 40,
                                  "Sounds of pianos", "", [])
        status, key = scan.persist(client, item)
        self.assertEqual(status, "created")
        self.assertTrue(key.startswith("internal/music-candidates/v1/"))
        self.assertEqual(client.put_object.call_args.kwargs["IfNoneMatch"], "*")
        saved = json.loads(client.put_object.call_args.kwargs["Body"].decode())
        self.assertEqual(saved["asset_id"], None)
        self.assertEqual(saved["candidate_id"], item["candidate_id"])

    def test_idempotent_existing_candidate(self):
        client = Mock()
        client.put_object.side_effect = ClientError(
            {"Error": {"Code": "PreconditionFailed"},
             "ResponseMetadata": {"HTTPStatusCode": 412}}, "PutObject")
        item = scan.source_record(stub_rights("piano.ogg"), "grand-piano", "a" * 40,
                                  "Sounds of pianos", "", [])
        status, key = scan.persist(client, item)
        self.assertEqual(status, "existing")

    def test_readonly_scan_does_not_create_r2_client(self):
        with tempfile.TemporaryDirectory() as temp:
            args = SimpleNamespace(persist=False, shard_index=0, shard_count=2,
                max_candidates=25, per_group=3, per_group_api_requests=2,
                output=str(Path(temp) / "test.json"))
            with (
                patch.object(scan, "discover_family", return_value=[]),
                patch.object(scan, "s3_client") as client,
                patch.object(scan, "emit"),
            ):
                report = scan.scan(args)
            self.assertGreater(report["families_scanned"], 0)
            self.assertEqual(report["found_unique_in_shard"], 0)
            self.assertEqual(report["storage"]["created"], 0)
            client.assert_not_called()
            self.assertTrue(Path(args.output).is_file())

    def test_shards_partition_all_families(self):
        sets = [{row[0] for row in scan.FAMILIES[shard::2]} for shard in (0, 1)]
        self.assertFalse(sets[0] & sets[1])
        self.assertEqual(len(sets[0] | sets[1]), scan.FAMILY_COUNT)

    def test_unsafe_shard_rejected(self):
        args = SimpleNamespace(persist=False, shard_index=2, shard_count=2,
            max_candidates=25, per_group=3, per_group_api_requests=2, output="unused.json")
        with self.assertRaises(ValueError):
            scan.scan(args)


if __name__ == "__main__":
    unittest.main()
