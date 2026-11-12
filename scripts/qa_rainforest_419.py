#!/usr/bin/env python3
"""Diagnose high frequency at 04:15–04:20 in the rainforest V3 timeline."""
import json, subprocess, tempfile, hashlib, os
from pathlib import Path
import boto3, numpy as np
from botocore.config import Config

RECORDINGS = [
 ("19 | Graceful Pitta (starts 04:13)", "asset-library/raw/sha256/5d/5d9e3406b8a1a76e7d439bb02cf706a54df64c590bd94598f5dba2fd01a87c14.wav", 253, .17, 8200),
 ("05 | Soft forest crickets (looped)", "asset-library/raw/sha256/29/2990dbaec8939396d4f083fe1524a2cb26a1a8102c19a3701645ca5acbcb2b8e27.mp3", 0, .068, 4400)
]
# The second source is optional: its key is dynamically recovered in catalog when possible.
import re
cat=Path("studio-catalog.js").read_text()
arr=json.loads(cat[cat.index("[",cat.index("const studioPublishedAssets")):cat.rfind("]")+1])
RECORDINGS[1]=(RECORDINGS[1][0],arr[42]["key"],0,.068,4400)
RECORDINGS.append(("06 | Frog/cricket creek (looped)",arr[44]["key"],0,.059,4300))

s3=boto3.client("s3",endpoint_url="https://7483501ad8365fe26b0448b96b54fb9f.r2.cloudflarestorage.com",region_name="auto",
 aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
 config=Config(signature_version="s3v4",request_checksum_calculation="when_required",response_checksum_validation="when_required"))
def analyze(name,key,start,gain,lowpass):
 with tempfile.TemporaryDirectory() as folder:
  path=Path(folder)/("source"+Path(key).suffix)
  s3.download_file("whitenoisechoir-media",key,str(path))
  expected=re.search(r"([a-f0-9]{64})\.[a-z0-9]+$",key).group(1)
  if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(name+" checksum mismatch")
  cmd=["ffmpeg","-hide_banner","-loglevel","error","-i",str(path),"-ac","1","-ar","16000","-f","f32le","-"]
  r=subprocess.run(cmd,capture_output=True,timeout=100)
  if r.returncode:raise RuntimeError(r.stderr.decode()[-300:])
  signal=np.frombuffer(r.stdout,dtype="<f4")
  sampleRate=16000
  total=len(signal)/sampleRate
  secRows=[]
  for second in range(12):
   if start and second>=total:break
   # segment relative to start of first 12 source seconds, to capture suspected tonal 2–7s
   x=signal[second*sampleRate:min((second+1)*sampleRate,len(signal))].astype("float64")
   if len(x)<sampleRate*.3:break
   amp=np.sqrt(np.mean(x*x))
   power=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2
   freqs=np.fft.rfftfreq(len(x),1/sampleRate)
   totalPower=power[(freqs>=80)&(freqs<=7900)].sum()
   fractions={str(f):round(float(power[(freqs>=f)&(freqs<=7900)].sum()/max(totalPower,1e-16)),3) for f in (2000,3000,4000,5000,6000)}
   peakFreq=float(freqs[np.argmax(power[1:])+1])
   secRows.append({"source_second":second,"timeline_second":start+second if start else None,
      "rms_db":round(20*np.log10(max(amp,1e-9)),1),
      "peak_db":round(20*np.log10(max(np.max(np.abs(x)),1e-9)),1),
      "dominant_hz":round(peakFreq),
      "energy_above_hz":fractions})
  report={"name":name,"duration":round(total,3),"gain":gain,"lowpass":lowpass,
          "seconds":secRows,"hash":expected}
  print("TROPICAL_419_DIAG "+json.dumps(report,ensure_ascii=False),flush=True)
  return report

output=[analyze(*item) for item in RECORDINGS]
Path("tropical-419-diagnostic.json").write_text(json.dumps(output,ensure_ascii=False,indent=2))
