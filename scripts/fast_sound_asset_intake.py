#!/usr/bin/env python3
"""WhiteNoiseChoir FAST bulk intake: local, offline, no publishing or audio upload.

Bulk probe hundreds of authorized source files, dedupe exact SHA, verify required
rights evidence, and produce an upload-ready JSON manifest. Never imposes 600s
minimum or a per-file human listening approval.
Use: python3 scripts/fast_sound_asset_intake.py --input /private/batch.json --output /private/results.json
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, pathlib, datetime, re, sys

ROLES={"CONTINUOUS_BED","SEAMLESS_LOOP","ONE_SHOT","RECURRING_EVENT","PASS_BY","TRANSITION","TEXTURE","SPEECH_OR_VOCAL"}
SUPPORTED={"CC0-1.0","PUBLIC_DOMAIN_VERIFIED","CC-BY-4.0_WITH_ATTRIBUTION","EXPLICIT_COMMERCIAL_DISTRIBUTION_LICENSE"}
AUDIO_EXT={".mp3",".wav",".flac",".ogg",".opus",".m4a",".aiff",".aif"}
MAX_FILE_BYTES=1_000_000_000
MIN_DURATION=0.05
def nonempty_string(x):return isinstance(x,str) and bool(x.strip())
def url(x):return nonempty_string(x) and x.startswith("https://") and len(x)<2048
def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def probe(p):
    run=subprocess.run(["ffprobe","-v","error","-show_entries",
        "format=duration,size,bit_rate,format_name:stream=codec_type,codec_name,sample_rate,channels",
        "-of","json",str(p)],capture_output=True,text=True,timeout=35,check=False)
    if run.returncode:raise ValueError("ffprobe failed to decode header")
    meta=json.loads(run.stdout)
    stream=next((x for x in meta.get("streams",[]) if x.get("codec_type")=="audio"),None)
    if not stream:raise ValueError("no audio stream")
    dur=float(meta.get("format",{}).get("duration",0))
    if not MIN_DURATION<=dur<=86400:raise ValueError("duration out of bounds")
    return dur,stream,meta.get("format",{})
def valid_rights(row):
    rights=row.get("rights",{})
    license=rights.get("license")
    if license not in SUPPORTED:return False,["LICENSE_NOT_ELIGIBLE"]
    errs=[]
    for k in ("source_license_verified","authorized_download","website_playback_allowed","remix_allowed"):
        if rights.get(k) is not True:errs.append("RIGHTS_"+k.upper()+"_NOT_VERIFIED")
    if not url(row.get("source_url")):errs.append("SOURCE_URL_MISSING")
    if not url(rights.get("license_evidence_url")):errs.append("LICENSE_EVIDENCE_URL_MISSING")
    if not nonempty_string(rights.get("verified_at")):errs.append("LICENSE_VERIFICATION_DATE_MISSING")
    if license=="CC-BY-4.0_WITH_ATTRIBUTION" and not nonempty_string(rights.get("attribution_text")):
        errs.append("CC_BY_ATTRIBUTION_MISSING")
    return not errs,errs
def inspect(row,seen):
    ident=str(row.get("candidate_id","")).strip()
    result={"candidate_id":ident,"concept_ids":row.get("concept_ids",[]),
            "status":"NEEDS_REVIEW","warnings":[],"automatic_human_listening_required":False,
            "commercial_export_ready":False}
    if not ident or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}",ident):
        result.update(status="REJECTED",warnings=["INVALID_CANDIDATE_ID"]);return result
    role=row.get("role")
    if role not in ROLES:
        result.update(status="REJECTED",warnings=["UNKNOWN_ROLE"]);return result
    result["role"]=role
    p=pathlib.Path(str(row.get("local_file",""))).expanduser()
    if not p.is_file() or p.suffix.lower() not in AUDIO_EXT:
        result.update(status="REJECTED",warnings=["FILE_MISSING_OR_FORMAT_UNSUPPORTED"]);return result
    if not 1000<=p.stat().st_size<=MAX_FILE_BYTES:
        result.update(status="REJECTED",warnings=["FILE_SIZE_OUT_OF_BOUNDS"]);return result
    try:
        duration,stream,fmt=probe(p)
    except (ValueError,subprocess.TimeoutExpired,json.JSONDecodeError) as exc:
        result.update(status="REJECTED",warnings=["UNREADABLE_AUDIO",str(exc)[:150]]);return result
    digest=sha256(p)
    result.update(file_sha256=digest,bytes=p.stat().st_size,duration_seconds=round(duration,3),
                  actual_independent_seconds="NOT_MEASURED",codec=stream.get("codec_name"),
                  sample_rate_hz=int(stream.get("sample_rate",0)),channels=stream.get("channels"),
                  source_url=row.get("source_url"),creator=row.get("creator"),
                  rights=row.get("rights"),source_filename=p.name,
                  planned_storage_key="asset-library/sha256/"+digest[:2]+"/"+digest+p.suffix.lower(),
                  upload_performed=False,public_url=None)
    if digest in seen:
        result.update(status="DUPLICATE",duplicate_of=seen[digest],warnings=["EXACT_SHA256_DUPLICATE"]);return result
    seen[digest]=ident
    if duration<0.3:result["warnings"].append("ULTRA_SHORT_CLIP_VERIFY_IF_USEFUL")
    if role=="SPEECH_OR_VOCAL":result["warnings"].append("SPEECH_VOICE_PRIVACY_AND_RIGHTS_REVIEW")
    if stream.get("codec_name")=="mp3" and int(fmt.get("bit_rate",0))<64000:
        result["warnings"].append("LOW_BITRATE_QUALITY_SPOT_CHECK")
    rights_ok,rights_err=valid_rights(row)
    if not rights_ok:result["warnings"].extend(rights_err)
    if not nonempty_string(row.get("creator")):result["warnings"].append("CREATOR_MISSING")
    concepts=result["concept_ids"]
    if not isinstance(concepts,list) or not concepts or any(not nonempty_string(x) for x in concepts):
        result["warnings"].append("BAD_CONCEPT_IDS")
    needs_attention=(not rights_ok or not nonempty_string(row.get("creator"))
            or role=="SPEECH_OR_VOCAL" or "BAD_CONCEPT_IDS" in result["warnings"])
    if needs_attention:
        result["status"]="NEEDS_REVIEW"
        result["automatic_human_listening_required"]=(role=="SPEECH_OR_VOCAL")
    else:
        # Fast track to uploading: no 10-minute gate, waveform audition,
        # per-file owner signoff or re-render. Storage upload checked separately.
        result["status"]="READY_FOR_STORAGE"
        result["commercial_export_ready"]=(row["rights"].get("commercial_export_allowed") is True)
    return result
def run(rows):
    seen={}
    results=[inspect(row,seen) for row in rows]
    counts={status:sum(x["status"]==status for x in results) for status in
            ["READY_FOR_STORAGE","NEEDS_REVIEW","DUPLICATE","REJECTED"]}
    return {"schema_version":1,"pipeline":"FAST_AUDIO_ASSET_INTAKE",
      "verified_usable_files_uploaded":0,
      "readiness":"READY_FOR_STORAGE_IS_NOT_MIX_READY",
      "indexing_changes":0,"production_releases":0,
      "counts":counts,"items":results}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True,help="JSON list or object with assets list, referencing locally authorized files")
    ap.add_argument("--output",required=True,help="JSON audit manifest, NOT audio assets")
    args=ap.parse_args()
    data=json.loads(pathlib.Path(args.input).read_text(encoding="utf8"))
    rows=data if isinstance(data,list) else data.get("assets")
    if not isinstance(rows,list):raise ValueError("Input must contain an assets array")
    output=run(rows)
    pathlib.Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    pathlib.Path(args.output).write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("FAST_INTAKE_REPORT "+json.dumps({"candidate_count":len(rows),"counts":output["counts"],
         "uploaded":0,"published":0},ensure_ascii=False))
if __name__=="__main__":main()
