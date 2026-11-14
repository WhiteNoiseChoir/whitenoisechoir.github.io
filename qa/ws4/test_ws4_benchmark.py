import importlib.util,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("ws4",ROOT/"scripts/ws4_composition_qa.py")
ws4=importlib.util.module_from_spec(spec);spec.loader.exec_module(ws4)
CASES=json.loads((ROOT/"qa/ws4/benchmark_30.json").read_text())["cases"]
class TestCompositionQA(unittest.TestCase):
 def test_manifest(self):
  self.assertEqual(len(CASES),30)
  self.assertEqual(len({c["id"] for c in CASES}),30)
  self.assertEqual({c["intent"] for c in CASES},{"sleep","relaxation"})
 def test_empty_retrieval_not_success(self):
  report=ws4.evaluate(CASES,{})
  self.assertIsNone(report["top5_relevance_proxy"])
  self.assertEqual(report["prompts_with_verified_r2_audio_pct"],0)
  self.assertEqual(len(report["failures"]),30)
 def test_verified_and_candidate_distinction(self):
  c=CASES[0]; r=ws4.evaluate([c],{c["id"]:[
   {"sound_family":"rain","composition_role":"CONTINUOUS_BED","habitat":"rainforest","r2_key":"private/key","audio_status":"verified","license":"CC-BY-4.0","sha256":"abc"},
   {"sound_family":"rain","composition_role":"CONTINUOUS_BED","habitat":"rainforest","r2_key":"private/key","audio_status":"candidate","license":"unknown","sha256":"abc"}]})
  self.assertEqual(r["top5_relevance_proxy"],1)
  self.assertEqual(r["prompts_with_verified_r2_audio_pct"],100)
  self.assertEqual(r["known_license_pct"],50)
  self.assertEqual(r["duplicate_hits"],1)
  self.assertEqual(r["per_case"][0]["unverified_r2_count"],1)
if __name__=="__main__":unittest.main()
