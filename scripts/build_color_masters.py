#!/usr/bin/env python3
"""WhiteNoiseChoir original colored-noise production masters, batch 02.

Create exactly three independent full-length 10-minute noise master files.
White ~ 1/f^0, pink ~ 1/f^1, brown ~ 1/f^2 (power spectral density).
No repeated 60-second samples, field recordings, or procedural nature fakes.
DSP is deterministic (fixed seeds) and rendered as 44.1kHz centered stereo MP3.
The QA inspects the FINAL decoded MP3 after lossy encoding, not only the PCM.
Human listening approval remains separate from technical PASS.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import re
import subprocess
import tempfile
import gc

import numpy as np
from scipy.fft import irfft, rfftfreq
from scipy.signal import welch

ROOT = Path("audio")
ROOT.mkdir(parents=True, exist_ok=True)
SR = 44100
DURATION = 600
LOOP_BLEND = 5
BITRATE_KBPS = 192
VERSION = "color-master-v1-20261107"
TRACKS = (
    ("white-noise", "White Noise", 0.0, 2026110711),
    ("pink-noise", "Pink Noise", 1.0, 2026110712),
    ("brown-noise", "Brown Noise", 2.0, 2026110713),
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def db(x):
    return 20 * math.log10(max(float(x), 1e-12))


def synth(alpha: float, seed: int):
    """Independently synthesize 605s of noise; overlap first 5s with the last
    5s beyond 600s to maintain a natural sample-to-sample loop boundary.
    FFT-based power-law shaping provides each noise its measurable identity.
    """
    frames = (DURATION + LOOP_BLEND) * SR
    rng = np.random.default_rng(seed)
    freqs = rfftfreq(frames, d=1/SR).astype(np.float32)
    # Spectral exponent alpha applies to power: |X(f)|^2 ~ 1/f^alpha.
    profile = np.power(np.maximum(freqs, 22), -alpha / 2, dtype=np.float32)
    profile *= freqs / np.sqrt(freqs * freqs + 22.0 * 22.0)
    profile *= 1.0 / np.sqrt(1.0 + (freqs / 15500.0)**10)
    spec = (rng.standard_normal(freqs.size, dtype=np.float32) +
            1j * rng.standard_normal(freqs.size, dtype=np.float32)).astype(np.complex64)
    spec *= profile
    spec[0] = 0
    del freqs, profile
    mono = irfft(spec, n=frames, workers=1).astype(np.float32)
    del spec
    mono /= np.std(mono, dtype=np.float64) + 1e-12

    n = DURATION * SR
    fade = LOOP_BLEND * SR
    raw = mono[:n].copy()
    blend = np.sin(np.linspace(0, np.pi/2, fade, dtype=np.float32))**2
    raw[:fade] = mono[n:n+fade] * (1-blend) + raw[:fade] * blend
    del mono, blend

    # Slightly softer white noise avoids harshness; all share consistent
    # -28/-27/-26 dBFS targets but need separate real-device listening review.
    target_rms = {0.0:-28.0, 1.0:-27.0, 2.0:-26.0}[alpha]
    raw -= float(raw.mean(dtype=np.float64))
    raw *= (10**(target_rms/20)) / (math.sqrt(float(np.mean(raw*raw, dtype=np.float64))) + 1e-12)
    peak = float(np.max(np.abs(raw)))
    # Maintain headroom, trim globally instead of compressing/limiting peaks.
    ceiling = 10**(-5/20)
    if peak > ceiling:
        raw *= ceiling / peak
    return raw


def write_mp3(path: Path, mono: np.ndarray):
    # Centered two-channel output; do not introduce artificial stereo beating
    # or phase cancellation when mono combined by a phone's small speaker.
    # Stream fixed-size chunks to avoid another full-length 2-channel allocation.
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "pipe:0",
        "-c:a", "libmp3lame", "-b:a", f"{BITRATE_KBPS}k", str(path)
    ]
    p = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        step = SR * 5
        for start in range(0, len(mono), step):
            block = mono[start:start+step]
            stereo = np.empty((len(block), 2), dtype=np.float32)
            stereo[:, 0] = block
            stereo[:, 1] = block
            p.stdin.write(stereo.astype("<f4", copy=False).tobytes())
        p.stdin.close()
        error = p.stderr.read().decode(errors="replace")
        code = p.wait()
        if code:
            raise RuntimeError("MP3 encoder failed: " + error[-800:])
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
    if not path.exists() or path.stat().st_size < 10_000_000:
        raise RuntimeError("MP3 output unexpectedly small")


def decode_mp3(path: Path) -> np.ndarray:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
           "-i", str(path), "-ar", str(SR), "-ac", "2", "-f", "f32le", "pipe:1"]
    result = subprocess.run(cmd, capture_output=True, check=True)
    if len(result.stdout) % 8:
        raise RuntimeError("Not a complete stereo float32 stream")
    return np.frombuffer(result.stdout, dtype="<f4").reshape(-1, 2)


def r128(path: Path):
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-nostdin", "-i", str(path),
           "-filter:a", "ebur128=peak=true", "-f", "null", "-"]
    p = subprocess.run(cmd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError("EBU R128 failed: " + p.stderr[-800:])
    lufs = re.search(r"Integrated loudness:\s*I:\s*([-+]?\d+(?:\.\d+)?)\s*LUFS", p.stderr)
    peak = re.search(r"True peak:\s*Peak:\s*([-+]?\d+(?:\.\d+)?)\s*dBFS", p.stderr)
    if not lufs or not peak:
        raise RuntimeError("Could not parse FFmpeg EBU R128 summary")
    return float(lufs.group(1)), float(peak.group(1))


def verify(path: Path, alpha: float):
    x = decode_mp3(path)
    seconds = len(x) / SR
    mono = x[:, 0]
    level = math.sqrt(float(np.mean(np.square(mono), dtype=np.float64)))
    pk = float(np.max(np.abs(x)))
    rms_dbfs = db(level)
    pk_dbfs = db(pk)
    crest = pk_dbfs - rms_dbfs
    slope_freq, pxx = welch(mono[::4], fs=SR/4, nperseg=8192)
    valid = (slope_freq>=110) & (slope_freq<=5000) & (pxx>1e-18)
    slope = float(np.polyfit(np.log10(slope_freq[valid]),
                            10*np.log10(pxx[valid]),1)[0])
    window = SR // 4
    segments = mono[:(len(mono)//window)*window].reshape(-1, window)
    levels = 10 * np.log10(np.mean(np.square(segments), axis=1, dtype=np.float64)+1e-18)
    quiet = int(np.count_nonzero(levels < -65))
    delta = float(abs(mono[0] - mono[-1]))
    typical = math.sqrt(float(np.mean(np.square(np.diff(mono[::10]).astype(np.float64))))+1e-12)
    # because typical uses every 10th sample, the more stringent threshold below remains useful
    jump_ratio = delta / typical
    correlation = float(np.corrcoef(mono[SR:2*SR:29], mono[61*SR:62*SR:29])[0,1])
    avg_10s = []
    for start in range(0, len(mono)-SR*10+1, SR*10):
        block = mono[start:start+SR*10]
        avg_10s.append(db(math.sqrt(float(np.mean(np.square(block), dtype=np.float64)))))
    drift_db = max(avg_10s)-min(avg_10s)
    lufs, true_peak = r128(path)
    flags = []
    if not (599.8 <= seconds <= 600.2): flags.append("duration_not_10_minutes")
    if pk_dbfs > -3: flags.append("peak_headroom_low")
    if true_peak > -1.5: flags.append("true_peak_headroom_low")
    if not (-34 <= rms_dbfs <= -23): flags.append("rms_out_of_range")
    if crest > 23: flags.append("crest_too_high")
    if not (-38<=lufs<=-17): flags.append("lufs_out_of_range")
    if abs(slope + alpha*10) > 2.5: flags.append("incorrect_noise_color_spectral_slope")
    if quiet > 1: flags.append("unexpected_silence")
    if jump_ratio > 3: flags.append("loop_boundary_discontinuity")
    if abs(correlation) > .25: flags.append("suspect_60_second_repetition")
    if drift_db > 3.2: flags.append("unstable_10_second_loudness")
    data = {
        "duration_seconds":round(seconds,3),
        "sample_rate":SR,"channels":2,"stereo_mode":"centered_dual_mono",
        "codec":"mp3","bitrate_kbps":BITRATE_KBPS,
        "rms_dbfs":round(rms_dbfs,2),"sample_peak_dbfs":round(pk_dbfs,2),
        "crest_factor_db":round(crest,2),
        "integrated_loudness_lufs":round(lufs,1),
        "true_peak_dbtp":round(true_peak,1),
        "spectral_slope_db_per_decade":round(slope,2),
        "target_spectral_slope_db_per_decade":-alpha*10,
        "quiet_windows_250ms_below_minus65dbfs":quiet,
        "loop_boundary_jump_vs_typical_diff":round(jump_ratio,3),
        "correlation_60_seconds_apart":round(correlation,4),
        "max_10_second_rms_variation_db":round(drift_db,2),
        "technical_status":"PASS" if not flags else "REVIEW",
        "flags":flags,
        "long_form_human_listening_status":"PENDING_USER_REVIEW",
    }
    del x,mono,segments,levels
    return data


def run():
    result = []
    for id,title,alpha,seed in TRACKS:
        print(f"START {id}: synth full 10 min of original independent 1/f^{alpha} noise",flush=True)
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            temp = Path(td)/(id+".mp3")
            pcm = synth(alpha,seed)
            write_mp3(temp,pcm)
            del pcm
            gc.collect()
            qa = verify(temp,alpha)
            print("TECHNICAL_QA", json.dumps({"id":id,**qa}),flush=True)
            if qa["technical_status"] != "PASS":
                raise RuntimeError(f"{id}: {qa['flags']}")
            out = ROOT/(id+".mp3")
            out.write_bytes(temp.read_bytes())
        result.append({
            "id":id,"title":title,
            "file":f"audio/{id}.mp3",
            "file_sha256":sha256(out),
            "bytes":out.stat().st_size,
            "algorithm":"independent_original_full_length_frequency_domain_colored_noise",
            "power_spectral_exponent_alpha":alpha,
            "seed":seed,"qa":qa,
        })
        print(f"BUILT {id}: {out.stat().st_size} bytes, sha256 {sha256(out)}",flush=True)
    manifest={
        "collection":"WhiteNoiseChoir original color-noise masters",
        "version":VERSION,
        "tracks":result,
        "duration_seconds":DURATION,
        "approval":"automated technical QA only; device listening review pending",
        "loop_note":"PCM 5-second boundary crossfade; final MP3 gapless playback depends on browser/decoder.",
        "source":"original DSP, no sample or external recording",
    }
    path=ROOT/"color-master-manifest.json"
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SUMMARY",json.dumps({"total":len(result),"passes":sum(i["qa"]["technical_status"]=="PASS" for i in result)}),flush=True)

if __name__ == "__main__":
    run()
