#!/usr/bin/env python3
"""Integration regression for FAST audio intake: short clips, dedupe, rights, quarantine."""
from __future__ import annotations
import tempfile, wave, math, struct, pathlib, sys, json
sys.path.insert(0,"scripts")
import fast_sound_asset_intake as intake

RIGHTS={
 "license":"CC0-1.0",
 "source_license_verified":True,
 "authorized_download":True,
 "website_playback_allowed":True,
 "remix_allowed":True,
 "commercial_export_allowed":True,
 "license_evidence_url":"https://example.org/licenses/source/42",
 "verified_at":"2026-11-10"
}
def wavefile(path,secs,frequency):
    with wave.open(str(path),"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(8000)
        chunk=bytearray()
        for i in range(int(8000*secs)):
            v=int(6000*math.sin(2*math.pi*frequency*i/8000))
            chunk.extend(struct.pack("<h",v))
        f.writeframes(chunk)
def asset(id,file,role,rights=None,concept_ids=None):
    return {"candidate_id":id,"local_file":str(file),"source_url":"https://example.org/recordings/42",
            "creator":"Test creator","concept_ids":concept_ids if concept_ids is not None else ["forest"],
            "role":role,"rights":rights if rights is not None else dict(RIGHTS)}
with tempfile.TemporaryDirectory() as tmp:
    d=pathlib.Path(tmp)
    short=d/"wolf.wav";bed=d/"stream.wav";broken=d/"bad.wav"
    wavefile(short,0.5,440);wavefile(bed,2.5,220)
    broken.write_bytes(b"bad audio file"*200)
    rows=[
      asset("wolf-short",short,"ONE_SHOT"),
      asset("wolf-duplicate",short,"ONE_SHOT"),
      asset("stream-short-bed",bed,"CONTINUOUS_BED"),
      asset("source-without-rights",bed,"PASS_BY",{**RIGHTS,"license":"CC-BY-NC","source_license_verified":False}),
      asset("broken-file",broken,"ONE_SHOT"),
      asset("requires-voice-review",short,"SPEECH_OR_VOCAL"),
      asset("no-concept",short,"ONE_SHOT",concept_ids=[]),
    ]
    # Use distinct files to make rights / voice cases not collide with SHA dedup first.
    alt=d/"alt.wav";wavefile(alt,1.1,550)
    rows[3]["local_file"]=str(alt)
    rows[5]["local_file"]=str(d/"voice.wav");wavefile(d/"voice.wav",1.2,640)
    rows[6]["local_file"]=str(d/"nocat.wav");wavefile(d/"nocat.wav",1.3,760)
    report=intake.run(rows)
    states={x["candidate_id"]:x["status"] for x in report["items"]}
    expected={
      "wolf-short":"READY_FOR_STORAGE","wolf-duplicate":"DUPLICATE",
      "stream-short-bed":"READY_FOR_STORAGE","source-without-rights":"NEEDS_REVIEW",
      "broken-file":"REJECTED","requires-voice-review":"NEEDS_REVIEW",
      "no-concept":"NEEDS_REVIEW"
    }
    assert states==expected, (states,expected)
    assert report["counts"]=={"READY_FOR_STORAGE":2,"NEEDS_REVIEW":3,"DUPLICATE":1,"REJECTED":1}
    short_output=report["items"][0]
    assert 0.4<short_output["duration_seconds"]<0.6
    assert short_output["commercial_export_ready"] is True
    assert short_output["automatic_human_listening_required"] is False
    assert short_output["upload_performed"] is False
    assert report["verified_usable_files_uploaded"]==0 and report["production_releases"]==0
    assert report["indexing_changes"]==0
    # Same rights cannot auto-approve speech; zero manual listening for low-risk assets.
    voice=report["items"][5]
    assert voice["automatic_human_listening_required"] is True
    print("FAST_BULK_AUDIO_INTAKE_PASS "+json.dumps(report["counts"],ensure_ascii=False))
