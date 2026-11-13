#!/usr/bin/env python3
"""Offline regression suite for IA source-record intake. Never calls real APIs/R2."""
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_archive_music_metadata as arch


def document():
    return {"identifier": "piano-cc0-example", "title": "Piano sample",
            "mediatype": "audio",
            "licenseurl": "https://creativecommons.org/publicdomain/zero/1.0/"}


def payload():
    return {"metadata": document(), "files": [
        {"name": "piano.wav", "source": "original", "size": "2000", "sha1": "a" * 40},
        {"name": "piano-vbr.mp3", "source": "derivative", "size": "900"},
        {"name": "cover.jpg", "source": "original", "size": "5000"},
    ]}


class ArchiveTests(unittest.TestCase):
    def test_license_allowlist_only(self):
        self.assertEqual(arch.license_claim(
            "https://creativecommons.org/publicdomain/zero/1.0/"), "CC0-1.0")
        self.assertEqual(arch.license_claim(
            "https://creativecommons.org/licenses/by/4.0/"), "CC-BY-4.0")
        self.assertEqual(arch.license_claim(
            "https://creativecommons.org/licenses/by/3.0/"), "CC-BY-3.0")
        for value in ("https://creativecommons.org/licenses/by-nc/4.0/",
                      "https://creativecommons.org/licenses/by-sa/4.0/",
                      "https://example.com/licenses/by/4.0/",
                      "http://creativecommons.org/publicdomain/zero/1.0/",
                      "", None):
            self.assertIsNone(arch.license_claim(value))

    def test_candidate_id_stable_independent_of_bytes(self):
        a = arch.stable_id("piano-test", "audio.wav")
        self.assertEqual(a, arch.stable_id("piano-test", "audio.wav"))
        self.assertNotEqual(a, arch.stable_id("piano-test", "another.wav"))
        self.assertNotEqual(a, arch.stable_id("other-item", "audio.wav"))

    def test_original_audio_only(self):
        stats = Counter()
        originals = arch.parse_original_files(payload(), stats)
        self.assertEqual(len(originals), 1)
        self.assertEqual(originals[0][0], "piano.wav")
        self.assertEqual(stats["skip_derivative"], 1)
        self.assertEqual(stats["skip_non_audio"], 1)

    def test_bad_files_rejected(self):
        stats = Counter()
        result = arch.parse_original_files({"files": [
            {"name": "../secret.mp3", "size": "1200"},
            {"name": "empty.wav", "size": "0"},
            {"name": "huge.flac", "size": str(arch.MAX_SOURCE_SIZE + 1)},
            {"name": "bad.mp3", "size": "garbage"},
        ]}, stats)
        self.assertEqual(result, [])
        self.assertEqual(stats["skip_bad_size"], 3)

    def test_candidate_is_unverified_metadata_not_asset(self):
        item = arch.build_candidate(
            "piano-test", ("tone.wav", ".wav", 2000, "b" * 40),
            document(), "grand-piano", "piano", "CC0-1.0",
            "https://creativecommons.org/publicdomain/zero/1.0/")
        self.assertEqual(item["provider"], "Internet Archive")
        self.assertEqual(item["status"], "candidate_only_not_downloaded")
        self.assertEqual(item["license_evidence_type"], "internet_archive_uploader_metadata_unverified")
        self.assertIsNone(item["asset_id"])
        self.assertIsNone(item["audio_storage_key"])
        self.assertIsNone(item["content_sha256"])
        self.assertIsNone(item["classification"]["tempo_bpm"])
        self.assertIsNone(item["classification"]["musical_key"])
        self.assertIsNone(item["classification"]["chords"])
        self.assertIsNone(item["technical"]["duration_seconds"])
        self.assertIsNone(item["source_license_verified_at"])

    def test_valid_result_discovered_metadata_only(self):
        session = Mock()
        args = SimpleNamespace(per_group=4, pages=1, max_item_details=3)
        with (
            patch.object(arch, "search_items", return_value=[document()]),
            patch.object(arch, "fetch_json", return_value=payload()),
        ):
            result = arch.discover_family(session, "grand-piano", ["piano"], args, Counter())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["file_name"], "piano.wav")
        self.assertEqual(result[0]["license"], "CC0-1.0")

    def test_missing_license_rejected_before_details(self):
        doc = document() | {"licenseurl": "https://creativecommons.org/licenses/by-nc/4.0/"}
        session = Mock()
        args = SimpleNamespace(per_group=4, pages=1, max_item_details=3)
        with (
            patch.object(arch, "search_items", return_value=[doc]),
            patch.object(arch, "fetch_json") as detail,
        ):
            result = arch.discover_family(session, "grand-piano", ["piano"], args, Counter())
        self.assertEqual(result, [])
        detail.assert_not_called()

    def test_license_disagreement_rejected(self):
        item = payload()
        item["metadata"] = document() | {"licenseurl": "https://creativecommons.org/licenses/by/4.0/"}
        with (
            patch.object(arch, "search_items", return_value=[document()]),
            patch.object(arch, "fetch_json", return_value=item),
        ):
            result = arch.discover_family(Mock(), "grand-piano", ["piano"],
                                         SimpleNamespace(per_group=4, pages=1, max_item_details=3),
                                         Counter())
        self.assertEqual(result, [])

    def test_no_network_in_readonly_mocked_scan_and_no_r2(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(persist=False, shard_index=0, shard_count=2,
                max_candidates=25, per_group=4, pages=1, max_item_details=2,
                output=str(Path(tmp)/"test.json"))
            with (patch.object(arch, "discover_family", return_value=[]),
                  patch.object(arch, "make_session") as session,
                  patch.object(arch.core, "s3_client") as client,
                  patch.object(arch.core, "emit")):
                output = arch.scan(args)
            client.assert_not_called()
            session.assert_called_once()
            self.assertGreater(output["family_count_scanned"], 0)
            self.assertTrue(Path(args.output).is_file())

    def test_source_record_storage_is_create_only(self):
        item = arch.build_candidate("test-id", ("a.wav", ".wav", 100, None),
                                    document(), "grand-piano", "piano", "CC0-1.0",
                                    "https://creativecommons.org/publicdomain/zero/1.0/")
        client = Mock()
        status, key = arch.core.persist(client, item)
        self.assertEqual(status, "created")
        self.assertEqual(client.put_object.call_args.kwargs["IfNoneMatch"], "*")
        self.assertTrue(key.startswith("internal/music-candidates/v1/"))
        self.assertEqual(json.loads(client.put_object.call_args.kwargs["Body"])["audio_storage_key"], None)

    def test_invalid_shard_rejected(self):
        args = SimpleNamespace(persist=False, shard_index=2, shard_count=2,
                               max_candidates=5, per_group=5, pages=1, max_item_details=2,
                               output="bad.json")
        with self.assertRaises(ValueError):
            arch.scan(args)


if __name__ == "__main__":
    unittest.main()
