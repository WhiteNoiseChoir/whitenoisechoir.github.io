#!/usr/bin/env python3
"""One-off 3-track licensed piano ingest. Never silently substitute a different song."""
import hashlib, html, json, os, re, subprocess, tempfile, urllib.parse, urllib.request
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET="whitenoisechoir-media"
ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
MUSIC=[
 {"slug":"splashkabona-inspiring-positive-cinematic-calming-ambient-piano","name":"Inspiring Positive Cinematic Calming Ambient Piano","artist":"Splashkabona","page":"https://freemusicarchive.org/music/splashkabona/single/inspiring-positive-cinematic-calming-ambient-piano/","expected":269,"license":"CC BY 4.0","credit":"Music: Inspiring Positive Cinematic Calming Ambient Piano by Splashkabona · CC BY 4.0 · https://creativecommons.org/licenses/by/4.0/"},
 {"slug":"pamela-yuen-in-the-light-of-fall","name":"In The Light Of Fall","artist":"Pamela Yuen","page":"https://freemusicarchive.org/music/pamela-yuen/piano-pieces/in-the-light-of-fall/","expected":123,"license":"CC BY 4.0","credit":"Music: In The Light Of Fall by Pamela Yuen · CC BY 4.0 · https://creativecommons.org/licenses/by/4.0/"},
 {"slug":"natureseye-reflections-of-winter","name":"Reflections of Winter","artist":"NaturesEye","page":"https://pixabay.com/music/solo-piano-reflections-of-winter-11662/","expected":227,"license":"Pixabay Content License","credit":"Music: Reflections of Winter by NaturesEye · Pixabay Content License"}
]
UA="Mozilla/5.0 (compatible; WhiteNoiseChoir-Internal-Asset-Intake/1.0)"
def req(url,limit=12_000_000):
    r=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"*/*","Referer":"https://freemusicarchive.org/" if "freemusicarchive" in url else "https://pixabay.com/"})
    with urllib.request.urlopen(r,timeout=35) as f:
        typ=f.headers.get("Content-Type","")
        data=f.read(limit+1)
        if len(data)>limit: raise RuntimeError("oversized source")
        return data,typ,f.geturl()
def urls_from_page(page):
    data,ct,final=req(page)
    body=html.unescape(data.decode("utf-8","replace")).replace("\\/","/")
    # Real audio URL must be explicitly present in the official source's HTML/metadata.
    patterns=[
      r'''(?:https?:)?//(?:files\.freemusicarchive\.org|cdn\.pixabay\.com|freemusicarchive\.org|pixabay\.com)[^"' <>\r\n\\]+''',
      r'''(?:https?:)?\\u002f\\u002f(?:files\.freemusicarchive\.org|cdn\.pixabay\.com)[^"' <>\r\n\\]+'''
    ]
    found=[]
    for p in patterns:
        for m in re.finditer(p,body,re.I):
            u=m.group(0).replace("\\u002F","/").replace("\\u002f","/")
            u=u.rstrip(");,}].")
            if u.startswith("//"): u="https:"+u
            parsed=urllib.parse.urlsplit(u)
            host=(parsed.hostname or "").lower()
            if host not in ("files.freemusicarchive.org","cdn.pixabay.com","freemusicarchive.org","pixabay.com"):continue
            if not (".mp3" in parsed.path.lower() or ("/download" in parsed.path.lower() and ("audio" in parsed.path.lower() or "track" in parsed.path.lower()))):continue
            if u not in found:found.append(u)
    # Also include official track download control, if linked within the HTML.
    for m in re.findall(r'''(?:href|data-url|data-download|data-src|src)\s*=\s*["']([^"']+)["']''',body,re.I):
        v=html.unescape(m)
        if v.startswith("/"):v=urllib.parse.urljoin(page,v)
        host=(urllib.parse.urlsplit(v).hostname or "").lower()
        if host in ("freemusicarchive.org","pixabay.com","files.freemusicarchive.org","cdn.pixabay.com") and (".mp3" in v.lower() or "/download" in v.lower()):
            if v not in found:found.append(v)
    return found
def probe(path):
    p=subprocess.run(["ffprobe","-v","error","-of","json","-show_entries","format=duration:stream=codec_name,sample_rate,channels,codec_type",str(path)],capture_output=True,text=True,timeout=40)
    if p.returncode: raise RuntimeError("ffprobe: "+p.stderr[-180:])
    x=json.loads(p.stdout)
    a=next((s for s in x.get("streams",[]) if s.get("codec_type")=="audio"),None)
    if a is None:raise RuntimeError("no audio stream")
    return {"duration":round(float(x["format"]["duration"]),3),"codec":a["codec_name"],"channels":a.get("channels"),"sample_rate":a.get("sample_rate")}
def get_s3():
    if not os.getenv("R2_ACCESS_KEY_ID") or not os.getenv("R2_SECRET_ACCESS_KEY"):raise RuntimeError("R2 secrets unavailable")
    return boto3.client("s3",endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",region_name="auto",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",s3={"addressing_style":"path"},retries={"max_attempts":4},request_checksum_calculation="when_required",response_checksum_validation="when_required"))
def main():
    output={"date":"2026-11-13","type":"three-piano-one-off","music":[]}
    s3=get_s3()
    with tempfile.TemporaryDirectory() as td:
        for src in MUSIC:
            record={k:src[k] for k in ("slug","name","artist","page","expected","license","credit")}
            try:
                options=urls_from_page(src["page"])
                record["candidate_count"]=len(options)
                errors=[]
                for url in options[:16]:
                    try:
                        audio,content_type,actual=req(url,65000000)
                        if len(audio)<120000 or (audio[:16].lower().startswith(b"<!doctype") or "html" in content_type.lower()):raise RuntimeError("not a full audio file")
                        f=Path(td)/(src["slug"]+".mp3")
                        f.write_bytes(audio)
                        meta=probe(f)
                        if not abs(meta["duration"]-src["expected"])<=8:raise RuntimeError("duration mismatch: "+str(meta["duration"]))
                        v=subprocess.run(["ffmpeg","-v","error","-nostdin","-i",str(f),"-f","null","-"],capture_output=True,text=True,timeout=100)
                        if v.returncode:raise RuntimeError("decode failure "+v.stderr[-120:])
                        sha=hashlib.sha256(audio).hexdigest()
                        key=f"asset-library/raw/sha256/{sha[:2]}/{sha}.mp3"
                        try:
                            head=s3.head_object(Bucket=BUCKET,Key=key)
                            if head["ContentLength"]!=len(audio):raise RuntimeError("R2 length collision")
                            action="reused"
                        except ClientError as ex:
                            if str(ex.response.get("Error",{}).get("Code")) not in ("404","NoSuchKey","NotFound"):raise
                            s3.put_object(Bucket=BUCKET,Key=key,Body=audio,ContentType="audio/mpeg",CacheControl="public, max-age=31536000, immutable",Metadata={"sha256":sha,"license":src["license"].replace(" ","_"),"origin":"music-source"})
                            action="uploaded"
                        check=s3.head_object(Bucket=BUCKET,Key=key)
                        if check["ContentLength"]!=len(audio):raise RuntimeError("R2 head verification failed")
                        record.update({"status":"STORED_R2","qa":"TECHNICAL_PASS_LISTENING_PENDING","key":key,"sha256":sha,"bytes":len(audio),"download_url":actual,"upload_action":action,**meta})
                        break
                    except Exception as exc:
                        errors.append(str(exc)[:160])
                if "status" not in record:
                    record["status"]="NOT_IMPORTED"
                    record["error"]="No source-provided downloadable full-length audio passed validation"
                    record["attempt_errors"]=errors[:8]
            except Exception as exc:
                record["status"]="NOT_IMPORTED"
                record["error"]=str(exc)[:350]
            output["music"].append(record)
            print("PIANO_INGEST_RESULT "+json.dumps(record,ensure_ascii=False),flush=True)
    Path("three-piano-r2-import-report.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print("PIANO_INGEST_SUMMARY "+json.dumps({"stored":sum(v.get("status")=="STORED_R2" for v in output["music"]),"missing":sum(v.get("status")!="STORED_R2" for v in output["music"])}),flush=True)
    if any(v["status"]!="STORED_R2" for v in output["music"]):raise SystemExit(1)
if __name__=="__main__":main()
