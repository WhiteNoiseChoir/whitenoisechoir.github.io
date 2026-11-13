#!/usr/bin/env python3
"""Offline mix-loudness approximation from original R2 bytes and stored Studio timeline.
FFmpeg measures input_i and input_tp before loudnorm gain; no normalized file is published.
Browser stereo panner math is intentionally omitted; this is not pixel-identical to WAV exporter.
"""
import os,json,hashlib,requests,subprocess,re
from pathlib import Path
PROJECT=Path("data/studio-projects/the-sleeping-lake-v1.json")
ROOT="https://media.whitenoisechoir.com/"
def main():
 p=json.loads(PROJECT.read_text())
 tracks=p["tracks"]
 assert p["length"]==600 and len(tracks)==10
 Path("tmp-sleeping-lake").mkdir(exist_ok=True)
 media={}
 for i,t in enumerate(tracks):
  h=t["assetRef"].replace("r2-","")
  assert re.fullmatch(r"[a-f0-9]{64}",h)
  if h in media:continue
  ext="ogg" if h=="a512974fcff448950f86fa26d07fbb8d52b55e8cbdf24e8d721f42161a1d7f53" else "wav" if h=="5c381856745b4706e7eba55eb9271a61a530e90c05df8126adb2db89ecfa6c5a" else "mp3"
  key="asset-library/raw/sha256/"+h[:2]+"/"+h+"."+ext
  out=Path("tmp-sleeping-lake")/(h+"."+ext)
  with requests.get(ROOT+key,stream=True,timeout=(20,60)) as r:
   r.raise_for_status()
   with out.open("wb") as f:
    for chunk in r.iter_content(256*1024):f.write(chunk)
  digest=hashlib.sha256(out.read_bytes()).hexdigest()
  if digest!=h:raise ValueError("SHA mismatch: "+key)
  media[h]=str(out)
 args=["ffmpeg","-hide_banner","-nostdin","-v","info","-y"]
 for t in tracks:args.extend(["-i",media[t["assetRef"][3:]]])
 filters=[]
 for i,t in enumerate(tracks):
  offset=t.get("offset",0);d=t["duration"];start=t["start"];lo=t.get("lowpass",8000)
  fadeoutstart=max(0,d-t.get("fadeOut",0))
  chain=f"[{i}:a]atrim=start={offset}:duration={d},asetpts=PTS-STARTPTS,aresample=48000"
  if lo:chain+=f",lowpass=f={lo}"
  chain+=f",volume={t['gain']},afade=t=in:st=0:d={t['fadeIn']},afade=t=out:st={fadeoutstart}:d={t['fadeOut']},adelay={int(start*1000)}:all=1[t{i}]"
  filters.append(chain)
 comb="".join(f"[t{i}]" for i in range(len(tracks)))
 filters.append(comb+f"amix=inputs={len(tracks)}:duration=longest:normalize=0:dropout_transition=0,volume={p['master']},atrim=duration=600,loudnorm=I=-18:TP=-1.5:LRA=11:print_format=json[m]")
 args+=["-filter_complex",";".join(filters),"-map","[m]","-f","null","-"]
 run=subprocess.run(args,capture_output=True,text=True,timeout=320)
 if run.returncode:raise RuntimeError("Offline ffmpeg failed: "+run.stderr[-1000:])
 matches=list(re.finditer(r'\{\s*"input_i"[\s\S]*?\}',run.stderr))
 if not matches:raise RuntimeError("EBU R128 loudnorm stats not returned")
 stats=json.loads(matches[-1].group())
 result={"mix":"THE SLEEPING LAKE V1","duration":600,"tracks":len(tracks),"unique_real_r2_sources":len(media),"master":p["master"],
  "measured_mix_input_lufs":stats.get("input_i"),"measured_mix_true_peak_dbtp":stats.get("input_tp"),
  "measured_mix_lra":stats.get("input_lra"),"method":"FFmpeg offline mix with individual fades, source offsets, lowpasses, gain and master; stereo pan interpolation is not simulated; measured input before loudnorm"}
 Path("sleeping-lake-mix-loudness.json").write_text(json.dumps(result,indent=2))
 s="## THE SLEEPING LAKE V1 — 600s offline mix loudness\n\n"+ "\n".join("- "+k+": "+str(v) for k,v in result.items())
 Path("sleeping-lake-mix-loudness.md").write_text(s)
 print("SLEEPING_LAKE_600S_MIX_LOUDNESS "+json.dumps(result),flush=True)
if __name__=="__main__":main()
