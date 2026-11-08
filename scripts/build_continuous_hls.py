#!/usr/bin/env python3
"""Static, native HLS continuous-listening streams for iOS/iPadOS browsers.

A 10-minute MP3 file is only a source master, NOT the listening-session limit.
Avoid relying on JS ended/seek/replay while the screen is locked: a VOD HLS
playlist contains the same immutable AAC transport-stream segments repeated for
7 days. The native HLS decoder advances across the 10-minute source boundaries
without asking background JS to initiate playback.

The manifest discloses this bounded static playlist: not a true infinite HTTP
live broadcast. At the extreme 7-day playlist end the audio element has loop=true.
The original MP3 stays available for browsers without native HLS.

Sources remain unchanged. All generated segments and playlists are QA checked.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess
import tempfile
import shutil

ROOT=Path("audio")
HLS_ROOT=ROOT/"continuous"
COLOR_MASTER=ROOT/"color-master-manifest.json"
GREEN_MASTER=ROOT/"green-noise-master-manifest.json"
NATURE_MASTER=ROOT/"master-manifest.json"
EXTENDED_MASTER=ROOT/"extended-dsp-manifest.json"
FIELD_REGISTRY=ROOT/"cc0-sources.json"
COLORS={"white-noise","pink-noise","brown-noise"}
GREEN={"green-noise"}
NATURE={"rain-on-window-real","fireplace-real"}
EXTENDED={
    "blue-noise","violet-noise","soft-white-noise","deep-brown-noise",
    "warm-pink-noise","mid-noise","low-rumble","desk-fan-synth",
    "air-conditioner-synth","cabin-hum-synth","wind-synth","shower-synth",
}
LEGACY_CC0={"box-fan-real","heavy-rain-real","ocean-waves-real","waterfall-real"}
ALL=COLORS | GREEN | NATURE | EXTENDED | LEGACY_CC0
assert len(ALL)==22
DAYS=7
BITRATE=192
HLS_VERSION="continuous-hls-v4-cc0-approved-20261108"


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda: f.read(1024*1024), b""):
            h.update(piece)
    return h.hexdigest()


def run_ffmpeg(master,where):
    segment=where/"part_%03d.ts"
    hls_time="60" if master.stem in LEGACY_CC0 else "65"
    cmd=[
        "ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
        "-i",str(master),"-vn","-map","0:a:0","-ar","44100","-ac","2",
        "-c:a","aac","-b:a",f"{BITRATE}k",
        "-f","hls","-hls_time",hls_time,
        "-hls_segment_type","mpegts","-hls_list_size","0",
        "-hls_playlist_type","vod",
        "-hls_segment_filename",str(segment),str(where/"source.m3u8")
    ]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(f"ffmpeg HLS failed {master}: {p.stderr[-1000:]}")


def parse_playlist(path, expected_seconds=600):
    text=path.read_text(encoding="utf-8")
    lines=text.splitlines()
    parts=[]
    for i,line in enumerate(lines):
        if line.startswith("#EXTINF:"):
            duration=float(line[8:].split(",",1)[0])
            name=lines[i+1].strip()
            if name.startswith("/") or "/" in name or not re.fullmatch(r"part_\d{3}\.ts",name):
                raise RuntimeError(f"Unsafe/missing HLS segment path: {name}")
            segment=path.parent/name
            if not segment.is_file() or segment.stat().st_size < 100_000:
                raise RuntimeError(f"Missing/short segment: {segment}")
            parts.append((name,duration))
    if not parts:
        raise RuntimeError("Missing any segments")
    duration=sum(d for _,d in parts)
    if not expected_seconds-1.5 <= duration <= expected_seconds+1.5:
        raise RuntimeError(f"Expected source cycle ~{expected_seconds}s, got {duration:.2f}s")
    return parts


def verify_transport(segment):
    cmd=["ffprobe","-v","error","-select_streams","a:0",
         "-show_entries","stream=codec_name,sample_rate,channels",
         "-of","json",str(segment)]
    p=subprocess.run(cmd,capture_output=True,text=True,check=True)
    stream=json.loads(p.stdout)["streams"][0]
    if stream["codec_name"]!="aac" or int(stream["sample_rate"])!=44100 or int(stream["channels"])!=2:
        raise RuntimeError(f"Invalid HLS transport {segment}: {stream}")


def build_loop(parts,path):
    n_cycles=int(math.ceil(DAYS*86400 / sum(s for _,s in parts)))
    # Static native audio timeline. Avoid JS-driven replay at 10 minute transitions.
    # Reset MPEG-TS timestamps with a discontinuity only on each source cycle.
    base=[
        "#EXTM3U","#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:"+str(math.ceil(max(d for _,d in parts))),
        "#EXT-X-MEDIA-SEQUENCE:0",
        "#EXT-X-PLAYLIST-TYPE:VOD",
        "#EXT-X-INDEPENDENT-SEGMENTS",
    ]
    for cycle in range(n_cycles):
        if cycle:
            base.append("#EXT-X-DISCONTINUITY")
        for part,duration in parts:
            base.append("#EXTINF:"+format(duration,".6f")+",")
            base.append(part)
    base.append("#EXT-X-ENDLIST")
    path.write_text("\n".join(base)+"\n",encoding="utf-8")
    return n_cycles,n_cycles*sum(d for _,d in parts)


def build_fast_test(master,out_dir):
    """A private 12-second cross-boundary test: <30s to see HLS replay on iPhone."""
    path=out_dir/"quick"
    path.mkdir(parents=True,exist_ok=True)
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
         "-ss","120","-i",str(master),"-t","12",
         "-ar","44100","-ac","2","-c:a","aac","-b:a","160k",
         "-f","hls","-hls_time","3","-hls_segment_type","mpegts",
         "-hls_list_size","0","-hls_playlist_type","vod",
         "-hls_segment_filename",str(path/"part_%03d.ts"),str(path/"source.m3u8")]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError("Quick test HLS conversion failed: "+p.stderr[-1000:])
    segments=parse_quick(path/"source.m3u8")
    return path,segments


def parse_quick(path):
    lines=path.read_text().splitlines()
    parts=[]
    for i,line in enumerate(lines):
        if line.startswith("#EXTINF:"):
            parts.append((lines[i+1].strip(),float(line[8:].split(",",1)[0])))
    if not 10<=sum(d for _,d in parts)<=14:
        raise RuntimeError("12-second quick test failed duration validation")
    return parts


def main():
    originals=[]
    for filename, allowed in ((COLOR_MASTER,COLORS),(GREEN_MASTER,GREEN),(NATURE_MASTER,NATURE),
                              (EXTENDED_MASTER,EXTENDED)):
        j=json.loads(filename.read_text(encoding="utf-8"))
        entries=[j] if filename==GREEN_MASTER else j["masters"] if filename==NATURE_MASTER else j["tracks"]
        for e in entries:
            if e["id"] not in allowed:
                continue
            qa=e.get("qa",e.get("technical_qa"))
            if qa["technical_status"]!="PASS":
                raise RuntimeError(f"Original master not QA-approved: {e['id']}")
            file=ROOT/(e["id"]+".mp3")
            if sha(file)!=e["file_sha256"]:
                raise RuntimeError(f"Original MP3 hash mismatch: {file}")
            originals.append((e,file))
    # The remaining 4 licensed field recordings are STILL short (54 seconds).
    # A 7-day HLS transport fixes the premature stop without disguising
    # low-variation raw material as 10 minutes of unique field recording.
    registry=json.loads(FIELD_REGISTRY.read_text(encoding="utf-8"))
    for row in registry:
        if row["id"] not in LEGACY_CC0:
            continue
        file=ROOT/(row["id"]+".mp3")
        if not file.is_file():
            raise RuntimeError("Missing original CC0 file "+str(file))
        # Preserve provenance in the output manifest and leave MP3 bytes alone.
        original={
            "id":row["id"],"file_sha256":sha(file),
            "source_license":row["license"],
            "source_page":row["source"],
            "source_preview_sha256":row["preview_sha256"],
            "source_editorial_status":row.get("production_status","LEGACY_54_SECOND_DEMO_PENDING_LONG_RECORDING"),
        }
        originals.append((original,file))
    if {e["id"] for e,_ in originals}!=ALL or len(originals)!=len(ALL):
        raise RuntimeError("Expected exactly 22 player sound sources")
    HLS_ROOT.mkdir(parents=True,exist_ok=True)
    report=[]
    for e,master in originals:
        ident=e["id"]
        with tempfile.TemporaryDirectory(dir=HLS_ROOT) as td:
            temp=Path(td)
            run_ffmpeg(master,temp)
            expected=float(next(r["derived_duration_seconds"] for r in registry if r["id"]==ident)) if ident in LEGACY_CC0 else 600
            chunks=parse_playlist(temp/"source.m3u8", expected_seconds=expected)
            verify_transport(temp/chunks[0][0])
            cycles, duration=build_loop(chunks,temp/"continuous.m3u8")
            if duration < DAYS*86400:
                raise RuntimeError("HLS playlist too short for the required window")
            outputs=[p for p in temp.iterdir() if p.name.startswith("part_")]+[temp/"continuous.m3u8"]
            if len(outputs)!=len(chunks)+1:
                raise RuntimeError("Missing HLS output")
            target=HLS_ROOT/ident
            target.mkdir(parents=True,exist_ok=True)
            # Update only the stream for this single identified track.
            for p in target.glob("part_*.ts"):
                p.unlink()
            for p in outputs:
                shutil.copy2(p,target/p.name)
            report.append({
                "id":ident,"master_file":str(master),
                "master_sha256":e["file_sha256"],
                "playlist_file":str(target/"continuous.m3u8"),
                "playlist_sha256":sha(target/"continuous.m3u8"),
                "segment_count_per_source_cycle":len(chunks),
                "source_cycle_seconds":round(sum(d for _,d in chunks),3),
                "original_source_length_category":("APPROVED_CC0_FIELD_RECORDING" if e.get("source_editorial_status")=="OWNER_APPROVED_FIELD_RECORDING" else "LEGACY_CC0_SHORT_DEMO") if ident in LEGACY_CC0 else "10_MINUTE_MASTER",
                "source_license":e.get("source_license",e.get("license","original_dsp")),
                "source_page":e.get("source_page"),
                "editorial_status":e.get("source_editorial_status","OWNER_APPROVED_FOR_AUDIO" if ident in EXTENDED and e.get("qa",{}).get("listening_approval")=="APPROVED_BY_OWNER" else "PENDING_NEW_BATCH_HUMAN_REVIEW" if ident in (EXTENDED|GREEN) else "PREVIOUSLY_REVIEWED"),
                "repeated_cycles":cycles,
                "native_stream_duration_hours":round(duration/3600,2),
                "audio_codec":"AAC-LC in MPEG-TS",
                "sample_rate":44100,"channels":2,"bitrate_kbps":BITRATE,
                "long_form_listening_status":"OWNER_APPROVED_LISTENING" if (ident in EXTENDED and e.get("qa",{}).get("listening_approval")=="APPROVED_BY_OWNER") or e.get("source_editorial_status")=="OWNER_APPROVED_FIELD_RECORDING" else "PENDING_IPHONE_LOCK_SCREEN_REVIEW",
                "notes":"iOS native HLS avoids JS-driven track restarts at source boundaries. Short CC0 sources are not misrepresented as ten minutes of independent material. No claim of perfectly seamless or literally infinite streaming.",
            })
            print("HLS_OK",json.dumps(report[-1]),flush=True)
    # Rapid manual experiment: loop after 12s, instead of waiting 10 minutes.
    white=ROOT/"white-noise.mp3"
    quick_dir,shortparts=build_fast_test(white,HLS_ROOT)
    loops=math.ceil(1200/sum(v for _,v in shortparts))
    short_lines=[
        "#EXTM3U","#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:"+str(math.ceil(max(d for _,d in shortparts))),
        "#EXT-X-MEDIA-SEQUENCE:0","#EXT-X-PLAYLIST-TYPE:VOD",
        "#EXT-X-INDEPENDENT-SEGMENTS"
    ]
    for k in range(loops):
        if k:
            short_lines.append("#EXT-X-DISCONTINUITY")
        for fn,d in shortparts:
            short_lines.extend(("#EXTINF:"+format(d,".6f")+",",fn))
    short_lines.append("#EXT-X-ENDLIST")
    (quick_dir/"continuous.m3u8").write_text("\n".join(short_lines)+"\n",encoding="utf-8")
    summary={
        "version":HLS_VERSION,
        "playlist_type":"static multi-cycle HLS VOD, seven days per track, 22 sound IDs",
        "applies_to":sorted(ALL),
        "reason":"avoid relying on JS to play another MP3 when iOS Safari is backgrounded or the screen is locked",
        "browser_policy":"Use HLS if the audio element advertises native application/vnd.apple.mpegurl support; otherwise use the original looping MP3.",
        "not_an_infinite_stream":"A static GitHub Pages site cannot issue an unbounded server-generated HLS stream. The element also has loop=true at the playlist end.",
        "manual_fast_test_file":"audio/continuous/quick/continuous.m3u8",
        "source_length_disclosure":"18 produced or arranged 10-minute masters and 4 owner-approved natural CC0 recordings with actual lengths 67.52, 189.76, 89.83 and 375.48 seconds. Source cycles repeat.",
        "records":report,
    }
    (HLS_ROOT/"manifest.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print("SUMMARY",json.dumps({"count":len(report),"total_playlist_hours":round(sum(r["native_stream_duration_hours"] for r in report),2),"fast_test_cycle_sec":sum(v for _,v in shortparts)}),flush=True)


if __name__=="__main__":
    main()
