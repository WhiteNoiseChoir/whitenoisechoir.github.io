#!/usr/bin/env python3
"""Research-only: inspect public CC0 long-recording preview availability.
Does not publish or modify master audio, previews or manifests.
"""
from __future__ import annotations
import html, json, re, subprocess, tempfile
from pathlib import Path
from urllib.request import Request, urlopen

CANDIDATES = [
 ("heavy-rain", "https://freesound.org/people/Valerie-Vivegnis/sounds/759545/", 597.14),
 ("ocean-waves", "https://freesound.org/people/hotemogf/sounds/635403/", 2719.349),
 ("ocean-waves-optional", "https://freesound.org/people/hotemogf/sounds/635404/", 707.004),
]
UA="Mozilla/5.0 (compatible; WhiteNoiseChoir-Source-Review/1.0; no production edits)"

def read(url, maxbytes=8_000_000):
    with urlopen(Request(url,headers={"User-Agent":UA}),timeout=60) as resp:
        return resp.read(maxbytes)

def probe(name,url,reported):
    raw=read(url,3_000_000).decode("utf-8","replace")
    rendered=html.unescape(raw).replace(r"\/", "/").replace(r"\u002F","/")
    cc0=("Creative Commons 0" in rendered or "cc0" in rendered.lower())
    patterns=[
        r"https?://(?:cdn\.)?freesound\.org/(?:data/)?previews/\d+/\d+_\d+-hq\.mp3",
        r"https?://(?:cdn\.)?freesound\.org/(?:data/)?previews/\d+/\d+_\d+-hq\.ogg",
        r"https?://(?:cdn\.)?freesound\.org/(?:data/)?previews/\d+/\d+_\d+-lq\.mp3",
    ]
    found=[]
    for p in patterns:
        for match in re.findall(p,rendered,re.IGNORECASE):
            if match not in found:found.append(match)
    result={"id":name,"source_page":url,"page_claims_cc0":cc0,"reported_duration_seconds":reported,
            "discovered_preview_urls":found[:5],"stage":"SOURCE_PREVIEW_PROBE_NOT_APPROVAL"}
    if cc0 and found:
        with tempfile.TemporaryDirectory() as tmp:
            local=Path(tmp)/"preview.bin"
            data=read(found[0],80_000_000)
            local.write_bytes(data)
            meta=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,bit_rate",
                                 "-of","json",str(local)],capture_output=True,text=True)
            result["bytes_received"]=len(data)
            result["ffprobe_status"]=meta.returncode
            if meta.returncode==0:
                d=json.loads(meta.stdout).get("format",{})
                result["preview_decoded_seconds"]=round(float(d.get("duration",0)),3)
                result["preview_bitrate"]=d.get("bit_rate")
            else:result["error"]=meta.stderr[-400:]
    print("CC0_PROBE",json.dumps(result,ensure_ascii=False),flush=True)
    return result

results=[]
for name,url,dur in CANDIDATES:
    try:results.append(probe(name,url,dur))
    except Exception as exc:
        fail={"id":name,"source_page":url,"error":type(exc).__name__+": "+str(exc)[:350],"stage":"SOURCE_PREVIEW_UNAVAILABLE"}
        print("CC0_PROBE",json.dumps(fail),flush=True)
        results.append(fail)
print("PROBE_DONE",json.dumps({"count":len(results),"available":sum(bool(x.get("preview_decoded_seconds",0)>300) for x in results),"note":"No audio was promoted, no output files were published"}),flush=True)
