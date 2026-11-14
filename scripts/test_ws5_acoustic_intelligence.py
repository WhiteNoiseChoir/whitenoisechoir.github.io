#!/usr/bin/env python3
"""WS5 deterministic offline contract tests, no R2 or original media access."""
import math,unittest
from pathlib import Path
import importlib.util
import numpy as np

module_path=Path(__file__).resolve().parent/"ws5_acoustic_intelligence.py"
spec=importlib.util.spec_from_file_location("wnc_ws5",module_path)
ws5=importlib.util.module_from_spec(spec);spec.loader.exec_module(ws5)

class AcousticTests(unittest.TestCase):
 def test_filename_sha_key_consistency(self):
  sha="a"*64
  key=f"asset-library/raw/sha256/aa/{sha}.mp3"
  self.assertEqual(ws5.KEY_RE.fullmatch(key)[1],sha)
  self.assertIsNone(ws5.KEY_RE.fullmatch(f"internal/private/{sha}.mp3"))
  self.assertIsNone(ws5.KEY_RE.fullmatch(f"asset-library/raw/sha256/aa/{sha}.exe"))
 def test_quiet_signal_basic_stats(self):
  rate=16000
  x=(.03*np.sin(2*np.pi*150*np.arange(rate*25)/rate)).astype("<f4")
  result=ws5.profile(x)
  self.assertTrue(-35<result["rms_dbfs"]<-25)
  self.assertTrue(result["silent_window_fraction"]<.01)
  self.assertTrue(0<=result["highband_energy_ratio_gt4khz"]<.002)
  self.assertTrue(result["centroid_hz"]<300)
 def test_jump_detects_transient(self):
  x=np.full(16000*25,.00004,dtype="<f4")
  x[16000*10:16000*11]=.35
  p=ws5.profile(x)
  self.assertGreater(p["max_rms_jump_db_per_100ms"],30)
 def test_summary_no_semantic_confidence(self):
  x=(.01*np.sin(2*np.pi*350*np.arange(16000*25)/16000)).astype("<f4")
  metrics=ws5.summarize([ws5.profile(x)])
  self.assertIn("rms_dbfs",metrics)
  self.assertNotIn("speech_detected",metrics)
  self.assertNotIn("sleep_approved",metrics)
 def test_priority_terms(self):
  self.assertIsNotNone(ws5.PREFER.search("mild rain forest creek"))
  self.assertIsNone(ws5.PREFER.search("piano sample remix"))
if __name__=="__main__":unittest.main()
