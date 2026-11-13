#!/usr/bin/env python3
"""Offline regression tests for aggregate-only candidate audit."""
import json
from unittest import TestCase, main
from unittest.mock import Mock, patch
import audit_music_metadata_diversity as audit


def record(char="a", provider="Wikimedia Commons", hints=None, media="https://example.org/audio.wav"):
    digest = char * 64
    return (f"internal/music-candidates/v1/{digest[:2]}/{digest}.json", {
        "schema": "music_source_candidate_v1",
        "candidate_id": "music-candidate-" + digest,
        "status": "candidate_only_not_downloaded",
        "provider": provider,
        "license": "CC0-1.0",
        "rights_review_status": "composition_and_reuse_rights_pending",
        "source_page": "https://example.org/page",
        "source_media_url": media,
        "classification": {"instrument_hints": hints if hints is not None else ["violin"], "audio_kind": "unclassified"},
        "technical": {},
    })


class AuditTests(TestCase):
    def test_distinct_source_overlap_not_content_sha(self):
        result = audit.audit_records([record("a"), record("b", "Internet Archive", ["violin", "cello"], "https://EXAMPLE.org/audio.wav?tracking=1")])
        self.assertEqual(result["objects_read"], 2)
        self.assertEqual(result["valid_core_records"], 2)
        self.assertEqual(result["possible_source_media_url_overlaps"]["normalized_keys_with_multiple_candidate_ids"], 1)
        self.assertEqual(result["records_with_multiple_family_hints"], 1)
        self.assertEqual(result["instrument_family_hint_counts_not_audio_verified"]["violin"], 2)
        self.assertEqual(result["duplicate_candidate_id_excess"], 0)
        self.assertEqual(result["audio_downloads_performed"], 0)
        self.assertFalse(result["commercial_rights_cleared_by_audit"])
        self.assertNotIn("example.org", json.dumps(result))

    def test_key_shard_mismatch_invalid(self):
        key, data = record("b")
        result = audit.audit_records([(key.replace("/bb/", "/aa/"), data)])
        self.assertEqual(result["valid_core_records"], 0)
        self.assertEqual(result["invalid_checks"]["shard_mismatch"], 1)

    def test_missing_families(self):
        result = audit.audit_records([record()])
        self.assertIn("violin", result["instrument_family_hint_counts_not_audio_verified"])
        self.assertEqual(result["families_covered"], 1)
        self.assertEqual(len(result["priority_gap_families"]), 10)

    def test_normalized_url_rejects_invalid_and_strips_tracking(self):
        self.assertIsNone(audit.normalized_url("file:///tmp/private.wav"))
        self.assertIsNone(audit.normalized_url("https://"))
        self.assertEqual(audit.normalized_url("https://EXAMPLE.org/a.mp3?secret=1#part"), "https://example.org/a.mp3")

    def test_duplicate_candidate_id(self):
        item = record()
        result = audit.audit_records([item, item])
        self.assertEqual(result["duplicate_candidate_id_excess"], 1)

    def test_list_excludes_reports_and_zero_size(self):
        fake = Mock()
        fake.get_paginator.return_value.paginate.return_value = [{"Contents": [
            {"Key": record()[0], "Size": 500},
            {"Key": "internal/music-candidates/runs/1.json", "Size": 500},
            {"Key": record("b")[0], "Size": 0},
        ]}]
        self.assertEqual(audit.list_candidate_keys(fake), [(record()[0], 500)])

    def test_r2_read_only_no_put_calls(self):
        fake = Mock()
        fake.get_paginator.return_value.paginate.return_value = [{"Contents": [
            {"Key": record()[0], "Size": 500},
        ]}]
        fake.get_object.return_value = {"Body": Mock(read=lambda n: json.dumps(record()[1]).encode(), close=lambda: None)}
        result = audit.audit_r2(fake, workers=1)
        self.assertTrue(result["complete_read"])
        self.assertEqual(result["valid_core_records"], 1)
        fake.put_object.assert_not_called()
        fake.delete_object.assert_not_called()

    def test_broken_json_is_incomplete(self):
        fake = Mock()
        fake.get_paginator.return_value.paginate.return_value = [{"Contents": [{"Key": record()[0], "Size": 100}]}]
        fake.get_object.return_value = {"Body": Mock(read=lambda n: b"{broken", close=lambda: None)}
        result = audit.audit_r2(fake, workers=1)
        self.assertFalse(result["complete_read"])
        self.assertEqual(result["objects_failed_to_read"], 1)


if __name__ == "__main__":
    main()
