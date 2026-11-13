#!/usr/bin/env python3
"""Offline, read-only converter: old intake/sidecar records -> canonical Metadata V2.

No R2/Studio writes, no audio download, no AI inference, no license claims.
Usage: python scripts/normalize_audio_metadata_v2.py --input batch.json --output batch-v2.json
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

DIGEST_PATH = re.compile(r"/([a-f0-9]{64})\.[a-z0-9]+$", re.I)
HEX = re.compile(r"^[a-f0-9]{64}$")
ROLES = {"CONTINUOUS_BED", "SEAMLESS_LOOP", "ONE_SHOT", "RECURRING_EVENT", "PASS_BY", "TRANSITION", "TEXTURE", "SPEECH_OR_VOCAL", "MUSICAL_FOREGROUND", "MUSICAL_ACCOMPANIMENT"}


def first(*items):
    return next((x for x in items if x is not None and x != ""), None)


def txt(value):
    return str(value).strip() if value is not None and str(value).strip() else None


def https(value):
    s = txt(value)
    return s if s and s.startswith("https://") and len(s) < 2048 else None


def number(value, *, integer=False, positive=False):
    try:
        value = int(value) if integer else float(value)
        if not math.isfinite(value) or (positive and value <= 0):
            return None
        return value
    except (TypeError, ValueError, OverflowError):
        return None


def missing_evidence():
    return {"method": "unknown", "tool": None, "confidence": None, "evidence_url": None}


def normalize(row):
    if not isinstance(row, dict):
        raise ValueError("expected metadata object")
    if row.get("schema_version") == 2:
        return row  # idempotent; validation is performed after conversion
    src = row.get("source") if isinstance(row.get("source"), dict) else {}
    rights = row.get("rights") if isinstance(row.get("rights"), dict) else {}
    technical = row.get("technical") if isinstance(row.get("technical"), dict) else {}
    semantic = row.get("semantic") if isinstance(row.get("semantic"), dict) else {}
    key = txt(first(row.get("audio_storage_key"), row.get("storage_key"), row.get("key")))
    key_digest = DIGEST_PATH.search(key).group(1).lower() if key and DIGEST_PATH.search(key) else None
    source_sha = first(row.get("audio_sha256"), row.get("file_sha256"), row.get("sha256"))
    source_sha = txt(source_sha)
    source_sha = source_sha.lower() if source_sha else None
    if source_sha and not HEX.fullmatch(source_sha):
        raise ValueError("invalid SHA-256")
    if key_digest and source_sha and key_digest != source_sha:
        raise ValueError("SHA-256 differs from storage key")
    digest = first(source_sha, key_digest)
    url = https(first(row.get("source_page"), row.get("source_url"), src.get("source_url"), row.get("url")))
    if digest:
        asset_id = "r2-" + digest
        basis = "content_sha256_from_sidecar" if source_sha else "storage_key_digest_unverified"
    elif key:
        asset_id = "legacy-key-" + hashlib.sha256(key.encode("utf-8")).hexdigest()
        basis = "legacy_storage_key"
    elif url:
        asset_id = "legacy-url-" + hashlib.sha256(url.encode("utf-8")).hexdigest()
        basis = "legacy_source_url"
    else:
        raise ValueError("no stable identity available")

    license_name = txt(first(row.get("license"), rights.get("license"), src.get("license")))
    evidence_url = https(first(row.get("license_evidence_url"), rights.get("license_evidence_url"), src.get("evidence_url")))
    license_url = https(first(row.get("license_url"), src.get("license_url")))
    verified_at = txt(first(row.get("license_checked_at"), rights.get("verified_at"), row.get("verified_at")))
    explicit_verified = rights.get("source_license_verified") is True
    # A license label or HTTP link alone is not independent rights verification.
    rights_status = "attested" if explicit_verified and license_name and evidence_url and verified_at else "unverified"
    duration = number(first(row.get("duration_seconds"), row.get("duration"), technical.get("duration_seconds")), positive=True)
    file_bytes = number(first(row.get("file_bytes"), row.get("bytes"), technical.get("file_bytes")), integer=True, positive=True)
    rate = number(first(row.get("sample_rate_hz"), technical.get("sample_rate_hz")), integer=True, positive=True)
    channels = number(first(row.get("channels"), technical.get("channels")), integer=True, positive=True)
    group = txt(first(row.get("group_hint"), row.get("group"), row.get("category"), semantic.get("group")))
    name = txt(first(row.get("title"), row.get("file_title"), row.get("original_filename"), row.get("name")))
    role = txt(first(row.get("role"), row.get("sound_role"), semantic.get("sound_role")))
    if role not in ROLES:
        role = None
    aliases = row.get("aliases")
    if isinstance(aliases, str):
        aliases = [aliases]
    if not isinstance(aliases, list):
        aliases = []
    aliases = list(dict.fromkeys(x for x in (txt(a) for a in aliases) if x))
    slots = row.get("legacy_slots", [])
    if not isinstance(slots, list) or any(not isinstance(v, int) or v < 0 for v in slots):
        slots = []
    slots = sorted(set(slots))
    # Imported descriptive tags are not presented as audio-model measurements.
    hints = first(row.get("source_tags"), row.get("discovery_hint"))
    tags = list(dict.fromkeys([v for v in (txt(x) for x in ([hints] if isinstance(hints, str) else hints or [])) if v]))
    evidence = {"identity": {"method": "verified" if source_sha else "inferred", "tool": "sidecar" if source_sha else "storage-key", "confidence": None, "evidence_url": None},
                "source.license": {"method": "inferred" if rights_status == "attested" else "unknown", "tool": "source-rights-attestation" if rights_status == "attested" else None, "confidence": None, "evidence_url": evidence_url},
                "technical.duration_seconds": {"method": "inferred" if duration is not None else "unknown", "tool": "imported-metadata" if duration is not None else None, "confidence": None, "evidence_url": None},
                "semantic.group": {"method": "inferred" if group else "unknown", "tool": "source-metadata" if group else None, "confidence": None, "evidence_url": None},
                "semantic.sound_role": {"method": "inferred" if role else "unknown", "tool": "source-metadata" if role else None, "confidence": None, "evidence_url": None}}
    return {
        "schema_version": 2, "asset_id": asset_id, "identity_basis": basis,
        "content_sha256": digest, "storage_key": key, "legacy_slots": slots, "aliases": aliases,
        "lifecycle": "discovered",  # R2 object existence is NOT verified by this offline converter
        "source": {"provider": txt(first(row.get("source_provider"), src.get("provider"))), "source_url": url,
                   "creator": txt(first(row.get("creator"), row.get("attribution"), row.get("uploader"), src.get("creator"))),
                   "license": license_name, "license_url": license_url, "evidence_url": evidence_url,
                   "verified_at": verified_at if verified_at and verified_at.endswith("Z") else None,
                   "rights_status": rights_status},
        "technical": {"duration_seconds": duration, "codec": txt(first(row.get("codec"), technical.get("codec"))),
                      "sample_rate_hz": rate, "channels": channels, "file_bytes": file_bytes,
                      "integrated_lufs": None, "true_peak_dbtp": None},
        "semantic": {"name": name, "group": group, "entity": None, "tags": tags, "sound_role": role,
                     "environment": None, "near_far": None, "texture": None, "mood": None,
                     "intensity": None, "loop_capability": None},
        "musical": {"instrument": None, "bpm": None, "time_signature": None, "key": None,
                    "chords": None, "musical_role": None},
        "evidence": evidence,
    }


def convert(rows):
    seen = set()
    out = []
    errors = []
    for i, row in enumerate(rows):
        try:
            item = normalize(row)
            if item["asset_id"] in seen:
                continue  # dedup by stable ID
            seen.add(item["asset_id"])
            out.append(item)
        except ValueError as exc:
            errors.append({"index": i, "error": str(exc)})
    return out, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--schema", default=str(Path(__file__).resolve().parents[1] / "schema" / "asset-metadata-v2.schema.json"))
    args = ap.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("assets", data.get("items", data.get("rows")))
    if not isinstance(rows, list):
        raise SystemExit("input must contain assets/items/rows array")
    out, errors = convert(rows)
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise SystemExit("Install jsonschema (pip install jsonschema>=4)") from exc
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for i, row in enumerate(out):
        for error in validator.iter_errors(row):
            errors.append({"index": i, "asset_id": row.get("asset_id"), "error": error.message})
    result = {"schema_version": 2, "mode": "offline_read_only", "output_count": len(out), "error_count": len(errors), "assets": out, "errors": errors}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("output_count", "error_count")}, ensure_ascii=False))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
