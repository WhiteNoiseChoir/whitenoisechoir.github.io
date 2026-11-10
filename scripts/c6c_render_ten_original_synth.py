#!/usr/bin/env python3
"""C6C generate 10 ORIGINAL, DISTINCT 600s DSP non-production audition MP3s.

No external sound recordings, no sample loops, no copyrighted works, no vocal recordings.
Never writes to audio/, library.json, production HLS, release gates or SEO.
Source generation at 22.05 kHz floating-point stereo; resample 44.1 kHz and encode
192 kbps MP3. Random generator and continuous filter state do not restart per block.
"""
from __future__ import annotations
import hashlib,json,math,os,subprocess,time
from pathlib import Path
import numpy as np
from scipy import signal

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/"catalog/c6c-ten-synthetic-review.json").read_text())
OUT=ROOT/"audits/c6c-original-render"
SR=22050
SECONDS=600
FRAMES=SR*SECONDS
CHUNK=SR*5
RATE=44100
LIMIT=0.91
assert MANIFEST["audio_spec"]["seconds"]==SECONDS
assert MANIFEST["audio_spec"]["render_sample_rate_hz"]==SR
assert MANIFEST["audio_spec"]["mp3_sample_rate_hz"]==RATE
assert len(MANIFEST["items"])==10

def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()

def run(args,seconds=120):
 result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
 if result.returncode:
  raise RuntimeError("Command failed "+str(args[:4])+": "+result.stderr.decode("utf-8","replace")[-800:])
 return result.stdout

class Renderer:
 def __init__(self,kind:str,seed:int):
  self.kind=kind;self.rng=np.random.default_rng(seed)
  bands={
   "low":signal.butter(2,260,fs=SR,output="sos"),
   "mid":signal.butter(2,[130,3200],btype="bandpass",fs=SR,output="sos"),
   "air":signal.butter(2,[650,8500],btype="bandpass",fs=SR,output="sos")
  }
  self.sos=bands
  self.state={k:np.zeros((s.shape[0],2,2),np.float64) for k,s in bands.items()}
  self.gain=None;self.max_peak=0;self.energy=0;self.samples=0
 def bands_for(self,noise):
  result={}
  for key in ("low","mid","air"):
   x,self.state[key]=signal.sosfilt(self.sos[key],noise,axis=0,zi=self.state[key])
   result[key]=x.astype(np.float32,copy=False)
  return result
 def create(self,start:int,count:int)->np.ndarray:
  t=(start+np.arange(count,dtype=np.float64))/SR
  white=self.rng.standard_normal((count,2),dtype=np.float32)
  v=self.bands_for(white);lo,mid,air=v["low"],v["mid"],v["air"]
  kind=self.kind
  tone=lambda f: np.sin(2*np.pi*f*t).astype(np.float32)[:,None]
  if kind=="tower_fan":
   m=(0.9+0.075*np.sin(2*np.pi*0.35*t))[:,None]
   out=0.75*mid*m+0.50*lo+0.24*tone(83)+0.10*tone(166)
  elif kind=="oscillating_fan":
   phase=np.sin(2*np.pi*0.074*t)
   env=(0.53+0.37*(0.5+0.5*phase))[:,None]
   pan=np.column_stack((0.80-0.14*phase,0.80+0.14*phase)).astype(np.float32)
   out=(0.85*mid*env+0.38*lo+0.14*tone(71))*pan
  elif kind=="womb":
   heartbeat_period=60/68
   phase=np.mod(t,heartbeat_period)/heartbeat_period
   pulse=np.exp(-((phase-.085)/.050)**2)+0.62*np.exp(-((phase-.31)/.067)**2)
   out=0.95*lo+0.22*tone(57)+(0.58*pulse*np.sin(2*np.pi*70*t))[:,None]
  elif kind=="shushing":
   env=(0.09+0.91*(0.5+0.5*np.sin(2*np.pi*0.42*t))**2)[:,None]
   out=(0.90*mid+0.45*air)*env+0.07*lo
  elif kind=="heartbeat":
   p=60/65
   phase=np.mod(t,p)/p
   pulse=(np.exp(-((phase-.11)/.044)**2)+0.55*np.exp(-((phase-.29)/.063)**2))
   out=(0.95*pulse*np.sin(2*np.pi*57*t))[:,None]+0.14*lo
  elif kind=="breathing":
   breath=(0.07+0.93*(0.5-0.5*np.cos(2*np.pi*0.16*t))**1.45)[:,None]
   out=(0.7*mid+0.35*lo+0.22*air)*breath
  elif kind=="grey":
   out=0.45*lo+0.78*mid+0.52*air
  elif kind=="radio":
   carrier=(0.08*np.sin(2*np.pi*(740*t+0.9*np.sin(2*np.pi*.06*t))))[:,None]
   oscill=(0.77+0.12*np.sin(2*np.pi*0.38*t))[:,None]
   out=(0.70*air+0.37*mid)*oscill+carrier
  elif kind=="vinyl":
   clicks=np.zeros(count,dtype=np.float32)
   n_clicks=self.rng.poisson(count/SR*11.5)
   if n_clicks:
    loc=self.rng.integers(0,count,size=n_clicks)
    length=96
    decay=np.exp(-np.arange(length)/12).astype(np.float32)
    for p in loc:
     end=min(count,p+length)
     clicks[p:end]+=0.43*decay[:end-p]
   out=0.66*lo+0.23*mid+0.25*air+clicks[:,None]*np.array([[1.,0.83]],np.float32)
  elif kind=="electrical":
   tone50=(0.65*np.sin(2*np.pi*50*t)+0.23*np.sin(2*np.pi*100*t)+
    0.14*np.sin(2*np.pi*150*t)+0.055*np.sin(2*np.pi*250*t))
   drift=(1+0.025*np.sin(2*np.pi*.05*t))
   out=(tone50*drift)[:,None]+0.24*lo+0.08*mid
  else:
   raise RuntimeError("Unknown synthesis algorithm "+kind)
  out=np.asarray(out,dtype=np.float32)
  if out.shape==(count,1):out=np.repeat(out,2,axis=1)
  assert out.shape==(count,2),("channel layout",out.shape)
  if self.gain is None:
   rms=float(np.sqrt(np.mean(out.astype(np.float64)**2)))
   assert rms>0.001,("silent source",kind,rms)
   self.gain=min(12.0,(0.030 if kind not in ("heartbeat","womb") else 0.033)/rms)
  out*=self.gain
  # Avoid digital discontinuity when native playback returns from minute 10 to 00.
  # The 55 ms edge ramp removes clicks, while the continuous body never repeats.
  fade=round(0.055*SR)
  if start<fade:
   left=min(count,fade-start)
   out[:left]*=((start+np.arange(left))/fade)[:,None]
  if start+count>FRAMES-fade:
   begin=max(0,FRAMES-fade-start)
   taper=(FRAMES-(start+np.arange(begin,count)))/fade
   out[begin:]*=np.clip(taper[:,None],0,1)
  out=np.tanh(out/0.93)*0.93
  peak=float(np.max(np.abs(out)))
  assert math.isfinite(peak) and peak<LIMIT,("peak safety",kind,peak)
  self.max_peak=max(self.max_peak,peak)
  self.energy+=float(np.sum(out.astype(np.float64)**2))
  self.samples+=out.size
  return out

def render(item,ix:int):
 OUT.mkdir(parents=True,exist_ok=True)
 ident=item["id"]
 outfile=OUT/(ident+".mp3")
 assert not outfile.exists(),"No silent overwrites of pre-existing artifacts"
 proc=subprocess.Popen([
  "ffmpeg","-hide_banner","-nostdin","-loglevel","error","-f","f32le",
  "-ar",str(SR),"-ac","2","-i","pipe:0","-map","0:a:0",
  "-ar",str(RATE),"-ac","2","-c:a","libmp3lame","-b:a","192k",
  "-t",str(SECONDS),"-y",str(outfile)
 ],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 r=Renderer(item["algorithm"],seed=0x6C6C2026+ix*19997)
 try:
  for start in range(0,FRAMES,CHUNK):
   count=min(CHUNK,FRAMES-start)
   audio=r.create(start,count)
   proc.stdin.write(audio.tobytes(order="C"))
  proc.stdin.close()
  proc.wait(timeout=270)
  err=proc.stderr.read().decode("utf8","replace")
  assert proc.returncode==0,("FFmpeg encoding failed",ident,err[-700:])
 except Exception:
  proc.kill()
  proc.wait()
  outfile.unlink(missing_ok=True)
  raise
 finally:
  proc.stderr.close()
 probe=json.loads(run(["ffprobe","-v","error","-show_entries",
  "format=duration,size:stream=codec_name,channels,sample_rate,bit_rate",
  "-of","json",str(outfile)]))
 duration=float(probe["format"]["duration"])
 assert 599.6<=duration<=600.6,(ident,"duration",duration)
 stream=probe["streams"][0]
 assert stream["codec_name"]=="mp3" and stream["channels"]==2 and int(stream["sample_rate"])==RATE
 assert 12_000_000<outfile.stat().st_size<16_000_000
 run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-xerror",
  "-i",str(outfile),"-f","null","-"],180)
 rms=(r.energy/r.samples)**0.5
 assert 0.010<=rms<=0.070,(ident,"RMS",rms)
 d={
   "record_id":ident,"title":item["review_label"],"source_kind":"original_procedural_DSP",
   "algorithm":item["algorithm"],"source_is_field_recording":False,
   "source_is_sample_loop":False,"rendered_independent_seconds":SECONDS,
   "review_only":True,"owner_listening_approved":False,"acoustic_human_qa":"PENDING",
   "source_seed":0x6C6C2026+ix*19997,
   "sha256":sha(outfile),"bytes":outfile.stat().st_size,
   "codec":"mp3","sample_rate_hz":RATE,"channels":2,"bitrate_kbps":192,
   "duration_seconds":round(duration,3),
   "sample_peak_max":round(r.max_peak,5),"render_rms":round(rms,6),
   "full_mp3_decode":"PASS","synthetic_content_label_required":True
 }
 print("C6C_DSP_RENDERED",json.dumps(d,sort_keys=True),flush=True)
 return d

def main():
 try:
  import shutil
  assert shutil.which("ffmpeg") and shutil.which("ffprobe")
  assert len(MANIFEST["items"])==10
  assert len(set(x["id"] for x in MANIFEST["items"]))==10
  assert set(x["id"] for x in MANIFEST["items"]).isdisjoint({"SND-0039","SND-0040"})
  manifest=[]
  for ix,row in enumerate(MANIFEST["items"]):
   manifest.append(render(row,ix))
  assert len(set(x["sha256"] for x in manifest))==10,"10 MP3 outputs must differ"
  report={"phase":"C6C_TEN_INDEPENDENT_SYNTH_REVIEW_ONLY",
   "rendered_count":len(manifest),"new_production_mp3":0,"new_seo_urls":0,
   "owner_approval":False,"synthetic_not_field":True,
   "generated_without_external_audio_assets":True,
   "items":manifest}
  (OUT/"audit.json").write_text(json.dumps(report,indent=2)+"\n")
  print("C6C_TEN_ORIGINAL_600S_SYNTH_MASTERS_PASS",flush=True)
 except Exception:
  (OUT/"audit.json").write_text(json.dumps({"phase":"C6C_BLOCKED_NOT_RELEASABLE",
   "error":"At least one 600s render or decode failed, no release allowed",
   "owner_approval":False},indent=2)+"\n")
  raise
if __name__=="__main__":main()
