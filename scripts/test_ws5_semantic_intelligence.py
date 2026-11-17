#!/usr/bin/env python3
"""Offline WS5 CLAP pilot contract checks (no model weights, no R2 access)."""
import unittest
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
spec = importlib.util.spec_from_file_location(
    "wnc_ws5_semantic", Path(__file__).resolve().parent / "ws5_semantic_intelligence.py"
)
semantic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(semantic)


class SemanticContractTests(unittest.TestCase):
    def test_windows_are_deterministic_and_cover_ends(self):
        self.assertEqual(semantic.sample_windows(7), [(0.0, 7)])
        self.assertEqual(semantic.sample_windows(10), [(0.0, 10)])
        self.assertEqual(semantic.sample_windows(40), [(0.0, 10), (15.0, 10), (30, 10)])
        self.assertEqual(semantic.sample_windows(600), [(0.0, 10), (295.0, 10), (590, 10)])
        for value in [0, -1, float("inf"), float("nan")]:
            with self.assertRaises(ValueError):
                semantic.sample_windows(value)

    def test_ranking_is_uncalibrated_and_keeps_review_gate(self):
        keys = list(semantic.PROMPTS)
        row = {name: 0.05 for name in keys}
        row.update(rain=0.62, river_stream=0.49, human_speech=0.54, traffic=0.30)
        result = semantic.ranking([row])
        self.assertEqual(result["top_matches"][0]["label"], "rain")
        self.assertEqual(result["top_matches"][1]["label"], "human_speech")
        self.assertIn("human_speech", result["possible_contamination_review"])
        self.assertIn("bed_candidate", result["role_hints_unverified"])
        self.assertFalse(result["scores_are_probabilities"])
        self.assertEqual(result["classifier_confidence"], "UNCALIBRATED")
        self.assertEqual(result["speech_detection"], "NOT_VERIFIED")
        self.assertEqual(result["sleep_approval"], "NOT_APPROVED")
        self.assertEqual(result["license_approval"], "NOT_CHECKED")

    def test_scoring_does_not_turn_labels_into_clearance(self):
        row = {name: -0.2 for name in semantic.PROMPTS}
        row["rain"] = 0.9
        result = semantic.ranking([row, row, row])
        self.assertEqual(result["possible_contamination_review"], [])
        self.assertEqual(result["speech_detection"], "NOT_VERIFIED")
        self.assertEqual(result["music_detection"], "NOT_VERIFIED")
        self.assertIsNotNone(result["top_matches"])

    def test_bad_scores_fail_closed(self):
        rows = [
            {"rain": 0.2},
            {k: float("nan") for k in semantic.PROMPTS},
            {k: 2.0 for k in semantic.PROMPTS},
        ]
        for item in rows:
            with self.assertRaises(ValueError):
                semantic.ranking([item])
        with self.assertRaises(ValueError):
            semantic.ranking([])

    def test_storage_and_budget_isolated_from_v1(self):
        self.assertIn("/v2-clap/", semantic.PREFIX)
        self.assertNotEqual(semantic.PREFIX, semantic.base.WS5)
        self.assertLessEqual(semantic.MAX_FILES, 4)
        self.assertEqual(semantic.RATE, 48000)
        self.assertEqual(semantic.WINDOW_S, 10)
        self.assertEqual(semantic.LABEL_VERSION, "wnc_clap_scene_labels_20261117_1")


if __name__ == "__main__":
    unittest.main()
