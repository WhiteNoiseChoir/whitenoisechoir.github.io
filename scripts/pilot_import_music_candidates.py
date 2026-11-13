#!/usr/bin/env python3
"""Small CC0-only, rights-approved music candidate audio intake into PRIVATE R2.

Default is a read-only preflight; --ingest requires a distinct pre-existing
approval object in the private R2 ledger. Never infers recording / underlying
composition rights from a candidate source license alone. No website, mixer or
production catalog modification. No public URLs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit
from urllib.parse import urljoin

import requests

import scan_music_candidate_metadata as core

CANDIDATES = core.PRIVATE_ROOT + "v1/"
APPROVALS = core.PRIVATE_ROOT + "approved-audio/v1/"
IMPORTS = core.PRIVATE_ROOT + "audio-imports/v1/"
KEY_RE = re.compile(r"^internal/music-candidates/v1/([a-f0-9]{2})/([a-f0-9]{64})\.json$")
ALLOWED_MEDIA_HOSTS = {"upload.wikimedia.org"}
EXTENSIONS = {".wav", ".flac", ".ogg", ".opus", ".mp3", ".m4a", ".aif", ".aiff"}
MAX_SOURCE_BYTES = 32 * 1024 * 1024
BUDGET_BYTES = 250 * 1024 * 1024
CHUNK = 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def candidate_keys(s3, max_records=5000):
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(
            Bucket=core.BUCKET, Prefix=CANDIDATES):
        for obj in page.get("Contents", []):
            if KEY_RE.fullmatch(obj["Key"]) and obj.get("Size", 0) > 0:
                keys.append(obj["Key"])
                if len(keys) > max_records:
                    raise ValueError("Candidate count exceeded safe scan cap")
    return sorted(keys)


def safe_media_url(raw):
    if not isinstance(raw, str) or len(raw) > 2048:
        return False
    try:
        url = urlsplit(raw)
        return (url.scheme == "https" and url.hostname in ALLOWED_MEDIA_HOSTS
                and not url.username and not url.password and not url.port
                and not url.fragment and
                Path(url.path).suffix.lower() in EXTENSIONS)
    except ValueError:
        return False


def load_json(s3, key, max_bytes=50000):
    data = s3.get_object(Bucket=core.BUCKET, Key=key)
    length = int(data.get("ContentLength") or 0)
    if length > max_bytes:
        raise ValueError("Unexpectedly large private JSON")
    payload = data["Body"].read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("Oversize private JSON body")
    return json.loads(payload)


def approval_key(candidate):
    return APPROVALS + candidate["candidate_id"] + ".json"


def gate(candidate, approval):
    """No source metadata can self-authorize audio import."""
    if not isinstance(candidate, dict):
        return "BAD_CANDIDATE"
    if candidate.get("schema") != "music_source_candidate_v1":
        return "BAD_SCHEMA"
    if candidate.get("provider") != "Wikimedia Commons":
        return "PROVIDER_NOT_APPROVED"
    if candidate.get("license") != "CC0-1.0":
        return "NO_VERIFIED_CC0"
    if not candidate.get("source_license_verified_at"):
        return "SOURCE_LICENSE_UNVERIFIED"
    if not safe_media_url(candidate.get("source_media_url")):
        return "URL_NOT_ALLOWLISTED"
    size = candidate.get("source_file_bytes")
    if not isinstance(size, int) or not 1000 <= size <= MAX_SOURCE_BYTES:
        return "FILE_SIZE_OUT_OF_RANGE"
    if not isinstance(approval, dict):
        return "NO_INDEPENDENT_RIGHTS_APPROVAL"
    if approval.get("schema") != "music_audio_rights_approval_v1":
        return "INVALID_APPROVAL_SCHEMA"
    if approval.get("candidate_id") != candidate.get("candidate_id"):
        return "APPROVAL_WRONG_CANDIDATE"
    if approval.get("source_media_url") != candidate.get("source_media_url"):
        return "APPROVAL_WRONG_SOURCE_VERSION"
    required = ("recording_rights_verified", "composition_rights_verified",
                "download_authorized", "commercial_derivative_reuse_allowed")
    if not all(approval.get(k) is True for k in required):
        return "RIGHTS_NOT_CLEARED"
    if not isinstance(approval.get("reviewed_by"), str) or not approval["reviewed_by"].strip():
        return "MISSING_REVIEWER"
    if not isinstance(approval.get("reviewed_at"), str) or not approval["reviewed_at"].strip():
        return "MISSING_REVIEW_TIME"
    evidence = approval.get("evidence_urls")
    if (not isinstance(evidence, list) or not evidence
            or not all(isinstance(u, str) and u.startswith("https://") for u in evidence)):
        return "MISSING_RIGHTS_EVIDENCE"
    return "ELIGIBLE"


def read_approval(s3, candidate):
    key = approval_key(candidate)
    try:
        return load_json(s3, key)
    except s3.exceptions.NoSuchKey:
        return None
    except Exception as exc:
        # Never interpret R2 permission or network failure as a missing approval.
        if getattr(exc, "response", {}).get("Error", {}).get("Code") in (
                "NoSuchKey", "404", "NotFound"):
            return None
        raise


def available_candidates(s3, max_records):
    counts = Counter()
    candidates = []
    for key in candidate_keys(s3, max_records):
        try:
            candidate = load_json(s3, key)
            match = KEY_RE.fullmatch(key)
            if candidate.get("candidate_id") != "music-candidate-" + match.group(2):
                counts["WRONG_CANDIDATE_ID"] += 1
                continue
            if candidate.get("provider") != "Wikimedia Commons":
                counts["PROVIDER_NOT_APPROVED"] += 1
                continue
            if candidate.get("license") != "CC0-1.0":
                counts["NO_VERIFIED_CC0"] += 1
                continue
            if not candidate.get("source_license_verified_at"):
                counts["SOURCE_LICENSE_UNVERIFIED"] += 1
                continue
            if not safe_media_url(candidate.get("source_media_url")):
                counts["URL_NOT_ALLOWLISTED"] += 1
                continue
            if (not isinstance(candidate.get("source_file_bytes"), int)
                    or not 1000 <= candidate["source_file_bytes"] <= MAX_SOURCE_BYTES):
                counts["FILE_SIZE_OUT_OF_RANGE"] += 1
                continue
            approval = read_approval(s3, candidate)
            reason = gate(candidate, approval)
            counts[reason] += 1
            if reason == "ELIGIBLE":
                candidates.append((candidate, approval))
        except Exception as exc:
            counts["READ_ERROR"] += 1
            print("MUSIC_AUDIO_PREFLIGHT_ERROR " +
                  json.dumps({"type": type(exc).__name__}), flush=True)
    return candidates, counts


def stream_safe_media(candidate, destination):
    """Never follow a redirect to an untrusted host; hard byte cap."""
    url = candidate["source_media_url"]
    with requests.Session() as session:
        session.headers.update({"User-Agent": "WhiteNoiseChoir-PrivateApprovedAudio/1.0"})
        response = None
        for redirect_index in range(4):
            if not safe_media_url(url):
                raise ValueError("Source/redirect media URL not allowlisted")
            if response is not None:
                response.close()
            response = session.get(url, stream=True, timeout=(12, 40),
                                   allow_redirects=False)
            if response.status_code in (301, 302, 303, 307, 308):
                if redirect_index == 3:
                    raise ValueError("Too many media redirects")
                target = response.headers.get("Location", "")
                url = urljoin(url, target)
                continue
            response.raise_for_status()
            break
        if response is None:
            raise ValueError("No source response")
        try:
            if response.headers.get("Content-Length"):
                size = int(response.headers["Content-Length"])
                if size > MAX_SOURCE_BYTES:
                    raise ValueError("Media too large")
            count = 0
            sha = hashlib.sha256()
            with destination.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=CHUNK):
                    if not chunk:
                        continue
                    count += len(chunk)
                    if count > MAX_SOURCE_BYTES:
                        raise ValueError("Source exceeded byte limit")
                    sha.update(chunk)
                    fh.write(chunk)
            if count < 1000:
                raise ValueError("Source too small to be audio")
            if count != candidate["source_file_bytes"]:
                raise ValueError("Size differs from source metadata")
            return sha.hexdigest(), count
        finally:
            response.close()


def ffprobe(path):
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
        "format=duration,format_name:stream=codec_type,codec_name,sample_rate,channels",
        "-of", "json", str(path)], text=True, capture_output=True,
        timeout=30, check=False)
    if proc.returncode:
        raise ValueError("ffprobe audio check failed")
    meta = json.loads(proc.stdout)
    audio = next((s for s in meta.get("streams", [])
                  if s.get("codec_type") == "audio"), None)
    if audio is None:
        raise ValueError("No valid audio stream")
    duration = float(meta.get("format", {}).get("duration", 0))
    if not 0.2 <= duration <= 3600:
        raise ValueError("Audio duration out of bounds")
    return {"duration_seconds": duration, "codec": audio.get("codec_name"),
            "channels": audio.get("channels"),
            "sample_rate_hz": int(audio.get("sample_rate") or 0)}


def existing_digest_set(s3):
    """Dedup by true content SHA, also against the existing 22k+ asset library."""
    prefixes = ("asset-library/raw/sha256/", "asset-library/commons/sha256/",
                "asset-library/kenney/sha256/", "asset-library/cc0-github-mirror/sha256/")
    digests = set()
    for prefix in prefixes:
        pages = s3.get_paginator("list_objects_v2").paginate(
            Bucket=core.BUCKET, Prefix=prefix)
        for page in pages:
            for obj in page.get("Contents", []):
                m = re.search(r"/([a-f0-9]{64})\.[a-z0-9]+$", obj["Key"])
                if m:
                    digests.add(m.group(1))
    return digests


def persist_one(s3, candidate, approval, digest, byte_count, path, technical):
    ext = Path(candidate["source_media_url"].split("?", 1)[0]).suffix.lower()
    key = f"asset-library/raw/sha256/{digest[:2]}/{digest}{ext}"
    mime = mimetypes.guess_type(key)[0] or "application/octet-stream"
    with path.open("rb") as fh:
        s3.put_object(Bucket=core.BUCKET, Key=key, Body=fh,
                      ContentLength=byte_count, ContentType=mime,
                      IfNoneMatch="*", CacheControl="private,no-store",
                      Metadata={"sha256": digest, "candidate-id": candidate["candidate_id"]})
    head = s3.head_object(Bucket=core.BUCKET, Key=key)
    if int(head.get("ContentLength", -1)) != byte_count:
        raise RuntimeError("R2 HEAD size mismatch after upload")
    if (head.get("Metadata") or {}).get("sha256") != digest:
        raise RuntimeError("R2 HEAD SHA metadata mismatch after upload")
    sidecar = {
        "schema": "music_audio_import_provenance_v1",
        "state": "STORED_R2_QA_LISTENING_PENDING",
        "studio_ready": False, "cataloged": False,
        "source_candidate_id": candidate["candidate_id"],
        "source_page": candidate["source_page"],
        "source_media_url": candidate["source_media_url"],
        "license": "CC0-1.0",
        "rights_approval_key": approval_key(candidate),
        "rights_evidence_urls": approval["evidence_urls"],
        "content_sha256": digest, "storage_key": key,
        "bytes": byte_count, "technical": technical,
        "ingested_at": now(),
    }
    s3.put_object(Bucket=core.BUCKET, Key=IMPORTS + digest + ".json",
                  Body=json.dumps(sidecar, ensure_ascii=False).encode("utf-8"),
                  ContentType="application/json",
                  CacheControl="private,no-store", IfNoneMatch="*")
    return key


def process(s3, candidates, limit, byte_budget, dry_run):
    states = Counter()
    existing = existing_digest_set(s3) if not dry_run and candidates else set()
    budget_used = 0
    with tempfile.TemporaryDirectory(prefix="wnc-approved-audio-") as tmp:
        for candidate, approval in candidates[:limit]:
            estimate = candidate["source_file_bytes"]
            if budget_used + estimate > byte_budget:
                states["SKIP_BUDGET"] += 1
                continue
            if dry_run:
                states["READY_FOR_APPROVED_IMPORT"] += 1
                budget_used += estimate
                continue
            path = Path(tmp) / (candidate["candidate_id"] + Path(candidate["file_name"]).suffix.lower())
            try:
                digest, size = stream_safe_media(candidate, path)
                states["DOWNLOADED"] += 1
                if digest in existing:
                    states["SKIP_SHA256_DUPLICATE"] += 1
                    continue
                tech = ffprobe(path)
                states["VALIDATED"] += 1
                persist_one(s3, candidate, approval, digest, size, path, tech)
                states["STORED_R2"] += 1
                existing.add(digest)
                budget_used += size
            except Exception as exc:
                states["FAILED"] += 1
                print("MUSIC_AUDIO_IMPORT_ERROR " + json.dumps({
                    "type": type(exc).__name__, "message": str(exc)[:120]}), flush=True)
            finally:
                path.unlink(missing_ok=True)
    return states, budget_used


def run(args):
    if not 1 <= args.batch_size <= 8 or not 1 <= args.max_records <= 10000:
        raise ValueError("Unsafe cap")
    if not 1 <= args.byte_budget_mib <= 250:
        raise ValueError("Unsafe storage budget")
    s3 = core.s3_client()
    eligible, diagnostics = available_candidates(s3, args.max_records)
    selected, bytes_used = process(s3, eligible, args.batch_size,
                                   args.byte_budget_mib * 1024**2, not args.ingest)
    result = {
        "schema": "music_candidate_audio_pilot_report_v1", "at": now(),
        "mode": "ingest" if args.ingest else "preflight_only",
        "candidate_objects_scanned": sum(diagnostics.values()),
        "rights_eligible": len(eligible),
        "rejected_by_gate": dict(diagnostics),
        "selected": dict(selected), "bytes_imported": bytes_used if args.ingest else 0,
        "audio_files_stored_r2": selected["STORED_R2"],
        "cataloged": 0, "studio_ready": 0,
        "media_allowed_license": "CC0-1.0", "approval_mode": "private_manual_review_required",
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("MUSIC_AUDIO_PILOT_FINAL " + json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ingest", action="store_true")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-records", type=int, default=5000)
    ap.add_argument("--byte-budget-mib", type=int, default=250)
    ap.add_argument("--output", default="audits/music-candidate-audio-pilot.json")
    args = ap.parse_args()
    result = run(args)
    if result["selected"].get("FAILED"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
