#!/usr/bin/env python3
"""Build small gapless Studio sound proxies from approved R2 MP3 masters.

Full 10-minute master MP3s expand to ~100MB/each in Web Audio, crashing some
Chromium-based browsers when decoded concurrently on refresh. Generate 92s
seamless, original-content loop proxies for Studio. Do not modify any masters.
This is for preview and browser-side WAV render, not a new field recording.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import numpy as np

BUCKET="whitenoisechoir-media"
ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
PUBLIC="https://media.whitenoisechoir.com/"
SR=44100
CHANNELS=2
READ_SECONDS=96
FADE_SECONDS=4
SOURCE_IDS={
  5:"fireplace-real",
  6:"rain-on-window-real",
  9:"rain-leaves-real",
  31:"wind-synth",
  35:"light-rain-real",
  41:"forest-stream-real"
}

def check(cmd: list[str], timeout=160):
    result=subprocess.run(cmd,capture_output=True,timeout=timeout)
    if result.returncode:
        raise RuntimeError("Command failed: "+" ".join(cmd[:5])+" "+result.stderr.decode(errors="replace")[-450:])
    return result.stdout

def main():
    if not os.getenv("R2_ACCESS_KEY_ID") or not os.getenv("R2_SECRET_ACCESS_KEY"):
        raise RuntimeError("Missing R2 bucket credentials")
    s3=boto3.session.Session().client("s3",
       endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",
       region_name="auto",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
       aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
       config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
             connect_timeout=20,read_timeout=90,retries={"mode":"standard","max_attempts":5},
             request_checksum_calculation="when_required",response_checksum_validation="when_required"))
    inventory=json.loads(Path("audio/continuous/manifest.json").read_text(encoding="utf8"))
    by_id={r["id"]:r for r in inventory["records"]}
    outcomes=[]
    with tempfile.TemporaryDirectory(prefix="studio-loop-") as td:
      root=Path(td)
      for asset,stem in SOURCE_IDS.items():
        source_key=f"audio/{stem}.mp3"
        source=root/f"source-{asset}.mp3"
        dest=root/f"loop-{asset}.mp3"
        print("STUDIO_LOOP_START "+json.dumps({"asset":asset,"source_key":source_key}),flush=True)
        original=s3.get_object(Bucket=BUCKET,Key=source_key)
        with source.open("wb") as out:
          body=original["Body"]
          try:
            while part:=body.read(1024*1024): out.write(part)
          finally:body.close()
        sha=hashlib.sha256(source.read_bytes()).hexdigest()
        approved=by_id.get(stem)
        if not approved: raise RuntimeError("Missing original master inventory for "+stem)
        if approved["master_sha256"]!=sha:
          raise RuntimeError("Original R2 audio doesn't match master inventory sha "+stem)
        # Decode only the first 96 seconds, not the 600-second master.
        raw=check(["ffmpeg","-v","error","-nostdin","-i",str(source),
              "-t",str(READ_SECONDS),"-ar",str(SR),"-ac",str(CHANNELS),"-f","f32le","pipe:1"])
        pcm=np.frombuffer(raw,dtype="<f4").reshape(-1,2).copy()
        required=READ_SECONDS*SR
        if len(pcm)<required-SR: raise RuntimeError("Source less than 95 seconds")
        pcm=pcm[:required]
        # Put 4 seconds of tail->head crossfade at the beginning.
        # Output ends at frame 92s and seamlessly transitions into the tail of
        # the original, which becomes the start of this proxy. No silence gap.
        fade=FADE_SECONDS*SR
        n=len(pcm)-fade
        output=pcm[:n].copy()
        phase=np.linspace(0,np.pi/2,fade,dtype=np.float32)[:,None]
        output[:fade]=pcm[n:n+fade]*np.cos(phase)+pcm[:fade]*np.sin(phase)
        ceiling=10**(-1/20)
        maxamp=float(np.max(np.abs(output)))
        if maxamp>ceiling:output*=ceiling/maxamp
        cmd=["ffmpeg","-y","-v","error","-nostdin","-f","f32le","-ar",str(SR),
             "-ac",str(CHANNELS),"-i","pipe:0","-c:a","libmp3lame","-b:a","160k",str(dest)]
        proc=subprocess.run(cmd,input=output.astype("<f4",copy=False).tobytes(),
                            capture_output=True,timeout=160)
        if proc.returncode:raise RuntimeError("Proxy encode failed "+proc.stderr.decode(errors="replace")[-350:])
        check(["ffmpeg","-v","error","-nostdin","-i",str(dest),
               "-t","4","-f","null","-"],timeout=70)
        data=dest.read_bytes()
        key_sha=hashlib.sha256(data).hexdigest()
        proxy_key=f"asset-library/studio-loop/sha256/{key_sha[:2]}/{key_sha}.mp3"
        try:
          head=s3.head_object(Bucket=BUCKET,Key=proxy_key)
        except ClientError as exc:
          if str(exc.response.get("Error",{}).get("Code")) not in ("404","NotFound","NoSuchKey"):raise
          head=None
        if head is None:
          s3.put_object(Bucket=BUCKET,Key=proxy_key,Body=data,ContentLength=len(data),
             ContentType="audio/mpeg",CacheControl="public,max-age=31536000,immutable",
             Metadata={"sha256":key_sha,"source-sha256":sha,"kind":"studio-loop-92s"})
          uploaded="uploaded"
        else:
          if int(head["ContentLength"])!=len(data):raise RuntimeError("R2 preview SHA collision")
          uploaded="reused"
        checkremote=s3.get_object(Bucket=BUCKET,Key=proxy_key)
        remote=checkremote["Body"].read();checkremote["Body"].close()
        if hashlib.sha256(remote).hexdigest()!=key_sha:raise RuntimeError("R2 loop proxy checksum mismatch")
        outcome={"asset_id":asset,"source":source_key,"source_sha256":sha,
                 "proxy_key":proxy_key,"proxy_sha256":key_sha,
                 "duration_seconds":round(n/SR,3),"bytes":len(data),
                 "mode":"gapless_circular_crossfade_4s","status":"STORED_R2",
                 "original_master_untouched":True,"upload":uploaded}
        print("STUDIO_LOOP_PROXY_JSON "+json.dumps(outcome),flush=True)
        outcomes.append(outcome)
    Path("studio-loop-proxies-report.json").write_text(json.dumps(outcomes,indent=2)+"\n",encoding="utf8")
    print("STUDIO_LOOP_PROXY_SUMMARY "+json.dumps({"passed":len(outcomes),"expected":len(SOURCE_IDS)}),flush=True)
    if len(outcomes)!=len(SOURCE_IDS):raise RuntimeError("Incomplete proxy build")

if __name__=="__main__":main()
