#!/usr/bin/env python3
"""WS2 offline safety and sequencing tests; no network/R2 credentials required."""
import argparse
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import expand_music_metadata_5k as ws


class TestWS2(unittest.TestCase):
    def test_new_queries_are_not_previous_openverse_waves(self):
        self.assertEqual(len(ws.WAVES), 18)
        self.assertGreaterEqual(len(ws.EXTRA_FAMILIES), 30)
        self.assertEqual(len({tuple(x[1]) for x in ws.WAVES}), 18)
        provider, terms = ws.families(0)
        self.assertEqual(provider, "openverse")
        self.assertTrue(any("one shot" in q[0] for _, q in terms))
        self.assertTrue(any("dan tranh" in q[0] for _, q in terms))

    def test_checkpoint_uses_create_only(self):
        client = Mock()
        ws.save(client, 0, {"created": 5})
        self.assertEqual(client.put_object.call_args.kwargs["IfNoneMatch"], "*")
        self.assertTrue(client.put_object.call_args.kwargs["Key"].startswith(ws.CONTROL))

    def test_checkpoint_not_found_only(self):
        client = Mock()
        from botocore.exceptions import ClientError
        client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}, "ResponseMetadata": {"HTTPStatusCode": 404}},
            "HeadObject")
        self.assertFalse(ws.is_done(client, 0))
        client.head_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
            "HeadObject")
        with self.assertRaises(ClientError):
            ws.is_done(client, 0)

    def test_existing_target_verifies_without_scanning(self):
        args = argparse.Namespace(target=5000, max_waves=2, requests_per_wave=10,
                                  seconds_per_wave=10, new_per_wave=10, total_seconds=100)
        with (patch.object(ws.core, "s3_client", return_value=Mock()),
              patch.object(ws, "candidate_keys", return_value=set(range(5000))),
              patch.object(ws, "verify_full_index", return_value={"valid": 5000}) as verify,
              patch.object(ws, "collect_wave") as collect):
            result = ws.run(args)
        self.assertEqual(result["state"], "TARGET_REACHED")
        verify.assert_called_once()
        collect.assert_not_called()

    def test_sequential_checkpoint_and_no_false_target(self):
        args = argparse.Namespace(target=5000, max_waves=2, requests_per_wave=10,
                                  seconds_per_wave=10, new_per_wave=10, total_seconds=100)
        with (patch.object(ws.core, "s3_client", return_value=Mock()),
              patch.object(ws, "candidate_keys",
                           side_effect=[set(range(1344)), set(range(1354)), set(range(1364))]),
              patch.object(ws, "is_done", return_value=False),
              patch.object(ws, "save") as checkpoint,
              patch.object(ws, "collect_wave", return_value={
                  "state": "COMPLETED", "created": 10, "existing": 0,
                  "api_errors": 0, "requests": 10}),
              patch.object(ws.core, "emit")):
            result = ws.run(args)
        self.assertEqual(result["state"], "WAVES_EXHAUSTED")
        self.assertEqual(result["missing"], 3636)
        self.assertEqual(checkpoint.call_count, 2)

    def test_error_not_checkpointed(self):
        args = argparse.Namespace(target=5000, max_waves=1, requests_per_wave=10,
                                  seconds_per_wave=10, new_per_wave=10, total_seconds=100)
        with (patch.object(ws.core, "s3_client", return_value=Mock()),
              patch.object(ws, "candidate_keys",
                           side_effect=[set(range(1344)), set(range(1344))]),
              patch.object(ws, "is_done", return_value=False),
              patch.object(ws, "save") as checkpoint,
              patch.object(ws, "collect_wave", return_value={
                  "state": "API_BLOCKED", "created": 0, "existing": 0, "api_errors": 5}),
              patch.object(ws.core, "emit")):
            result = ws.run(args)
        self.assertEqual(result["state"], "API_BLOCKED")
        checkpoint.assert_not_called()

    def test_new_openverse_record_is_metadata_only(self):
        sample = {"foreign_landing_url": "https://example.com/audio/1",
                  "source": "freesound", "license": "cc0",
                  "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                  "id": "abcdefghijklmnop", "title": "oud note", "mature": False}
        record, reason = ws.ov.build_candidate(sample, "oud", "oud one shot")
        self.assertIsNone(reason)
        self.assertIsNone(record["audio_storage_key"])
        self.assertEqual(record["status"], "candidate_only_not_downloaded")
        self.assertEqual(record["rights_review_status"],
                         "source_claim_and_composition_rights_pending")


if __name__ == "__main__":
    unittest.main()
