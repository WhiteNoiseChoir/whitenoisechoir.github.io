#!/usr/bin/env python3
"""Offline contracts for private WS5 semantic QA; never access real R2."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ws5_semantic_review as qa
import ws5_semantic_intelligence as semantic


def sample(group="rain_storm", winner="rain", changing=False, contaminant=False):
    labels = list(semantic.PROMPTS)
    order = [winner] + [x for x in labels if x != winner]
    if contaminant:
        order = [winner, "human_speech"] + [x for x in labels if x not in (winner, "human_speech")]
    top = [{"label": label, "cosine_similarity": round(.7 - idx * .03, 4)}
           for idx, label in enumerate(order[:6])]
    first = top[:4]
    second = ([{"label": "river_stream", "cosine_similarity": .72}] +
              [x for x in first if x["label"] != "river_stream"][:3]) if changing else first
    return {
        "status": "SEMANTIC_SCORED_UNCALIBRATED",
        "schema": semantic.SCHEMA,
        "source_sha256_verified": True,
        "model": semantic.MODEL_ID,
        "model_revision": semantic.MODEL_REVISION,
        "vocabulary_version": semantic.LABEL_VERSION,
        "sleep_approval": "NOT_APPROVED",
        "license_approval": "NOT_CHECKED",
        "suitability_score": None,
        "speech_detection": "NOT_VERIFIED",
        "top_matches": top,
        "window_top_matches": [first, second],
        "possible_contamination_review": ["human_speech"] if contaminant else [],
    }


class CLAPReviewTests(unittest.TestCase):
    def test_hints_not_accuracy_or_clearance(self):
        a = qa.inspect_record(sample(), "rain_storm")
        self.assertEqual(a["best_expected_rank"], 1)
        self.assertEqual(a["review_flags"], [])
        self.assertEqual(a["human_reference_label"], "UNKNOWN")
        self.assertIs(a["semantic_accuracy_verified"], False)
        self.assertIs(a["publication_approved"], False)

    def test_top3_metadata_only(self):
        s = sample(winner="ocean_waves")
        unrelated = ["ocean_waves", "river_stream", "waterfall", "wind_trees", "forest_birds", "owl_call"]
        s["top_matches"] = [
            {"label": label, "cosine_similarity": round(.7 - idx * .03, 4)}
            for idx, label in enumerate(unrelated)
        ]
        s["window_top_matches"] = [s["top_matches"][:4]]
        a = qa.inspect_record(s, "rain_storm")
        self.assertIsNone(a["best_expected_rank"])
        self.assertIn("METADATA_CLAP_DISAGREEMENT", a["review_flags"])
        self.assertFalse(a["semantic_accuracy_verified"])

    def test_unknown_or_window_varies_is_review(self):
        a = qa.inspect_record(sample(changing=True), "other")
        self.assertIn("WINDOW_TOP1_VARIATION", a["review_flags"])
        self.assertIn("METADATA_CATEGORY_UNKNOWN", a["review_flags"])

    def test_contamination_only_possible(self):
        a = qa.inspect_record(sample(contaminant=True), "rain_storm")
        self.assertIn("POSSIBLE_CONTAMINATION_UNVERIFIED", a["review_flags"])
        self.assertEqual(a["human_listening_pass"], "NOT_RUN")

    def test_invalid_approvals_fail_closed(self):
        x = sample()
        x["license_approval"] = "APPROVED"
        with self.assertRaises(ValueError):
            qa.inspect_record(x, "rain_storm")
        x = sample()
        x["top_matches"][0]["cosine_similarity"] = float("nan")
        with self.assertRaises(ValueError):
            qa.inspect_record(x, "rain_storm")
        x = sample()
        x["model_revision"] = "main"
        with self.assertRaises(ValueError):
            qa.inspect_record(x, "rain_storm")
        x = sample()
        x["status"] = "ERROR"
        with self.assertRaises(ValueError):
            qa.inspect_record(x, "rain_storm")

    def test_summary_no_false_claim(self):
        rows = [
            {"audit_status": "AUDITED", "assessment": qa.inspect_record(sample(), "rain_storm")},
            {"audit_status": "AUDITED", "assessment": qa.inspect_record(sample(winner="traffic"), "other")},
            {"audit_status": "INVALID_MODEL_RESULT", "invalid_reason": "not valid"}
        ]
        out = qa.summarize(rows)
        self.assertEqual(out["audited_records"], 3)
        self.assertEqual(out["AUDITED"], 2)
        self.assertEqual(out["INVALID_MODEL_RESULT"], 1)
        self.assertEqual(out["metadata_agreement_top3_not_truth"], 1)
        self.assertEqual(out["metadata_agreement_not_established"], 1)
        self.assertEqual(out["items_for_human_review"], 1)


if __name__ == "__main__":
    unittest.main()
