#!/usr/bin/env python3
"""Offline tests only; no R2/network/audio/model weights."""
import unittest

import ws5_ast_secondary_review as secondary
import ws5_semantic_intelligence as semantic
import ws5_semantic_review as qa


def entry(n=0, flagged=True):
    return {
        "source_sha256": ("%064x" % (n + 1)),
        "audit_status": "AUDITED",
        "source_r2_key_private": "asset-library/raw/sha256/aa/" + ("%064x" % (n + 1)) + ".mp3",
        "assessment": {
            "review_flags": ["METADATA_CLAP_DISAGREEMENT"] if flagged else [],
            "human_reference_label": "UNKNOWN",
            "human_listening_pass": "NOT_RUN",
        }
    }


class ASTReviewContract(unittest.TestCase):
    def test_select_only_six_flagged_from_exact_eight(self):
        report = {
            "schema": qa.SCHEMA,
            "analysis_method": "METADATA_HINT_VS_CLAP_RELATIVE_SIMILARITY_NOT_GROUND_TRUTH",
            "private_review_queue": [entry(i, i < 6) for i in range(8)],
        }
        selected = secondary.chosen_rows(report)
        self.assertEqual(len(selected), 6)
        self.assertTrue(all(x["assessment"]["review_flags"] for x in selected))
        report["private_review_queue"][0]["assessment"]["human_listening_pass"] = "PASSED"
        with self.assertRaises(ValueError):
            secondary.chosen_rows(report)

    def test_broad_scan_and_duplicates_fail_closed(self):
        report = {
            "schema": qa.SCHEMA,
            "analysis_method": "METADATA_HINT_VS_CLAP_RELATIVE_SIMILARITY_NOT_GROUND_TRUTH",
            "private_review_queue": [entry(i, True) for i in range(8)],
        }
        with self.assertRaises(ValueError):
            secondary.chosen_rows(report)
        report["private_review_queue"][7] = entry(0, True)
        with self.assertRaises(ValueError):
            secondary.chosen_rows(report)
        report["private_review_queue"][7] = entry(7, False)
        report["schema"] = "not-authorized"
        with self.assertRaises(ValueError):
            secondary.chosen_rows(report)

    def test_audio_windows_match_existing_clap_sampling(self):
        self.assertEqual(secondary.RATE, 16000)
        self.assertEqual(secondary.windows_for_duration(600),
                         semantic.sample_windows(600))
        self.assertLessEqual(secondary.MAX_WINDOWS, 3)
        self.assertEqual(secondary.MAX_BYTES, secondary.base.MAX_BYTES)

    def test_secondary_scores_are_unverified(self):
        scores = {f"Event {i}": 0.01 for i in range(140)}
        scores.update({"Speech": 0.9, "Rain": .7, "Stream": .6})
        result = secondary.summarize_outputs([scores])
        self.assertEqual(result["top_event_hints"][0]["label"], "Speech")
        self.assertIn("speech", result["event_families_possible_not_verified"])
        self.assertIn("rain", result["event_families_possible_not_verified"])
        self.assertIn("freshwater", result["event_families_possible_not_verified"])
        self.assertEqual(result["speaker_detection"], "NOT_VERIFIED")
        self.assertEqual(result["human_listening_pass"], "NOT_RUN")
        self.assertFalse(result["sound_identity_verified"])
        self.assertFalse(result["model_accuracy_verified"])
        self.assertFalse(result["publication_approved"])
        self.assertFalse(result["scores_are_calibrated_probabilities"])

    def test_invalid_output_raises(self):
        tiny = {f"Event {i}": .1 for i in range(10)}
        with self.assertRaises(ValueError):
            secondary.summarize_outputs([tiny])
        ok = {f"Event {i}": .1 for i in range(120)}
        bad = dict(ok)
        bad["Event 0"] = float("nan")
        with self.assertRaises(ValueError):
            secondary.summarize_outputs([ok, bad])
        with self.assertRaises(ValueError):
            secondary.summarize_outputs([])

    def test_license_and_no_public_storage_guards(self):
        self.assertEqual(secondary.MODEL_REVISION,
                         "f826b80d28226b62986cc218e5cec390b1096902")
        self.assertTrue(secondary.PREFIX.startswith(semantic.PREFIX))
        self.assertNotEqual(secondary.PREFIX, semantic.DIVERSITY_PREFIX)
        self.assertEqual(secondary.MAX_FILES, 6)


if __name__ == "__main__":
    unittest.main()
