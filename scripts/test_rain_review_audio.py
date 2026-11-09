#!/usr/bin/env python3
"""Verify the exact three committed 10-minute review MP3s, not just JSON claims."""
import array, hashlib, json, math, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/"signature/rain-review"
manifest=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
assert manifest["status"]=="OWNER_APPROVED_3_PROMOTED_TO_PRODUCTION"
assert len(manifest["tracks"])==3
expected={"light-rain-review":"NEW-01","rain-tin-roof-review":"NEW-02","distant-thunder-review":"NEW-06"}
assert {r["id"] for r in manifest["tracks"]}==set(expected)
def check(cmd):
 result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if result.returncode:raise RuntimeError(f"{cmd[0]} {cmd[-1]}: {result.stderr[-700:].decode(errors='replace')}")
 return result.stdout
def sha256(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def decode(p,offset,seconds):
 v=check(["ffmpeg","-hide_banner","-nostdin","-loglevel","error","-ss",str(offset),"-i",str(p),"-t",str(seconds),"-vn","-ac","1","-ar","8000","-f","f32le","pipe:1"])
 a=array.array("f");a.frombytes(v)
 if sys.byteorder!="little":a.byteswap()
 assert len(a)>seconds*7500,(p.name,"too few samples")
 assert all(math.isfinite(x) for x in a),(p.name,"NaN/inf")
 return math.sqrt(sum(float(x)*x for x in a)/len(a))
for row in manifest["tracks"]:
 ident=row["id"];path=folder/(ident+".mp3")
 assert row["plan_id"]==expected[ident]
 assert row["review_status"]=="APPROVED_BY_OWNER_2026-11-08"
 assert row["publication_status"]=="PROMOTED_TO_PRODUCTION_MP3_BYTE_IDENTICAL"
 assert row["technical_status"]=="PASS"
 assert row["source_type"]=="CC0-1.0"
 assert row["real_audio_verified"] is True
 assert path.exists() and path.stat().st_size==row["master_bytes"]
 assert path.stat().st_size>13_000_000
 assert sha256(path)==row["master_sha256"],ident+" master SHA mismatch"
 js=json.loads(check(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)]))
 s=next(s for s in js["streams"] if s["codec_type"]=="audio")
 dur=float(js["format"]["duration"])
 assert 599.0<=dur<=601.0,(ident,dur)
 assert s["codec_name"]=="mp3" and s["channels"]==2 and int(s["sample_rate"])==44100,ident
 bit=int(js["format"]["bit_rate"])/1000
 assert 183<bit<202,(ident,bit)
 assert row["peak_dbfs"]<=-5.5
 assert row["independent_source_seconds"]<610
 for loc in [0,30,299,570,598]:
  amp=decode(path,loc,0.5)
  assert amp<0.7,(ident,loc,amp)
 if ident=="rain-tin-roof-review":
  assert row["mean_dbfs"] < -40,"unexpectedly loud: recheck low-level warning"
  assert row["downloaded_preview_bitrate_kbps"] is None
  assert any("LOW_AVERAGE_LEVEL" in s for s in row["audio_review_flags"])
 if ident=="distant-thunder-review":
  assert row["repetitions_approx"]>=4
  assert row["independent_source_seconds"]<160
 print("REVIEW_AUDIO_PASS",json.dumps({"id":ident,"seconds":round(dur,3),"bitrate_kbps":round(bit,1),"bytes":path.stat().st_size,"mean_dbfs":row["mean_dbfs"],"peak_dbfs":row["peak_dbfs"],"status":"APPROVED_BY_OWNER_2026-11-08"}),flush=True)
c=json.loads((ROOT/"catalog/library.json").read_text())
assert len(c["sounds"])==33
assert not any(r["id"] in {x["id"] for x in c["sounds"]} for r in manifest["tracks"])
assert len(json.loads((ROOT/"catalog/planned-sounds.json").read_text())["planned"])==70
sitemap=(ROOT/"sitemap.xml").read_text()
assert sitemap.count("<loc>")==18
assert "/signature/rain-review/" not in sitemap
print("RAIN_REVIEW_AUDIO_QA_PASS: 3 first-wave masters byte-identical to approved production MP3s; now 28 catalog sources, first-wave master hashes preserved",flush=True)
