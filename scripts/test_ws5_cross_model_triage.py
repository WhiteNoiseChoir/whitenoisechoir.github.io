#!/usr/bin/env python3
"""Offline safety/priority tests; no R2 reads, no model inference, no audio."""
import unittest

import ws5_cross_model_triage as triage
import ws5_ast_secondary_review as ast
import ws5_semantic_review as clapqa


def source(n, flagged=True):
    sha = ("%064x" % (n + 1))
    return {
        "source_sha256": sha,
        "source_title_private": "test fixture",
        "source_r2_key_private": "asset-library/raw/sha256/aa/" + sha + ".mp3",
        "audit_status": "AUDITED",
        "assessment": {
            "human_listening_pass": "NOT_RUN",
            "human_reference_label": "UNKNOWN",
            "review_flags": ["POSSIBLE_CONTAMINATION_UNVERIFIED"] if flagged else [],
            "top_matches": [{"label":"rain", "cosine_similarity":.6}],
        }
    }


def ast_record(row, event_families=None):
    return {
        "schema": ast.SCHEMA,
        "sha256": row["source_sha256"],
        "model": ast.MODEL_ID,
        "model_revision": ast.MODEL_REVISION,
        "status": "SECOND_MODEL_EVENT_HINTS_UNVERIFIED",
        "source_sha256_verified": True,
        "human_listening_pass": "NOT_RUN",
        "publication_approved": False,
        "event_families_possible_not_verified": event_families or [],
        "top_event_hints": [{"label":"Rain","uncalibrated_sigmoid":.7}],
        "sample_windows": [
            {"start_seconds":0.0, "decoded_seconds":10.0},
            {"start_seconds":95.0, "decoded_seconds":10.0},
            {"start_seconds":190.0, "decoded_seconds":10.0}
        ],
    }


class TriageTests(unittest.TestCase):
    def test_risks_are_priority_only_not_truth(self):
        x = source(0)
        r = triage.triage_item(x, ast_record(x, ["speech", "rain"]))
        self.assertEqual(r["review_priority_ordinal_only"], 1)
        self.assertEqual(r["speech_presence"], "NOT_VERIFIED")
        self.assertEqual(r["listening_result"], "NOT_RUN")
        self.assertEqual(r["label_accuracy"], "NOT_MEASURED")
        self.assertFalse(r["publication_approved"])
        self.assertEqual(len(r["audition_windows"]), 3)

    def test_crossmodel_queue_exact_six(self):
        rows = [source(i, i < 6) for i in range(8)]
        clap = {"schema":clapqa.SCHEMA,
                "analysis_method":"METADATA_HINT_VS_CLAP_RELATIVE_SIMILARITY_NOT_GROUND_TRUTH",
                "private_review_queue":rows}
        records = {row["source_sha256"]:ast_record(row, ["speech"] if i == 0 else [])
                   for i, row in enumerate(rows[:6])}
        out = triage.synthesize(clap, records)
        self.assertEqual(out["source_count"],6)
        self.assertEqual(out["audition_total_windows"],18)
        self.assertEqual(out["priority_counts"]["1"],1)
        self.assertEqual(out["priority_counts"]["2"],5)
        self.assertEqual(out["reference_accuracy"],None)
        self.assertEqual(out["human_verified_count"],0)
        self.assertEqual(out["status"],"HUMAN_LISTENING_NOT_STARTED")
        self.assertEqual(out["private_listening_queue"][0]["source_sha256_private"],rows[0]["source_sha256"])

    def test_unverified_source_cannot_be_auto_cleared(self):
        x = source(0)
        rec = ast_record(x)
        rec["publication_approved"] = True
        with self.assertRaises(ValueError):
            triage.triage_item(x, rec)
        rec = ast_record(x)
        rec["source_sha256_verified"] = False
        with self.assertRaises(ValueError):
            triage.triage_item(x, rec)
        rec = ast_record(x)
        rec["sample_windows"][0]["decoded_seconds"] = 20.0
        with self.assertRaises(ValueError):
            triage.triage_item(x, rec)
        x = source(0)
        x["source_r2_key_private"] = "internal/audio/" + x["source_sha256"]
        with self.assertRaises(ValueError):
            triage.triage_item(x, ast_record(x))

    def test_missing_record_fails_closed(self):
        rows = [source(i, i < 6) for i in range(8)]
        clap = {"schema":clapqa.SCHEMA,
                "analysis_method":"METADATA_HINT_VS_CLAP_RELATIVE_SIMILARITY_NOT_GROUND_TRUTH",
                "private_review_queue":rows}
        records = {row["source_sha256"]:ast_record(row) for row in rows[:5]}
        with self.assertRaises(ValueError):
            triage.synthesize(clap, records)

    def test_unknown_metadata_only_low_priority(self):
        x = source(0)
        x["assessment"]["review_flags"] = ["METADATA_CATEGORY_UNKNOWN"]
        r = triage.triage_item(x, ast_record(x))
        self.assertEqual(r["review_priority_ordinal_only"],4)


if __name__ == "__main__":
    unittest.main()
