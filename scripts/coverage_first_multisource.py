#!/usr/bin/env python3
"""Coverage-first audio metadata discovery, without bulk media ingestion.

Searches public APIs only. Persists encrypted, resumable candidate evidence in R2.
New candidates do NOT count as verified recordings or modify the legacy catalog state.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
import re
import time
import unicodedata
from urllib.parse import quote, urlparse

import requests
from botocore.exceptions import ClientError

import harvest_commons_cc0_to_r2 as commons
from harvest_nature_diversity_to_r2 import BUCKET, Intake, emit
from run_catalog_harvest_queue import CONTROL, Matcher, cipher, decode, encode, load_input, read_state
from harvest_targeted_nature_to_r2 import EXCLUDED

STATE_KEY = CONTROL + "coverage-first-v1.enc"
MAX_CANDIDATES_PER_CODE = 3
USER_AGENT = commons.USER_AGENT
LICENSE_RE = re.compile(
    r"^https?://creativecommons\.org/(?:publicdomain/zero/1\.0|licenses/by/(?:2\.0|2\.5|3\.0|4\.0))/?",
    re.I,
)
BAD_CONTENT = re.compile(r"\b(?:music|remix|album|podcast|cover version|karaoke)\b", re.I)
STOP = {"a", "an", "the", "of", "in", "on", "to", "with", "for", "and",
        "sound", "sounds", "audio", "recording", "recordings", "effect", "effects", "sfx"}
EQUIV = {"rainfall": "rain", "raining": "rain", "rains": "rain",
         "chirping": "chirp", "chirps": "chirp", "tweeting": "chirp",
         "howling": "howl", "howls": "howl", "barking": "bark",
         "barks": "bark", "hoots": "hoot", "hooting": "hoot",
         "calls": "call", "calling": "call", "footsteps": "footstep",
         "waves": "wave", "rustling": "rustle", "rustles": "rustle",
         "crackling": "crackle", "crackles": "crackle", "streams": "stream",
         "waterfalls": "waterfall", "thunders": "thunder", "birds": "bird",
         "cuckoos": "cuckoo", "owls": "owl", "wolves": "wolf"}
SYNONYMS = {"rain": "rainfall", "wave": "surf", "stream": "brook",
            "hoot": "call", "chirp": "call",
            "waterfall": "cascade", "wind": "breeze",
            "crackle": "crackling", "thunder": "thunderstorm",
            "footstep": "walking", "howl": "howling"}
PER_SOURCE = ("openverse", "commons", "internet_archive", "xeno_canto")


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def tokens(value):
    parts = re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", str(value or "")).lower())
    return [EQUIV.get(word, word) for word in parts if word not in STOP]


def relevance(target, title, tags="", description=""):
    """Only accept full lexical evidence; a species name alone is not a call variant."""
    need = tokens(target)
    if not need:
        return None
    title_tokens = tokens(title)
    other_tokens = tokens(str(tags) + " " + str(description))
    if BAD_CONTENT.search(str(title) + " " + str(description)[:400]):
        return None
    t = set(title_tokens)
    all_tokens = t | set(other_tokens)
    if not set(need).issubset(all_tokens):
        return None
    title_overlap = sum(word in t for word in set(need))
    if not title_overlap or (len(set(need)) >= 3 and title_overlap < 2):
        return None
    if set(need).issubset(t):
        return ("title", 95 if " ".join(need) in " ".join(title_tokens) else 90)
    return ("title+metadata", 75)


def queries(english):
    parts = tokens(english)
    if not parts:
        return []
    base = " ".join(parts)
    variants = [base]
    for i, value in enumerate(parts):
        if value in SYNONYMS:
            variants.append(" ".join(parts[:i] + SYNONYMS[value].split() + parts[i + 1:]))
            break
    # Preserve the exact target when synonyms or morphology differ.
    raw = re.sub(r"\s+", " ", str(english).strip())
    if raw and raw.lower() not in {q.lower() for q in variants}:
        variants.append(raw)
    return list(dict.fromkeys(variants))[:3]


def valid_url(url):
    try:
        p = urlparse(str(url))
        return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password
    except ValueError:
        return False


def permitted_license(url, name=""):
    # Do not infer rights from a repository, uploader, or a vague "free" badge.
    url = str(url or "").strip()
    if LICENSE_RE.match(url):
        return True
    return str(name).strip().lower() in ("cc0", "by") and not url


def source_record(provider, code, title, tags, description, landing, audio_url,
                  license_name, license_url, creator="", source_id="", query=""):
    if not valid_url(landing) or not permitted_license(license_url, license_name):
        return None
    match = relevance(query, title, tags, description)
    if not match:
        return None
    evidence_type, score = match
    return {"source": provider, "code": code, "title": str(title)[:300],
            "landing_url": landing, "audio_url": audio_url if valid_url(audio_url) else None,
            "license": str(license_name)[:60], "license_url": str(license_url)[:250],
            "creator": str(creator)[:160], "source_id": str(source_id)[:160],
            "match_evidence": evidence_type, "confidence": score, "query": query,
            "discovered_at": utcnow(), "status": "metadata_candidate_unverified"}


def request_json(session, endpoint, params, *, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            response = session.get(endpoint, params=params, timeout=(12, 35))
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt == max_attempts - 1:
                    response.raise_for_status()
                retry = response.headers.get("Retry-After", "")
                time.sleep(min(30, int(retry)) if retry.isdigit() else 2 ** attempt + 2)
                continue
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError):
            if attempt == max_attempts - 1:
                raise
            time.sleep(2 ** attempt + 1)


def openverse(session, code, english, query):
    result = request_json(session, "https://api.openverse.org/v1/audio/",
                          {"q": query, "license": "cc0,by", "page_size": 20,
                           "mature": "false"})
    for item in result.get("results", []):
        rights = item.get("license_url") or ""
        lic = item.get("license") or ""
        tags = " ".join((t.get("name", "") if isinstance(t, dict) else str(t))
                        for t in item.get("tags", [])[:30])
        landing = item.get("foreign_landing_url") or item.get("detail_url")
        record = source_record("openverse:" + str(item.get("source") or "mixed"),
                    code, item.get("title") or "", tags, "",
                    landing, item.get("url"), lic, rights,
                    item.get("creator") or "", item.get("id") or "", english)
        if record:
            yield record


def wikimedia(session, code, english, query):
    result = request_json(session, "https://commons.wikimedia.org/w/api.php",
        {"action": "query", "format": "json", "generator": "search",
         "gsrsearch": query + " filetype:audio", "gsrnamespace": "6", "gsrlimit": "30",
         "prop": "imageinfo", "iiprop": "url|mime|size|sha1|extmetadata"})
    for item in (result.get("query") or {}).get("pages", []):
        try:
            row = commons.decide(item, code, 160 * 1024 ** 2, allow_cc_by=True)
            if row.get("state") != "ELIGIBLE":
                continue
            ext = item["imageinfo"][0].get("extmetadata") or {}
            description = commons.plain(commons.val(ext, "ImageDescription"))[:1000]
            categories = commons.val(ext, "Categories")
            rec = source_record("wikimedia_commons", code,
                row.get("file_name") or item.get("title") or "", categories,
                description, row.get("source_url"), row.get("direct_file_url"),
                row.get("source_license"), row.get("license_url"),
                row.get("author"), item.get("pageid"), english)
            if rec:
                yield rec
        except (KeyError, ValueError, TypeError):
            continue


def internet_archive(session, code, english, query):
    # Archive item metadata is not proof that any of its files are usable audio.
    q = 'mediatype:audio AND (' + " AND ".join(
        '"' + word.replace('"', "") + '"' for word in tokens(query)[:5]) + ')'
    result = request_json(session, "https://archive.org/advancedsearch.php",
        {"q": q, "output": "json", "rows": 15,
         "fl[]": ["identifier", "title", "description", "subject", "licenseurl"]})
    for item in (result.get("response") or {}).get("docs", []):
        license_url = item.get("licenseurl") or ""
        if isinstance(license_url, list):
            license_url = next((v for v in license_url if permitted_license(v)), "")
        identifier = str(item.get("identifier") or "")
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,180}", identifier):
            continue
        tags = item.get("subject") or []
        desc = item.get("description") or ""
        if isinstance(tags, list):
            tags = " ".join(str(t) for t in tags)
        if isinstance(desc, list):
            desc = " ".join(str(t) for t in desc)
        record = source_record("internet_archive_item", code, item.get("title") or "",
            tags, desc[:1000], "https://archive.org/details/" + quote(identifier),
            None, "", license_url, "", identifier, english)
        if record:
            record["status"] = "item_metadata_only_audio_file_not_verified"
            yield record


def xeno_canto(session, code, english, query):
    key = os.getenv("XENO_CANTO_API_KEY")
    if not key:
        return
    result = request_json(session, "https://xeno-canto.org/api/3/recordings",
                          {"query": query, "key": key, "page": 1})
    for item in result.get("recordings", [])[:20]:
        title = " ".join(str(item.get(k) or "") for k in ("en", "gen", "sp", "type"))
        recording_id = str(item.get("id") or "")
        url = "https://xeno-canto.org/" + recording_id if recording_id.isdigit() else ""
        rec = source_record("xeno_canto", code, title, item.get("type") or "",
                    item.get("remarks") or "", url, item.get("file") or "",
                    "", item.get("lic") or "", item.get("rec") or "",
                    recording_id, english)
        if rec:
            yield rec


SEARCH = {"openverse": openverse, "commons": wikimedia,
          "internet_archive": internet_archive, "xeno_canto": xeno_canto}


def state_read(s3):
    try:
        encrypted = s3.get_object(Bucket=BUCKET, Key=STATE_KEY)["Body"].read()
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
            return None
        raise
    aes, context = cipher("coverage-first-v1")
    return decode(aes.decrypt(encrypted[:12], encrypted[12:], context))


def state_save(s3, state):
    aes, context = cipher("coverage-first-v1")
    nonce = os.urandom(12)
    s3.put_object(Bucket=BUCKET, Key=STATE_KEY,
                  Body=nonce + aes.encrypt(nonce, encode(state), context),
                  ContentType="application/octet-stream")


def order_targets(bundle, verified):
    # Prioritize verified-missing P0, then remaining missing targets.
    return sorted(bundle["targets"],
                  key=lambda row: (row[0] in verified, row[4] != "P0", row[0]))


def run(max_targets, dry_run=False):
    intake = Intake()
    s3 = intake.s3
    bundle = load_input(s3)
    legacy = read_state(s3)
    verified = set((legacy or {}).get("counts", {}))
    state = state_read(s3)
    if state is None:
        state = {"version": 1, "created_at": utcnow(), "cursor": 0,
                 "ordered_codes": [r[0] for r in order_targets(bundle, verified)],
                 "candidates": {}, "errors": [], "scanned": 0,
                 "queries_completed": 0, "source_queries": {}}
    targets = {row[0]: row for row in bundle["targets"]}
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    start = state["cursor"]
    end = min(start + max_targets, len(state["ordered_codes"]))
    new_codes = 0
    failures = Counter()
    for index in range(start, end):
        code = state["ordered_codes"][index]
        english = targets[code][2]
        candidates = state["candidates"].setdefault(code, [])
        existing = {(r["source"], r["landing_url"]) for r in candidates}
        code_failed = False
        if code not in verified and len(candidates) < MAX_CANDIDATES_PER_CODE:
            for source in PER_SOURCE:
                if any(r["source"].split(":")[0] == {"commons": "wikimedia_commons", "internet_archive": "internet_archive_item"}.get(source, source) for r in candidates):
                    continue
                if source == "xeno_canto" and not os.getenv("XENO_CANTO_API_KEY"):
                    continue
                if len(candidates) >= MAX_CANDIDATES_PER_CODE:
                    break
                for query in queries(english)[:2]:
                    if len(candidates) >= MAX_CANDIDATES_PER_CODE or any(r["source"].split(":")[0] == {"commons": "wikimedia_commons", "internet_archive": "internet_archive_item"}.get(source, source) for r in candidates):
                        break
                    try:
                        for record in SEARCH[source](session, code, english, query):
                            identity = (record["source"], record["landing_url"])
                            if identity not in existing:
                                candidates.append(record)
                                existing.add(identity)
                            if len(candidates) >= MAX_CANDIDATES_PER_CODE or any(r["source"].split(":")[0] == {"commons": "wikimedia_commons", "internet_archive": "internet_archive_item"}.get(source, source) for r in candidates):
                                break
                        state["queries_completed"] += 1
                        state["source_queries"][source] = state["source_queries"].get(source, 0) + 1
                    except (requests.RequestException, KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
                        # Continue to other providers; surface incomplete coverage, not false success.
                        failures[source] += 1
                        code_failed = True
                        state["errors"].append({"code": code, "provider": source,
                                                "kind": type(error).__name__})
                        if len(state["errors"]) > 100:
                            state["errors"] = state["errors"][-100:]
                    time.sleep(0.25)
        if code_failed and state.setdefault("retry_counts", {}).get(code, 0) < 2:
            state["ordered_codes"].append(code)
            state["retry_counts"][code] = state["retry_counts"].get(code, 0) + 1
        if code not in verified and candidates:
            new_codes += 1
        state["cursor"] = index + 1
        state["scanned"] += 1
        if (index - start + 1) % 5 == 0 and not dry_run:
            state_save(s3, state)
            emit("COVERAGE_CHECKPOINT", {"cursor": state["cursor"], "total": len(state["ordered_codes"]),
                  "new_candidate_codes_in_segment": new_codes, "source_errors": dict(failures)})
    candidate_codes = {key for key, rows in state["candidates"].items() if rows}
    missing_candidate = candidate_codes - verified
    final = {"cursor": state["cursor"], "total_codes": len(targets),
             "legacy_mapped_codes": len(verified),
             "new_candidate_codes": len(missing_candidate),
             "candidate_codes_all": len(candidate_codes),
             "legacy_or_candidate_codes": len(verified | candidate_codes),
             "legacy_p0_missing": sum(row[4] == "P0" and row[0] not in verified for row in bundle["targets"]),
             "new_candidate_p0": sum(targets[code][4] == "P0" for code in missing_candidate),
             "source_counts": dict(Counter(r["source"] for rows in state["candidates"].values() for r in rows)),
             "metadata_candidates": sum(len(v) for v in state["candidates"].values()),
             "source_errors": dict(failures), "complete": state["cursor"] >= len(state["ordered_codes"]),
             "audio_files_downloaded": 0, "updated_at": utcnow()}
    state["summary"] = final
    if not dry_run:
        state_save(s3, state)
    emit("COVERAGE_DISCOVERY", final)
    return final


def self_test():
    assert tokens("Rainfall sounds") == ["rain"]
    assert relevance("Owl hoot", "Forest owl hooting at night") is not None
    assert relevance("Owl hoot", "Wolf howling at night") is None
    assert relevance("Wolf howl", "Wolf walking at night") is None
    assert relevance("Wolf howl", "Wolf howling in forest")[1] >= 90
    assert relevance("Rain", "Calm piano music and rain") is None
    assert permitted_license("https://creativecommons.org/publicdomain/zero/1.0/")
    assert permitted_license("https://creativecommons.org/licenses/by/4.0/")
    assert not permitted_license("https://creativecommons.org/licenses/by-nc/4.0/")
    assert not permitted_license("https://creativecommons.org/licenses/by-sa/4.0/")
    assert not permitted_license("https://example.com/unknown")
    assert queries("Owl hoot") == ["owl hoot", "owl call"]
    print("COVERAGE_SELF_TEST PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--max-targets", type=int, default=60)
    args = p.parse_args()
    if args.self_test:
        self_test()
    else:
        if not 1 <= args.max_targets <= 200:
            raise SystemExit("max-targets must be 1..200")
        result = run(args.max_targets)
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
                out.write("complete=" + str(result["complete"]).lower() + "\n")
