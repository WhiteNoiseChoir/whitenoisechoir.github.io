#!/usr/bin/env python3
"""Targeted 2026-11-13 R2 QA and one original Commons CC0 lakeshore import."""
import os,json,re,hashlib,subprocess,tempfile
from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime,timezone
import requests,boto3
from botocore.config import Config
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
BUCKET="whitenoisechoir-media"
PAGE="https://commons.wikimedia.org/wiki/File:17650_thoschi_issyk-kul.ogg"
UA={"User-Agent":"WhiteNoiseChoirAssetResearch/1.0 (https://whitenoisechoir.com)"}
EXISTING={
 "finch_lake_morning": "0d71302843d107b706717c6ea593c11366d5678ce00635f39913b392dba687fb.mp3",
 "yellowstone_lake": "602ab26a5e5f8a3a99b254bd03af0676d94eb04a679b95a8f7219700a991d3fd.mp3",
 "wind_gem_lake": "aa4bd8042d04eb6b956bc1721fe6856145526bda5ff89edd8bc78559cd38451c.mp3",
 "park_wind": "5c381856745b4706e7eba55eb9271a61a530e90c05df8126adb2db89ecfa6c5a.wav"
}
def sha_file(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for v in iter(lambda:f.read(262144),b""):h.update(v)
 return h.hexdigest()
def probe(p):
 c=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,sample_rate,channels","-of","json",str(p)],capture_output=True,text=True,timeout=40,check=True)
 d=json.loads(c.stdout);a=d["streams"][0]
 v=subprocess.run(["ffmpeg","-v","error","-nostdin","-i",str(p),"-map","0:a:0","-f","null","-"],capture_output=True,text=True,timeout=260)
 if v.returncode:raise ValueError("Full decode failed "+v.stderr[-250:])
 q=subprocess.run(["ffmpeg","-nostdin","-i",str(p),"-t","90","-af","loudnorm=I=-18:TP=-3:LRA=11:print_format=json","-f","null","-"],capture_output=True,text=True,timeout=70)
 m=re.search(r"\{\s*\"input_i\"[\s\S]*?\}",q.stderr)
 loud=json.loads(m.group(0)) if m else {}
 return {"duration":round(float(d["format"]["duration"]),3),"codec":a.get("codec_name"),"sample_rate":a.get("sample_rate"),"channels":a.get("channels"),"measured_lufs":loud.get("input_i"),"true_peak_db":loud.get("input_tp")}
def browse(key):
 try:
  r=requests.get("https://media.whitenoisechoir.com/"+key,headers={**UA,"Origin":"https://whitenoisechoir.com","Range":"bytes=0-1023"},timeout=18)
  return {"status":r.status_code,"cors":r.headers.get("Access-Control-Allow-Origin"),"bytes":len(r.content)}
 except Exception as e:return {"error":str(e)[:150]}
def main():
 s3=boto3.client("s3",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",region_name="auto",
  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
  config=Config(signature_version="s3v4",s3={"addressing_style":"path"}))
 report={"datetime":datetime.now(timezone.utc).isoformat(),"existing":[],"external":{}}
 with tempfile.TemporaryDirectory() as folder:
  for name,filename in EXISTING.items():
   h,ext=filename.split(".");key="asset-library/raw/sha256/"+h[:2]+"/"+filename
   d={"label":name,"key":key,"sha256":h}
   try:
    head=s3.head_object(Bucket=BUCKET,Key=key);p=Path(folder)/filename
    with p.open("wb") as f:s3.download_fileobj(BUCKET,key,f)
    d["head_bytes"]=head["ContentLength"]
    if sha_file(p)!=h:raise ValueError("R2 checksum mismatch")
    d.update(probe(p));d["range"]=browse(key);d["state"]="R2_SHA_FULL_DECODE_OK"
   except Exception as e:d.update(state="ERROR",error=str(e)[:230])
   report["existing"].append(d)
  ext={"source_page":PAGE}
  try:
   r=requests.get("https://commons.wikimedia.org/w/api.php",params={
    "action":"query","format":"json","formatversion":2,"titles":"File:17650 thoschi issyk-kul.ogg",
    "prop":"imageinfo","iiprop":"url|mime|size|extmetadata|user"},headers=UA,timeout=35);r.raise_for_status()
   i=r.json()["query"]["pages"][0]["imageinfo"][0]; meta=i.get("extmetadata") or {}
   lic=meta.get("LicenseShortName",{}).get("value","")
   if "CC0" not in lic.upper():raise ValueError("Original Commons licensing not CC0: "+lic)
   if not i.get("mime","").startswith("audio/") or int(i.get("size",0))>16000000:raise ValueError("Invalid or oversized original audio")
   url=i["url"]
   if urlsplit(url).hostname!="upload.wikimedia.org":raise ValueError("Unexpected source host")
   p=Path(folder)/"issyk-kul.ogg"
   with requests.get(url,headers=UA,stream=True,timeout=(20,60)) as r:
    r.raise_for_status()
    if urlsplit(r.url).hostname!="upload.wikimedia.org":raise ValueError("External redirect")
    n=0
    with p.open("wb") as f:
     for b in r.iter_content(262144):
      n+=len(b)
      if n>16000000:raise ValueError("Audio too large")
      f.write(b)
   if p.open("rb").read(4)!=b"OggS":raise ValueError("Not Ogg media")
   h=sha_file(p);key="asset-library/raw/sha256/"+h[:2]+"/"+h+".ogg"
   ext.update({"sha256":h,"key":key,"bytes":n,"license":lic})
   ext.update(probe(p))
   try:
    head=s3.head_object(Bucket=BUCKET,Key=key)
    ext["ingested"]="existing"
   except Exception:
    with p.open("rb") as f:s3.put_object(Bucket=BUCKET,Key=key,Body=f,ContentLength=n,IfNoneMatch="*",ContentType="audio/ogg",Metadata={"sha256":h,"license":"cc0-1.0"})
    head=s3.head_object(Bucket=BUCKET,Key=key)
    ext["ingested"]="new"
   if head["ContentLength"]!=n:raise ValueError("R2 HEAD bytes mismatch")
   record={"schema_version":2,"title":"Issyk Kul gentle lakeshore (source field recording)","source_page":PAGE,
     "source_provider":"Wikimedia Commons","license":"CC0-1.0","license_url":"https://creativecommons.org/publicdomain/zero/1.0/",
     "audio_sha256":h,"audio_storage_key":key,"file_bytes":n,"duration_seconds":ext["duration"],
     "codec":ext["codec"],"sample_rate_hz":ext["sample_rate"],"channels":ext["channels"],
     "group_hint":"lake-water","classification_status":"pending","classification_labels":[],"ingested_at":report["datetime"]}
   s3.put_object(Bucket=BUCKET,Key="asset-library/records/sha256/"+h[:2]+"/"+h+".json",
     Body=json.dumps(record).encode(),ContentType="application/json")
   ext["range"]=browse(key);ext["state"]="R2_SHA_FULL_DECODE_OK"
  except Exception as e:ext.update(state="NOT_IMPORTED",error=str(e)[:300])
  report["external"]=ext
 Path("sleeping-lake-qa-report.json").write_text(json.dumps(report,indent=2))
 lines=["## Sleeping Lake — targeted audio report","",
  "External original: "+ext["state"],"External SHA: "+ext.get("sha256","none"),
  "External R2 key: "+ext.get("key","none"),"External error: "+ext.get("error","none"),"",
  "### Existing R2 checks"]
 for s in report["existing"]:
  lines+=["- "+s["label"]+": "+s["state"]+"; duration="+str(s.get("duration"))+"; LUFS="+str(s.get("measured_lufs"))+"; true_peak="+str(s.get("true_peak_db"))+"; Range="+str(s.get("range"))+"; error="+s.get("error","none")]
 lines+=["","ffmpeg full decode does not prove browser WebAudio playback."]
 Path("sleeping-lake-qa-summary.md").write_text("\n".join(lines))
 print("SLEEPING_LAKE_QA_RESULT "+json.dumps(report),flush=True)
if __name__=="__main__":main()
