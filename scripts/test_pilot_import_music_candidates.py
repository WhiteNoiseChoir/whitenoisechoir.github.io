#!/usr/bin/env python3
"""Offline safety and reporting tests for private candidate music audio pilot."""
import argparse
import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_import_music_candidates as pilot


def candidate():
    return {
        "schema": "music_source_candidate_v1",
        "candidate_id": "music-candidate-" + "a"*64,
        "provider": "Wikimedia Commons",
        "license": "CC0-1.0",
        "source_license_verified_at": "2026-11-13T06:00:00+00:00",
        "source_media_url": "https://upload.wikimedia.org/wikipedia/commons/a/a1/test.wav",
        "source_file_bytes": 12345,
        "source_page": "https://commons.wikimedia.org/wiki/File:Test.wav",
        "file_name": "test.wav",
    }


def approval():
    return {
        "schema": "music_audio_rights_approval_v1",
        "candidate_id": candidate()["candidate_id"],
        "source_media_url": candidate()["source_media_url"],
        "recording_rights_verified": True,
        "composition_rights_verified": True,
        "download_authorized": True,
        "commercial_derivative_reuse_allowed": True,
        "reviewed_by": "owner-authorized-reviewer",
        "reviewed_at": "2026-11-13",
        "evidence_urls": ["https://commons.wikimedia.org/wiki/File:Test.wav"],
    }


class PilotTests(TestCase):
    def test_no_auto_clearance_from_source_cc0(self):
        self.assertEqual(pilot.gate(candidate(), None), "NO_INDEPENDENT_RIGHTS_APPROVAL")

    def test_explicit_review_allows_fully_clear_cc0(self):
        self.assertEqual(pilot.gate(candidate(), approval()), "ELIGIBLE")

    def test_missing_composition_clearance_rejected(self):
        p = approval()
        p["composition_rights_verified"] = False
        self.assertEqual(pilot.gate(candidate(), p), "RIGHTS_NOT_CLEARED")

    def test_unverified_provider_and_license_rejected(self):
        c = candidate()
        c["provider"] = "Openverse"
        self.assertEqual(pilot.gate(c, approval()), "PROVIDER_NOT_APPROVED")
        c = candidate()
        c["license"] = "CC-BY-4.0"
        self.assertEqual(pilot.gate(c, approval()), "NO_VERIFIED_CC0")

    def test_url_allowlist_blocks_ssrf_and_redirect_hosts(self):
        self.assertTrue(pilot.safe_media_url(candidate()["source_media_url"]))
        for bad in [
            "http://upload.wikimedia.org/a.wav",
            "https://upload.wikimedia.org.evil.example/a.wav",
            "https://example.org/a.wav",
            "https://127.0.0.1/a.wav",
            "https://user@upload.wikimedia.org/a.wav",
            "https://upload.wikimedia.org:8443/a.wav",
            "https://upload.wikimedia.org/a.exe",
            "file:///tmp/a.wav",
            "https://upload.wikimedia.org/a.wav#attack",
        ]:
            self.assertFalse(pilot.safe_media_url(bad), bad)

    def test_no_status_advancement_when_no_approval(self):
        fake = Mock()
        good = "a"*64
        key = f"{pilot.CANDIDATES}aa/{good}.json"
        fake.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": key, "Size": 2700}]}
        ]
        with (
            patch.object(pilot, "load_json", side_effect=[candidate(), None]) as loaded,
            patch.object(pilot, "read_approval", return_value=None),
        ):
            rows, counts = pilot.available_candidates(fake, 100)
        self.assertEqual(len(rows), 0)
        self.assertEqual(counts["NO_INDEPENDENT_RIGHTS_APPROVAL"], 1)

    def test_no_download_on_empty_eligible_list(self):
        with (
            patch.object(pilot, "existing_digest_set") as known,
            patch.object(pilot, "stream_safe_media") as download,
        ):
            states, count = pilot.process(Mock(), [], 8, 250*1024**2, dry_run=False)
        self.assertEqual(count, 0)
        self.assertEqual(dict(states), {})
        known.assert_not_called()
        download.assert_not_called()

    def test_safe_dry_run_does_not_fetch_or_put_audio(self):
        with (
            patch.object(pilot, "existing_digest_set") as known,
            patch.object(pilot, "stream_safe_media") as download,
        ):
            states, byte_count = pilot.process(
                Mock(), [(candidate(), approval())], 8, 250*1024**2, dry_run=True)
        self.assertEqual(states["READY_FOR_APPROVED_IMPORT"], 1)
        self.assertEqual(byte_count, 12345)
        known.assert_not_called()
        download.assert_not_called()

    def test_scan_capped(self):
        fake = Mock()
        sha = "a"*64
        fake.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": f"{pilot.CANDIDATES}aa/{sha}.json", "Size": 99}]}
        ]
        with self.assertRaises(ValueError):
            pilot.candidate_keys(fake, max_records=0)

    def test_reporting_no_candidates_does_not_imply_import(self):
        with tempfile.TemporaryDirectory() as folder:
            args = argparse.Namespace(ingest=True, batch_size=8, max_records=100,
                                      byte_budget_mib=250,
                                      output=str(Path(folder) / "out.json"))
            with (patch.object(pilot.core, "s3_client", return_value=Mock()),
                  patch.object(pilot, "available_candidates",
                               return_value=([], {"NO_INDEPENDENT_RIGHTS_APPROVAL": 1344}))):
                result = pilot.run(args)
            self.assertEqual(result["audio_files_stored_r2"], 0)
            self.assertEqual(result["cataloged"], 0)
            self.assertEqual(result["studio_ready"], 0)
            self.assertEqual(result["rights_eligible"], 0)
            self.assertEqual(result["candidate_objects_scanned"], 1344)


if __name__ == "__main__":
    main()
