#!/usr/bin/env python3
"""Offline contract tests for the full-WS1/private-GitHub bridge (no R2 credentials)."""
import hashlib,importlib.util,io,json,sqlite3,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import sync_r2_ai_index_private_github as m
from botocore.exceptions import ClientError

def make_db(path):
 db=sqlite3.connect(str(path))
 db.execute("CREATE TABLE assets (id TEXT PRIMARY KEY, source_class TEXT, name TEXT, description TEXT, scientific_name TEXT, sound_family TEXT, habitat TEXT, region TEXT, provider TEXT, source_page TEXT, license TEXT, duration REAL, r2_key TEXT, tags TEXT, taxon TEXT, qa_status TEXT)")
 sha1=hashlib.sha256(b"sample0").hexdigest()
 sha2=hashlib.sha256(b"sample1").hexdigest()
 key="asset-library/raw/sha256/"+sha1[:2]+"/"+sha1+".ogg"
 rows=[
 ("nature:"+sha1,"nature","Quiet lakeshore","Gentle distant ripples","", "lake","forest","europe","Commons","https://example.org/a?token=SECRET","CC0-1.0",180,key,"water tranquil","","pending"),
 ("nature:"+sha2,"nature","Wind through trees","Breeze","", "wind","woods","europe","NPS","https://example.org/b","Public Domain",270,"asset-library/raw/sha256/"+sha2[:2]+"/"+sha2+".mp3","wind nature","","pending"),
 ("music-candidate-"+hashlib.sha256(b"music").hexdigest(),"music","Soft piano","Piano ambient","", "music","interior","","Music","https://example.org/c","CC-BY-4.0",0,"","piano sleep","","candidate_only")
 ]
 db.executemany("INSERT INTO assets VALUES ("+",".join("?" for _ in range(16))+")",rows)
 db.commit();db.close()
 return sha1,sha2,key

class FakeS3:
 def __init__(self,data):
  self.data=data
  self.exceptions=type("Exc",(),{"NoSuchKey":KeyError})
 def get_object(self,**kwargs):
  key=kwargs["Key"]
  if key=="internal/ws2-sleep-relax-enrichment/v1/source-"+self.digest[:16]+"/checkpoint.json":
   raise ClientError({"Error":{"Code":"NoSuchKey","Message":"No such key"}},"GetObject")
  return {"Body":io.BytesIO(self.data[key])}
 def download_file(self,bucket,key,dest):Path(dest).write_bytes(self.data[key])

class CanonicalIndexTests(unittest.TestCase):
 def make(self,where):
  sqlitepath=Path(where)/"canonical.sqlite"
  sha1,sha2,key=make_db(sqlitepath)
  body=sqlitepath.read_bytes()
  digest=hashlib.sha256(body).hexdigest()
  obj="internal/ai-metadata-index/v1/versions/sample.sqlite"
  manifest={"indexed_total":3,"index_r2_key":obj,"index_sha256":digest}
  fake=FakeS3({m.SOURCE:json.dumps(manifest).encode(),obj:body})
  fake.digest=digest
  return fake,sha1,sha2,key
 def test_all_ws1_classes_exported_without_audio_claims(self):
  with tempfile.TemporaryDirectory() as d:
   s3,sha1,sha2,key=self.make(d)
   old=m.MIN_ROWS,m.MIN_NATURE,m.MIN_MUSIC
   m.MIN_ROWS=3;m.MIN_NATURE=2;m.MIN_MUSIC=1
   try:
    with patch.object(m.common,"objects",return_value=[{"Key":key,"Size":4321}]):
     result=m.export(s3,d)
   finally:m.MIN_ROWS,m.MIN_NATURE,m.MIN_MUSIC=old
   self.assertEqual(result["index_unique_records"],3)
   self.assertEqual(result["source_class_counts"],{"nature":2,"music":1})
   self.assertEqual(result["availability"],{"R2_OBJECT_LISTED":1,"METADATA_ONLY":2})
   self.assertEqual(result["ws2_role_overlay"]["processed"],0)
   files=[Path(d)/p for group in result["groups"] for p in group["files"]]
   data=[json.loads(line) for file in files for line in file.read_text().splitlines()]
   self.assertEqual(len(data),3)
   lakes=next(x for x in data if x["name"]=="Quiet lakeshore")
   self.assertEqual(lakes["id"],"r2-"+sha1)
   self.assertEqual(lakes["source_url"],"https://example.org/a")
   self.assertEqual(lakes["playback"],"UNVERIFIED")
   self.assertEqual(lakes["sleep_suitability"],"UNVERIFIED")
   self.assertEqual(lakes["rights"],"LICENSE_DECLARED_REVIEW")
   wind=next(x for x in data if x["name"]=="Wind through trees")
   self.assertEqual(wind["availability"],"METADATA_ONLY")
   self.assertIsNone(wind["r2_key"])
   music=next(x for x in data if x["class"]=="music")
   self.assertEqual(music["availability"],"METADATA_ONLY")
   self.assertNotIn("SECRET","".join(x.read_text() for x in files))
 def test_reject_broken_index_sha(self):
  with tempfile.TemporaryDirectory() as d:
   s3,_,__,key=self.make(d)
   manifest=json.loads(s3.data[m.SOURCE])
   manifest["index_sha256"]="f"*64
   s3.data[m.SOURCE]=json.dumps(manifest).encode()
   with self.assertRaisesRegex(RuntimeError,"SHA mismatch"):
    m.export(s3,d)
 def test_ws2_overlay_integrity(self):
  digest="a"*64
  class S:
   def get_object(self,**kwargs):
    key=kwargs["Key"]
    if key.endswith("checkpoint.json"):
     data={"source_index_sha256":digest,"processed":500,"errors":0}
    else:
     data={"schema":"wnc_ws2_batch_v1","source_index_sha256":digest,"offset":0,"records":[
       {"id":"nature:"+str(i),"composition":{"role_hint":"CONTINUOUS_BED"}} for i in range(500)]}
    return {"Body":io.BytesIO(json.dumps(data).encode())}
  hints,state=m.ws2_roles(S(),digest,1000)
  self.assertEqual(len(hints),500)
  self.assertEqual(state["status"],"PARTIAL")
  self.assertEqual(hints["nature:499"],"CONTINUOUS_BED")
 def test_public_repo_guard_precedes_r2_access(self):
  class Response:
   status_code=200
   def json(self):return {"private":False}
  with patch.dict("os.environ",{"WNC_METADATA_REPO_TOKEN":"TEST_FAKE"},clear=True):
   with patch.object(m.requests,"get",return_value=Response()):
    with self.assertRaisesRegex(RuntimeError,"SECURITY BLOCK"):
     m.main()
if __name__=="__main__":unittest.main()
