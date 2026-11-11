#!/usr/bin/env python3
"""Read-only snapshot of unique R2 audio files and their source metadata."""
import base64
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import re

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from harvest_nature_diversity_to_r2 import Intake, BUCKET

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAupHZS7dPOUA83UGBPUPw
Im1jmFADzLDqqqW6aOGxvXPWyegEo1VPAmJpsvuQeGw0wgH8Ix+x8aB27IJVDl3T
aGKOvGhhuIlynkWWqiOHTvj044C3sxy2ZUnGhjQ8MmssW3FxKsIelxm7kSJEot47
JkvOxAdEVviMHeKzxF1HTCahPPySYIr78w6E4o+zao6VOH4vApjLMDmYiDV4cshj
1KzzJY8+i50QzVkjS2VJYFQ6FA81IaREoglCK3tYNMXhICcVN7AgnPfTBfKx1KlU
PoYaL+dFZyEaNzzk71YdtdCBMmRKe7XMEki7al/HNUkSb0JcYqu5gdbvloxawwWo
dwIDAQAB
-----END PUBLIC KEY-----"""
AUDIO = re.compile(r"^asset-library/(.*?)/sha256/(?:[a-f0-9]{2}/)?([a-f0-9]{64})\.(wav|mp3|ogg|oga|opus|flac|m4a|aiff?|au|wma)$", re.I)
METADATA = re.compile(r"/([a-f0-9]{64})\.json$")
FIELDS = (
    "title", "file_title", "original_filename", "source_provider", "source_page", "download_url", "license",
    "source_pack", "taxonomy_query_category", "category_initial", "group_hint", "discovery_hint",
    "scientific_name", "species_taxon_id", "iconic_taxon", "environment_hint", "recorded_date",
    "time_from_filename", "recording_date_from_filename", "library", "duration_seconds", "codec",
    "sample_rate_hz", "channels", "classification_status", "description", "source_tags",
    "source_version_note", "creator", "credit", "original_page", "source_title", "filename", "category",
)
def main():
    s3 = Intake().s3
    files = defaultdict(list)
    sidecars = defaultdict(list)
    aliases = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix="asset-library/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            audio = AUDIO.fullmatch(key)
            if audio and obj["Size"]:
                files[audio[2]].append((key, obj["Size"], audio[1]))
            if "/records/" in key and key.endswith(".json"):
                match = METADATA.search(key)
                if match:
                    sidecars[match[1]].append(key)
                else:
                    aliases.append(key)
    checked_at = datetime.now(timezone.utc).isoformat()
    order = ("raw", "commons", "kenney", "cc0-github-mirror")
    rank = lambda x: order.index(x[2]) if x[2] in order else len(order)

    def read(key):
        try:
            response = s3.get_object(Bucket=BUCKET, Key=key)
            with response["Body"] as body:
                payload = json.load(body)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def metadata(digest):
        options = sorted(sidecars.get(digest, []), key=lambda key: (not key.startswith("asset-library/records/sha256/"), key))
        for key in options:
            value = read(key)
            if value and value.get("audio_sha256", value.get("sha256", digest)) == digest:
                return key, value
        return "", {}

    rows = {}
    with ThreadPoolExecutor(max_workers=24) as pool:
        jobs = {pool.submit(metadata, digest): digest for digest in files}
        for future in as_completed(jobs):
            digest = jobs[future]
            meta_key, value = future.result()
            selected = sorted(files[digest], key=rank)
            key, size, prefix = selected[0]
            rows[digest] = {"sha256": digest, "key": key, "bytes": size, "prefix": prefix,
                            "object_count": len(selected), "record_key": meta_key,
                            **{field: value[field] for field in FIELDS if value.get(field) is not None}}
        missing = {digest for digest, row in rows.items() if not row["record_key"]}
        # Only read source aliases when a canonical record is absent.
        if missing and aliases:
            for alias, value in zip(aliases, pool.map(read, aliases)):
                digest = value.get("audio_sha256") or value.get("sha256")
                if digest not in missing:
                    continue
                rows[digest].update(record_key=alias, **{field: value[field] for field in FIELDS if value.get(field) is not None})
                missing.remove(digest)
                if not missing:
                    break
    snapshot = {"checked_at": checked_at, "unique_files": len(rows),
                "audio_objects": sum(len(items) for items in files.values()),
                "total_bytes": sum(item["bytes"] for item in rows.values()),
                "missing_metadata": sum(not item["record_key"] for item in rows.values()),
                "by_prefix": dict(Counter(row["prefix"] for row in rows.values())),
                "assets": sorted(rows.values(), key=lambda row: row["sha256"])}
    payload = gzip.compress(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode())
    public_key = serialization.load_pem_public_key(PUBLIC_KEY.encode())
    secret = AESGCM.generate_key(bit_length=256)
    wrapped = public_key.encrypt(secret, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    nonce = __import__("os").urandom(12)
    sealed = wrapped + nonce + AESGCM(secret).encrypt(nonce, payload, None)
    Path("snapshot.enc").write_bytes(sealed)
    encoded = base64.b64encode(sealed).decode()
    for index in range(0, len(encoded), 3000):
        print(f"SNAPSHOT_PART {index // 3000:04d} {encoded[index:index+3000]}", flush=True)
    print("AUDIT_FINAL " + json.dumps({k: v for k, v in snapshot.items() if k != "assets"}
          | {"sealed_bytes": len(sealed), "parts": (len(encoded)+2999)//3000}), flush=True)


if __name__ == "__main__":
    main()
