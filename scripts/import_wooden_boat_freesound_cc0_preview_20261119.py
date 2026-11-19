#!/usr/bin/env python3
"""Try authorized publicly served CC0 Freesound MP3 PREVIEWS of boat field recordings.
Does NOT access Freesound original files behind login, bypass access controls,
or present previews as masters. Scoped to exact creator/source pages reviewed
for CC0 on 2026-11-19. Fail closed on source, license, or preview mismatch.
"""
import hashlib,html,json,os,re,subprocess,tempfile,urllib.request,urllib.parse,pathlib
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET="whitenoisechoir-media"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
SOURCES=[
 {"id":265553,"creator":"AugustSandberg","name":"Moored sailboat interior in strong breeze","approx_duration":395.129,"page":"https://freesound.org/people/AugustSandberg/sounds/265553/"},
 {"id":439368,"creator":"Falcet","name":"Ambience Sea Boat Night Ropes 1","approx_duration":120.319,"page":"https://freesound.org/people/Falcet/sounds/439368/"},
 {"id":627067,"creator":"KaleidacousticsAudio","name":"Anchored boat rolling Below deck recording","approx_duration":219.959,"page":"https://freesound.org/people/KaleidacousticsAudio/sounds/627067/"}
]

def get(url,maxsize,ctype_is_audio=False):
    q=urllib.request.Request(url,headers={"User-Agent":"WhiteNoiseChoir/1.0 CC0 audition asset intake","Accept":"text/html,audio/mpeg,*/*;q=0.2"})
    with urllib.request.urlopen(q,timeout=38) as r:
        typ=(r.headers.get("content-type") or "").lower()
        data=r.read(maxsize+1)
        if len(data)>maxsize:raise ValueError("MAX_BYTES_REACHED")
        if ctype_is_audio and ("html" in typ or data.startswith(b"<")):raise ValueError("HTML_NOT_MP3")
    return data

def resolve_preview(page,sound_id):
    raw=get(page,1800000)
    t=html.unescape(raw.decode("utf-8","replace"))
    t=t.replace("\\/", "/").replace("\\u002F","/").replace("\\u002f","/")
    if "Creative Commons 0" not in t and "CC0" not in t:raise ValueError("SOURCE_NOT_DECLARING_CC0")
    if "freesound" not in t.lower():raise ValueError("INVALID_SOURCE_PAGE")
    patterns=[
        r'(https?://(?:cdn\\.)?freesound\\.org/(?:data/)?previews/\\d+/'+str(sound_id)+r'_[^"\\s<>]+?\\.mp3)',
        r'((?:/data)?/previews/\\d+/'+str(sound_id)+r'_[^"\\s<>]+?\\.mp3)',
    ]
    matches=[]
    for pattern in patterns:
        matches.extend(re.findall(pattern,t,flags=re.I))
    urls=[]
    for candidate in matches:
        candidate=candidate.split("?")[0]
        if candidate.startswith("/"):candidate="https://cdn.freesound.org"+candidate.replace("/data/previews/","/previews/")
        candidate=candidate.replace("https://freesound.org/data/previews/","https://cdn.freesound.org/previews/")
        candidate=candidate.replace("https://freesound.org/previews/","https://cdn.freesound.org/previews/")
        u=urllib.parse.urlparse(candidate)
        if u.scheme=="https" and u.hostname=="cdn.freesound.org" and re.search(r'/previews/\\d+/'+str(sound_id)+r'_',u.path):
            urls.append(candidate)
    urls=list(dict.fromkeys(urls))
    # Prefer HQ preview when source page actually provides one.
    urls.sort(key=lambda u:(("-hq.mp3" not in u),len(u)))
    if not urls:raise ValueError("NO_PUBLIC_PREVIEW_LINK_ON_LICENSE_PAGE")
    return urls[0]

def probe(data,path,approx):
    path.write_bytes(data)
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,codec_name,sample_rate,channels","-of","json",str(path)],capture_output=True,text=True,timeout=30)
    if p.returncode:raise ValueError("FFPROBE_"+p.stderr[-150:])
    doc=json.loads(p.stdout)
    streams=[a for a in doc.get("streams",[]) if a.get("codec_type")=="audio"]
    if len(streams)!=1 or streams[0].get("codec_name")!="mp3":raise ValueError("NOT_MP3_AUDIO")
    dur=float(doc["format"]["duration"])
    if dur<20 or abs(dur-approx)>10:raise ValueError("DURATION_NOT_MATCHING_SOURCE")
    dec=subprocess.run(["ffmpeg","-hide_banner","-v","error","-nostdin","-i",str(path),"-f","null","-"],capture_output=True,text=True,timeout=100)
    if dec.returncode:raise ValueError("FULL_DECODE_FAILED")
    return {"duration_seconds":round(dur,3),"codec":"mp3","sample_rate":streams[0].get("sample_rate"),"channels":streams[0].get("channels")}

def main():
    if not os.getenv("R2_ACCESS_KEY_ID") or not os.getenv("R2_SECRET_ACCESS_KEY"):raise ValueError("MISSING_R2_CREDENTIALS")
    s3=boto3.client("s3",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",region_name="auto",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",s3={"addressing_style":"path"},connect_timeout=20,read_timeout=70,retries={"mode":"standard","max_attempts":4},request_checksum_calculation="when_required",response_checksum_validation="when_required"))
    report={"schema":"wnc_freesound_boat_cc0_preview_v1","date":"2026-11-19","status":"PREVIEW_ONLY_NOT_RELEASE_APPROVED","assets":[],"errors":[]}
    with tempfile.TemporaryDirectory() as td:
        for src in SOURCES:
            try:
                url=resolve_preview(src["page"],src["id"])
                data=get(url,35_000_000,True)
                if len(data)<100_000:raise ValueError("PREVIEW_TOO_SMALL")
                meta=probe(data,pathlib.Path(td)/(str(src["id"])+".mp3"),src["approx_duration"])
                sha=hashlib.sha256(data).hexdigest()
                key=f"asset-library/raw/sha256/{sha[:2]}/{sha}.mp3"
                try:head=s3.head_object(Bucket=BUCKET,Key=key)
                except ClientError as e:
                    if str(e.response.get("Error",{}).get("Code")) in ("404","NoSuchKey","NotFound"):head=None
                    else:raise
                if head is None:
                    s3.put_object(Bucket=BUCKET,Key=key,Body=data,ContentType="audio/mpeg",CacheControl="public,max-age=31536000,immutable",Metadata={"sha256":sha,"license":"CC0","media-quality":"preview","freesound-id":str(src["id"])})
                    action="uploaded"
                else:
                    if head["ContentLength"]!=len(data):raise ValueError("EXISTING_SHA_KEY_SIZE_MISMATCH")
                    action="reused"
                obj=s3.get_object(Bucket=BUCKET,Key=key)
                read=obj["Body"].read();obj["Body"].close()
                if hashlib.sha256(read).hexdigest()!=sha:raise ValueError("R2_SHA_READBACK_FAILED")
                row={"source":src["page"],"name":src["name"],"creator":src["creator"],"freesound_id":src["id"],"declared_license":"CC0","type":"PUBLIC_FREESOUND_PREVIEW_NOT_ORIGINAL","preview_url":url,"sha256":sha,"assetRef":"r2-"+sha,"key":key,"r2_bucket":BUCKET,"action":action,"bytes":len(data),"studio_ready":False,"publication_approved":False,**meta}
                report["assets"].append(row)
                print("WNC_FIELD_BOAT_CC0_OK "+json.dumps(row,ensure_ascii=False),flush=True)
            except Exception as e:
                row={"id":src["id"],"error":str(e)[:350]}
                report["errors"].append(row)
                print("WNC_FIELD_BOAT_CC0_ERROR "+json.dumps(row),flush=True)
    pathlib.Path("audits").mkdir(exist_ok=True)
    pathlib.Path("audits/wooden-boat-freesound-cc0-preview-report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("WNC_FIELD_BOAT_SUMMARY "+json.dumps({"imported":len(report["assets"]),"errors":len(report["errors"])}),flush=True)
    if not report["assets"]:raise SystemExit(2)

if __name__=="__main__":main()
