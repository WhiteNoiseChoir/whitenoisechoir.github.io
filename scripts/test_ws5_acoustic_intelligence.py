#!/usr/bin/env python3
"""WS5 deterministic offline contract tests, no R2 or original media access."""
import math,unittest
from datetime import datetime, timezone, timedelta
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
  self.assertAlmostEqual(result["sampled_spectral_peak_hz_approx"],150,delta=1)
  self.assertLess(result["rms_variation_p90_p10_db"],1)
  self.assertGreater(result["sampled_peak_energy_fraction"],.1)
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
 def test_checkpoint_schedule_cooldown(self):
  time=datetime(2026,11,17,8,0,tzinfo=timezone.utc)
  prior=lambda minutes: {"updated_at":(time-timedelta(minutes=minutes)).isoformat()}
  self.assertTrue(ws5.is_recent_checkpoint(prior(10),time,45))
  self.assertFalse(ws5.is_recent_checkpoint(prior(45),time,45))
  self.assertFalse(ws5.is_recent_checkpoint(prior(60),time,45))
  self.assertFalse(ws5.is_recent_checkpoint(prior(1),time,0))
  self.assertFalse(ws5.is_recent_checkpoint({},time,45))
  with self.assertRaises(ValueError):
   ws5.is_recent_checkpoint({"updated_at":"bad"},time,45)
  with self.assertRaises(ValueError):
   ws5.is_recent_checkpoint({"updated_at":(time+timedelta(minutes=10)).isoformat()},time,45)
  with self.assertRaises(ValueError):
   ws5.is_recent_checkpoint({},time,150)
 def test_music_pre_download_gate(self):
  self.assertEqual(ws5.metadata_content_gate("Rain with piano music","Rain"),"EXCLUDED_MUSIC")
  self.assertEqual(ws5.metadata_content_gate("Guitar instrumental","Nature"),"EXCLUDED_MUSIC")
  self.assertEqual(ws5.metadata_content_gate("Ambient music with ocean waves","Ocean"),"EXCLUDED_MUSIC")
  self.assertEqual(ws5.metadata_content_gate("Forest creek and birds","Nature"),"NATURE_SFX_METADATA_ONLY")
  self.assertEqual(ws5.metadata_content_gate("Ambient noise fan","Mechanical SFX"),"NATURE_SFX_METADATA_ONLY")
  self.assertEqual(ws5.metadata_content_gate("Unknown recording","Unknown"),"SKIPPED_UNCERTAIN_CONTENT")
  self.assertEqual(ws5.metadata_content_gate("Bird song in forest","Nature"),"NATURE_SFX_METADATA_ONLY")
  self.assertEqual(ws5.metadata_content_gate("Singing birds in forest","Nature"),"NATURE_SFX_METADATA_ONLY")
  self.assertEqual(ws5.metadata_content_gate("Whale song underwater","Ocean"),"NATURE_SFX_METADATA_ONLY")
  self.assertEqual(ws5.metadata_content_gate("Bird song with piano","Nature"),"EXCLUDED_MUSIC")
  self.assertEqual(ws5.metadata_content_gate("Whale song remix","Ocean"),"EXCLUDED_MUSIC")
 def test_priority_terms(self):
  self.assertIsNotNone(ws5.PREFER.search("mild rain forest creek"))
  self.assertIsNone(ws5.PREFER.search("piano sample remix"))
if __name__=="__main__":unittest.main()
