#!/usr/bin/env python3
"""Offline Openverse API source-candidate regression tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_openverse_music_metadata as ov


def sample(**kwargs):
    row = {
        "id": "8624ba61-57f1-4f98-8a85-ece206c319cf",
        "title": "Piano soft note",
        "source": "freesound",
        "foreign_landing_url": "https://freesound.org/s/12345/",
        "url": "https://freesound.org/data/previews/12345.ogg",
        "creator": "Test artist",
        "attribution": "Test artist",
        "license": "cc0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "mature": False,
        "tags": [{"name": "piano"}, {"name": "single note"}],
        "duration": 6.5,
        "bit_rate": 160000,
        "sample_rate": 44100,
        "filesize": 250000,
        "filetype": "ogg",
    }
    row.update(kwargs)
    return row


class OpenverseTests(unittest.TestCase):
    def test_valid_cc0(self):
        candidate, error = ov.build_candidate(sample(), "grand-piano", "piano")
        self.assertIsNone(error)
        self.assertEqual(candidate["license"], "CC0-1.0")
        self.assertEqual(candidate["status"], "candidate_only_not_downloaded")
        self.assertEqual(candidate["rights_review_status"], "source_claim_and_composition_rights_pending")
        self.assertIsNone(candidate["source_license_verified_at"])
        self.assertIsNone(candidate["asset_id"])
        self.assertIsNone(candidate["audio_storage_key"])
        self.assertIsNone(candidate["content_sha256"])
        self.assertIsNone(candidate["technical"]["duration_seconds"])
        self.assertEqual(candidate["source_reported_audio_metadata"]["duration_seconds"], 6.5)
        self.assertIsNone(candidate["classification"]["tempo_bpm"])
        self.assertIsNone(candidate["classification"]["musical_key"])

    def test_cc_by_version(self):
        r = sample(license="by", license_url="https://creativecommons.org/licenses/by/4.0/")
        item, error = ov.build_candidate(r, "flute", "flute")
        self.assertIsNone(error)
        self.assertEqual(item["license"], "CC-BY-4.0")

    def test_reject_nc_and_sa_even_if_claim_by(self):
        for suffix in ("by-nc/4.0/", "by-sa/4.0/", "by-nd/4.0/"):
            _, err = ov.build_candidate(
                sample(license="by", license_url="https://creativecommons.org/licenses/" + suffix),
                "flute", "flute")
            self.assertEqual(err, "skip_license_not_cc0_or_by")

    def test_no_inferred_cc0_from_invalid_url(self):
        _, err = ov.build_candidate(sample(license="cc0",
                        license_url="https://example.com/publicdomain/zero/1.0/"),
                        "grand-piano", "piano")
        self.assertEqual(err, "skip_license_not_cc0_or_by")

    def test_skip_prior_commons_archive(self):
        for src in ("wikimedia_commons", "internet_archive"):
            _, err = ov.build_candidate(sample(source=src), "grand-piano", "piano")
            self.assertEqual(err, "skip_existing_provider")

    def test_skip_unsafe_and_missing_sources(self):
        _, err = ov.build_candidate(sample(foreign_landing_url="http://example.com/x"),
                                    "grand-piano", "piano")
        self.assertEqual(err, "skip_no_https_source_page")
        _, err = ov.build_candidate(sample(mature=True), "grand-piano", "piano")
        self.assertEqual(err, "skip_mature")
        _, err = ov.build_candidate(sample(title="Piano bootleg audio"), "grand-piano", "piano")
        self.assertEqual(err, "skip_unsuitable")

    def test_ids_stable_across_tracking_fragment(self):
        self.assertEqual(ov.stable_id("https://freesound.org/s/12345/#info"),
                         ov.stable_id("https://freesound.org/s/12345/"))
        self.assertNotEqual(ov.stable_id("https://freesound.org/s/12345/"),
                            ov.stable_id("https://freesound.org/s/99999/"))

    def test_untrusted_numeric_metadata_not_certified(self):
        row = sample(duration="nan", sample_rate=-100, filesize="garbage")
        item, error = ov.build_candidate(row, "flute", "flute")
        self.assertIsNone(error)
        self.assertIsNone(item["source_reported_audio_metadata"]["duration_seconds"])
        self.assertIsNone(item["source_reported_audio_metadata"]["sample_rate_hz"])
        self.assertIsNone(item["source_file_bytes"])

    def test_readonly_shard_never_writes(self):
        with tempfile.TemporaryDirectory() as t:
            args = SimpleNamespace(persist=False, shard_index=0, shard_count=2,
                max_candidates=40, per_group=5, pages=1,
                output=str(Path(t) / "report.json"))
            fake_client = Mock()
            with (
                patch.object(ov, "session", return_value=fake_client),
                patch.object(ov, "query_api", return_value=([sample()], 1)),
                patch.object(ov.core, "s3_client") as r2,
                patch.object(ov.core, "emit"),
            ):
                output = ov.scan(args)
            self.assertTrue(Path(args.output).is_file())
            self.assertGreater(output["found_unique_in_shard"], 0)
            r2.assert_not_called()

    def test_api_uses_only_official_endpoint_and_license_filter(self):
        client = Mock()
        result = Mock()
        result.json.return_value = {"results": [sample()], "page_count": 1}
        client.get.return_value = result
        with patch.object(ov.time, "sleep"):
            out, pages = ov.query_api(client, "piano", 1, Counter())
        self.assertEqual(len(out), 1)
        self.assertEqual(pages, 1)
        self.assertEqual(client.get.call_args.args[0], ov.API)
        self.assertEqual(client.get.call_args.kwargs["params"]["license"], "cc0,by")

    def test_bad_shard_rejected(self):
        with self.assertRaises(ValueError):
            ov.scan(SimpleNamespace(persist=False, shard_count=2, shard_index=3,
                    max_candidates=20, per_group=5, pages=1, output="unused"))


if __name__ == "__main__":
    unittest.main()
