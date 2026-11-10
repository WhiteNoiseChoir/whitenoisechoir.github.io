#!/usr/bin/env python3
"""C6C owner-approved 10-audio media promotion to Cloudflare R2.

Only 10 new production identifiers. Originals are copied byte-exact from
previously verified R2 REVIEW MP3s. FFmpeg transcodes each 600s master into
AAC TS segments and a 7-day native iOS HLS timeline. NEVER touches legacy
35 MP3/HLS, 45 presets, existing library catalog or sitemap.
SEO page/indexing gates remain separate.
"""
from __future__ import annotations
import concurrent.futures,hashlib,json,math,os,re,subprocess,tempfile,time
from pathlib import Path
from urllib.request import Request,urlopen
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ROOT=Path(__file__).resolve().parents[1]
APPROVAL=json.loads((ROOT/"catalog/c6c-production-audio-approval.json").read_text())
R2_ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
BUCKET="whitenoisechoir-media"
PUBLIC="https://media.whitenoisechoir.com/"
OUT=Path("audits/c6c-production-promotion")
assert os.environ.get("R2_ACCESS_KEY_ID") and os.environ.get("R2_SECRET_ACCESS_KEY"),"R2 credentials missing"
s3=boto3.session.Session().client(
 "s3",region_name="auto",endpoint_url="https://"+R2_ACCOUNT+".r2.cloudflarestorage.com",
 aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
 aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
 config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
  retries={"max_attempts":5,"mode":"standard"},
  request_checksum_calculation="when_required",response_checksum_validation="when_required",
  connect_timeout=20,read_timeout=120))

def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()
def digest_remote(key):
 obj=s3.get_object(Bucket=BUCKET,Key=key); h=hashlib.sha256()
 try:
  for chunk in obj["Body"].iter_chunks(chunk_size=1048576):
   if chunk:h.update(chunk)
 finally:obj["Body"].close()
 return h.hexdigest()
def head(key):
 try:return s3.head_object(Bucket=BUCKET,Key=key)
 except ClientError as e:
  if str(e.response.get("Error",{}).get("Code")) in ("404","NoSuchKey","NotFound"):return None
  raise
def copy_from_review(row,target):
 key=row["approved_review_mp3"]
 assert re.fullmatch(r"review/c6c-20261110/SND-[0-9]{4}\.mp3",key)
 remote=s3.get_object(Bucket=BUCKET,Key=key)
 with target.open("wb") as f:
  h=hashlib.sha256()
  try:
   for chunk in remote["Body"].iter_chunks(chunk_size=1048576):
    if chunk:f.write(chunk);h.update(chunk)
  finally:remote["Body"].close()
 assert h.hexdigest()==row["approved_review_master_sha256"],"Reviewed original differs from user-approved hash"
 assert target.stat().st_size==14401453
 probe=json.loads(run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,channels,sample_rate",
  "-of","json",str(target)]))
 assert 599.8<float(probe["format"]["duration"])<600.3
 assert any(x.get("codec_name")=="mp3" and int(x.get("channels",0))==2 and int(x.get("sample_rate",0))==44100 for x in probe["streams"])
 return target
def run(args,timeout=240):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if p.returncode:raise RuntimeError(str(args[:5])+" "+p.stderr[-1000:])
 return p.stdout
def render_hls(mp3,folder):
 folder.mkdir(parents=True,exist_ok=True)
 template=folder/"source.m3u8"
 run(["ffmpeg","-hide_banner","-nostdin","-loglevel","error","-xerror","-y",
  "-i",str(mp3),"-map","0:a:0","-ar","44100","-ac","2","-c:a","aac","-b:a","192k",
  "-f","hls","-hls_time","65","-hls_segment_type","mpegts","-hls_list_size","0",
  "-hls_playlist_type","vod","-hls_segment_filename",str(folder/"part_%03d.ts"),str(template)],timeout=260)
 lines=template.read_text().splitlines()
 pieces=[]
 for i,line in enumerate(lines):
  if not line.startswith("#EXTINF:"):continue
  dur=float(line.split(":",1)[1].split(",")[0])
  n=lines[i+1].strip()
  assert re.fullmatch(r"part_\d{3}\.ts",n)
  assert (folder/n).is_file() and (folder/n).stat().st_size>=50000
  pieces.append((n,dur))
 assert 9<=len(pieces)<=11,("unexpected HLS source cycle",len(pieces))
 cycle=sum(dur for _,dur in pieces)
 assert 599<=cycle<=602,("HLS source cycle duration",cycle)
 count=math.ceil(7*86400/cycle)
 rows=["#EXTM3U","#EXT-X-VERSION:3",
  "#EXT-X-TARGETDURATION:"+str(math.ceil(max(d for _,d in pieces))),
  "#EXT-X-MEDIA-SEQUENCE:0","#EXT-X-PLAYLIST-TYPE:VOD","#EXT-X-INDEPENDENT-SEGMENTS"]
 for i in range(count):
  if i:rows.append("#EXT-X-DISCONTINUITY")
  for n,dur in pieces:rows+=["#EXTINF:"+format(dur,".6f")+",",n]
 rows.append("#EXT-X-ENDLIST")
 playlist=folder/"continuous.m3u8"
 playlist.write_text("\n".join(rows)+"\n")
 template.unlink()
 assert "#EXT-X-ENDLIST" in playlist.read_text()
 assert (playlist.read_text().count("#EXT-X-DISCONTINUITY"))==count-1
 sample=json.loads(run(["ffprobe","-v","error","-show_entries","stream=codec_name,sample_rate,channels","-of","json",str(folder/pieces[0][0])]))
 assert sample["streams"][0]["codec_name"]=="aac"
 assert int(sample["streams"][0]["sample_rate"])==44100
 assert int(sample["streams"][0]["channels"])==2
 return playlist,[folder/n for n,_ in pieces],cycle,count
def put_immutable(key,path,mime):
 assert (key.startswith("audio/c6c-") or key.startswith("audio/continuous/c6c-"))
 assert key.endswith((".mp3",".m3u8",".ts"))
 expect=sha(path); n=path.stat().st_size
 old=head(key)
 if old:
  assert int(old["ContentLength"])==n and old.get("Metadata",{}).get("sha256")==expect, \
   "Refuse overwrite unexpected existing audio production object "+key
  action="reused-identical"
 else:
  with path.open("rb") as f:
   s3.put_object(Bucket=BUCKET,Key=key,Body=f,ContentLength=n,
    ContentType=mime,CacheControl="public, max-age=300",
    Metadata={"sha256":expect,"owner_approved":"2026-11-10","source":"c6c-reviewed-original-dsp"})
  action="new-approved"
 out=head(key)
 assert int(out["ContentLength"])==n and out.get("Metadata",{}).get("sha256")==expect
 assert out.get("ContentType","").split(";")[0]==mime.split(";")[0]
 assert digest_remote(key)==expect
 return {"key":key,"sha256":expect,"bytes":n,"action":action}
def public_range(info,path,mime):
 key=info["key"];url=PUBLIC+key
 for attempt in range(5):
  try:
   with urlopen(Request(url,headers={"Range":"bytes=0-2047","User-Agent":"WNC-C6C-Production-R2-Range/1.0"}),timeout=40) as resp:
    code=resp.status;read=resp.read();content_type=resp.headers.get("Content-Type","").split(";")[0]
   with path.open("rb") as f:expect=f.read(2048)
   assert code==206 and read==expect and content_type==mime.split(";")[0]
   return "HTTP_206_EXACT_BYTES_PASS"
  except Exception:
   if attempt==4:raise
   time.sleep(2+attempt*2)
def build_one(row):
 ident=row["production_id"]
 assert re.fullmatch(r"c6c-[a-z0-9-]+",ident)
 assert row["owner_listening_status"]=="APPROVED_BY_OWNER_2026-11-10"
 assert row["license"]=="original_whiteNoiseChoir_DSP"
 with tempfile.TemporaryDirectory(prefix="wnc-c6c-production-") as tmp:
  folder=Path(tmp);master=copy_from_review(row,folder/"master.mp3")
  playlist,segments,cycle,repeats=render_hls(master,folder/"hls")
  verified=[]
  # Upload MP3 + segments first, then playlist after all media.
  mp3_key=row["approved_production_mp3"]
  assert mp3_key=="audio/"+ident+".mp3"
  verified.append(put_immutable(mp3_key,master,"audio/mpeg"))
  segment_pre="audio/continuous/"+ident+"/"
  for p in segments:verified.append(put_immutable(segment_pre+p.name,p,"video/mp2t"))
  hls_key=row["approved_hls_playlist"]
  assert hls_key==segment_pre+"continuous.m3u8"
  verified.append(put_immutable(hls_key,playlist,"application/vnd.apple.mpegurl"))
  # Actual public transport, HLS is text but must support range and play on iOS.
  sample_paths={mp3_key:(master,"audio/mpeg"),
                segment_pre+segments[0].name:(segments[0],"video/mp2t"),
                hls_key:(playlist,"application/vnd.apple.mpegurl")}
  transport={key:public_range(next(x for x in verified if x["key"]==key),p,mime)
             for key,(p,mime) in sample_paths.items()}
  obj={"record_id":row["record_id"],"production_id":ident,"approved_source_sha256":row["approved_review_master_sha256"],
   "production_sha256":sha(master),"source_cycle_seconds":round(cycle,3),
   "seven_day_cycles":repeats,"native_stream_hours":round(cycle*repeats/3600,2),
   "hls_segment_count":len(segments),"new_keys":verified,"public_range":transport,
   "production_audio_verified":True,"seo_indexing_approved":False}
  print("C6C_APPROVED_MEDIA_PASS",json.dumps({"id":ident,"source_sha":obj["production_sha256"],
   "segments":len(segments),"hours":obj["native_stream_hours"]}),flush=True)
  return obj
def main():
 assert APPROVAL["additional_sources"]==len(APPROVAL["items"])==10
 assert APPROVAL["previous_production_sources"]==35 and APPROVAL["existing_presets"]==45
 assert APPROVAL["seo_indexing_approved"] is False
 assert len(set(x["production_id"] for x in APPROVAL["items"]))==10
 OUT.mkdir(parents=True,exist_ok=True)
 # Limit simultaneous FFmpeg to avoid runner CPU/peak memory contention.
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  results=list(pool.map(build_one,APPROVAL["items"]))
 assert len(results)==10 and len(set(x["production_sha256"] for x in results))==10
 report={"release":"C6C-2026-11-10","status":"PRODUCTION_AUDIO_BYTES_AND_HLS_READY",
  "approved_by_user":True,"new_production_sources":10,"previous":35,"total":45,"presets_preserved":45,
  "source_type":"original_DSP_not_field_recording","owner_approval_reference":APPROVAL["owner_approval_reference"],
  "production_audio_live":True,"separate_website_integration_required":True,
  "site_indexing_not_approved":True,"items":results}
 (OUT/"audit.json").write_text(json.dumps(report,indent=2)+"\n")
 print("C6C_TEN_APPROVED_PRODUCTION_MP3_AND_7DAY_HLS_LIVE_PASS",flush=True)
if __name__=="__main__":main()
