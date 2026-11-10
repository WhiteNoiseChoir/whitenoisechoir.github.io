#!/usr/bin/env python3
"""C6B: produce NON-PRODUCTION 600s MP3 review artifacts from public CC0 HQ previews.

The original Freesound WAV/MP3 downloads require login and are NOT claimed acquired.
This tool never commits files, touches R2, changes release ledgers, or unlocks URLs.
Full-file rights, spoken events, source originality, A/B dedup and owner listening remain pending.
"""
from __future__ import annotations
import hashlib, html, json, re, subprocess, tempfile, urllib.parse, urllib.request
from pathlib import Path

SOURCES = [
  {"id": "SND-0039", "title": "Crickets at Night",
   "page": "https://freesound.org/people/hargissssound/sounds/536332/"},
  {"id": "SND-0040", "title": "Morning Birds",
   "page": "https://freesound.org/people/ali.g/sounds/855323/"},
]
OUT = Path("audits/c6b-audition-artifacts")
USER_AGENT = "Mozilla/5.0 (compatible; WhiteNoiseChoir-C6B-nonproduction-review/1.0)"
CAP_BYTES = 31_000_000
def digest(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()
def hash_file(p: Path) -> str:
  h=hashlib.sha256()
  with p.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1048576), b""): h.update(chunk)
  return h.hexdigest()
def fetch(url: str, cap: int):
  parsed=urllib.parse.urlparse(url)
  if parsed.scheme != "https" or parsed.hostname not in ("freesound.org", "cdn.freesound.org"):
    raise RuntimeError("Unapproved media host: " + parsed.netloc)
  req=urllib.request.Request(url, headers={
    "User-Agent": USER_AGENT, "Accept": "text/html,audio/mpeg,*/*",
    "Range": "bytes=0-" + str(cap-1)})
  with urllib.request.urlopen(req, timeout=95) as resp:
    if urllib.parse.urlparse(resp.url).hostname not in ("freesound.org", "cdn.freesound.org"):
      raise RuntimeError("Media redirect left Freesound host allowlist")
    data=resp.read(cap)
    status=resp.status
    content_type=resp.headers.get("Content-Type","")
  return data, status, content_type
def run(args, timeout=190):
  return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
def probe_duration(p):
  z=run(["ffprobe","-v","error","-show_entries",
    "format=duration,format_name:stream=codec_name,channels,sample_rate",
    "-of","json",str(p)],90)
  if z.returncode: raise RuntimeError("ffprobe failed: " + z.stderr[-350:])
  return json.loads(z.stdout)
def preview_link(page):
  raw, _, _=fetch(page,2_500_000)
  text=html.unescape(raw.decode("utf8","replace")).replace(r"\/","/").replace(r"\u002F","/")
  if "Creative Commons 0" not in text and "CC0" not in text:
    raise RuntimeError("No CC0 declaration visible on individual Freesound page")
  links=re.findall(r"https?://(?:cdn\.)?freesound\.org/(?:data/)?previews/\d+/\d+_\d+-hq\.(?:mp3|ogg)",text,re.I)
  if not links: raise RuntimeError("No publicly accessible HQ preview reference in page")
  return links[0],digest(raw)
def decode_seconds(path):
  cmd=["ffmpeg","-hide_banner","-nostdin","-v","error","-progress","pipe:1",
    "-i",str(path),"-map","0:a:0","-t","607","-f","null","-"]
  r=run(cmd,190)
  times=re.findall(r"out_time=(\d+):(\d+):(\d+(?:\.\d+)?)",r.stdout)
  seconds=max((3600*int(h)+60*int(m)+float(s) for h,m,s in times),default=0)
  if r.returncode or seconds < 605:
    raise RuntimeError("Actual decoded public preview <605s or FFmpeg failed: "+
      str(round(seconds,2))+" seconds; "+r.stderr[-350:])
  return round(seconds,3)
def prepare(item):
  preview_url,page_sha=preview_link(item["page"])
  # Caps come from previously decoded HQ-preview bitrate: SND-0039 ~185 kbps (entire file 14.17 MB),
  # SND-0040 reports ~96 kbps in the header but empirical 10MB decoded only 434.86 s.
  # Require an actual >=605s decode; 17MB includes a safety margin for variable bitrate.
  cap_by_id={"SND-0039":16_000_000,"SND-0040":17_000_000}
  preview_bytes,status,ct=fetch(preview_url,cap_by_id[item["id"]])
  if len(preview_bytes)<1_000_000: raise RuntimeError("Public HQ preview unavailable or too short")
  with tempfile.TemporaryDirectory(prefix="wnc-c6b-review-") as folder:
    f=Path(folder)/("preview."+("ogg" if preview_url.lower().endswith(".ogg") else "mp3"))
    f.write_bytes(preview_bytes)
    info=probe_duration(f)
    decoded=decode_seconds(f)
    target=OUT/(item["id"]+".mp3")
    encode=run(["ffmpeg","-hide_banner","-nostdin","-v","error","-xerror",
      "-i",str(f),"-map","0:a:0","-t","600",
      "-ar","44100","-ac","2","-c:a","libmp3lame","-b:a","192k",
      "-y",str(target)],190)
    if encode.returncode:
      raise RuntimeError("Review MP3 encode failed: "+encode.stderr[-350:])
  master_info=probe_duration(target)
  seconds=float(master_info.get("format",{}).get("duration",0))
  if not 599 <= seconds <= 601:
    target.unlink(missing_ok=True)
    raise RuntimeError("Master duration out of bounds: "+str(seconds))
  stream=master_info.get("streams",[{}])[0]
  if stream.get("codec_name")!="mp3" or int(stream.get("channels",0))!=2 or int(stream.get("sample_rate",0))!=44100:
    target.unlink(missing_ok=True)
    raise RuntimeError("Master codec/channel/sample rate verification failed")
  return {
    "record_id":item["id"],"title":item["title"],
    "status":"REVIEW_MP3_STAGED_IN_ACTION_ARTIFACT_NOT_RELEASED",
    "source_page":item["page"],"page_declares_cc0":True,
    "page_html_sha256":page_sha,"public_hq_preview_url":preview_url,
    "freesound_authenticated_original_downloaded":False,
    "source_is_lossy_public_preview":True,
    "http_status":status,"http_content_type":ct,
    "downloaded_preview_prefix_bytes":len(preview_bytes),
    "sha256_of_downloaded_preview_prefix":digest(preview_bytes),
    "verified_decoded_first_seconds":decoded,
    "review_mp3_filename":target.name,
    "review_mp3_sha256":hash_file(target),
    "review_mp3_duration_seconds":round(seconds,3),
    "review_mp3_bytes":target.stat().st_size,
    "codec_stream":stream,
    "recording_independence":"NOT_PROVEN_BY_DECODED_DURATION",
    "source_license_and_third_party_rights":"INDIVIDUAL_PAGE_CC0_ONLY_ADDITIONAL_AUDIT_REQUIRED",
    "speech_music_intrusive_events":"UNVERIFIED_AUDITION_REQUIRED",
    "clipping_loudness_seam_and_dedup":"NOT_CERTIFIED",
    "owner_listening_approved":False,"released_to_R2_HLS":False,
    "production_catalog_count_unchanged":35,"seo_indexing_enabled":False
  }
def main():
  OUT.mkdir(parents=True,exist_ok=True)
  results=[]
  for item in SOURCES:
    try: r=prepare(item)
    except Exception as exc:
      r={"record_id":item["id"],"status":"BLOCKED_NO_REVIEW_MP3",
         "error":type(exc).__name__+": "+str(exc)[:750],
         "owner_listening_approved":False,"released_to_R2_HLS":False}
      (OUT/(item["id"]+".mp3")).unlink(missing_ok=True)
    results.append(r)
    print("C6B_AUDITION",json.dumps(r,ensure_ascii=False),flush=True)
  report={"phase":"C6B_REVIEW_ARTIFACT_ONLY","original_count":2,"reports":results,
          "staged_review_mp3_count":sum(x.get("status","").startswith("REVIEW_MP3") for x in results),
          "production_mp3_published":0,"release_approvals":0,"new_indexable_pages":0}
  (OUT/"audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
  if report["staged_review_mp3_count"]!=2:
    print("C6B_BLOCKED: both candidates must decode >=605s to produce review artifacts",flush=True)
    raise SystemExit(2)
  print("C6B_REVIEW_MP3_ARTIFACTS_READY_ONLY_NOT_RELEASED",flush=True)
if __name__=="__main__": main()
