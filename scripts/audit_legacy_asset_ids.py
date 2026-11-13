#!/usr/bin/env python3
"""Read-only legacy Studio asset audit. No R2 access, no writes to Studio."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA_KEY = re.compile(r"/([a-f0-9]{64})\.[a-z0-9]+$", re.I)

def extract(path, start, end):
    source = (ROOT / path).read_text(encoding="utf-8")
    i = source.index(start) + len(start)
    j = source.index(end, i)
    return json.loads(source[i:j])

def identity(row):
    key = row.get("key") or ""
    match = SHA_KEY.search(key)
    if match:
        return "r2-" + match.group(1).lower(), "digest_from_path_not_verified"
    if key:
        return "legacy-key-" + hashlib.sha256(key.encode()).hexdigest(), "storage_key_derived"
    url = row.get("url") or ""
    if url:
        return "legacy-url-" + hashlib.sha256(url.encode()).hexdigest(), "external_url_derived"
    return None, "unresolved"

def main():
    core = extract("studio-engine.js", "const assets = ", ";\nassets.push")
    published = extract("studio-catalog.js", "const studioPublishedAssets = ", ";\n")
    rows = core + published
    ids = [identity(r)[0] for r in rows]
    keys = [r.get("key") for r in rows if r.get("key")]
    result = {
        "core_count": len(core),
        "published_count": len(published),
        "total_slots": len(rows),
        "explicit_id_count": sum(bool(r.get("id")) for r in rows),
        "sha256_named_key_count": sum(bool(SHA_KEY.search(r.get("key") or "")) for r in rows),
        "non_sha_storage_key_count": sum(bool(r.get("key")) and not SHA_KEY.search(r["key"]) for r in rows),
        "url_only_count": sum(not r.get("key") and bool(r.get("url")) for r in rows),
        "unique_storage_keys": len(set(keys)),
        "duplicate_storage_keys": [k for k, n in Counter(keys).items() if n > 1],
        "duplicate_proposed_ids": [k for k, n in Counter(ids).items() if n > 1],
        "missing_identity_slots": [i for i, x in enumerate(ids) if x is None],
        "mapping": [{"slot": i, "name": r.get("name"), "proposed_id": ids[i],
                     "id_basis": identity(r)[1]} for i, r in enumerate(rows)]
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert len(rows) == len(ids)
    assert len(set(ids)) == len(ids), "ID collision; inspect mapping before any migration"

if __name__ == "__main__":
    main()
