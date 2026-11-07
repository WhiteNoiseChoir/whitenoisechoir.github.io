#!/usr/bin/env python3
"""Remaster only the two QA outliers from existing Signature Collection MP3s.

This is a deterministic *dynamic-range remaster*, not a replacement source:
- Rain on Window: recover continuous low-level rain without adding synthesized noise.
- Fireplace: preserve authentic crackles while reducing excessive transient peaks.

Never auto-approve human listening QA. Keep all other eight MP3s unchanged.
"""
from pathlib import Path
import hashlib, json, math, re, subprocess
import numpy as np
from scipy.ndimage import uniform_filter1d, maximum_filter1d
from scipy.signal import welch

ROOT = Path("signature")
AUDIO = ROOT / "audio"
MANIFEST = ROOT / "manifest.json"
SUMMARY = ROOT / "quality-summary.json"
SR=44100
N=60*SR
# Only an original v1 asset may be remastered. Never repeatedly compress a v2 master.
ORIGINAL_V1_SHA256 = {
    "rain-window": "10b112f26f2ca7a8121ef247e99f869284aa3c6c74a8ddeafe754198ac09c392",
    "fireplace": "faacedb18850470870432acb7d18858a221d95b4fb20029a30e",
}
FIXES = {
    "rain-window": {"ratio": 5.5, "threshold_dbfs": -46, "target_rms_dbfs": -28.2, "peak_ceiling_dbfs": -7.0},
    "fireplace": {"ratio": 8.0, "threshold_dbfs": -49, "target_rms_dbfs": -29.2, "peak_ceiling_dbfs": -7.0},
}

def ffdecode(path):
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-i",str(path),
         "-t","60","-ar",str(SR),"-ac","2","-f","f32le","pipe:1"]
    result=subprocess.run(cmd,check=True,capture_output=True)
    output=np.frombuffer(result.stdout,dtype="<f4").reshape(-1,2).copy()
    if len(output)<N-SR//5: raise ValueError(f"{path} too short: {len(output)/SR}")
    return output[:N]

def ffencode(path,x):
    dest=path.with_name(path.stem+".remastered.mp3")
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","f32le","-ar",str(SR),"-ac","2",
         "-i","pipe:0","-codec:a","libmp3lame","-b:a","192k",str(dest)]
    result=subprocess.run(cmd,input=np.asarray(x,dtype="<f4").tobytes(),capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors="replace")[-1200:])
    dest.replace(path)

def rms_db(x):
    val=float(np.sqrt(np.mean(np.square(x.astype(np.float64)))))
    return 20*math.log10(max(1e-12,val))
def peak_db(x):
    return 20*math.log10(max(1e-12,float(np.max(np.abs(x)))))

def remaster(x,cfg):
    x=x.astype(np.float32,copy=True)
    x-=x.mean(axis=0,keepdims=True)
    thresh=10**(cfg["threshold_dbfs"]/20)
    # 55ms RMS envelope, shared across stereo channels to preserve placement.
    power=np.mean(x*x,axis=1)
    envelope=np.sqrt(np.maximum(1e-15,uniform_filter1d(power,size=round(SR*.055),mode="reflect")))
    gain=np.minimum(1.,(thresh/np.maximum(thresh,envelope))**(1.-1./cfg["ratio"]))
    # Smooth envelope gain to avoid rapid amplitude modulation / zipper noise.
    gain=uniform_filter1d(gain,size=round(SR*.050),mode="reflect")
    x*=gain[:,None]
    target=10**(cfg["target_rms_dbfs"]/20)
    actual=np.sqrt(np.mean(x.astype(np.float64)**2))
    x*=float(target/max(1e-12,actual))
    # Look-ahead-like peak limiter with a short rolling neighborhood.
    ceiling=10**(cfg["peak_ceiling_dbfs"]/20)
    local_peaks=maximum_filter1d(np.max(np.abs(x),axis=1),size=round(SR*.018),mode="reflect")
    limiter=np.minimum(1.,.94*ceiling/np.maximum(local_peaks,1e-8))
    limiter=uniform_filter1d(limiter,size=round(SR*.012),mode="reflect")
    x*=limiter[:,None]
    # Protective final trim (not hard clipping).
    pk=float(np.max(np.abs(x)))
    if pk>ceiling:x*=ceiling/pk
    return x

def ebu_r128(path):
    # Analyze the FINAL encoded MP3 with FFmpeg's EBU R128 meter, not the PCM intermediate.
    cmd=["ffmpeg","-hide_banner","-nostats","-nostdin","-i",str(path),
         "-filter:a","ebur128=peak=true","-f","null","-"]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode: raise RuntimeError("EBU R128 analysis failed: "+p.stderr[-700:])
    integrated=re.search(r"Integrated loudness:\s*I:\s*([-+]?\d+(?:\.\d+)?)\s*LUFS",p.stderr)
    true_peak=re.search(r"True peak:\s*Peak:\s*([-+]?\d+(?:\.\d+)?)\s*dBFS",p.stderr)
    if not integrated or not true_peak:
        raise ValueError("Missing EBU R128 final summary; refuse incomplete loudness QA")
    return float(integrated.group(1)),float(true_peak.group(1))

def qa(x,path):
    n=len(x);s=x.mean(axis=1)
    frame=SR//4
    windows=x[:(n//frame)*frame].reshape(-1,frame,2).astype(np.float64)
    window_rms=20*np.log10(np.sqrt(np.mean(windows**2,axis=(1,2)))+1e-12)
    silences=int((window_rms<-65).sum())
    frequencies,power=welch(s,fs=SR,nperseg=16384)
    valid=(frequencies>=110)&(frequencies<=6000)&(power>1e-19)
    slope=float(np.polyfit(np.log10(frequencies[valid]),10*np.log10(power[valid]),1)[0])
    boundary=float(np.sqrt(np.mean((x[0]-x[-1])**2)))
    adjacent=float(np.sqrt(np.mean(np.diff(x,axis=0).astype(np.float64)**2)))+1e-12
    loop_ratio=boundary/adjacent
    actual_rms=rms_db(x)
    pk=peak_db(x)
    crest=pk-actual_rms
    lufs,true_peak=ebu_r128(path)
    flags=[]
    if n<59.5*SR:flags.append("duration_too_short")
    if pk>=-0.05:flags.append("sample_clipping")
    if actual_rms < -32:flags.append("rms_level_too_low_relative_to_collection")
    if actual_rms > -22:flags.append("rms_level_too_high_relative_to_collection")
    if crest > 25:flags.append("crest_factor_too_high")
    if pk > -3:flags.append("peak_headroom_too_low")
    if true_peak > -1:flags.append("true_peak_headroom_too_low")
    if lufs < -38 or lufs > -18:flags.append("integrated_loudness_outside_audition_range")
    if silences>=4:flags.append("unexpected_silence_windows")
    if loop_ratio>6:flags.append("loop_transition_needs_review")
    return dict(duration_seconds=round(n/SR,3),sample_rate=SR,channels=2,codec="mp3",
      bitrate_kbps=192,rms_dbfs=round(actual_rms,2),sample_peak_dbfs=round(pk,2),
      crest_factor_db=round(crest,2),integrated_loudness_lufs=round(lufs,1),
      true_peak_dbtp=round(true_peak,1),
      spectral_slope_db_per_decade=round(slope,2),
      quiet_windows_250ms_below_minus65dbfs=silences,
      loop_boundary_jump_vs_typical_adjacent_diff=round(loop_ratio,3),
      technical_status="PASS" if not flags else "REVIEW",flags=flags,
      listening_status="PENDING_HUMAN_REVIEW",
      note="Dynamic-range remaster from the same original source. Automated technical results are not a listening approval.")

def main():
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    records={r["id"]:r for r in manifest["tracks"]}
    # Audit every existing file before any processing, including the eight untouched tracks.
    for row in manifest["tracks"]:
        audio=ROOT/row["file"]
        if not audio.is_file() or hashlib.sha256(audio.read_bytes()).hexdigest()!=row["file_sha256"]:
            raise RuntimeError("Audio file/manifest checksum mismatch: "+row["id"])
    for id,cfg in FIXES.items():
        row=records[id]
        path=ROOT/row["file"]
        old_sha=row["file_sha256"]
        before=ffdecode(path)
        if row.get("mastering_revision")=="signature-remaster-v2":
            # Existing v2 is already remastered; audit, DO NOT re-compress/re-encode.
            after=before
            action="AUDIT_EXISTING_V2"
        else:
            if old_sha!=ORIGINAL_V1_SHA256[id]:
                raise RuntimeError(f"Refusing to remaster unrecognized {id} source {old_sha}")
            raw_after=remaster(before,cfg)
            ffencode(path,raw_after)
            after=ffdecode(path)
            row["mastering_revision"]="signature-remaster-v2"
            row["mastering_settings"]=cfg
            row["previous_file_sha256"]=old_sha
            row["file_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
            action="REMASTERED_FROM_PINNED_V1"
        new_qa=qa(after,path)
        row["qa"]=new_qa
        print("REMASTER_QA",json.dumps({"id":id,"action":action,
              "before_rms_dbfs":round(rms_db(before),2),"after_rms_dbfs":new_qa["rms_dbfs"],
              "sample_peak_dbfs":new_qa["sample_peak_dbfs"],
              "crest_factor_db":new_qa["crest_factor_db"],
              "integrated_loudness_lufs":new_qa["integrated_loudness_lufs"],
              "true_peak_dbtp":new_qa["true_peak_dbtp"],
              "quiet_windows_250ms_below_minus65dbfs":new_qa["quiet_windows_250ms_below_minus65dbfs"],
              "sha256":row["file_sha256"],"status":new_qa["technical_status"],
              "flags":new_qa["flags"]}),flush=True)
        if new_qa["technical_status"]!="PASS":
            raise RuntimeError(f"{id} failed technical QA; do not publish audio")
    # Reconcile summary exclusively from the track manifest after reprocessing.
    all_tracks=manifest["tracks"]
    failures=[r for r in all_tracks if r["qa"]["technical_status"]!="PASS"]
    summary={"total":len(all_tracks),"technical_passes":len(all_tracks)-len(failures),
       "technical_review":len(failures),"human_approved":0,
       "mean_rms_dbfs":round(sum(r["qa"]["rms_dbfs"] for r in all_tracks)/len(all_tracks),2),
       "review_tracks":[r["id"] for r in failures],
       "revision":"dynamic-range-remaster-02-loudness-audit-01",
       "note":"Final encoded MP3 RMS, EBU R128 LUFS, true peak, and crest factor measured for remastered tracks. Human listening approval remains pending."}
    # Preserve version: audios are byte-identical after a successful v2 audit.
    manifest["version"]="batch-01-remaster-02"
    manifest["qa_caveat"]="Two former level outliers remastered and rechecked. Automated PASS does not indicate human listening approval."
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SIGNATURE_SUMMARY",json.dumps(summary),flush=True)
    if summary["technical_review"]:
       print("QA REVIEW STILL REQUIRED: "+", ".join(summary["review_tracks"]),flush=True)

if __name__=="__main__":main()
