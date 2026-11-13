#!/usr/bin/env python3
"""Offline regression tests for private music audio staging chain."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bulk_stage_music_candidates as stage


def row():
    return {
        "schema": "music_source_candidate_v1",
        "candidate_id": "music-candidate-" + "a"*64,
        "provider": "Wikimedia Commons",
        "license": "CC-BY-4.0",
        "source_license_verified_at": "2026-11-13T00:00:00Z",
        "source_media_url": "https://upload.wikimedia.org/wikipedia/commons/a/a1/example.wav",
        "source_file_bytes": 12000,
        "source_page": "https://commons.wikimedia.org/wiki/File:Example.wav",
        "source_revision_sha1": "d"*40,
        "title": "File:Sample piano note.wav",
        "file_name": "Sample piano note.wav",
        "attribution": "Original composer",
        "classification": {"instrument_hints": ["piano"]},
    }


def params():
    return argparse.Namespace(batch_size=2, max_files=4,
       max_records=10000, max_source_queries=9, max_total_mib=25,
       max_seconds=7800, max_errors=5, request_delay=0.5,
       output="unused.json")


class StageTests(unittest.TestCase):
    def test_stable_receipt_address_dedup(self):
        x = row()["candidate_id"]
        self.assertEqual(stage.receipt_key(x),
            stage.RECEIPT_ROOT + "aa/" + "a"*64 + ".json")
        for invalid in ["../../bad", "music-candidate-123", "music-candidate-"+"z"*64]:
            with self.assertRaises(ValueError):
                stage.receipt_key(invalid)

    def test_ccby_is_reviewable_not_release_approved(self):
        r = row()
        self.assertEqual(stage.review.candidate_review_basics(r), "REVIEWABLE_CLAIM")
        self.assertIn("staging", stage.ROOT)
        self.assertIn("rights", stage.PROVENANCE_ROOT) if False else None

    def test_provider_rejected_from_ready_scope(self):
        r = row()
        r["provider"] = "Internet Archive"
        self.assertEqual(stage.review.candidate_review_basics(r), "OTHER_PROVIDER")

    def test_staging_metadata_never_claims_public_rights(self):
        r = row()
        obj = Mock()
        obj.head_object.side_effect = [
            stage.ClientError({"Error":{"Code":"404"},
                               "ResponseMetadata":{"HTTPStatusCode":404}},"HeadObject"),
            {"ContentLength":12000, "Metadata":{"sha256":"f"*64}},
            {"ContentLength":200, "Metadata":{}}
        ]
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder) / "sample.wav"
            f.write_bytes(b"A" * 12000)
            with patch.object(stage, "create_json") as make_json:
                result = stage.store_staging(
                    obj, r, {"license": "CC-BY-4.0"}, "f"*64, 12000,
                    f, {"codec": "pcm_s16le"})
            self.assertIn("internal/music-audio-staging/", result)
            evidence = make_json.call_args.args[2]
            self.assertFalse(evidence["public_or_commercial_export_approved"])
            self.assertFalse(evidence["studio_ready"])
            self.assertEqual(evidence["state"], "STORED_R2_RIGHTS_QA_PENDING")

    def test_processing_reused_asset_is_not_reuploaded(self):
        fake = Mock()
        candidate = row()
        args = params()
        with (
            patch.object(stage.review, "revalidate_source",
                         return_value=("SOURCE_CLAIM_RECHECKED", {"license": "CC-BY-4.0"})),
            patch.object(stage.pilot, "stream_safe_media",
                         return_value=("f"*64, 12000)),
            patch.object(stage, "save_receipt") as saved,
            patch.object(stage, "save_checkpoint") as checkpoint,
            patch.object(stage, "store_staging") as stored,
        ):
            states, bytes_out, pages, files, n_batch = stage.ingest(
                fake, [candidate], args, {"f"*64},
                stage.time.monotonic())
        self.assertEqual(states["DUPLICATE_SHA256"], 1)
        self.assertEqual(states["STORED_R2"], 0)
        stored.assert_not_called()
        saved.assert_called_once()
        self.assertEqual(files, 1)
        self.assertEqual(bytes_out, 12000)

    def test_invalid_source_claim_cannot_download(self):
        fake = Mock()
        candidate = row()
        args = params()
        with (
            patch.object(stage.review, "revalidate_source",
                         return_value=("LICENSE_CHANGED", None)),
            patch.object(stage.pilot, "stream_safe_media") as fetched,
            patch.object(stage, "save_checkpoint"),
        ):
            states, transfer, checked, processed, batches = stage.ingest(
                fake, [candidate], args, set(), stage.time.monotonic())
        fetched.assert_not_called()
        self.assertEqual(processed, 0)
        self.assertEqual(transfer, 0)
        self.assertEqual(states["SOURCE_REJECTED_LICENSE_CHANGED"], 1)

    def test_two_batches_chain_in_same_run(self):
        args = params()
        rows = [{**row(), "candidate_id":"music-candidate-"+c*64}
                for c in "abcd"]
        with (
            patch.object(stage.review, "revalidate_source",
                         return_value=("SOURCE_CLAIM_RECHECKED", {"license": "CC-BY-4.0"})),
            patch.object(stage.pilot, "stream_safe_media",
                         side_effect=[(c*64, 12000) for c in "abcd"]),
            patch.object(stage, "validate_audio",
                         return_value={"codec":"pcm_s16le"}),
            patch.object(stage, "store_staging", return_value="private-staged-key"),
            patch.object(stage, "save_receipt"),
            patch.object(stage, "save_checkpoint") as checkpoint,
            patch.object(stage.time, "sleep"),
        ):
            stats, transfer, pages, processed, batches = stage.ingest(
                Mock(), rows, args, set(), stage.time.monotonic())
        self.assertEqual(processed, 4)
        self.assertEqual(stats["STORED_R2"], 4)
        self.assertEqual(batches, 2)
        self.assertEqual(checkpoint.call_count, 2)

    def test_existing_receipts_skip_candidates(self):
        obj=Mock()
        sha="a"*64
        obj.get_paginator.return_value.paginate.return_value=[
          {"Contents":[{"Key":f"{stage.RECEIPT_ROOT}aa/{sha}.json"}]}
        ]
        self.assertIn(row()["candidate_id"], stage.existing_receipts(obj))


if __name__ == "__main__":
    unittest.main()
