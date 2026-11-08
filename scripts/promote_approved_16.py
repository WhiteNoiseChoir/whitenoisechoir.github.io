#!/usr/bin/env python3
"""One-time, owner-authorized promotion of WhiteNoiseChoir's 16 listening-approved sounds.

12 DSP 600s masters are already in audio/ and only get approval metadata.
Four CC0 full-source audition MP3s are copied byte-for-byte to live audio/,
with each real length retained. Rebuild ONLY their HLS segment sets, keeping
all other streams and player transport unchanged. Keep sound pages noindex
until separate editorial SEO review.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from build_continuous_hls import build_loop, parse_playlist, verify_transport, sha as hls_sha

ROOT = Path(".")
FIELD_IDS = ("box-fan-real", "heavy-rain-real", "ocean-waves-real", "waterfall-real")
VERSION = "cc0-full-approved-20261108"
HLS_VERSION = "continuous-hls-v4-cc0-approved-20261108"

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def save(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def require(cond, description):
    if not cond:
        raise AssertionError(description)

def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1024*1024), b""):
            h.update(part)
    return h.hexdigest()

def edit_text(path, replacements):
    p=Path(path)
    s=p.read_text(encoding="utf-8")
    for old,new in replacements:
        require(old in s, str(p)+" missing text target "+old[:120])
        s=s.replace(old,new)
    p.write_text(s, encoding="utf-8")

def iso_duration(seconds):
    t=int(math.floor(seconds+0.5))
    m,s=divmod(t,60)
    return "PT"+(str(m)+"M" if m else "")+str(s)+"S"

def human_duration(seconds):
    t=int(math.floor(seconds+0.5))
    m,s=divmod(t,60)
    return (str(m)+" minute"+("s" if m!=1 else "")+" "+str(s)+" seconds") if m else (str(s)+" seconds")

def encode_hls(master, directory):
    cmd=[
        "ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
        "-i",str(master),"-vn","-map","0:a:0",
        "-ar","44100","-ac","2","-c:a","aac","-b:a","192k",
        "-f","hls","-hls_time","60","-hls_segment_type","mpegts",
        "-hls_list_size","0","-hls_playlist_type","vod",
        "-hls_segment_filename",str(directory/"part_%03d.ts"),
        str(directory/"source.m3u8")]
    p=subprocess.run(cmd,capture_output=True,text=True)
    require(p.returncode==0,"FFmpeg failed for "+str(master)+": "+p.stderr[-500:])

def check_audio(master, seconds):
    raw=subprocess.run([
        "ffprobe","-v","error","-show_streams","-show_format",
        "-of","json",str(master)
    ],capture_output=True,text=True,check=True)
    obj=json.loads(raw.stdout)
    audio=next(x for x in obj["streams"] if x.get("codec_type")=="audio")
    require(audio.get("codec_name")=="mp3","Wrong codec "+str(master))
    require(int(audio.get("channels"))==2 and int(audio.get("sample_rate"))==44100,"Wrong audio format")
    require(abs(float(obj["format"]["duration"])-seconds)<0.75,"Wrong duration "+str(master))

def build_field_hls(source, seconds):
    target=Path("audio/continuous")/source.stem
    target.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="approved-cc0-") as tmp:
        td=Path(tmp)
        encode_hls(source,td)
        segments=parse_playlist(td/"source.m3u8",expected_seconds=seconds)
        verify_transport(td/segments[0][0])
        cycles,hours=build_loop(segments,td/"continuous.m3u8")
        require(hours>=7*86400,"HLS less than seven days")
        # Publish as an atomic Git commit at the end of the workflow.
        for old in target.glob("part_*.ts"):
            old.unlink()
        for piece,_ in segments:
            shutil.copyfile(td/piece,target/piece)
        shutil.copyfile(td/"continuous.m3u8",target/"continuous.m3u8")
    return {
        "playlist_file":str(target/"continuous.m3u8"),
        "playlist_sha256":file_sha(target/"continuous.m3u8"),
        "segment_count_per_source_cycle":len(segments),
        "source_cycle_seconds":round(sum(d for _,d in segments),3),
        "repeated_cycles":cycles,
        "native_stream_duration_hours":round(hours/3600,2),
        "original_source_length_category":"APPROVED_CC0_FIELD_RECORDING",
        "editorial_status":"OWNER_APPROVED_FOR_AUDIO",
        "long_form_listening_status":"OWNER_APPROVED_LISTENING",
        "source_length_note":"Independent natural field source; repeated as a short source cycle, not a 10-minute original recording.",
    }

def upgrade_four_source_pages(source_rows,catalog):
    by_id={x["id"]:x for x in catalog["sounds"]}
    for ident,row in source_rows.items():
        p=Path("sounds")/by_id[ident]["slug"]/"index.html"
        html=p.read_text(encoding="utf-8")
        seconds=row["source_material_used_seconds"]
        display=human_duration(seconds)
        require('"duration":"PT54S"' in html,ident+": expected old JSON-LD duration")
        require("<dd>54 seconds</dd>" in html,ident+": expected old duration text")
        html=html.replace('"duration":"PT54S"','"duration":"'+iso_duration(seconds)+'"')
        html=html.replace("<dd>54 seconds</dd>","<dd>"+display+" ("+format(seconds,".2f")+" s)</dd>")
        html= re.sub(r'<section class="note warn" aria-label="Recording transparency">.*?</section>',
            '<section class="note warn" aria-label="Recording transparency">'
            "Owner-approved, independently recorded CC0 sound. This production master uses "
            +format(seconds,".2f")+" seconds of the source, not ten minutes of unique recording. "
            "Long listening sessions repeat the recorded source cycle through native HLS or MP3 looping."
            "</section>",html,count=1,flags=re.DOTALL)
        html=re.sub(r'(<h2>What does [^<]+ sound like\?</h2><p class="lede">).*?(</p>)',
            lambda m:m.group(1)+"This approved CC0 master preserves "+format(seconds,".2f")
            +" seconds of the source recording and loops for continuous listening. "
            +"The same recorded cycle will repeat; the source is not a ten-minute field recording."+m.group(2),
            html,count=1,flags=re.DOTALL)
        # Correct stale audio-provenance sentences in the natural sound sections.
        html=html.replace("The production file is currently a short CC0 cut. A longer candidate is available for review, but has not replaced the live source.","The full-source CC0 edit is now the production master.")
        html=html.replace("The live CC0 master is still short while a fuller original-source edit is under listening review.","The owner-approved full-source edit is now served to listeners.")
        html=html.replace("The current master is a short cut awaiting review of a longer edit from the original source.","The approved full-source recording is the current production master.")
        html=html.replace("This CC0 production cut is short; the longer original recording is under listening review before replacement.","The owner-approved full-source CC0 recording is now the current production master.")
        html=html.replace("The continuous stream repeats the short material. It must not be mistaken for hours of independently captured fan sound.","Continuous playback repeats the original recording cycle; it is not hours of independent fan recording.")
        html=html.replace("The HLS playlist creates long playback time; it does not add unique recorded rainfall.","The native HLS playlist provides long playback by repeating the "+display+" recording.")
        html=html.replace("The apparent continuous sound comes from looping short source material.","The full-source "+display+" recording is looped to make longer listening possible.")
        html=html.replace("54s loop",display+" loop")
        html=html.replace("Explore all 21 available sound sources","Explore all 22 available sound sources")
        # Invalidate cached old 54-second recordings on Safari and progressive browsers.
        for kind in ("data-mp3","src"):
            literal=kind+'="/audio/'+ident+'.mp3"'
            require(literal in html, ident+" missing "+kind)
            html=html.replace(literal,kind+'="/audio/'+ident+'.mp3?v='+VERSION+'"')
        hls_old='data-hls="/audio/continuous/'+ident+'/continuous.m3u8"'
        require(hls_old in html,ident+" missing HLS data attribute")
        html=html.replace(hls_old,'data-hls="/audio/continuous/'+ident+'/continuous.m3u8?v='+HLS_VERSION+'"')
        p.write_text(html,encoding="utf-8")

def update_other_pages(dsp_ids,catalog,field_rows):
    by_id={x["id"]:x for x in catalog["sounds"]}
    for ident in dsp_ids:
        p=Path("sounds")/by_id[ident]["slug"]/"index.html"
        s=p.read_text(encoding="utf-8")
        s=s.replace("Approval for all-night listening or realism on actual devices has not yet been recorded.",
           "The site owner has approved the current 10-minute audio master. Realism varies by listener; use a comfortable volume.")
        s=s.replace("listening review pending","owner-approved audio; SEO editorial review pending")
        s=s.replace("Listening review pending","Owner-approved audio")
        s=s.replace("listening approval pending","owner-approved audio")
        s=s.replace("Listening approval pending","Owner-approved audio")
        s=s.replace("Explore all 21 available sound sources","Explore all 22 available sound sources")
        p.write_text(s,encoding="utf-8")
    src=Path("sources.html")
    s=src.read_text(encoding="utf-8")
    for ident,row in field_rows.items():
        label=human_duration(row["source_material_used_seconds"])
        orig="Local processed sample: "+ident+" · 54s loop"
        require(orig in s,"sources page missing "+ident)
        s=s.replace(orig,"Owner-approved original-source edit: "+ident+" · "+label+" loop")
        s=s.replace('href="/audio/'+ident+'.mp3"','href="/audio/'+ident+'.mp3?v='+VERSION+'"')
    s=s.replace("Our processed listening preview","Our owner-approved full-source listening master")
    src.write_text(s,encoding="utf-8")
    page=Path("signature/field-review/index.html")
    s=page.read_text(encoding="utf-8")
    s=s.replace("These are four unapproved listening candidates", "These are four owner-approved production source recordings")
    s=s.replace("Audition only · not production-approved","Owner-approved · published to production")
    s=s.replace("Moving a recording into the main site requires a separate change after listening approval.","These exact approved recordings have now been published to the main site.")
    page.write_text(s,encoding="utf-8")
    page=Path("signature/dsp-review/index.html")
    s=page.read_text(encoding="utf-8")
    s=s.replace("have <strong>not</strong> been approved by a human listener", "have been approved for audio publication by the site owner")
    s=s.replace("Human listening pending","Owner-approved listening")
    page.write_text(s,encoding="utf-8")
    page=Path("signature/listening-approval/index.html")
    s=page.read_text(encoding="utf-8")
    s=s.replace("12 bản DSP tổng hợp và 4 bản ghi tự nhiên CC0. Đánh giá ở đây", "12 bản DSP và 4 bản CC0 đã được chủ website duyệt và đưa lên production. Công cụ tiếp tục giúp theo dõi phản hồi; đánh giá ở đây")
    page.write_text(s,encoding="utf-8")

def update_future_hls_builder():
    p=Path("scripts/build_continuous_hls.py")
    s=p.read_text(encoding="utf-8")
    pairs=[
      ('HLS_VERSION="continuous-hls-v3-green-20261108"',
       'HLS_VERSION="'+HLS_VERSION+'"'),
      ('    segment=where/"part_%03d.ts"\n    cmd=',
       '    segment=where/"part_%03d.ts"\n    hls_time="60" if master.stem in LEGACY_CC0 else "65"\n    cmd='),
      ('"-f","hls","-hls_time","65",',
       '"-f","hls","-hls_time",hls_time,'),
      ('"source_editorial_status":"LEGACY_54_SECOND_DEMO_PENDING_LONG_RECORDING",',
       '"source_editorial_status":row.get("production_status","LEGACY_54_SECOND_DEMO_PENDING_LONG_RECORDING"),'),
      ('expected=54 if ident in LEGACY_CC0 else 600',
       'expected=float(next(r["derived_duration_seconds"] for r in registry if r["id"]==ident)) if ident in LEGACY_CC0 else 600'),
      ('"original_source_length_category":"LEGACY_CC0_SHORT_DEMO" if ident in LEGACY_CC0 else "10_MINUTE_MASTER",',
       '"original_source_length_category":("APPROVED_CC0_FIELD_RECORDING" if e.get("source_editorial_status")=="OWNER_APPROVED_FIELD_RECORDING" else "LEGACY_CC0_SHORT_DEMO") if ident in LEGACY_CC0 else "10_MINUTE_MASTER",'),
      ('"editorial_status":e.get("source_editorial_status","PENDING_NEW_BATCH_HUMAN_REVIEW" if ident in (EXTENDED|GREEN) else "PREVIOUSLY_REVIEWED"),',
       '"editorial_status":e.get("source_editorial_status","OWNER_APPROVED_FOR_AUDIO" if ident in EXTENDED and e.get("qa",{}).get("listening_approval")=="APPROVED_BY_OWNER" else "PENDING_NEW_BATCH_HUMAN_REVIEW" if ident in (EXTENDED|GREEN) else "PREVIOUSLY_REVIEWED"),'),
      ('"long_form_listening_status":"PENDING_IPHONE_LOCK_SCREEN_REVIEW",',
       '"long_form_listening_status":"OWNER_APPROVED_LISTENING" if (ident in EXTENDED and e.get("qa",{}).get("listening_approval")=="APPROVED_BY_OWNER") or e.get("source_editorial_status")=="OWNER_APPROVED_FIELD_RECORDING" else "PENDING_IPHONE_LOCK_SCREEN_REVIEW",'),
      ('"source_length_disclosure":"18 independently produced/arranged 10-minute masters; 4 short 54-second CC0 demos. HLS changes transport continuity, not source recording length.",',
       '"source_length_disclosure":"18 produced or arranged 10-minute masters and 4 owner-approved natural CC0 recordings with actual lengths 67.52, 189.76, 89.83 and 375.48 seconds. Source cycles repeat.",')
    ]
    for old,new in pairs:
        require(old in s,"Future HLS builder patch target absent: "+old[:100])
        s=s.replace(old,new)
    s=s.replace("Expected exactly 21 original player sound sources","Expected exactly 22 player sound sources")
    p.write_text(s,encoding="utf-8")

def main():
    registry=load("audio/cc0-sources.json")
    field=load("signature/field-review/manifest.json")
    extended=load("audio/extended-dsp-manifest.json")
    queue=load("audio/review-queue-20261108.json")
    hls=load("audio/continuous/manifest.json")
    catalog=load("catalog/library.json")
    dsp_ids={t["id"] for t in extended["tracks"]}
    require(len(dsp_ids)==12,"Expected twelve DSP")
    require(queue["state"]=="TECHNICAL_QA_COMPLETE_HUMAN_LISTENING_INCOMPLETE","Approval source must still be staged")
    require(field["status"]=="AUDITION_ONLY_NO_MAIN_SITE_ASSET_REPLACEMENT","Unexpected field-review status")
    approved={r["id"]:r for r in field["records"]}
    require(set(approved)==set(FIELD_IDS),"Unexpected natural audio candidates")
    hls_rows={r["id"]:r for r in hls["records"]}
    require(len(hls_rows)==22,"Unexpected HLS inventory")
    mapping={r["id"]:r for r in registry}
    require(all(mapping[i]["derived_duration_seconds"]==54 for i in FIELD_IDS),"Legacy files already modified")
    require(dsp_ids=={r["id"] for r in queue["dsp"]},"Review DSP inventory differs")
    for id,row in approved.items():
        audition=Path(row["preview_file"])
        require(file_sha(audition)==row["sha256"],id+" audition checksum mismatch")
        require(row["qa"]["status"]=="PASS",id+" invalid candidate technical QA")
        require(row["license"]=="CC0-1.0",id+" license mismatch")
        require(row["source_url"]==mapping[id]["source"],id+" source attribution mismatch")
        check_audio(audition,row["qa"]["seconds"])
        prod=Path("audio")/(id+".mp3")
        shutil.copyfile(audition,prod)
        require(file_sha(prod)==row["sha256"],id+" copy verification failed")
        manifest_fields=build_field_hls(prod,row["qa"]["seconds"])
        hls_rows[id].update(manifest_fields)
        hls_rows[id]["master_file"]=str(prod)
        hls_rows[id]["master_sha256"]=row["sha256"]
        hls_rows[id]["source_license"]=row["license"]
        hls_rows[id]["source_page"]=row["source_url"]
        hls_rows[id]["notes"]="Owner approved genuine CC0 field source. Natural source length is not misrepresented as 10 minutes. Playback loops until stopped."
        mapping[id]["derived_duration_seconds"]=row["qa"]["seconds"]
        mapping[id]["production_master_sha256"]=row["sha256"]
        mapping[id]["independent_source_duration_seconds"]=row["independent_recording_seconds"]
        mapping[id]["source_material_used_seconds"]=row["source_material_used_seconds"]
        mapping[id]["processing"]=row["processing"]
        mapping[id]["production_status"]="OWNER_APPROVED_FIELD_RECORDING"
        row["qa"]["human_approved"]=True
        row["listening_status"]="APPROVED_BY_OWNER_PUBLISHED"
        print("APPROVED_FIELD",json.dumps({"id":id,"seconds":row["qa"]["seconds"],"sha256":row["sha256"],"hls_seconds":hls_rows[id]["source_cycle_seconds"]}),flush=True)

    for item in extended["tracks"]:
        require(item["qa"]["technical_status"]=="PASS",item["id"]+" no DSP technical PASS")
        require(file_sha(item["file"])==item["file_sha256"],item["id"]+" DSP file mismatch")
        item["qa"]["listening_approval"]="APPROVED_BY_OWNER"
        hls_rows[item["id"]]["editorial_status"]="OWNER_APPROVED_FOR_AUDIO"
        hls_rows[item["id"]]["long_form_listening_status"]="OWNER_APPROVED_LISTENING"
    extended["human_approval"]="APPROVED_BY_OWNER_FOR_AUDIO_PUBLICATION_2026_11_08"

    for item in queue["dsp"]:
        item["human_listening"]="APPROVED_BY_OWNER"
    for item in queue["cc0_field"]:
        item["human_listening"]="APPROVED_BY_OWNER"
        item["production_policy"]="APPROVED_FULL_SOURCE_PRODUCTION"
    queue["state"]="OWNER_APPROVED_16_DEPLOYED"
    queue["production_change_authorized_by_listening"]=True
    queue["approval_provenance"]="Site owner explicitly confirmed all 16 sound candidates approved for production in ChatGPT on 2026-11-08."
    queue["audio_release_version"]=VERSION

    for row in catalog["sounds"]:
        if row["id"] in dsp_ids or row["id"] in FIELD_IDS:
            row["status"]="listening-approved"
            row["desc"]=row["desc"].replace("; listening review pending","")
            row["desc"]=row["desc"].replace("listening review pending","listening approved by site owner")
            if row["id"] in FIELD_IDS:
                row["desc"]="Owner-approved CC0 field recording; "+human_duration(approved[row["id"]]["qa"]["seconds"])+" of independently recorded sound, looped continuously"
    catalog["version"]="2026-11-08-catalog-v3-owner-approved-audio"
    catalog["editorial_note"]="Owner approved 12 DSP masters and 4 longer natural CC0 records for playback. Audio approval is distinct from individual page editorial/SEO indexing approval."

    hls["version"]=HLS_VERSION
    hls["source_length_disclosure"]="18 10-minute produced/arranged masters; 4 owner-approved field-recording masters at 67.52s, 189.76s, 89.83s, 375.48s. HLS repeats source cycles."
    hls["records"]=[hls_rows[r["id"]] for r in hls["records"]]
    field["status"]="OWNER_APPROVED_AND_PUBLISHED"

    save("audio/cc0-sources.json",registry)
    save("audio/extended-dsp-manifest.json",extended)
    save("audio/review-queue-20261108.json",queue)
    save("signature/field-review/manifest.json",field)
    save("audio/continuous/manifest.json",hls)
    save("catalog/library.json",catalog)

    upgrade_four_source_pages(approved,catalog)
    update_other_pages(dsp_ids,catalog,approved)
    update_future_hls_builder()

    home=Path("index.html")
    html=home.read_text(encoding="utf-8")
    old='var mp3url="audio/"+id+".mp3"+versioned;'
    new='var mp3url="audio/"+id+".mp3"+(approvedFieldIDs.indexOf(id)!==-1?"?v='+VERSION+'":versioned);'
    require(old in html,"Main audio player URL block missing")
    html=html.replace(old,'var approvedFieldIDs='+json.dumps(list(FIELD_IDS))+';\n    '+new)
    require("continuous-hls-v3-green-20261108" in html,"Main HLS URL version missing")
    html=html.replace("continuous-hls-v3-green-20261108",HLS_VERSION)
    home.write_text(html,encoding="utf-8")

    # Verify after staging but before GitHub workflow creates a production commit.
    for id,row in approved.items():
        require(file_sha("audio/"+id+".mp3")==row["sha256"],id+" production SHA changed")
        require(hls_sha(Path(hls_rows[id]["playlist_file"]))==hls_rows[id]["playlist_sha256"],id+" HLS SHA changed")
        require(abs(hls_rows[id]["source_cycle_seconds"]-row["qa"]["seconds"])<0.75,id+" HLS cycle mismatch")
    require(len([x for x in catalog["sounds"] if x["status"]=="listening-approved"])==16,"All 16 must be audio-approved")
    print("PROMOTION_READY",json.dumps({
        "approved_dsp":len(dsp_ids),
        "approved_cc0":len(approved),
        "production_audio_files_replaced":list(FIELD_IDS),
        "HLS_regenerated":list(FIELD_IDS),
        "other_streams_untouched":18,
        "page_indexing_policy":"unchanged_noindex_until_editorial_review"
    }),flush=True)

if __name__=="__main__":
    main()
