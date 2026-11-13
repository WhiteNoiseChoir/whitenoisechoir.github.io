#!/usr/bin/env python3
"""No-network R2 gate, chaining and non-duplication regression tests."""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_music_metadata_batches as chain
import scan_openverse_music_metadata as openverse


class ChainedBatchesTests(unittest.TestCase):
    def test_distinct_waves_not_identical_original(self):
        original = ("piano solo", "soft piano")
        families = [openverse.family_queries("grand-piano", original, i) for i in range(10)]
        self.assertEqual(len({tuple(x) for x in families}), 10)
        self.assertTrue(all(len(v) == 2 for v in families))
        with self.assertRaises(ValueError):
            openverse.family_queries("grand-piano", original, 10)

    def test_count_only_candidate_objects_not_reports_or_audio(self):
        good = "a" * 64
        fake = Mock()
        fake.get_paginator.return_value.paginate.return_value = [
            {"Contents": [
                {"Key": f"internal/music-candidates/v1/aa/{good}.json", "Size": 400},
                {"Key": f"internal/music-candidates/v1/aa/{good}.json", "Size": 400},
                {"Key": "internal/music-candidates/runs/latest.json", "Size": 300},
                {"Key": "asset-library/raw/sha256/foo.mp3", "Size": 2000},
                {"Key": f"internal/music-candidates/v1/aa/{'b'*64}.json", "Size": 0},
            ]}
        ]
        self.assertEqual(len(chain.candidate_keys(fake)), 1)
        self.assertEqual(fake.get_paginator.call_args.args[0], "list_objects_v2")

    def test_wave_checkpoint_discovery(self):
        fake = Mock()
        fake.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": chain.CHECKPOINT + "wave-1.json"},
                          {"Key": chain.CHECKPOINT + "wave-4.json"},
                          {"Key": chain.CHECKPOINT + "wave-99.json"}]}]
        self.assertEqual(chain.checkpoint_waves(fake), {1, 4})

    def test_checkpoint_is_create_only(self):
        fake = Mock()
        chain.save_checkpoint(fake, 1, {"stored_candidate_objects": 400})
        self.assertEqual(fake.put_object.call_args.kwargs["IfNoneMatch"], "*")
        self.assertTrue(fake.put_object.call_args.kwargs["Key"].startswith(chain.CHECKPOINT))

    def test_candidate_sha_id_matches_object_key(self):
        digest = "b" * 64
        key = f"internal/music-candidates/v1/bb/{digest}.json"
        fake = Mock()
        fake.get_object.return_value = {"Body": Mock(read=lambda: json.dumps({
            "schema": "music_source_candidate_v1",
            "candidate_id": "music-candidate-" + digest,
            "status": "candidate_only_not_downloaded",
            "source_page": "https://example.org/sound",
        }).encode())}
        self.assertTrue(chain.verify_candidate(fake, key))
        fake.get_object.return_value = {"Body": Mock(read=lambda: json.dumps({
            "schema": "music_source_candidate_v1", "candidate_id": "music-candidate-" + "c"*64,
            "status": "candidate_only_not_downloaded", "source_page": "https://example.org/sound",
        }).encode())}
        self.assertFalse(chain.verify_candidate(fake, key))

    def test_preceding_run_must_finish(self):
        response = Mock()
        response.json.return_value = {"status": "completed", "conclusion": "success"}
        with patch.object(chain.requests, "get", return_value=response):
            self.assertEqual(chain.wait_for_prior_run(123, 20), "success")
        self.assertEqual(chain.wait_for_prior_run(0), "skipped")

    def test_existing_target_means_no_scans(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(target=1000, max_batches=9,
                wait_for_run=0, wait_seconds=20, budget_seconds=100,
                output=str(Path(tmp) / "audit.json"))
            fake_keys = {"test-key-" + str(i) for i in range(1001)}
            with (
                patch.object(chain.core, "s3_client", return_value=Mock()),
                patch.object(chain, "candidate_keys", return_value=fake_keys),
                patch.object(chain, "verify_full_index", return_value={"valid": 1001, "invalid": 0}),
                patch.object(chain.openverse, "scan") as scanner,
                patch.object(chain.core, "emit"),
            ):
                result = chain.run(args)
            self.assertEqual(result["state"], "TARGET_REACHED")
            scanner.assert_not_called()

    def test_next_wave_starts_only_after_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(target=1000, max_batches=2,
                wait_for_run=0, wait_seconds=20, budget_seconds=100,
                output=str(Path(tmp) / "audit.json"))
            fake = {"storage": {"created": 150, "existing": 50, "errors": 0},
                    "found_unique_in_shard": 200, "family_diagnostics": {}}
            with (
                patch.object(chain.core, "s3_client", return_value=Mock()),
                patch.object(chain, "candidate_keys",
                    side_effect=[{"x" + str(i) for i in range(650)},
                                 {"x" + str(i) for i in range(800)},
                                 {"x" + str(i) for i in range(950)}]),
                patch.object(chain, "checkpoint_waves", return_value=set()),
                patch.object(chain, "save_checkpoint", return_value="checkpoint"),
                patch.object(chain.openverse, "scan", return_value=fake) as scanner,
                patch.object(chain.core, "emit"),
            ):
                result = chain.run(args)
            self.assertEqual(result["state"], "QUERY_WAVES_EXHAUSTED")
            self.assertEqual([x["wave"] for x in result["batches"]], [1, 2])
            self.assertEqual(scanner.call_count, 2)
            self.assertEqual(result["candidate_objects"], 950)

    def test_reject_invalid_target(self):
        with self.assertRaises(ValueError):
            chain.run(argparse.Namespace(target=0))


if __name__ == "__main__":
    unittest.main()
