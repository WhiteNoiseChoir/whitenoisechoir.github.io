#!/usr/bin/env python3
"""Offline correctness gates for the Commons CC0 bulk ingestion filter."""
from __future__ import annotations
import sys
sys.path.insert(0,"scripts")
import harvest_commons_cc0_to_r2 as h
def page(license_name="CC0",license_url="https://creativecommons.org/publicdomain/zero/1.0/",size=120000,mime="audio/ogg",filename="Example.ogg"):
 return {"title":"File:"+filename,"imageinfo":[{
  "url":"https://upload.wikimedia.org/wikipedia/commons/1/11/Example.ogg",
  "descriptionurl":"https://commons.wikimedia.org/wiki/File:Example.ogg",
  "mime":mime,"size":size,
  "extmetadata":{"LicenseShortName":{"value":license_name},
   "LicenseUrl":{"value":license_url},"Artist":{"value":"Sound recordist"}}}]}
good=h.decide(page(),"nature",1000000)
assert good["state"]=="ELIGIBLE",good
assert good["source_license"]=="CC0-1.0"
assert good["rights_evidence_url"].startswith("https://commons.wikimedia.org/wiki/")
assert h.decide(page("CC BY 4.0","https://creativecommons.org/licenses/by/4.0/"),"nature",1000000)["state"]=="SKIP_LICENSE_NOT_CC0"
assert h.decide(page("CC BY-NC 4.0","https://creativecommons.org/licenses/by-nc/4.0/"),"nature",1000000)["state"]=="SKIP_LICENSE_NOT_CC0"
assert h.decide(page(size=100000000),"nature",1000000)["state"]=="SKIP_SIZE_LIMIT"
assert h.decide(page(mime="image/jpeg"),"nature",1000000)["state"]=="SKIP_NOT_AUDIO"
assert h.decide(page(filename="Cat.jpg"),"nature",1000000)["state"]=="SKIP_NOT_SUPPORTED_AUDIO"
blocked=page()
blocked["imageinfo"][0]["extmetadata"]["Restrictions"]={"value":"Personality rights"}
assert h.decide(blocked,"nature",1000000)["state"]=="SKIP_RESTRICTIONS"
print("COMMONS_CC0_INTAKE_FILTER_TEST_PASS — CC0 only; no CC-BY/NC, images, large files or restricted files")
