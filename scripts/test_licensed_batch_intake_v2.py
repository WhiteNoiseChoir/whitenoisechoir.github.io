#!/usr/bin/env python3
"""Offline contract tests for CC0 / CC BY candidate evidence, R2 sidecars and no automatic publication approval."""
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("harvest",ROOT/"scripts"/"harvest_commons_cc0_to_r2.py")
harvest=importlib.util.module_from_spec(spec)
spec.loader.exec_module(harvest)

def entry(short,url,restrictions=""):
    return {"title":"File:Gentle_rain.ogg","imageinfo":[{
       "mime":"audio/ogg","size":4096,"url":"https://upload.wikimedia.org/wikipedia/commons/gentle_rain.ogg",
       "descriptionurl":"https://commons.wikimedia.org/wiki/File:Gentle_rain.ogg","user":"CreatorOwnWork",
       "extmetadata":{"LicenseShortName":{"value":short},"LicenseUrl":{"value":url},
          "Artist":{"value":"CreatorOwnWork"},"Attribution":{"value":"CreatorOwnWork — gentle rain"},
          "Restrictions":{"value":restrictions}}}]}

class FakeS3:
    def __init__(self):self.objects={}
    def head_object(self,Bucket,Key):
        if Key not in self.objects:
            from botocore.exceptions import ClientError
            raise ClientError({"Error":{"Code":"404","Message":"Not Found"}},"HeadObject")
        o=self.objects[Key];return {"ContentLength":len(o["bytes"]),"Metadata":o["Metadata"]}
    def put_object(self,**kw):
        body=kw["Body"]
        if hasattr(body,"read"):body=body.read()
        self.objects[kw["Key"]]={"bytes":body,"Metadata":kw.get("Metadata",{}),"CacheControl":kw.get("CacheControl","")}
        return {"ETag":"not-real"}
class LicensedIntakeTest(unittest.TestCase):
    def test_cc_by_is_separately_enabled_and_restrictions_are_observed(self):
        page=entry("CC BY 4.0","https://creativecommons.org/licenses/by/4.0/")
        self.assertNotEqual(harvest.decide(page,"rain",8192)["state"],"ELIGIBLE")
        good=harvest.decide(page,"rain",8192,allow_cc_by=True)
        self.assertEqual(good["state"],"ELIGIBLE")
        self.assertEqual(good["source_license"],"CC-BY-4.0")
        self.assertEqual(good["attribution"],"CreatorOwnWork — gentle rain")
        blocked=harvest.decide(entry("CC BY-NC 4.0","https://creativecommons.org/licenses/by-nc/4.0/"),"rain",8192,allow_cc_by=True)
        self.assertNotEqual(blocked["state"],"ELIGIBLE")
        blocked=harvest.decide(entry("CC BY-ND 4.0","https://creativecommons.org/licenses/by-nd/4.0/"),"rain",8192,allow_cc_by=True)
        self.assertNotEqual(blocked["state"],"ELIGIBLE")
        blocked=harvest.decide(entry("CC BY 4.0","https://creativecommons.org/licenses/by/4.0/","No commercial use"),"rain",8192,allow_cc_by=True)
        self.assertEqual(blocked["state"],"SKIP_RESTRICTIONS")
    def test_cc0_is_permitted_without_cc_by_flag(self):
        r=harvest.decide(entry("CC0 1.0","https://creativecommons.org/publicdomain/zero/1.0/"),"rain",8192)
        self.assertEqual(r["source_license"],"CC0-1.0")
        self.assertEqual(r["state"],"ELIGIBLE")
    def test_r2_sidecar_never_mislabels_by_as_cc0_or_publication_approved(self):
        row=harvest.decide(entry("CC BY 4.0","https://creativecommons.org/licenses/by/4.0/"),"rain",8192,allow_cc_by=True)
        s3=FakeS3()
        old=(harvest.PREFIX,harvest.RECORDS_PREFIX,harvest.PRIVATE_STAGING)
        harvest.PREFIX="internal/licensed-batch/v1/sha256/"
        harvest.RECORDS_PREFIX="internal/licensed-batch/v1/records/"
        harvest.PRIVATE_STAGING=True
        try:
            with tempfile.TemporaryDirectory() as d:
                f=pathlib.Path(d)/"source.ogg"
                blob=b"A"*4096; f.write_bytes(blob);sha=hashlib.sha256(blob).hexdigest()
                r=harvest.upload(s3,row,f,len(blob),sha,12,{"codec_name":"vorbis","sample_rate":"44100","channels":2})
            obj=s3.objects[r["storage_key"]]
            self.assertEqual(obj["Metadata"]["license"],"cc-by-4.0")
            self.assertEqual(obj["CacheControl"],"private, no-store")
            self.assertTrue(r["storage_key"].startswith("internal/licensed-batch/"))
            sidecar=json.loads(s3.objects[r["metadata_storage_key"]]["bytes"])
            self.assertEqual(sidecar["license"],"CC-BY-4.0")
            self.assertEqual(sidecar["attribution"],"CreatorOwnWork — gentle rain")
            self.assertFalse(sidecar["ready_for_mixer"])
            self.assertFalse(sidecar["publicationApproved"])
        finally:
            harvest.PREFIX,harvest.RECORDS_PREFIX,harvest.PRIVATE_STAGING=old
if __name__=="__main__":unittest.main()
