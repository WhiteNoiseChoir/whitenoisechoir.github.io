#!/usr/bin/env python3
"""Run a strict public R2 custom-domain CORS, Range, MIME and byte check.

Read only: makes no changes to Cloudflare, GitHub or production player.
"""
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE="https://media.whitenoisechoir.com"
ORIGINS=("https://whitenoisechoir.github.io",
         "https://whitenoisechoir.com",
         "https://www.whitenoisechoir.com")
FILES=(
 ("audio/white-noise.mp3","audio/mpeg"),
 ("audio/continuous/white-noise/continuous.m3u8","application/vnd.apple.mpegurl"),
 ("audio/continuous/white-noise/part_000.ts","video/mp2t"),
 ("audio/crashing-ocean-real.mp3","audio/mpeg"),
 ("audio/continuous/crashing-ocean-real/continuous.m3u8","application/vnd.apple.mpegurl"),
 ("audio/continuous/crashing-ocean-real/part_009.ts","video/mp2t"),
)
ROOT=Path(__file__).resolve().parents[1]
total=0
for origin in ORIGINS:
 for key,mime in FILES:
  # Unique query prevents a cached pre-CORS copy from masking the new policy.
  url=f"{BASE}/{key}?wnc-cors-qa=20261109-v2"
  request=Request(url,headers={
      "Origin":origin,"Range":"bytes=0-2047",
      "User-Agent":"WNC-R2-CORS-Transport-QA/1.0"})
  try:
   with urlopen(request,timeout=45) as res:
    status=res.status
    headers={k.lower():v for k,v in res.headers.items()}
    data=res.read()
  except HTTPError as e:
   raise AssertionError(f"HTTP {e.code} for {origin} {key}") from e
  cors=headers.get("access-control-allow-origin")
  print("R2_CORS_OBSERVED",json.dumps({
      "origin":origin,"key":key,"http":status,
      "allow_origin":cors,"mime":headers.get("content-type"),
      "range":headers.get("content-range"),"bytes_received":len(data),
      "cache":headers.get("cf-cache-status")
  }),flush=True)
  assert status==206,(origin,key,"HTTP Range returned",status)
  assert cors==origin,(origin,key,"CORS missing or mismatched:",cors)
  assert headers.get("content-type","").split(";")[0]==mime,(origin,key,"MIME",headers.get("content-type"))
  assert headers.get("content-range","").startswith("bytes 0-2047/"),(origin,key,"Content-Range")
  assert data==(ROOT/key).read_bytes()[:2048],(origin,key,"Data does not match source")
  total+=1
# Block all unknown origins from reading by JS CORS; non-browser HTTP remains public by design.
bad=Request(BASE+"/audio/white-noise.mp3?wnc-cors-qa=20261109-negative",headers={
 "Origin":"https://example.invalid","Range":"bytes=0-2047"})
try:
 with urlopen(bad,timeout=45) as resp:
  assert resp.headers.get("Access-Control-Allow-Origin") not in ["*","https://example.invalid"],"Unexpected public cross-origin permissions"
  assert resp.status==206
except HTTPError as error:
 assert error.code in (403,404),"Unexpected deny response for foreign origin: "+str(error.code)
 assert error.headers.get("Access-Control-Allow-Origin") not in ["*","https://example.invalid"],"Foreign origin was allowed"
 print("R2_FOREIGN_ORIGIN_DENIED",json.dumps({"http":error.code}),flush=True)
print("R2_CORS_TRANSPORT_PASS",json.dumps({
 "requests":total,"origins":list(ORIGINS),
 "sampled_objects":len(FILES),"range":"0-2047",
 "original_mp3_hls_unmodified":True}),flush=True)
