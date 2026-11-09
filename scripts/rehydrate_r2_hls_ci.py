#!/usr/bin/env python3
"""Restore missing, *SHA-1 Git-blob pinned* HLS objects from R2 into CI workspace.

Never commits restored objects; public read-only HTTP GET, no credentials.
Network bytes are hashed with exact Git blob framing "blob {bytes}\0" before use.
Used by historical acoustic/regression QA after removing duplicate GH HLS media.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
LEDGER=json.loads((ROOT/"audits/r2-hls-immutable-source-inventory.json").read_text())
REMOTE="https://media.whitenoisechoir.com/"
KEEP={"white-noise","pink-noise","brown-noise","rain-on-window-real",
      "box-fan-real","heavy-rain-real","ocean-waves-real","waterfall-real"}
assert len(LEDGER["files"])==360
assert LEDGER["retirable_bytes"]==514374326
GROUPS={x["path"].split("/")[2] for x in LEDGER["files"]}
assert len(GROUPS)==35 and KEEP.issubset(GROUPS)
RETIRE=GROUPS-KEEP
assert len(RETIRE)==27
def git_sha(path,expected_size):
 h=hashlib.sha1()
 h.update(f"blob {expected_size}\0".encode())
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):
   h.update(chunk)
 return h.hexdigest()

def fetch(entry):
 path=entry["path"]
 if not path.startswith("audio/continuous/") or ".." in path:
  raise AssertionError("Unsafe ledger path: "+path)
 target=ROOT/path
 expected=entry["size"]
 sha=entry["git_blob_sha1"]
 if target.is_file():
  assert target.stat().st_size==expected and git_sha(target,expected)==sha,"LOCAL_HLS_SHA_MISMATCH "+path
  return ("preserved",expected,path)
 target.parent.mkdir(parents=True,exist_ok=True)
 temp=Path(str(target)+".r2-ci-part")
 for retry in range(4):
  try:
   request=Request(REMOTE+path,headers={"User-Agent":"WNC-Verified-CI-HLS-Rehydration/1.0"})
   with urlopen(request,timeout=120) as stream, temp.open("wb") as output:
    ctype=(stream.headers.get("Content-Type") or "").split(";")[0]
    assert ctype==("video/mp2t" if path.endswith(".ts") else "application/vnd.apple.mpegurl"),"MIME "+path
    length=int(stream.headers.get("Content-Length","0"))
    assert length==expected,"Remote HLS size changed: "+path
    total=0
    while True:
     chunk=stream.read(1024*1024)
     if not chunk:break
     output.write(chunk);total+=len(chunk)
   assert total==expected,"Remote content truncated "+path
   assert git_sha(temp,expected)==sha,"REMOTE HLS CONTENT SHA MISMATCH "+path
   os.replace(temp,target)
   return ("rehydrated",expected,path)
  except (HTTPError,URLError,TimeoutError) as e:
   temp.unlink(missing_ok=True)
   if retry==3:raise
   time.sleep(1+retry*2)
  except BaseException:
   temp.unlink(missing_ok=True)
   raise
 raise AssertionError("download retry exhaustion "+path)

def main():
 only={x.strip() for x in os.environ.get("WNC_REHYDRATE_IDS","").split(",") if x.strip()}
 assert not only or only.issubset(GROUPS),"Unexpected source IDs in hydration scope"
 data=[x for x in LEDGER["files"] if not only or x["path"].split("/")[2] in only]
 expected_bytes=sum(x["size"] for x in data)
 with ThreadPoolExecutor(max_workers=6) as pool:
  results=list(pool.map(fetch,data))
 assert len(results)==len(data)
 assert sum(x[1] for x in results)==expected_bytes
 d={"total":len(results),"preserved":sum(x[0]=="preserved" for x in results),
    "rehydrated":sum(x[0]=="rehydrated" for x in results),
    "total_bytes":sum(x[1] for x in results),
    "source_count":len(only) if only else len(GROUPS),
    "temporary_ci_only":True}
 print("R2_HLS_CI_REHYDRATION_SHA_PASS",json.dumps(d,sort_keys=True),flush=True)
if __name__=="__main__":main()
