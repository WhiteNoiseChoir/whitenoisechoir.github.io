#!/usr/bin/env python3
"""Audit source identity, SHA and available ORIGINAL CC0 preview durations.

No raw source is copied into the public repository, no sound is silently
replaced by a shorter recording, and license/artist provenance is preserved.
This audit establishes whether 10-minute masters would contain substantial
real variation rather than repetitions of a 54-second preview.
"""
from pathlib import Path
import hashlib,json,subprocess,tempfile,time
from urllib.request import Request,urlopen

SOURCES=Path("audio/cc0-sources.json")
REPORT=Path("audio/field-source-audit.json")
FOUR={"box-fan-real","heavy-rain-real","ocean-waves-real","waterfall-real"}
SOURCE_DURATIONS={
    "box-fan-real":70.524,"heavy-rain-real":192.758,
    "ocean-waves-real":92.833,"waterfall-real":378.475,
}

def fetch(url):
    error=None
    for attempt in range(3):
        try:
            req=Request(url,headers={"User-Agent":"Mozilla/5.0 (WhiteNoiseChoir CC0 audio duration audit)","Accept":"audio/*,*/*"})
            with urlopen(req,timeout=35) as resp: data=resp.read(37*1024*1024)
            if len(data)<30000:raise ValueError("Preview too short")
            return data
        except Exception as e:
            error=e;time.sleep(1+attempt)
    raise RuntimeError(f"Could not fetch pinned preview from {url}: {error}")

def probe(path):
    r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                      "-of","json",str(path)],check=True,capture_output=True,text=True)
    return float(json.loads(r.stdout)["format"]["duration"])

def main():
    rows=json.loads(SOURCES.read_text(encoding="utf-8"))
    out=[]
    for row in rows:
        if row["id"] not in FOUR:continue
        blob=fetch(row["preview_url"])
        hash=hashlib.sha256(blob).hexdigest()
        if hash!=row["preview_sha256"]:
            raise RuntimeError(f"{row['id']} preview checksum changed: {hash}; must re-review source")
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"preview.mp3";p.write_bytes(blob);seconds=probe(p)
        source_dur=SOURCE_DURATIONS[row["id"]]
        if seconds<54:
            raise RuntimeError(f"{row['id']} preview is unexpectedly shorter than 54s: {seconds}")
        if seconds>source_dur+10:
            raise RuntimeError(f"{row['id']} exceeds source page recording duration; provenance mismatch")
        record={
            "id":row["id"],"source_page":row["source"],"creator":row["creator"],
            "declared_source_license":row["license"],"preview_url":row["preview_url"],
            "pinned_preview_sha256":hash,"preview_bytes":len(blob),
            "original_page_source_duration_seconds":source_dur,
            "accessible_preview_duration_seconds":round(seconds,3),
            "current_public_demo_seconds":54,
            "natural_independent_content_from_verified_preview_minutes":round(seconds/60,2),
            "is_10_minutes_independent_recording":seconds>=598,
            "upgrade_decision":("REVIEW_LONG_SOURCE_REMASTER" if seconds>=180 else
                                "FIND_LONGER_CC0_SOURCE_BEFORE_10_MIN_MASTER"),
            "editorial_status":"PENDING_HUMAN_LISTENING",
        }
        print("FIELD_SOURCE_AUDIT",json.dumps(record),flush=True)
        out.append(record)
    if {x["id"] for x in out}!=FOUR:raise RuntimeError("Missing field source")
    summary={
        "version":"20261108-field-source-audit-v1",
        "tracks":out,"status":"SOURCE_AND_LICENSE_VERIFIED; LONGER_MASTER_NOT_YET_APPROVED",
        "policy":"Do not manufacture 10min of unique field recording by simply repeating <2min source. Approve replacements by ear before promotion.",
    }
    REPORT.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SOURCE_AUDIT_DONE",len(out),flush=True)

if __name__=="__main__":
    main()
