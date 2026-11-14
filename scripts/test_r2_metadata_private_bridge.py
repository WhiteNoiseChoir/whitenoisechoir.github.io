#!/usr/bin/env python3
"""Offline safety tests: no R2 credentials, no GitHub access or private data."""
import importlib.util
import io
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("sync_bridge",ROOT/"scripts/sync_r2_metadata_private_github.py")
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

class FakePager:
    def paginate(self,**kwargs):
        prefix=kwargs["Prefix"]
        if prefix.startswith("asset-library/raw/sha256/"):
            keys=[{"Key":f"asset-library/raw/sha256/{h[:2]}/{h}.ogg","Size":123456} for h in FakeS3.hashes]
        elif prefix=="asset-library/records/sha256/":
            keys=[{"Key":f"asset-library/records/sha256/{h[:2]}/{h}.json","Size":500} for h in FakeS3.hashes]
        else:keys=[]
        return [{"Contents":keys}]
class FakeS3:
    hashes=[hashlib.sha256(str(x).encode()).hexdigest() for x in range(125)]
    def get_paginator(self,name):
        assert name=="list_objects_v2"
        return FakePager()
    def get_object(self,**kwargs):
        h=kwargs["Key"].rsplit("/",1)[-1].replace(".json","")
        doc={"audio_sha256":h,"title":"Quiet lake pines","source_page":"https://example.org/sound?token=SECRET",
             "group_hint":"lake","duration_seconds":230,"license":"CC0-1.0","audio_storage_key":f"asset-library/raw/sha256/{h[:2]}/{h}.ogg"}
        return {"Body":io.BytesIO(json.dumps(doc).encode())}

class ExportTests(unittest.TestCase):
    def test_redact_query_and_https(self):
        self.assertEqual(m.safe_url("https://example.org/file?token=SECRET#frag"),"https://example.org/file")
        self.assertEqual(m.safe_url("http://unsafe.net/a"),"")
        self.assertEqual(m.safe_url("https://user:password@example.org/a"),"")
    def test_r2_not_playback_or_rights_claim(self):
        h="a"*64
        x=m.make_row({"audio_sha256":h,"title":"lake","group_hint":"water","license":"CC0-1.0"},h,{h:[{"key":"asset-library/raw/sha256/aa/"+h+".wav","bytes":4000}]})
        self.assertEqual(x["availability"],"R2_OBJECT_LISTED")
        self.assertEqual(x["playback"],"NOT_VERIFIED_BY_INDEX")
        self.assertEqual(x["rights"],"LICENSE_DECLARED_REVIEW")
        self.assertEqual(x["id"],"r2-"+h)
    def test_missing_object_candidate_not_fake_asset(self):
        h="c"*64
        x=m.make_row({"audio_sha256":h,"title":"sound"},h,{})
        self.assertEqual(x["availability"],"METADATA_ONLY")
        self.assertEqual(x["id"],"candidate-"+h)
        self.assertIsNone(x["r2_key"])
    def test_private_shards_and_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            manifest=m.build(FakeS3(),root)
            self.assertEqual(manifest["index_unique_records"],125)
            self.assertEqual(manifest["r2_unique_sha_object_names"],125)
            self.assertEqual(manifest["availability"]["R2_OBJECT_LISTED"],125)
            self.assertEqual(len(manifest["groups"]),1)
            target=Path(root)/"index/groups/lake/part-001.jsonl"
            data=target.read_text()
            self.assertEqual(len(data.splitlines()),125)
            self.assertNotIn("SECRET",data)
            self.assertEqual(json.loads(data.splitlines()[0])["playback"],"NOT_VERIFIED_BY_INDEX")
    def test_snapshot_noop_only_if_rows_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"staging";b=Path(d)/"remote"
            for root in (a,b):
                (root/"groups/nature").mkdir(parents=True)
                (root/"groups/nature/part-001.jsonl").write_text('{"id":"nature:abc"}\n')
            (a/"manifest.json").write_text(json.dumps({"schema_version":2,"generated_utc":"T2","ws2_role_overlay":{"processed":1000}}))
            (b/"manifest.json").write_text(json.dumps({"schema_version":2,"generated_utc":"T1","ws2_role_overlay":{"processed":1000}}))
            self.assertTrue(m.snapshot_unchanged(a,b))
            (a/"groups/nature/part-001.jsonl").write_text('{"id":"nature:changed"}\n')
            self.assertFalse(m.snapshot_unchanged(a,b))
            (a/"groups/nature/part-001.jsonl").write_text('{"id":"nature:abc"}\n')
            (a/"manifest.json").write_text(json.dumps({"schema_version":2,"generated_utc":"T2","ws2_role_overlay":{"processed":1500}}))
            self.assertFalse(m.snapshot_unchanged(a,b))
    def test_public_destination_rejected_before_git_clone(self):
        class R:
            status_code=200
            def json(self):return {"private":False,"full_name":m.DEST,"default_branch":"main"}
        with patch.dict("sys.modules",{}):
            with patch("requests.get",return_value=R()):
                with self.assertRaisesRegex(RuntimeError,"SAFETY BLOCK"):
                    m.publish("/tmp/will-not-be-read","dummy-token")

if __name__=="__main__":unittest.main()
