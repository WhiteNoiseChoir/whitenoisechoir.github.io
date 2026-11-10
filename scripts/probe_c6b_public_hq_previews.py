#!/usr/bin/env python3
"""C6B research-only. Check public Freesound HQ previews; never download authenticated originals.
No audio is committed, published, staged or approved. Partial previews stay in tempfile.
"""
from __future__ import annotations
import hashlib, html, json, re, subprocess, tempfile, urllib.request
from pathlib import Path

SOURCES = [
    {"id":"SND-0039","title":"Crickets at Night","url":"https://freesound.org/people/hargissssound/sounds/536332/","page_seconds":614.115},
    {"id":"SND-0040","title":"Morning Birds","url":"https://freesound.org/people/ali.g/sounds/855323/","page_seconds":2580.099},
]
CAP_BYTES=31_000_000
UA="Mozilla/5.0 (compatible; WhiteNoiseChoir C6B rights-and-quality-research/1.0)"
REPORT_PATH=Path("audits/c6b-public-hq-preview-probe.json")
def request(url,byte_cap):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,audio/mpeg,*/*","Range":f"bytes=0-{byte_cap-1}"})
    with urllib.request.urlopen(req,timeout=90) as r:
        data=r.read(byte_cap)
        status=r.status
        typ=r.headers.get("Content-Type","")
    return data,status,typ
def sha(b):return hashlib.sha256(b).hexdigest()
def run(args):
    return subprocess.run(args,text=True,capture_output=True,timeout=160)
def discover(p):
    raw,status,typ=request(p["url"],2_500_000)
    txt=html.unescape(raw.decode("utf-8","replace")).replace(r"\\/","/").replace(r"\u002F","/")
    if "Creative Commons 0" not in txt and "CC0" not in txt:
        raise RuntimeError("Individual source page does not visibly declare CC0; stop")
    urls=[]
    for pattern in [
        r"https?://(?:cdn\.)?freesound\.org/(?:data/)?previews/\d+/\d+_\d+-hq\.mp3",
        r"https?://(?:cdn\.)?freesound\.org/(?:data/)?previews/\d+/\d+_\d+-hq\.ogg"
    ]:
        urls += re.findall(pattern,txt,re.IGNORECASE)
    urls=list(dict.fromkeys(urls))
    if not urls:raise RuntimeError("Page did not expose a public HQ preview URL")
    if not urls[0].startswith(("https://cdn.freesound.org/previews/","https://freesound.org/data/previews/","https://freesound.org/previews/")):
        raise RuntimeError("Unexpected HQ preview origin")
    return urls[0],sha(raw),status,typ
def probe(p):
    preview_url,page_sha,status,typ=discover(p)
    with tempfile.TemporaryDirectory(prefix="c6b-source-probe-") as tmp:
        media=Path(tmp)/"public-hq-preview.mp3"
        received,hstatus,content_type=request(preview_url,CAP_BYTES)
        if len(received)<1_000_000:raise RuntimeError("HQ preview was too short/unavailable")
        media.write_bytes(received)
        meta=run(["ffprobe","-v","error","-show_entries","format=duration,bit_rate,format_name:stream=codec_name,channels,sample_rate","-of","json",str(media)])
        if meta.returncode:raise RuntimeError("Unprobeable public preview: "+meta.stderr[-250:])
        info=json.loads(meta.stdout)
        # Decode first 620 seconds rather than trusting MP3 header duration when HTTP Range truncated.
        decode=run(["ffmpeg","-hide_banner","-nostdin","-v","error","-i",str(media),"-map","0:a:0","-t","620","-f","null","-","-progress","pipe:1"])
        moments=re.findall(r"out_time=(\d+):(\d+):(\d+(?:\.\d+)?)",decode.stdout)
        decoded=max((int(h)*3600+int(m)*60+float(s) for h,m,s in moments),default=0)
        return {
            "record_id":p["id"],"title":p["title"],"source_page":p["url"],
            "page_declares_cc0":True,"page_reported_seconds":p["page_seconds"],
            "page_html_sha256":page_sha,"public_hq_preview_url":preview_url,
            "preview_only_not_authenticated_original":True,"source_is_lossy_preview":True,
            "http_status":hstatus,"http_content_type":content_type,
            "downloaded_prefix_bytes":len(received),"sha256_of_downloaded_prefix":sha(received),
            "ffprobe_format":info.get("format",{}),
            "ffprobe_streams":info.get("streams",[]),
            "decoded_first_seconds":round(decoded,3),
            "preview_proves_at_least_605_decoded_seconds":decoded>=605,
            "source_provenance_and_license_evidence":"PAGE_ONLY_NOT_BINARY_RIGHTS_AUDITED",
            "independent_unlooped_recording":"NOT_PROVABLE_FROM_PAGE_OR_BITSTREAM_DURATION",
            "acoustic_speech_unwanted_events":"NOT_REVIEWED",
            "owner_listening_approved":False,"new_audio_approved":False,
            "eligible_for_live":False,"eligible_for_index":False,
            "technical_decode_exit_code":decode.returncode,
            "decode_error_tail":decode.stderr[-650:]
        }
def main():
    results=[]
    for candidate in SOURCES:
        try:
            out=probe(candidate)
        except Exception as e:
            out={"record_id":candidate["id"],"source_page":candidate["url"],
                 "status":"SOURCE_PREVIEW_PROBE_BLOCKED","error":type(e).__name__+": "+str(e)[:450],
                 "owner_listening_approved":False,"eligible_for_live":False}
        results.append(out)
        print("C6B_RESEARCH",json.dumps(out,ensure_ascii=False),flush=True)
    REPORT_PATH.parent.mkdir(parents=True,exist_ok=True)
    REPORT_PATH.write_text(json.dumps({"stage":"RESEARCH_ONLY","records":results,
      "new_masters_created":0,"new_release_approvals":0},indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("C6B_RESEARCH_DONE",json.dumps({"count":len(results),"preview_decodable_605s":
      sum(bool(x.get("preview_proves_at_least_605_decoded_seconds")) for x in results),
      "master_mp3_created":0,"indexed":0}),flush=True)
if __name__=="__main__":main()
