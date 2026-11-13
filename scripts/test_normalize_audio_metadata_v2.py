import importlib.util
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator, FormatChecker

HERE = Path(__file__).resolve().parent
S = json.loads((HERE.parent / "schema" / "asset-metadata-v2.schema.json").read_text())
spec = importlib.util.spec_from_file_location("normalize_audio_metadata_v2", HERE / "normalize_audio_metadata_v2.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
V = Draft202012Validator(S, format_checker=FormatChecker())
DIGEST = "a" * 64
KEY = f"asset-library/commons/sha256/aa/{DIGEST}.wav"


def sidecar(**kwargs):
    return {"audio_sha256": DIGEST, "audio_storage_key": KEY, "title": "Forest stream", "duration_seconds": 12.4,
            "file_bytes": 9000, "codec": "pcm_s16le", "source_page": "https://commons.wikimedia.org/wiki/File:Stream.wav",
            "license": "CC0-1.0", "license_evidence_url": "https://commons.wikimedia.org/wiki/File:Stream.wav",
            "license_checked_at": "2026-11-13T00:00:00Z", "rights": {"source_license_verified": True}, **kwargs}


class MetadataV2Tests(unittest.TestCase):
    def test_sidecar_valid(self):
        x = m.normalize(sidecar())
        self.assertEqual(x["asset_id"], "r2-" + DIGEST)
        self.assertEqual(x["source"]["rights_status"], "attested")
        self.assertEqual(x["musical"]["bpm"], None)
        V.validate(x)

    def test_idempotent(self):
        x = m.normalize(sidecar())
        self.assertEqual(m.normalize(x), x)

    def test_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "differs"):
            m.normalize(sidecar(audio_sha256="b" * 64))

    def test_legacy_key_without_fake_content_hash(self):
        x = m.normalize({"name": "White noise", "key": "audio/white-noise.mp3", "duration": 600})
        self.assertTrue(x["asset_id"].startswith("legacy-key-"))
        self.assertIsNone(x["content_sha256"])
        V.validate(x)

    def test_url_only(self):
        x = m.normalize({"name": "Train", "url": "https://example.org/clip.wav"})
        self.assertTrue(x["asset_id"].startswith("legacy-url-"))
        V.validate(x)

    def test_missing_rights_unverified(self):
        x = m.normalize({"audio_sha256": DIGEST, "audio_storage_key": KEY, "duration": 3})
        self.assertEqual(x["source"]["rights_status"], "unverified")
        self.assertNotEqual(x["lifecycle"], "mix_ready")
        V.validate(x)

    def test_dedup(self):
        rows, errors = m.convert([sidecar(), sidecar()])
        self.assertEqual(len(rows), 1)
        self.assertEqual(errors, [])

    def test_no_claim_inferred_music(self):
        x = m.normalize({"key": KEY, "title": "piano", "bpm": 100, "key_signature": "C"})
        self.assertIsNone(x["musical"]["bpm"])
        self.assertIsNone(x["musical"]["key"])
        V.validate(x)

    def test_mix_ready_cannot_be_unverified(self):
        x = m.normalize(sidecar())
        x["lifecycle"] = "mix_ready"
        x["source"]["rights_status"] = "unverified"
        self.assertTrue(list(V.iter_errors(x)))

    def test_invalid_row_does_not_stop_batch(self):
        rows, errs = m.convert([sidecar(), {"title": "no-id"}])
        self.assertEqual((len(rows), len(errs)), (1, 1))


if __name__ == "__main__":
    unittest.main()
