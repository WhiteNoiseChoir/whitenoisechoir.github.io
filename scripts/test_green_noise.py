#!/usr/bin/env python3
"""Post-production integrity checks for Green Noise and full original HLS inventory."""
import hashlib,json,math,subprocess
from pathlib import Path
import numpy as np
from scipy.signal import welch
root=Path("audio");p=root/"green-noise.mp3";m=json.loads((root/"green-noise-master-manifest.json").read_text())
playlist=root/"continuous"/"green-noise"/"continuous.m3u8"
allm=json.loads((root/"continuous"/"manifest.json").read_text())
assert m["id"]=="green-noise" and m["qa"]["technical_status"]=="PASS"
assert hashlib.sha256(p.read_bytes()).hexdigest()==m["file_sha256"]
# The 22 original HLS streams have since expanded to 35 approved streams.
# Validate every original locked master/playlist SHA, not a stale count of 22.
old22=json.loads((root/"original-22-hls-lock.json").read_text())
assert len(allm["records"])==35 and len(allm["applies_to"])==35
assert len({x["id"] for x in allm["records"]})==35
assert len(old22["records"])==22
for old in old22["records"]:
 current=next(x for x in allm["records"] if x["id"]==old["id"])
 assert current["master_sha256"]==old["master_sha256"]
 assert current["playlist_sha256"]==old["playlist_sha256"]
rec=next(x for x in allm["records"] if x["id"]=="green-noise")
assert hashlib.sha256(playlist.read_bytes()).hexdigest()==rec["playlist_sha256"]
assert rec["repeated_cycles"]>=1000 and rec["native_stream_duration_hours"]>=168
src=playlist.read_text()
assert src.count("#EXT-X-DISCONTINUITY")==rec["repeated_cycles"]-1
assert src.count("#EXTINF:")==rec["segment_count_per_source_cycle"]*rec["repeated_cycles"]
segments=list(playlist.parent.glob("part_*.ts"))
assert len(segments)==rec["segment_count_per_source_cycle"]
assert all(s.stat().st_size>100000 for s in segments)
args=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-xerror",
      "-ss","590","-i",str(playlist),"-t","25","-ar","8000","-ac","1","-f","f32le","pipe:1"]
p2=subprocess.run(args,capture_output=True)
assert p2.returncode==0,p2.stderr.decode(errors="replace")[-800:]
x=np.frombuffer(p2.stdout,dtype="<f4")
assert len(x)>24*8000
def db(segment):return 20*math.log10(max(1e-12,float(np.sqrt(np.mean(np.square(segment,dtype=np.float64))))))
a,b=db(x[2*8000:8*8000]),db(x[12*8000:18*8000])
assert abs(a-b)<4,(a,b)
print("PASS: Green Noise source MP3 SHA-256, 35-stream manifest and 22 original SHA locks, native HLS 7-day timeline, 10-minute transition",flush=True)
