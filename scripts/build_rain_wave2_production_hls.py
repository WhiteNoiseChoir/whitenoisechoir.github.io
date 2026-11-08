#!/usr/bin/env python3
"""Generate only the three owner-approved Rain Wave 2 seven-day native HLS streams.

Protects all 25 existing streams and their SHA-256 exactly.
The source MP3 bytes are byte-identical to the three owner-approved audio review files.
No re-encoding of the MP3 itself, no regeneration of existing production assets.
"""
from __future__ import annotations
import hashlib,json,math,re,subprocess
from pathlib import Path

ROOT=Path(".")
MASTER_ROOT=ROOT/"audio"
HLS_ROOT=MASTER_ROOT/"continuous"
MANIFEST=HLS_ROOT/"manifest.json"
REVIEW=ROOT/"signature/rain-wave2-review/manifest.json"
MAP={"rain-on-tent-review":"rain-on-tent-real","rain-car-roof-review":"rain-car-roof-real","rolling-thunder-review":"rolling-thunder-real"}
DAYS=7

def sh(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def run(args):
 p=subprocess.run(args,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(f"FAILED {' '.join(map(str,args[:5]))}: {p.stderr[-1200:]}")
 return p.stdout
def build(master,ident):
 folder=HLS_ROOT/ident;folder.mkdir(parents=True,exist_ok=True)
 output=folder/"source.m3u8"
 run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-i",str(master),"-vn","-map","0:a:0","-ar","44100","-ac","2","-c:a","aac","-b:a","192k","-f","hls","-hls_time","65","-hls_segment_type","mpegts","-hls_list_size","0","-hls_playlist_type","vod","-hls_segment_filename",str(folder/"part_%03d.ts"),str(output)])
 lines=output.read_text().splitlines();parts=[]
 for i,s in enumerate(lines):
  if not s.startswith("#EXTINF:"):continue
  d=float(s.split(":",1)[1].split(",")[0]);name=lines[i+1].strip()
  if not re.fullmatch(r"part_[0-9]{3}\.ts",name):raise RuntimeError("Invalid part name "+name)
  file=folder/name
  if not file.is_file() or file.stat().st_size<50_000:raise RuntimeError("Missing HLS media: "+name)
  parts.append((name,d))
 if not 9<=len(parts)<=11:raise RuntimeError(f"Incorrect 10minute segment count {len(parts)}")
 cycle=sum(d for _,d in parts)
 if abs(cycle-600)>1.5:raise RuntimeError(f"Incorrect source cycle {cycle}")
 count=math.ceil(DAYS*86400/cycle)
 rows=["#EXTM3U","#EXT-X-VERSION:3","#EXT-X-TARGETDURATION:"+str(math.ceil(max(d for _,d in parts))),"#EXT-X-MEDIA-SEQUENCE:0","#EXT-X-PLAYLIST-TYPE:VOD","#EXT-X-INDEPENDENT-SEGMENTS"]
 for i in range(count):
  if i:rows.append("#EXT-X-DISCONTINUITY")
  for name,d in parts:rows+=["#EXTINF:"+format(d,".6f")+",",name]
 rows.append("#EXT-X-ENDLIST")
 target=folder/"continuous.m3u8";target.write_text("\n".join(rows)+"\n")
 output.unlink()
 first=folder/parts[0][0]
 meta=json.loads(run(["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=codec_name,sample_rate,channels","-of","json",str(first)]))["streams"][0]
 if meta["codec_name"]!="aac" or int(meta["sample_rate"])!=44100 or int(meta["channels"])!=2:raise RuntimeError("Invalid AAC segment encoding")
 return target,parts,cycle,count,cycle*count
def main():
 data=json.loads(MANIFEST.read_text())
 review=json.loads(REVIEW.read_text())
 assert len(data["records"])==25 and len(data["applies_to"])==25
 assert len(review["tracks"])==3
 old_hashes={x["id"]:(sh(ROOT/x["playlist_file"]),x["playlist_sha256"]) for x in data["records"]}
 assert all(x==y for x,y in old_hashes.values()),"Existing 22 playlists changed before run"
 old_ids=set(data["applies_to"])
 assert not old_ids.intersection(MAP.values())
 for row in review["tracks"]:
  alias=row["id"];ident=MAP[alias]
  master=MASTER_ROOT/(ident+".mp3");src=ROOT/"signature/rain-wave2-review"/(alias+".mp3")
  assert master.is_file() and src.is_file()
  assert sh(master)==sh(src)==row["master_sha256"],"Approved MP3 must be copied byte-for-byte: "+ident
  assert row["duration_seconds"]==600 and row["source_type"]=="CC0-1.0"
  target,parts,cycle,count,total=build(master,ident)
  data["records"].append({
   "id":ident,"master_file":str(master),"master_sha256":sh(master),
   "playlist_file":str(target),"playlist_sha256":sh(target),
   "segment_count_per_source_cycle":len(parts),"source_cycle_seconds":round(cycle,3),
   "original_source_length_category":"10_MINUTE_MASTER_FROM_CC0_PREVIEW",
   "source_license":"CC0-1.0","source_page":row["source_page"],
   "editorial_status":"OWNER_APPROVED_FOR_AUDIO_SEO_PENDING",
   "repeated_cycles":count,"native_stream_duration_hours":round(total/3600,2),
   "audio_codec":"AAC-LC in MPEG-TS","sample_rate":44100,"channels":2,"bitrate_kbps":192,
   "long_form_listening_status":"OWNER_APPROVED_10MIN_MP3_LOCKSCREEN_HLS_QA_PENDING",
   "notes":"Owner approved 600s field-source-derived audition master. Preview is lossy and source WAV not downloaded. 7day static playlist repeats this 600s cycle; iPhone lock screen needs device QA.",
   "independent_source_duration_seconds":row["independent_source_seconds"],
   "repetitions_of_original_events":row["repetitions_approx"],
   "review_sha256":row["master_sha256"],
  })
  data["applies_to"].append(ident)
  print("RAIN_WAVE2_HLS_CREATED "+json.dumps({"id":ident,"segments":len(parts),"cycle_s":round(cycle,3),"cycles":count,"hours":round(total/3600,2),"sha":sh(target)}),flush=True)
 data["applies_to"].sort()
 assert len(data["records"])==28 and len(data["applies_to"])==28
 assert old_ids.issubset(set(data["applies_to"]))
 assert all(sh(ROOT/x["playlist_file"])==x["playlist_sha256"] for x in data["records"] if x["id"] in old_ids)
 data["version"]="continuous-hls-v6-rain-wave2-approved-20261109"
 data["playlist_type"]="static multi-cycle HLS VOD, seven days per track, 28 sound IDs"
 data["source_length_disclosure"]="24 ten-minute MP3 masters (including 6 preview-derived CC0 rain and thunder masters) and 4 shorter CC0 field sources. All true source durations and lossy MP3 preview limitations are documented."
 MANIFEST.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
 assert all(sh(ROOT/x["playlist_file"])==x["playlist_sha256"] for x in data["records"])
 print("RAIN_WAVE2_HLS_28_PASS: 25 old SHA unchanged; 3 new native iOS HLS streams 7 days each",flush=True)
if __name__=="__main__":main()
