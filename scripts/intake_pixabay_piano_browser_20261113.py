#!/usr/bin/env python3
"""Use standard headless Chrome's official Pixabay Free download button, no access-control bypass."""
import hashlib, json, os, re, subprocess, tempfile, time
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

PAGE="https://pixabay.com/music/solo-piano-reflections-of-winter-11662/"
BUCKET="whitenoisechoir-media"
ACCOUNT_ID="7483501ad8365fe26b0448b96b54fb9f"
def main():
    record={"source":PAGE,"title":"Reflections of Winter","artist":"NaturesEye","license":"Pixabay Content License","status":"NOT_IMPORTED"}
    try:
        with tempfile.TemporaryDirectory() as td:
            options=Options()
            for v in ("--headless=new","--no-sandbox","--disable-dev-shm-usage","--disable-gpu","--window-size=1366,900"):
                options.add_argument(v)
            options.add_experimental_option("prefs",{"download.default_directory":td,"download.prompt_for_download":False,"download.directory_upgrade":True,"safebrowsing.enabled":True})
            options.set_capability("goog:loggingPrefs",{"performance":"ALL"})
            d=webdriver.Chrome(options=options)
            try:
                d.execute_cdp_cmd("Page.setDownloadBehavior",{"behavior":"allow","downloadPath":td})
                d.set_page_load_timeout(50)
                d.get(PAGE)
                time.sleep(8)
                record["page_title"]=d.title
                record["page_url"]=d.current_url
                body=d.page_source
                record["page_chars"]=len(body)
                record["page_excerpt"]=re.sub(r"\s+"," ",d.find_element(By.TAG_NAME,"body").text)[:350]
                if "Reflections of Winter" not in body and "Reflections of winter" not in body:raise RuntimeError("Pixabay track not displayed in standard Chrome browser")
                buttons=d.find_elements(By.XPATH,"//button[contains(., 'Free download')]")
                record["download_button_count"]=len(buttons)
                if not buttons:raise RuntimeError("Official Free download button missing")
                buttons[0].click()
                time.sleep(3)
                for b in d.find_elements(By.XPATH,"//button[contains(., 'Download')]"):
                    if b.is_displayed() and b.is_enabled() and b!=buttons[0]:
                        try:b.click();break
                        except Exception:pass
                paths=[]
                for _ in range(24):
                    paths=[p for p in Path(td).iterdir() if p.is_file() and p.suffix.lower()==".mp3" and p.stat().st_size>120000]
                    if paths and not list(Path(td).glob("*.crdownload")):break
                    time.sleep(2)
                if not paths:raise RuntimeError("No MP3 obtained by clicking the official Pixabay Free download control")
                p=max(paths,key=lambda x:x.stat().st_size)
                cmd=["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,channels,sample_rate,codec_type","-of","json",str(p)]
                out=subprocess.run(cmd,text=True,capture_output=True,timeout=35,check=True)
                data=json.loads(out.stdout)
                duration=float(data["format"]["duration"])
                if not 219<duration<235:raise RuntimeError("Downloaded track has wrong duration "+str(duration))
                a=next((s for s in data.get("streams",[]) if s.get("codec_type")=="audio"),None)
                if not a or a["codec_name"]!="mp3":raise RuntimeError("Not the expected mp3 audio")
                ff=subprocess.run(["ffmpeg","-v","error","-nostdin","-i",str(p),"-f","null","-"],capture_output=True,text=True,timeout=130)
                if ff.returncode:raise RuntimeError("Audio decode failed")
                blob=p.read_bytes()
                sha=hashlib.sha256(blob).hexdigest()
                key=f"asset-library/raw/sha256/{sha[:2]}/{sha}.mp3"
                if not os.environ.get("R2_ACCESS_KEY_ID") or not os.environ.get("R2_SECRET_ACCESS_KEY"):raise RuntimeError("R2 credential missing")
                s3=boto3.client("s3",endpoint_url="https://"+ACCOUNT_ID+".r2.cloudflarestorage.com",region_name="auto",aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],config=Config(signature_version="s3v4",s3={"addressing_style":"path"},request_checksum_calculation="when_required",response_checksum_validation="when_required"))
                try:
                    hd=s3.head_object(Bucket=BUCKET,Key=key)
                    if hd["ContentLength"]!=len(blob):raise RuntimeError("existing length mismatch")
                    action="reused"
                except ClientError as ex:
                    if str(ex.response.get("Error",{}).get("Code")) not in ("404","NoSuchKey","NotFound"):raise
                    s3.put_object(Bucket=BUCKET,Key=key,Body=blob,ContentType="audio/mpeg",Metadata={"sha256":sha,"source":"pixabay","license":"pixabay_content_license"})
                    action="uploaded"
                hd=s3.head_object(Bucket=BUCKET,Key=key)
                if hd["ContentLength"]!=len(blob):raise RuntimeError("R2 HEAD mismatch")
                record.update({"status":"STORED_R2","qa":"TECHNICAL_PASS_LISTENING_PENDING","sha256":sha,"key":key,"bytes":len(blob),"duration":round(duration,3),"codec":a["codec_name"],"channels":a["channels"],"sample_rate":a["sample_rate"],"upload_action":action})
            finally:d.quit()
    except Exception as exc:
        record["status"]="NOT_IMPORTED"
        record["error"]=str(exc)[:600]
    Path("pixabay-piano-r2-report.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    print("PIXABAY_PIANO_INGEST "+json.dumps(record,ensure_ascii=False),flush=True)
    if record["status"]!="STORED_R2":raise SystemExit(1)
if __name__=="__main__":main()
