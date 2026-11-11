#!/usr/bin/env python3
"""Build the encrypted Vietnamese Studio catalog from current R2 audio and provenance."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from math import isfinite
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

import boto3
from botocore.config import Config
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from audit_r2_asset_inventory import ACCOUNT_ID, BUCKET, PREFIXES

DEST = "internal/studio-catalog/v1.json"
MEDIA = re.compile(r"/([a-f0-9]{64})\.(wav|mp3|m4a|aac|flac|ogg|oga|opus|webm|aif|aiff|au|caf|wma|mp4)$", re.I)
BROWSER_MEDIA = {"wav", "mp3", "m4a", "aac", "flac", "ogg", "oga", "opus", "webm", "mp4"}
SIDECARS = (
    "asset-library/records/sha256/",
    "asset-library/commons/records/",
    "asset-library/kenney/records/",
    "asset-library/cc0-github-mirror/records/",
)
DIGEST_JSON = re.compile(r"/([a-f0-9]{64})\.json$")
LICENSES = {"CC0", "CC0-1.0", "PUBLIC DOMAIN", "PUBLIC-DOMAIN", "CC-BY-3.0", "CC-BY-4.0"}
CONTEXT = b"WhiteNoiseChoir Studio catalog v1"


def objects(s3, prefix):
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        yield from page.get("Contents", [])


def get_json(s3, key):
    with s3.get_object(Bucket=BUCKET, Key=key)["Body"] as body:
        return json.load(body)


def clean(value, maximum):
    return " ".join(str(value or "").split())[:maximum]


def url(value):
    if not isinstance(value, str) or len(value) > 650:
        return ""
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme == "https" and parsed.hostname and not parsed.username else ""
    except ValueError:
        return ""


def asset(s3, item, keys):
    digest, candidates = item
    for key in keys.get(digest, []):
        record = get_json(s3, key)
        if record.get("audio_sha256") != digest:
            continue
        license_name = clean(record.get("license"), 40)
        if license_name.upper() not in LICENSES:
            continue
        source = url(record.get("source_page") or record.get("license_evidence_url"))
        attribution = clean(record.get("attribution") or record.get("creator") or record.get("uploader"), 280)
        license_url = url(record.get("license_url"))
        if not source or (license_name.upper().startswith("CC-BY") and not (attribution and license_url)):
            continue
        try:
            duration = float(record.get("duration_seconds") or 0)
        except (TypeError, ValueError):
            continue
        if not isfinite(duration) or duration <= 0:
            continue
        media = next((row for row in candidates if row["Key"] == record.get("audio_storage_key")), candidates[0])
        if int(record.get("file_bytes") or 0) != media["Size"]:
            continue
        title = clean(record.get("title") or record.get("file_title") or record.get("original_filename"), 180)
        if not title:
            continue
        hints = " ".join(clean(record.get(k), 120) for k in (
            "scientific_name", "iconic_taxon", "taxonomy_query_category", "category_initial",
            "discovery_hint", "source_tags", "group_hint"))
        return {
            "id": "r2-" + digest,
            "key": media["Key"], "name": title, "duration": round(duration, 3),
            "license": license_name, "source": source, "licenseUrl": license_url,
            "credit": attribution, "provider": clean(record.get("source_provider"), 65),
            "taxon": clean(record.get("iconic_taxon"), 35), "aliases": hints.strip()[:360],
        }
    return None


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def unb64(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def seal(payload, jwk):
    public = ec.EllipticCurvePublicNumbers(
        int.from_bytes(unb64(jwk["x"]), "big"), int.from_bytes(unb64(jwk["y"]), "big"),
        ec.SECP256R1(),
    ).public_key()
    ephemeral = ec.generate_private_key(ec.SECP256R1())
    shared = ephemeral.exchange(ec.ECDH(), public)
    key = hashlib.sha256(shared + CONTEXT).digest()
    nonce = os.urandom(12)
    plaintext = gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(), compresslevel=6)
    numbers = ephemeral.public_key().public_numbers()
    return {
        "v": 1, "ephemeral": {"kty": "EC", "crv": "P-256", "x": b64(numbers.x.to_bytes(32, "big")),
                              "y": b64(numbers.y.to_bytes(32, "big"))},
        "iv": b64(nonce), "cipher": b64(AESGCM(key).encrypt(nonce, plaintext, CONTEXT)),
    }



def write_worker_catalog(s3, bucket, payload):
    public = []
    shards = {}
    owner_rows = []
    for row in payload["rows"]:
        identifier = hashlib.sha256(("wnc-public-source-v1/" + row["id"]).encode()).hexdigest()[:32]
        shards.setdefault(identifier[:2], {})[identifier] = row["key"]
        owner_rows.append({**row, "publicId": "public-" + identifier})
        public.append({
            "id": identifier, "name": row["name"], "taxon": row["taxon"],
            "duration": row["duration"], "aliases": row["aliases"],
            "credit": row["credit"], "license": row["license"], "licenseUrl": row["licenseUrl"], "source": row["source"],
        })

    def put(key, value):
        s3.put_object(Bucket=bucket, Key=key,
                      Body=json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode(),
                      ContentType="application/json")

    with ThreadPoolExecutor(max_workers=24) as pool:
        list(pool.map(lambda pair: put("catalog/sources/" + pair[0] + ".json", pair[1]), shards.items()))
    put("catalog/owner.json", {**payload, "rows": owner_rows})
    put("catalog/public.json", {"version": 1, "generatedAt": payload["generatedAt"], "sounds": public})
    print("STUDIO_WORKER_CATALOG_READY " + json.dumps({"internal": len(payload["rows"]), "public_sources": len(public)}), flush=True)


def main():
    s3 = boto3.client(
        "s3", region_name="auto", endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4", max_pool_connections=48,
                      s3={"addressing_style": "path"}, retries={"max_attempts": 6, "mode": "standard"}),
    )
    catalog = {}
    stored = set()
    for prefix in PREFIXES.values():
        for item in objects(s3, prefix):
            match = MEDIA.search(item["Key"])
            if match and item["Size"] > 0:
                digest, extension = match.groups()
                digest = digest.lower()
                stored.add(digest)
                if extension.lower() in BROWSER_MEDIA:
                    catalog.setdefault(digest, []).append(item)

    metadata = {}
    for prefix in SIDECARS:
        for item in objects(s3, prefix):
            match = DIGEST_JSON.search(item["Key"])
            if match and match[1] in catalog:
                metadata.setdefault(match[1], []).append(item["Key"])
    rows = []
    items = sorted(catalog.items())
    with ThreadPoolExecutor(max_workers=40) as pool:
        for i, row in enumerate(pool.map(lambda item: asset(s3, item, metadata), items), start=1):
            if row:
                rows.append(row)
            if i % 2000 == 0:
                print(f"STUDIO_CATALOG_PROGRESS {i}/{len(items)}", flush=True)

    if len(rows) < 1000:
        raise RuntimeError("Catalog unexpectedly small. Existing encrypted snapshot retained.")
    payload = {
        "version": 1, "generatedAt": datetime.now(timezone.utc).isoformat(),
        "inventoryCount": len(stored), "browserFormats": len(catalog), "rows": rows,
    }
    worker_bucket = os.environ.get("STUDIO_STATE_BUCKET", "").strip()
    if worker_bucket:
        if worker_bucket == BUCKET:
            raise RuntimeError("Studio state must use its own private bucket")
        write_worker_catalog(s3, worker_bucket, payload)
    jwk = json.loads((Path(__file__).parents[1] / "data" / "studio-catalog-public-key.json").read_text())
    encoded = json.dumps(seal(payload, jwk), separators=(",", ":")).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    s3.put_object(Bucket=BUCKET, Key=DEST, Body=encoded, ContentType="application/json",
                  CacheControl="no-store", Metadata={"sha256": digest})
    saved = s3.head_object(Bucket=BUCKET, Key=DEST)
    if saved["ContentLength"] != len(encoded) or saved["Metadata"].get("sha256") != digest:
        raise RuntimeError("Encrypted R2 catalog failed write verification")
    print("STUDIO_CATALOG_READY " + json.dumps({
        "inventory": len(stored), "browser_formats": len(catalog), "indexed": len(rows),
        "generated_at": payload["generatedAt"], "encrypted_bytes": len(encoded),
    }), flush=True)


if __name__ == "__main__":
    main()
