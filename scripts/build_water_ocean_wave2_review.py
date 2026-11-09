#!/usr/bin/env python3
"""Build *review-only* Water Ocean Wave 2 audition masters from public HQ previews.

DO NOT promote these compressed Freesound preview derivatives as lossless source
masters or production-approved sound IDs. Source licenses are verified on the
linked Freesound pages. A full-quality original download requires separate login.
This script runs in a throwaway GitHub Actions job with network access, never in
the live player.
"""
from __future__ import annotations
import hashlib,json,math,re,subprocess,tempfile,urllib.request
from pathlib import Path

ROOT=Path("signature/water-ocean-wave2-review")
ROOT.mkdir(parents=True,exist_ok=True)
CONFIG=[
 {
  "plan_id": "NEW-10",
  "id": "bodetal-brook-review",
  "title": "Bodetal Brook & Birds — Bubbling Brook Candidate",
  "creator": "Borgory",
  "source_page": "https://freesound.org/people/Borgory/sounds/651194/",
  "source_preview": "https://cdn.freesound.org/previews/651/651194_801011-hq.mp3",
  "source_type": "CC0-1.0",
  "source_duration_seconds": 637.542,
  "target_mean_dbfs": -34,
  "notes": "Stereo field source from Harz/Bodetal valley in Germany, recorded Zoom H5. Description calls stream in distance with bird calls. NOT proven close-up bubbling brook: owner must compare with existing Forest Stream and decide if named Bubbling Brook is acoustically appropriate; otherwise reject or retitle. Unique 605s segment."
 },
 {
  "plan_id": "NEW-13",
  "id": "wakanui-surf-review",
  "title": "Crashing Ocean Waves — Wakanui Beach, New Zealand",
  "creator": "Desmond178",
  "source_page": "https://freesound.org/people/Desmond178/sounds/721591/",
  "source_preview": "https://cdn.freesound.org/previews/721/721591_12778541-hq.mp3",
  "source_type": "CC0-1.0",
  "source_duration_seconds": 2726.3,
  "target_mean_dbfs": -34,
  "notes": "Actual 45m26s stereo breaking waves at Wakanui Beach, Ashburton NZ. Original source is CC0. Compare with approved Gentle Ocean Waves (Scottish shore): must be significantly stronger; audit background wind, occasional transient and seam. Selected unique 605s segment."
 }
]
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 if p.returncode:raise RuntimeError(f"{' '.join(map(str,args[:8]))} failed ({p.returncode}): {p.stderr[-1800:]}")
 return p
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def probe(p):
 j=json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)]).stdout)
 s=next(x for x in j["streams"] if x["codec_type"]=="audio")
 return {"duration_seconds":float(j["format"]["duration"]),"codec":s["codec_name"],"channels":s["channels"],"sample_rate":int(s["sample_rate"]),"bitrate":int(j["format"].get("bit_rate",0))}
def stats(p):
 q=run(["ffmpeg","-hide_banner","-nostdin","-i",str(p),"-af","volumedetect","-vn","-f","null","-"])
 out=q.stderr
 mean=re.search(r"mean_volume:\s*(-?[\d.]+) dB",out)
 peak=re.search(r"max_volume:\s*(-?[\d.]+) dB",out)
 if not mean or not peak:raise RuntimeError("No volumedetect values")
 return float(mean.group(1)),float(peak.group(1))
def media(p,title,duration):
 data=probe(p);if_duration=data["duration_seconds"]
 if abs(duration-if_duration)>1.0:raise RuntimeError(f"{title} length {if_duration} != expected {duration}")
 return data
def make_cycle(src,duration,out):
    """Build a 600s loop from three *separately decoded* PCM sections.

    This avoids building a huge split-filter graph from an hour-long input.
    Output y[0..duration-5] = source[5..duration], and y[duration-5..duration]
    crossfades source[duration..duration+5] into source[0..5].
    The ending then meets the adjacent source point at t=5, without
    a hard jump or a silence fade on native MP3 loop.
    """
    overlap=5
    with tempfile.TemporaryDirectory(prefix="rain-seam-") as td:
        t=Path(td)
        slices=[
          ("body",overlap,duration-overlap),
          ("tail",duration,overlap),
          ("head",0,overlap),
        ]
        for name,offset,seconds in slices:
            target=t/(name+".flac")
            run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                 "-i",str(src),"-ss",str(offset),"-t",str(seconds),
                 "-ac","2","-ar","44100","-c:a","flac",str(target)])
        filt=(
          f"[1:a][2:a]acrossfade=d={overlap}:c1=tri:c2=tri[seam];"
          "[0:a][seam]concat=n=2:v=0:a=1[out]"
        )
        run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
             "-i",str(t/"body.flac"),"-i",str(t/"tail.flac"),"-i",str(t/"head.flac"),
             "-filter_complex",filt,"-map","[out]",
             "-ar","44100","-ac","2","-c:a","flac",str(out)])
    media(out,out.name,duration)
def download(url,dest,byte_cap=None):
    # We only need the first 605 seconds of a >20-minute field source.
    # Avoid fetching the remaining 15-45 minutes of public HQ preview audio.
    headers={"User-Agent":"WhiteNoiseChoirCC0Review/1.0 (audio provenance audit; Freesound attribution retained)","Accept":"audio/mpeg,*/*"}
    if byte_cap:headers["Range"]=f"bytes=0-{byte_cap-1}"
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=100) as r,open(dest,"wb") as w:
        ctype=r.headers.get("content-type","")
        remaining=byte_cap
        while True:
            take=1024*1024 if remaining is None else min(1024*1024,remaining)
            if take<=0:break
            chunk=r.read(take)
            if not chunk:break
            w.write(chunk)
            if remaining is not None:remaining-=len(chunk)
    if dest.stat().st_size<250000:raise RuntimeError("Preview file too small for sound, likely blocked "+url)
    fmt=probe(dest)
    if fmt["codec"]!="mp3":raise RuntimeError(f"Unexpected HQ preview codec: {fmt}")
    return fmt,ctype
def render(config,root):
 with tempfile.TemporaryDirectory(prefix="rain-qa-") as td:
  tmp=Path(td);src=tmp/"preview.mp3"
  byte_cap=18_000_000 if config["source_duration_seconds"]>605.5 else None
  incoming,ctype=download(config["source_preview"],src,byte_cap)
  if incoming["duration_seconds"]<25:raise RuntimeError("HQ preview shorter than 25s; not using fake extension")
  original_preview_seconds=incoming["duration_seconds"]
  if original_preview_seconds>605.5:
   segment=tmp/"cycle.flac"
   make_cycle(src,600,segment)
   variant="600s contiguous section with a 5s circular seam; selected from a longer independent field recording"
   source_window_seconds=605
   repetitions=0
  else:
   length=int(math.floor(min(incoming["duration_seconds"]-5.5,570)))
   if length<25:raise RuntimeError("Not enough short source for crossfade")
   short=tmp/"short-cycle.flac"
   make_cycle(src,length,short)
   total=tmp/"repeated.flac"
   # Decode the loop-safe short cycle as a repeated input, then make a 600s
   # output with a final circular seam. Metadata records that this is a looped
   # arrangement of a short source, not 10 minutes of novel events.
   run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-stream_loop","8","-i",str(short),"-t","605","-ac","2","-ar","44100","-c:a","flac",str(total)])
   segment=tmp/"cycle.flac";make_cycle(total,600,segment)
   variant=f"Reused approximately {length}s of independent source with 5s circular crossfades; recognizable source patterns may repeat"
   source_window_seconds=length
   repetitions=math.ceil(605/length)
  mean,peak=stats(segment)
  # Target is calm adult sleep; never increase sample peak beyond -9 dBFS.
  target=config["target_mean_dbfs"]
  gain=max(-18.0,min(3.0,target-mean,-9.0-peak))
  dest=ROOT/(config["id"]+".mp3")
  run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-i",str(segment),"-af",f"volume={gain:.3f}dB,highpass=f=25,lowpass=f=15000","-ar","44100","-ac","2","-c:a","libmp3lame","-b:a","192k",str(dest)])
  final=media(dest,config["title"],600)
  final_mean,final_peak=stats(dest)
  if final_peak>-5.5:raise RuntimeError(f"Unsafe sample peak: {final_peak}")
  if final_mean<-55:raise RuntimeError(f"Unexpectedly quiet master: {final_mean}")
  return dict(config,review_status="PENDING_OWNER_LISTENING",publication_status="REVIEW_ONLY_NOT_IN_PRODUCTION",downloaded_preview_codec=incoming["codec"],downloaded_preview_channels=incoming["channels"],downloaded_preview_bitrate_kbps=round(incoming["bitrate"]/1000,2),downloaded_preview_duration_seconds=round(original_preview_seconds,3),downloaded_preview_sha256=sha(src),independent_source_seconds=round(min(original_preview_seconds,source_window_seconds),3),arrangement=variant,repetitions_approx=repetitions,duration_seconds=round(final["duration_seconds"],3),output_codec=final["codec"],sample_rate=final["sample_rate"],channels=final["channels"],output_bitrate_kbps=round(final["bitrate"]/1000,1),mean_dbfs=final_mean,peak_dbfs=final_peak,gain_db=round(gain,2),master_sha256=sha(dest),master_bytes=dest.stat().st_size,source_preview_content_type=ctype,preview_byte_cap=byte_cap,preview_acquisition_note="Only up to 18,000,000 bytes of long preview requested; enough for first 605s; FFprobe header duration may report total original preview length, not bytes downloaded." if byte_cap else "Full short preview downloaded",technical_status="PASS",limitations=["Original lossless source NOT downloaded; publicly accessible HQ preview is lossy","Review listening needed: source identity, tonality, abrupt events, peak, physical listening comfort, 10min loop"])
def main():
 report=[]
 for cfg in CONFIG:
  print("DOWNLOADING "+cfg["id"]+" from public licensed preview",flush=True)
  row=render(cfg,ROOT)
  report.append(row)
  print("WATER_OCEAN_WAVE2_REVIEW_PASS "+json.dumps({k:row[k] for k in ["id","duration_seconds","mean_dbfs","peak_dbfs","downloaded_preview_duration_seconds","downloaded_preview_bitrate_kbps","repetitions_approx","master_sha256"]}),flush=True)
 manifest={"version":"water-ocean-wave2-audition-20261109","status":"REVIEW_ONLY_PENDING_OWNER","license_policy":"Two independent CC0 valley-brook and crashing-ocean field recordings; verification source links included; original WAV source is NOT downloaded","media_quality_policy":"Public Freesound HQ MP3 previews are lossy; actual bitrate varies and the first 18MB of any long preview cannot establish its true full-file bitrate. The 192 kbps audition MP3 is a transcoding step and cannot restore quality. Do not publish without listening approval; original lossless WAV recordings remain separate.","goal":"Two P0 audition masters; Bamboo Water Fountain NEW-11 not included due unverified/unsuitable CC0 recordings. Review only; no production source IDs or SEO URL promotion","tracks":report}
 (ROOT/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("WATER_OCEAN_WAVE2_REVIEW_ALL_2_READY",flush=True)
if __name__=="__main__":main()
