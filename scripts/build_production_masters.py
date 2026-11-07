#!/usr/bin/env python3
"""Build 10-minute *extended listening masters* from TWO user-approved 60s recordings.

No synthesized noise, unverified recordings, or changes to other audio.
This constructs varied crossfaded arrangements of the approved 60s MP3s.
It does NOT create 10 minutes of independent original field recording.
The long-form loop must be evaluated on iPhone before claiming human approval.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess
import tempfile
import numpy as np

SR = 44100
SECONDS = 600
WRAP_SECONDS = 6
ROOT = Path("signature")
OUT = Path("audio")
TARGETS = {
    "rain-window": ("rain-on-window-real", 2026110701),
    "fireplace": ("fireplace-real", 2026110702),
}
PINNED_APPROVED_MP3 = {
    "rain-window": "b77b2d020776e75e4ab37c7345081e8a058b2a8bdd3190c6e3effda20a294212",
    "fireplace": "05ef121e522af14fbf895c4cc3d9375fd0aaa69ff24ca2aeeba8ee1b998501f7",
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def decode(path, seconds=SECONDS + 1):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path),
           "-t", str(seconds), "-ar", str(SR), "-ac", "2", "-f", "f32le", "pipe:1"]
    p = subprocess.run(cmd, capture_output=True, check=True)
    if len(p.stdout) % 8:
        raise RuntimeError("Not a whole stereo float32 stream")
    return np.frombuffer(p.stdout, dtype="<f4").reshape(-1, 2).copy()

def encode(path, data):
    with tempfile.NamedTemporaryFile(dir=OUT, prefix=path.stem + ".", suffix=".mp3", delete=False) as tmp:
        staging = Path(tmp.name)
    try:
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "pipe:0",
               "-c:a", "libmp3lame", "-b:a", "192k", str(staging)]
        p = subprocess.run(cmd, input=np.asarray(data, dtype="<f4").tobytes(), capture_output=True)
        if p.returncode:
            raise RuntimeError("MP3 encoding failed: " + p.stderr.decode(errors="replace")[-600:])
        staging.replace(path)
    finally:
        staging.unlink(missing_ok=True)

def db(value):
    return 20 * math.log10(max(1e-12, float(value)))

def rms(x):
    return math.sqrt(float(np.mean(np.square(x), dtype=np.float64)))

def arrange(source, seed):
    """Deterministic 24-39s slices, 5s cosine/sine overlap-add; output is periodic.

    Slices are rearranged, never pitch shifted or populated with artificial noise.
    The final 6s beyond the file boundary are gently blended into the first 6s.
    """
    source = np.asarray(source, dtype=np.float32)
    src_frames = 60 * SR
    if len(source) != src_frames:
        raise RuntimeError(f"Expected 60-second approved source, got {len(source)/SR:.3f}s")
    total = (SECONDS + WRAP_SECONDS) * SR
    target = np.zeros((total, 2), dtype=np.float32)
    rng = np.random.default_rng(seed)
    filled = 0
    blocks = []
    previous_start = -1
    previous_length = 0
    fade = 5 * SR

    while filled < total:
        segment_seconds = int(rng.integers(24, 40))
        length = segment_seconds * SR
        # Ensure a different section of the underlying field recording is selected.
        candidates = np.arange(0, 60 - segment_seconds + 1)
        if previous_start >= 0:
            choices = candidates[np.abs(candidates - previous_start) >= 5]
            if len(choices):
                candidates = choices
        src_start = int(rng.choice(candidates))
        start = filled - fade if filled else 0
        written = min(length, total - start)
        clip = source[src_start*SR:src_start*SR + written]
        if len(clip) != written:
            raise RuntimeError("Source slice too short")
        if filled:
            overlap = min(fade, written)
            phase = np.linspace(0.0, np.pi/2, overlap, dtype=np.float32)[:, None]
            target[start:start+overlap] = (
                target[start:start+overlap] * np.cos(phase) +
                clip[:overlap] * np.sin(phase)
            )
            target[start+overlap:start+written] = clip[overlap:]
        else:
            target[:written] = clip
        filled = start + written
        blocks.append({"original_start_seconds": src_start,
                       "segment_seconds": round(written/SR, 2),
                       "crossfade_seconds": 0 if len(blocks)==0 else round(min(fade, written)/SR, 2)})
        previous_start = src_start
        previous_length = written

    n = SECONDS * SR
    f = WRAP_SECONDS * SR
    blend = np.sin(np.linspace(0, np.pi/2, f, dtype=np.float32)[:, None])**2
    # The final sample at 600s flows naturally into 600s+1 sample at the loop head.
    target[:f] = target[n:n+f] * (1-blend) + target[:f] * blend
    target = target[:n].copy()

    # Restore the source's average acoustic energy, without aggressive limiting.
    source_rms = rms(source)
    before_rms = rms(target)
    restoration = np.clip(source_rms / max(before_rms, 1e-12), 10**(-1.2/20), 10**(1.2/20))
    target *= float(restoration)
    # Protective global trim, rather than peak clipping.
    ceiling = 10**(-4.0/20)
    peak = float(np.max(np.abs(target)))
    if peak > ceiling:
        target *= ceiling/peak
    return target, blocks

def r128(path):
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-nostdin", "-i", str(path),
           "-filter:a", "ebur128=peak=true", "-f", "null", "-"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError("EBU R128 failed: " + p.stderr[-600:])
    loud = re.search(r"Integrated loudness:\s*I:\s*([-+]?\d+(?:\.\d+)?)\s*LUFS", p.stderr)
    peak = re.search(r"True peak:\s*Peak:\s*([-+]?\d+(?:\.\d+)?)\s*dBFS", p.stderr)
    if not loud or not peak:
        raise RuntimeError("Could not parse the integrated EBU R128 summary")
    return float(loud.group(1)), float(peak.group(1))

def qa(path, sample_qa):
    pcm = decode(path)
    if not (599.8 <= len(pcm) / SR <= 600.2):
        raise RuntimeError(f"Incorrect MP3 duration: {len(pcm)/SR}")
    pk = db(np.max(np.abs(pcm)))
    level = db(rms(pcm))
    crest = pk - level
    loudness, dbtp = r128(path)
    frame = SR // 4
    windows = pcm[:(len(pcm)//frame)*frame].reshape(-1, frame, 2)
    energy = np.mean(np.square(windows), axis=(1,2), dtype=np.float64)
    quiet = int(np.count_nonzero(10*np.log10(energy+1e-18)<-65))
    jump = float(np.sqrt(np.mean((pcm[0]-pcm[-1]).astype(np.float64)**2)))
    typical = math.sqrt(float(np.mean(np.square(np.diff(pcm, axis=0)), dtype=np.float64)))+1e-12
    ratio = jump / typical
    # A hard 60s copy-paste loop is not an acceptable 10-minute master.
    periodicity = float(np.corrcoef(pcm[SR:2*SR:31,0], pcm[61*SR:62*SR:31,0])[0,1])
    flags = []
    if pk > -3: flags.append("insufficient_sample_peak_headroom")
    if dbtp > -1.5: flags.append("insufficient_true_peak_headroom")
    if crest > 25: flags.append("crest_factor_over_25db")
    if level < -32 or level > -22: flags.append("rms_outside_normal_listening_range")
    if abs(level - sample_qa["rms_dbfs"]) > 3: flags.append("rms_changed_over_3db_from_approved_sample")
    if abs(loudness - sample_qa["integrated_loudness_lufs"]) > 3.5: flags.append("lufs_changed_over_3_5_from_approved_sample")
    if quiet > 15: flags.append("too_many_quiet_250ms_windows")
    if ratio > 6: flags.append("loop_boundary_jump")
    if periodicity > .98: flags.append("obvious_repeated_60_second_loop")
    return {
        "duration_seconds": round(len(pcm)/SR,2),
        "sample_rate": SR, "channels": 2, "codec": "mp3", "bitrate_kbps":192,
        "rms_dbfs": round(level,2), "sample_peak_dbfs": round(pk,2),
        "crest_factor_db": round(crest,2), "integrated_loudness_lufs":round(loudness,1),
        "true_peak_dbtp": round(dbtp,1),
        "quiet_windows_250ms_below_minus65dbfs":quiet,
        "loop_boundary_jump_vs_typical_adjacent_diff":round(ratio,3),
        "correlation_60_seconds_apart":round(periodicity,4),
        "technical_status":"PASS" if not flags else "REVIEW",
        "flags":flags,
        "human_approval":"APPROVED_60_SECOND_SOURCE_ONLY",
        "long_form_listening_status":"PENDING_IPHONE_LOOP_REVIEW",
    }

def run():
    manifest = json.loads((ROOT/"manifest.json").read_text(encoding="utf-8"))
    originals = {t["id"]: t for t in manifest["tracks"]}
    current = {}
    out_records = []
    for id,(dest_id,seed) in TARGETS.items():
        item = originals[id]
        src = ROOT/item["file"]
        actual_hash = digest(src)
        if actual_hash != item["file_sha256"] or actual_hash != PINNED_APPROVED_MP3[id]:
            raise RuntimeError(f"Approved source checksum mismatch: {id}")
        if item["qa"]["technical_status"]!="PASS" or item["qa"]["flags"]:
            raise RuntimeError(f"Approved source failed its own technical QA: {id}")
        src_pcm = decode(src, seconds=61)
        if len(src_pcm) < SR*60:
            raise RuntimeError(f"Source shorter than 60s: {id}")
        src_pcm = src_pcm[:SR*60]
        rendered, blocks = arrange(src_pcm, seed)
        destination = OUT/(dest_id+".mp3")
        # Only publish after all safety checks succeed; overwrite is deliberate.
        with tempfile.TemporaryDirectory(dir=OUT) as td:
            tmp_path = Path(td)/(dest_id+".mp3")
            encode(tmp_path, rendered)
            checks = qa(tmp_path, item["qa"])
            print("MASTER_QA",json.dumps({"id":dest_id,**checks}), flush=True)
            if checks["technical_status"]!="PASS":
                raise RuntimeError(f"Master QA failed for {dest_id}: {checks['flags']}")
            destination.write_bytes(tmp_path.read_bytes())
        out_records.append({
            "id":dest_id,"title":item["title"],"file":str(destination),
            "file_sha256":digest(destination),
            "bytes":destination.stat().st_size,
            "source_signature_file":str(src),"source_signature_sha256":actual_hash,
            "source_page":item["source_page"],"author":item["author"],
            "license":item["license"],"source_preview_sha256":item["source_preview_sha256"],
            "construction":"deterministic natural-recording segment reordering, 5s overlaps and 6s terminal loop splice",
            "independent_source_duration_seconds":60,
            "recorded_material_extended":True,
            "segment_count":len(blocks),
            "seed":seed,"technical_qa":checks
        })
        print("MASTER_CREATED", dest_id, digest(destination), destination.stat().st_size, flush=True)
    payload={
        "collection":"WhiteNoiseChoir long-form production candidates",
        "version":"long-master-v1-20261107",
        "generated_from":"Signature Collection Batch 01 v2 remasters, 60 seconds each",
        "duration_seconds":SECONDS,
        "independent_field_recording_minutes_per_track":1,
        "disclosure":"These 10-minute tracks repeat and rearrange material from a 60-second approved sample; not 10 minutes of unique field recording.",
        "sample_user_approved_date":"2026-11-07",
        "long_master_human_approved":False,
        "masters":out_records,
    }
    (OUT/"master-manifest.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("MASTER_SUMMARY", json.dumps({"total":len(out_records),
        "pass":sum(r["technical_qa"]["technical_status"]=="PASS" for r in out_records),
        "long_master_human_approved":False}), flush=True)

if __name__=="__main__":
    run()
