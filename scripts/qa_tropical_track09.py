#!/usr/bin/env python3
"""Quality diagnostics for tropical rainforest track 09 and neighboring bird clips."""
import json, os, tempfile, subprocess, hashlib, math
from pathlib import Path
import boto3
import numpy as np
from botocore.config import Config

CONFIG=[
 ("08 Black Hornbill", "asset-library/raw/sha256/5d/5d2435071282befb4fc8d2233939afa28683931d319d3624f20a904aa71d87dd.wav", .22),
 ("09 Streak-eared Bulbul", "asset-library/raw/sha256/56/5638fb8f8cee289529352b9a088a3b7e14d946451594fe28d75de31719cb1e62.wav", .16),
 ("10 Plaintive Cuckoo", "asset-library/raw/sha256/23/23ed12a8f47260f28c02f37e98adfe9aebc6427da9e2c0fc605b8a6428867ce7.m4a", .17),
 ("17 Yellow-vented Bulbul", "asset-library/raw/sha256/15/15444e51bb13a6d02e59fa33bcf2e1075fd2e6e8aa8a3a98c7fe44fec65519ea.wav", .19)
]
s3=boto3.client("s3",endpoint_url="https://7483501ad8365fe26b0448b96b54fb9f.r2.cloudflarestorage.com",region_name="auto",
 aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
 config=Config(signature_version="s3v4",request_checksum_calculation="when_required",response_checksum_validation="when_required"))
def audio_stats(name,key,gain):
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/("audio"+Path(key).suffix)
  s3.download_file("whitenoisechoir-media",key,str(path))
  sha=hashlib.sha256(path.read_bytes()).hexdigest()
  if sha not in key:raise RuntimeError("Bad checksum "+name)
  command=["ffmpeg","-hide_banner","-loglevel","error","-i",str(path),"-ac","1","-ar","16000","-f","f32le","-"]
  result=subprocess.run(command,capture_output=True,timeout=45)
  if result.returncode:raise RuntimeError(result.stderr.decode()[-400:])
  data=np.frombuffer(result.stdout,dtype="<f4")
  rms=np.sqrt(np.mean(data.astype(np.float64)**2))
  sec=[]
  for i in range(math.ceil(len(data)/16000)):
   a=data[i*16000:(i+1)*16000]
   if not len(a):continue
   e=float(np.sqrt(np.mean(a.astype(np.float64)**2)))
   sec.append({"sec":i,"peak_db":round(20*np.log10(max(float(np.max(np.abs(a))),1e-9)),1),
      "rms_db":round(20*np.log10(max(e,1e-9)),1),
      "rms_after_track_gain_db":round(20*np.log10(max(e*gain,1e-9)),1)})
  abs_data=np.abs(data)
  hist=np.histogram(data,bins=20,range=(-1,1))[0].tolist()
  return {"name":name,"key":key,"bytes":path.stat().st_size,"sample_count":len(data),
    "duration_s":round(len(data)/16000,2),"sha256":sha,
    "peak_dbfs":round(20*np.log10(max(float(abs_data.max()),1e-9)),2),
    "rms_dbfs":round(20*np.log10(max(float(rms),1e-9)),2),
    "rms_after_track_gain_db":round(20*np.log10(max(float(rms)*gain,1e-9)),2),
    "crest_factor_db":round(20*np.log10(max(float(abs_data.max()/max(rms,1e-9)),1e-9)),2),
    "sample_fraction_above_minus_1db":round(float(np.mean(abs_data>.8913)),5),
    "sample_fraction_near_silent_minus_65db":round(float(np.mean(abs_data<.00056)),4),
    "dc_bias":round(float(data.mean()),5),
    "seconds":sec,"histogram":hist}
rows=[]
for name,key,gain in CONFIG:
 try:
  stats=audio_stats(name,key,gain);rows.append(stats)
  print("TRACK09_QA "+json.dumps(stats,ensure_ascii=False),flush=True)
 except Exception as exc:
  print("TRACK09_QA_ERROR "+name+": "+str(exc),flush=True)
  raise
Path("tropical-track09-diagnostics.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2))
