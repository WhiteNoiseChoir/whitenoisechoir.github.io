#!/usr/bin/env python3
"""Offline regression tests: Commons current source checks NEVER grant music rights."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_music_rights_review as review


def candidate(license="CC-BY-4.0"):
    return {
        "schema": "music_source_candidate_v1",
        "candidate_id": "music-candidate-" + "a"*64,
        "provider": "Wikimedia Commons",
        "license": license,
        "source_license_verified_at": "2026-11-13T01:00:00+00:00",
        "source_media_url": "https://upload.wikimedia.org/wikipedia/commons/a/a1/test.wav",
        "source_file_bytes": 12345,
        "source_page": "https://commons.wikimedia.org/wiki/File:Test.wav",
        "title": "File:Sample instrument note.wav",
        "file_name": "Sample instrument note.wav",
        "source_revision_sha1": "b"*40,
        "attribution": "Example uploader",
        "classification": {"instrument_hints": ["kalimba"]},
    }


class RightsReviewTests(unittest.TestCase):
    def test_ccby_reviewable_but_not_rights_approved(self):
        row = candidate()
        self.assertEqual(review.candidate_review_basics(row), "REVIEWABLE_CLAIM")
        pack = review.draft_review(row, {"evidence_level": "source_claim_only"})
        self.assertEqual(pack["review_state"], "HUMAN_RIGHTS_REVIEW_REQUIRED")
        self.assertFalse(pack["audio_downloaded"])
        self.assertTrue(all(pack["approval_template"][k] is None
                            for k in ("recording_rights_verified",
                                      "composition_rights_verified",
                                      "commercial_derivative_reuse_allowed",
                                      "download_authorized")))
        self.assertIsNone(pack["approval_template"]["reviewed_by"])

    def test_reject_unsuitable_or_missing_attribution(self):
        c = candidate()
        c["title"] = "File:Cover song.wav"
        self.assertEqual(review.candidate_review_basics(c), "UNSUITABLE_TITLE_OR_DESCRIPTION")
        c = candidate()
        c["attribution"] = None
        self.assertEqual(review.candidate_review_basics(c), "MISSING_SOURCE_ATTRIBUTION")

    def test_reject_other_provider_or_untrusted_host(self):
        c = candidate()
        c["provider"] = "Internet Archive"
        self.assertEqual(review.candidate_review_basics(c), "OTHER_PROVIDER")
        c = candidate()
        c["source_media_url"] = "https://127.0.0.1/private.wav"
        self.assertEqual(review.candidate_review_basics(c), "UNTRUSTED_MEDIA_HOST")

    def test_source_licence_change_rejected(self):
        c = candidate()
        page = {"imageinfo": [{"sha1": "b"*40}]}
        with (
            patch.object(review, "latest_commons_page", return_value=page),
            patch.object(review.commons, "decide", return_value={
                "state": "ELIGIBLE", "source_license": "CC0-1.0",
            }),
        ):
            state, evidence = review.revalidate_source(Mock(), c)
        self.assertEqual(state, "LICENSE_CHANGED")
        self.assertIsNone(evidence)

    def test_source_version_changed_rejected(self):
        c = candidate()
        page = {"imageinfo": [{"sha1": "c"*40}]}
        with (
            patch.object(review, "latest_commons_page", return_value=page),
            patch.object(review.commons, "decide", return_value={
                "state": "ELIGIBLE", "source_license": "CC-BY-4.0",
                "direct_file_url": c["source_media_url"],
                "size": c["source_file_bytes"], "attribution": "Creator"
            }),
        ):
            state, _ = review.revalidate_source(Mock(), c)
        self.assertEqual(state, "SOURCE_SHA1_CHANGED")

    def test_current_claim_is_not_composition_clearance(self):
        c = candidate()
        page = {"imageinfo": [{"sha1": "b"*40}]}
        with (
            patch.object(review, "latest_commons_page", return_value=page),
            patch.object(review.commons, "decide", return_value={
                "state": "ELIGIBLE", "source_license": "CC-BY-4.0",
                "direct_file_url": c["source_media_url"],
                "size": c["source_file_bytes"],
                "attribution": "Creator", "author": "Creator",
                "source_url": c["source_page"], "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "rights_evidence_url": c["source_page"]
            }),
        ):
            state, evidence = review.revalidate_source(Mock(), c)
        self.assertEqual(state, "SOURCE_CLAIM_RECHECKED")
        self.assertEqual(evidence["evidence_level"],
            "current_public_source_claim_not_composition_rights_review")

    def test_priority_prefers_cc0_sample(self):
        a = candidate("CC0-1.0")
        b = candidate("CC-BY-4.0")
        self.assertLess(review.candidate_priority(a), review.candidate_priority(b))

    def test_no_download_when_just_collecting(self):
        c = candidate()
        fake = Mock()
        sha = "a"*64
        fake.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": f"{review.pilot.CANDIDATES}aa/{sha}.json", "Size": 1000}]}
        ]
        with (
            patch.object(review.pilot, "load_json", return_value=c),
            patch.object(review, "revalidate_source",
                return_value=("SOURCE_CLAIM_RECHECKED",
                              {"license": "CC-BY-4.0"})) as validated,
            patch.object(review.pilot, "stream_safe_media") as downloaded,
            patch.object(review.time, "sleep") as sleep,
        ):
            result = review.collect(fake, limit=8, max_records=100, max_queries=8, wait=0.4)
        self.assertEqual(result["source_rechecked_for_manual_review"], 1)
        self.assertEqual(result["audio_files_imported"], 0)
        self.assertEqual(result["review_approvals_created"], 0)
        validated.assert_called_once()
        downloaded.assert_not_called()


if __name__ == "__main__":
    unittest.main()
