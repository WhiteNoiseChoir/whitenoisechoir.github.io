#!/usr/bin/env python3
"""Public HTTP/CORS and browser-source QA for six imported Studio MP3s."""
from __future__ import annotations
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.request import Request,urlopen

ORIGIN="https://whitenoisechoir.com"
PUBLIC="https://media.whitenoisechoir.com/"
SOURCES={
12:"asset-library/raw/sha256/ea/ea2144a09b42a4e518fc83e3c1dc60de138029dec1cc8455ee2fb31884701c17.mp3",
13:"asset-library/raw/sha256/d5/d511520722dfdd79808d45f086c39b1b729282894800bf0dfac671297639d492.mp3",
56:"asset-library/raw/sha256/17/176d4ecdd1df7bc2aa50a36ee214b2e5e909782e262c52ce0c737a760a2b996b.mp3",
57:"asset-library/raw/sha256/3d/3d8cf3647f724dc7e1524268c1767dd3bce61bd89ab88db8fa2371f044aa398c.mp3",
59:"asset-library/raw/sha256/cf/cff22b830848d519235922ad438f026d3fa8b0607dfab6c7e912324057c22e98.mp3",
60:"asset-library/raw/sha256/68/682ff4846f4ada10371bd7e9481d55aeea4b66c5191146a3182524a3d94624e7.mp3",
105:"asset-library/studio-loop/sha256/be/be28cfade62766d75b4e7efb7e439540b4ee79633fe024ad3a727d9dd5575227.mp3",
106:"asset-library/studio-loop/sha256/53/5352c5e4d9f5c06dc0809625aecb528c07df10360327bec7cb2e8e1d37d0defe.mp3",
109:"asset-library/studio-loop/sha256/fa/fa83a81dfe7ff995e107cd7f4f716343725347e66d970dd91964460faceb208a.mp3",
131:"asset-library/studio-loop/sha256/63/636a28c6a8d3350c906a635aa5bec8bdf72b015a885bd4da360924bad1db8334.mp3",
135:"asset-library/studio-loop/sha256/5b/5be9a18fc851d8d0a51a4bacecb3bd9d60135f84bf7efbcab7373d7c9e00588b.mp3",
141:"asset-library/studio-loop/sha256/ee/eed2cf72da87123b94bfc6388ac2ebe5395f2137aaebed9e2f4ac27bb4ab30b7.mp3",
1:"asset-library/raw/sha256/0a/0a3c133128b94306396567cfc22ded8363645869d762c2bbc76b5c3519017cff.m4a"
}

def check(id:int,key:str):
    address=PUBLIC+key
    req=Request(address,headers={
      "Origin":ORIGIN,"Range":"bytes=0-2047",
      "User-Agent":"WhiteNoiseChoir-Studio-QA/1.0"
    })
    with urlopen(req,timeout=45) as r:
      status=r.status
      data=r.read(2048)
      mime=r.headers.get("Content-Type","")
      allow=r.headers.get("Access-Control-Allow-Origin","")
      range_header=r.headers.get("Content-Range","")
    if status!=206:raise RuntimeError(f"HTTP {status}, expected HTTP 206 Range")
    if len(data)!=2048:raise RuntimeError("Incorrect byte range response")
    if not ("audio/" in mime or "application/octet-stream" in mime):
      raise RuntimeError("Invalid audio Content-Type "+mime)
    if allow not in ("*",ORIGIN):
      raise RuntimeError("CORS missing or incorrect: Access-Control-Allow-Origin="+repr(allow))
    report={"id":id,"key":key,"status":"PASS","http":status,"range":range_header,"mime":mime,"cors":allow}
    print("STUDIO_BROWSER_PUBLIC_QA "+json.dumps(report),flush=True)
    return report

def frog_loudness():
    key=SOURCES[1]
    with tempfile.TemporaryDirectory() as td:
      path=Path(td)/"frog.m4a"
      req=Request(PUBLIC+key,headers={"User-Agent":"WhiteNoiseChoir-Studio-QA/1.0"})
      with urlopen(req,timeout=45) as response, path.open("wb") as file:
        while True:
          data=response.read(65536)
          if not data:break
          file.write(data)
          if file.tell()>20*1024*1024:raise RuntimeError("Unexpectedly large frog m4a")
      p=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-i",str(path),"-af","volumedetect",
         "-f","null","-"],capture_output=True,text=True,timeout=55)
      if p.returncode:raise RuntimeError("frog source decode failure: "+p.stderr[-400:])
      mean=re.findall(r"mean_volume:\s*([-\d.]+) dB",p.stderr)
      peak=re.findall(r"max_volume:\s*([-\d.]+) dB",p.stderr)
      report={"id":1,"sound":"Existing in-house frog iNaturalist 11.865 s",
        "mean_dbfs":float(mean[-1]) if mean else None,
        "max_dbfs":float(peak[-1]) if peak else None,"bytes":path.stat().st_size}
      print("STUDIO_FROG_VOLUME_QA "+json.dumps(report),flush=True)

def main():
    good=[];errors=[]
    for ident,key in SOURCES.items():
      try:good.append(check(ident,key))
      except Exception as exc:
        error={"id":ident,"error":str(exc)}
        print("STUDIO_BROWSER_PUBLIC_QA_ERROR "+json.dumps(error),flush=True)
        errors.append(error)
    try:frog_loudness()
    except Exception as exc:print("STUDIO_FROG_VOLUME_QA_WARNING "+str(exc),flush=True)
    print("STUDIO_BROWSER_QA_SUMMARY "+json.dumps({"passed":len(good),"failed":len(errors),"errors":errors}),flush=True)
    if errors:raise SystemExit(1)

if __name__=="__main__":main()
