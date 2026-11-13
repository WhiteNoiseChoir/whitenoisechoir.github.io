#!/usr/bin/env python3
"""Prepare immutable balanced audio derivatives in R2 for Sleeping Lake V2."""
import os,json,hashlib,re,requests,subprocess,tempfile
from pathlib import Path
from botocore.config import Config
import boto3
from botocore.exceptions import ClientError
SRC=[
("lake","a512974fcff448950f86fa26d07fbb8d52b55e8cbdf24e8d721f42161a1d7f53","ogg",-25.5,-4.0,10),
("gem_wind","aa4bd8042d04eb6b956bc1721fe6856145526bda5ff89edd8bc78559cd38451c","mp3",-27.0,-5.0,9),
("park_wind","5c381856745b4706e7eba55eb9271a61a530e90c05df8126adb2db89ecfa6c5a","wav",-31.5,-7.0,8),
]
BUCKET="whitenoisechoir-media"
ROOT="https://media.whitenoisechoir.com/"
def run(args):
 p=subprocess.run(args,text=True,capture_output=True,timeout=360)
 if p.returncode:raise RuntimeError("ffmpeg "+(p.stderr or p.stdout)[-600:])
 return p
def digest(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def meter(path,fil=None):
 p=run(["ffmpeg","-hide_banner","-nostdin","-i",str(path),"-vn","-af",fil or "loudnorm=I=-24:TP=-3:LRA=11:print_format=json","-f","null","-"])
 q=re.findall(r'\{\s*"input_i"[\s\S]*?\}',p.stderr)
 if not q:raise ValueError("Missing loudness stats")
 return json.loads(q[-1])
def probe(path):
 p=run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,sample_rate,channels","-of","json",str(path)])
 j=json.loads(p.stdout);a=j["streams"][0]
 return {"duration":round(float(j["format"]["duration"]),3),"codec":a["codec_name"],"sample_rate":int(a["sample_rate"]),"channels":int(a["channels"])}
def main():
 s3=boto3.client("s3",region_name="auto",endpoint_url="https://7483501ad8365fe26b0448b96b54fb9f.r2.cloudflarestorage.com",
 aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
 config=Config(signature_version="s3v4",s3={"addressing_style":"path"}))
 results=[]
 with tempfile.TemporaryDirectory() as work:
  for role,parent,ext,target,tp,lra in SRC:
   oldkey="asset-library/raw/sha256/"+parent[:2]+"/"+parent+"."+ext
   inp=Path(work)/(role+"_source."+ext)
   with requests.get(ROOT+oldkey,timeout=180,stream=True) as response:
    response.raise_for_status()
    with inp.open("wb") as f:
     for chunk in response.iter_content(1024*1024):f.write(chunk)
   if digest(inp)!=parent:raise ValueError("SHA mismatch for "+role)
   before=meter(inp)
   fil=f"loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json"
   first=meter(inp,fil)
   second=(f"loudnorm=I={target}:TP={tp}:LRA={lra}:measured_I={first['input_i']}"
           f":measured_TP={first['input_tp']}:measured_LRA={first['input_lra']}"
           f":measured_thresh={first['input_thresh']}:offset={first['target_offset']}:linear=false")
   out=Path(work)/(role+".mp3")
   run(["ffmpeg","-hide_banner","-nostdin","-y","-i",str(inp),"-map","0:a:0","-af",second,
        "-ac","2","-ar","44100","-codec:a","libmp3lame","-b:a","192k",str(out)])
   run(["ffmpeg","-v","error","-nostdin","-i",str(out),"-f","null","-"])
   after=meter(out);info=probe(out);oldinfo=probe(inp)
   if abs(float(after["input_i"])-target)>3:raise ValueError(role+" loudness out of target")
   if float(after["input_tp"])>-2.5:raise ValueError(role+" peak too high")
   if abs(info["duration"]-oldinfo["duration"])>.6:raise ValueError(role+" duration mismatch")
   sha=digest(out);key="asset-library/raw/sha256/"+sha[:2]+"/"+sha+".mp3"
   try:
    with out.open("rb") as f:s3.put_object(Bucket=BUCKET,Key=key,Body=f,ContentLength=out.stat().st_size,
      ContentType="audio/mpeg",IfNoneMatch="*",Metadata={"sha256":sha,"source-sha256":parent,"processing":"sleeping-lake-v2-normalized"})
    state="NEW"
   except ClientError as err:
    if err.response["ResponseMetadata"]["HTTPStatusCode"]!=412:raise
    state="REUSED"
   head=s3.head_object(Bucket=BUCKET,Key=key)
   if head["ContentLength"]!=out.stat().st_size or head.get("Metadata",{}).get("sha256")!=sha:raise ValueError(role+" R2 object mismatch")
   resp=requests.get(ROOT+key,headers={"Origin":"https://whitenoisechoir.com","Range":"bytes=0-1023"},timeout=30)
   if resp.status_code!=206 or resp.headers.get("Access-Control-Allow-Origin") not in ("*","https://whitenoisechoir.com"):
    raise ValueError(role+" CORS/Range missing")
   entry={"role":role,"sha256":sha,"key":key,"parent_sha256":parent,"parent_key":oldkey,"state":state,
     "source_lufs":before["input_i"],"output_lufs":after["input_i"],"output_true_peak":after["input_tp"],
     "target_lufs":target,"target_tp":tp,"duration":info["duration"],"sample_rate":info["sample_rate"],"channels":info["channels"],
     "codec":info["codec"],"bytes":head["ContentLength"],"r2_head":True,"cors_range":True}
   results.append(entry)
   print("SLEEPING_LAKE_V2_ASSET "+json.dumps(entry),flush=True)
 report={"status":"QA_PASS","sources":results,"new_sources_from_internet":0,"derivative_assets":len(results),
 "note":"Sources reprocessed from original R2 assets. Listening and full-mix loudness QA pending."}
 Path("sleeping-lake-v2-derivatives.json").write_text(json.dumps(report,indent=2))
 summary=["## Sleeping Lake V2 - derivative asset report",""]
 for a in results:summary += ["- "+a["role"]+": "+a["sha256"]+" | "+str(a["source_lufs"])+" -> "+str(a["output_lufs"])+" LUFS | "+str(a["output_true_peak"])+" dBTP; "+a["state"]]
 summary+=["","All source checks include SHA, full decode, duration, R2 HEAD, CORS and 206 Range. Browser + full-mix mastering remain separate."]
 Path("sleeping-lake-v2-derivatives.md").write_text("\n".join(summary))
 print("SLEEPING_LAKE_V2_REPORT "+json.dumps(report),flush=True)
if __name__=="__main__":main()
