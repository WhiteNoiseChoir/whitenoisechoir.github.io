#!/usr/bin/env python3
"""Single-project, rights-reviewed audio intake. No production Studio mutations."""
import hashlib, json, os, subprocess, tempfile, urllib.request, urllib.parse, time, pathlib
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET="whitenoisechoir-media"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
SOURCES=[
  {"slug":"years-grow-quiet-piano","filename":'Relaxing Piano Instrumental - "The Years Grow Quiet".flac',"license":"CC-BY-4.0","creator":"Mcwpiano","source_url":'https://commons.wikimedia.org/wiki/File:Relaxing_Piano_Instrumental_-_%22The_Years_Grow_Quiet%22.flac',"expected_duration_s":254.0,"max_bytes":105000000,"group":"music","composition_rights":"Self-published own-work claim by uploader, further publication review pending"},
  {"slug":"sleeping-train-wheels","filename":"Стук колёс поезда.ogg","license":"CC0-1.0","creator":"Ural-66","source_url":"https://commons.wikimedia.org/wiki/File:%D0%A1%D1%82%D1%83%D0%BA_%D0%BA%D0%BE%D0%BB%D1%91%D1%81_%D0%BF%D0%BE%D0%B5%D0%B7%D0%B4%D0%B0.ogg","expected_duration_s":241.0,"max_bytes":15000000,"group":"transit","composition_rights":"Original field recording; declared CC0 by source page"}
]
def fetch(item,dst):
    name=urllib.parse.quote(item["filename"])
    url="https://commons.wikimedia.org/wiki/Special:Redirect/file/"+name
    last=None
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"WhiteNoiseChoir-Audio-Intake/1.0 (https://whitenoisechoir.com)","Accept":"audio/*,application/octet-stream;q=0.8"})
            with urllib.request.urlopen(req,timeout=95) as r,open(dst,"wb") as f:
                typ=r.headers.get("Content-Type","")
                if "html" in typ or "json" in typ: raise ValueError("not-audio response: "+typ)
                total=0
                while True:
                    block=r.read(1024*512)
                    if not block: break
                    total+=len(block)
                    if total>item["max_bytes"]:raise ValueError("source too large")
                    f.write(block)
            if total<100000:raise ValueError("source too small")
            return url,total
        except Exception as exc:
            last=str(exc)
            if os.path.exists(dst):os.unlink(dst)
            time.sleep(2*(attempt+1))
    raise RuntimeError("Download blocked: "+str(last))
def probe(file,expected):
    cmd=["ffprobe","-v","error","-show_entries","format=duration,format_name:stream=codec_name,channels,sample_rate,codec_type","-of","json",file]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    if p.returncode:raise RuntimeError("ffprobe failed "+p.stderr[-200:])
    d=json.loads(p.stdout)
    streams=[s for s in d["streams"] if s.get("codec_type")=="audio"]
    if len(streams)!=1:raise RuntimeError("Expected one audio stream")
    duration=float(d["format"]["duration"])
    if abs(duration-expected)>9:raise RuntimeError("Duration differs from source page: "+str(duration))
    c=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-v","error","-i",file,"-f","null","-"],capture_output=True,text=True,timeout=300)
    if c.returncode:raise RuntimeError("Full decode failed "+c.stderr[-250:])
    return {"duration_s":round(duration,3),"codec":streams[0].get("codec_name"),"channels":streams[0].get("channels"),"sample_rate":streams[0].get("sample_rate")}
def main():
    ak=os.getenv("R2_ACCESS_KEY_ID");sk=os.getenv("R2_SECRET_ACCESS_KEY")
    if not ak or not sk:raise RuntimeError("R2 credentials unavailable")
    cli=boto3.client("s3",endpoint_url=f"https://{ACCOUNT}.r2.cloudflarestorage.com",region_name="auto",
      aws_access_key_id=ak,aws_secret_access_key=sk,config=Config(signature_version="s3v4",s3={"addressing_style":"path"},retries={"max_attempts":4}))
    results=[]
    with tempfile.TemporaryDirectory() as d:
        for item in SOURCES:
            dst=os.path.join(d,item["slug"]+pathlib.Path(item["filename"]).suffix)
            try:
                downloaded_url,n=fetch(item,dst)
                info=probe(dst,item["expected_duration_s"])
                h=hashlib.sha256()
                with open(dst,"rb") as f:
                    while True:
                        b=f.read(1024*1024)
                        if not b:break
                        h.update(b)
                sha=h.hexdigest()
                ext=pathlib.Path(item["filename"]).suffix.lower()
                key=f"asset-library/raw/sha256/{sha[:2]}/{sha}{ext}"
                mime="audio/flac" if ext==".flac" else "audio/ogg"
                try:
                    hd=cli.head_object(Bucket=BUCKET,Key=key)
                    if hd["ContentLength"]!=n:raise RuntimeError("R2 existing size mismatch")
                    action="reused"
                except ClientError as e:
                    if str(e.response.get("Error",{}).get("Code")) not in ("404","NoSuchKey","NotFound"):raise
                    cli.upload_file(dst,BUCKET,key,ExtraArgs={"ContentType":mime,"Metadata":{"sha256":sha,"license":item["license"].lower(),"source":"wikimedia-commons"}})
                    action="uploaded"
                hd=cli.head_object(Bucket=BUCKET,Key=key)
                if hd["ContentLength"]!=n:raise RuntimeError("R2 HEAD bytes mismatch")
                # Studio-friendly 44.1kHz 192kbps stereo MP3 derivative, keeping source master intact
                mp3=os.path.join(d,item["slug"]+"-studio.mp3")
                trans=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-y","-v","error","-i",dst,
                    "-map","0:a:0","-ar","44100","-ac","2","-c:a","libmp3lame","-b:a","192k",mp3],
                    capture_output=True,text=True,timeout=300)
                if trans.returncode:raise RuntimeError("Studio MP3 transcode failed: "+trans.stderr[-250:])
                studio_info=probe(mp3,item["expected_duration_s"])
                hs=hashlib.sha256()
                with open(mp3,"rb") as f:
                    while True:
                        b=f.read(1024*1024)
                        if not b:break
                        hs.update(b)
                studio_sha=hs.hexdigest()
                studio_key=f"asset-library/raw/sha256/{studio_sha[:2]}/{studio_sha}.mp3"
                studio_bytes=os.stat(mp3).st_size
                try:
                    dh=cli.head_object(Bucket=BUCKET,Key=studio_key)
                    if dh["ContentLength"]!=studio_bytes:raise RuntimeError("Studio R2 existing bytes mismatch")
                    studio_action="reused"
                except ClientError as e:
                    if str(e.response.get("Error",{}).get("Code")) not in ("404","NoSuchKey","NotFound"):raise
                    cli.upload_file(mp3,BUCKET,studio_key,ExtraArgs={"ContentType":"audio/mpeg",
                        "Metadata":{"sha256":studio_sha,"source-master-sha256":sha,"license":item["license"].lower()}})
                    studio_action="uploaded"
                dh=cli.head_object(Bucket=BUCKET,Key=studio_key)
                if dh["ContentLength"]!=studio_bytes:raise RuntimeError("Studio object HEAD failed")
                playback_url="https://media.whitenoisechoir.com/"+studio_key
                request=urllib.request.Request(playback_url,headers={"Range":"bytes=0-127",
                    "Origin":"https://whitenoisechoir.com","User-Agent":"WhiteNoiseChoir-Audio-Intake/1.0"})
                with urllib.request.urlopen(request,timeout=40) as test:
                    code=test.status
                    cors=test.headers.get("Access-Control-Allow-Origin","")
                    content=test.read(128)
                if code!=206 or len(content)!=128 or cors not in ("*","https://whitenoisechoir.com"):
                    raise RuntimeError(f"Public playback Range/CORS verification failed: status={code}, cors={cors}")
                rec={k:item[k] for k in ("slug","filename","license","creator","source_url","group","composition_rights")}
                rec.update({"status":"R2_STORED_QA_TECHNICAL_PASS_LISTENING_PENDING","assetRef":"r2-"+sha,"sha256":sha,"r2_key":key,"public_url":"https://media.whitenoisechoir.com/"+key,"bytes":n,"action":action,"downloaded_url":downloaded_url,
                    "studio_asset_ref":"r2-"+studio_sha,"studio_sha256":studio_sha,"studio_key":studio_key,
                    "studio_public_url":playback_url,"studio_bytes":studio_bytes,"studio_action":studio_action,
                    "studio_range_cors_verified":True,"studio_audio":studio_info,**info})
                print("WNC_INTAKE_OK "+json.dumps(rec,ensure_ascii=False),flush=True)
                results.append(rec)
            except Exception as exc:
                msg={"slug":item["slug"],"status":"FAILED","error":str(exc)[:450]}
                print("WNC_INTAKE_FAILED "+json.dumps(msg,ensure_ascii=False),flush=True)
                results.append(msg)
    pathlib.Path("midnight-rain-train-import-report.json").write_text(json.dumps({"project":"midnight-rain-train-v1","assets":results},ensure_ascii=False,indent=2))
    if any(x["status"]=="FAILED" for x in results):raise SystemExit(1)
if __name__=="__main__":main()
