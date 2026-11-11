#!/usr/bin/env python3
"""Run and reconcile the configured audio intake queue on the harvest branch."""
import ast
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import base64
import gzip
import hashlib
import hmac
import json
import os
from pathlib import Path
from urllib.error import HTTPError
import re
import subprocess
import sys
import time
import unicodedata

from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import harvest_commons_cc0_to_r2 as commons
from audit_r2_asset_inventory import PREFIXES, SHA
from harvest_nature_diversity_to_r2 import BUCKET, Intake, commons_media_downloader, emit
from harvest_targeted_nature_to_r2 import EXCLUDED

CONTROL = 'internal/wnc-catalog-20261111/'
STATE = CONTROL + 'state.enc'
INPUT = Path(__file__).with_name('catalog-chain-input.b64')
BASELINE = datetime.fromisoformat('2026-11-11T07:26:15.389823+00:00')
BASELINE_BYTES = 22193832458
PREVIOUS_FILES = 15224
FIRST_DELTA = 1555
FIRST_DELTA_BYTES = 1943740393
MODIFIERS = re.compile(r'\b(?:distant|nearby|chorus|single|multiple|alarm|warning|mating|courtship|wing|flight|nest|feeding|distress|chick|juvenile|drum|splash|foraging|night|morning|group|landing|takeoff)\b')
WILDLIFE = {'Aves': (336, 445), 'Insecta': (446, 484), 'Amphibia': (485, 502),
            'Reptilia': (503, 520), 'Mammalia': (521, 638)}
IGNORED = {'a', 'an', 'the', 'of', 'on', 'in', 'by', 'sound', 'effect', 'recording', 'sfx'}
ALIAS = {'calls': 'call', 'chirps': 'chirp', 'clicks': 'click', 'footsteps': 'footstep',
         'howls': 'howl', 'howling': 'howl', 'barking': 'bark', 'wooden': 'wood', 'crackling': 'crackle'}
DELTA_BATCH = 36
MAX_OFFSET = 950


def encode(value):
    return gzip.compress(json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode())


def decode(value):
    return json.loads(gzip.decompress(value))


def missing(error):
    return error.response['Error']['Code'] in ('404', 'NoSuchKey', 'NotFound')


def read_object(s3, path):
    with s3.get_object(Bucket=BUCKET, Key=path)['Body'] as body:
        return body.read()


def cipher(label):
    context = ('wnc-catalog-20261111 ' + label).encode()
    secret = hmac.digest(os.environ['R2_SECRET_ACCESS_KEY'].encode(), context, hashlib.sha256)
    return AESGCM(secret), context


def load_input(s3):
    encrypted = read_object(s3, CONTROL + 'bootstrap.enc')
    bootstrap, context = cipher('bootstrap')
    private = serialization.load_pem_private_key(
        bootstrap.decrypt(encrypted[:12], encrypted[12:], context), password=None)
    bundle = base64.b64decode(INPUT.read_text())
    wrapped = private.key_size // 8
    key = private.decrypt(bundle[:wrapped], padding.OAEP(
        mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    data = decode(AESGCM(key).decrypt(bundle[wrapped:wrapped + 12], bundle[wrapped + 12:],
                                      b'wnc-catalog-20261111 inputs'))
    expected = {f'SND-TAX-{i:05d}' for i in range(1, 1817)}
    if len(data['targets']) != 1816 or {row[0] for row in data['targets']} != expected:
        raise ValueError('Catalog must contain 1,816 distinct IDs')
    node = ast.parse(data['rules']).body[0]
    data['rules'] = ast.literal_eval(node.value)
    return data


def read_state(s3):
    try:
        encrypted = read_object(s3, STATE)
    except ClientError as error:
        if missing(error):
            return None
        raise
    decrypt, context = cipher('state')
    return decode(decrypt.decrypt(encrypted[:12], encrypted[12:], context))


def write_state(s3, state):
    encrypt, context = cipher('state')
    nonce = os.urandom(12)
    payload = nonce + encrypt.encrypt(nonce, encode(state), context)
    s3.put_object(Bucket=BUCKET, Key=STATE, Body=payload, ContentType='application/octet-stream')


def inventory(s3, cutoff=None):
    entries = {}
    for prefix in PREFIXES.values():
        pages = s3.get_paginator('list_objects_v2').paginate(Bucket=BUCKET, Prefix=prefix)
        for page in pages:
            for obj in page.get('Contents', []):
                match = SHA.search(obj['Key'])
                if match and obj['Size'] and (cutoff is None or obj['LastModified'] <= cutoff):
                    entries.setdefault(match[1], obj['Size'])
    return entries


def metadata(s3, digest):
    try:
        raw = read_object(s3, f'asset-library/records/sha256/{digest[:2]}/{digest}.json')
    except ClientError as error:
        if missing(error):
            return None
        raise
    record = json.loads(raw)
    if record.get('audio_sha256') != digest:
        raise ValueError('Metadata SHA-256 disagrees with object key')
    return record


def words(value):
    tokens = re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKC', str(value or '')).casefold())
    return [ALIAS.get(word, word) for word in tokens if word not in IGNORED]


def phrase(value):
    return ' ' + ' '.join(words(value)) + ' '


def source_fields(record):
    fields = []
    for field in ('title', 'original_filename', 'file_title', 'source_title'):
        value = re.sub(r'\.(?:wav|ogg|oga|mp3|flac|opus|m4a|aif|aiff|au|wma)$', '',
                       str(record.get(field) or ''), flags=re.I)
        if value:
            fields.append((field, value))
    return fields


class Matcher:
    def __init__(self, bundle):
        self.targets = bundle['targets']
        self.index = defaultdict(list)
        self.rules = []
        self.species = defaultdict(list)
        for code, _, english, _, _, _ in self.targets:
            number = int(code[-5:])
            tokens = words(english)
            if tokens:
                self.index[tokens[0]].append((code, ' ' + ' '.join(tokens) + ' '))
            expression = bundle['rules'].get(number)
            if not expression:
                continue
            compiled = re.compile(expression, re.I)
            self.rules.append((code, compiled))
            if not MODIFIERS.search(english.casefold()):
                for taxon, bounds in WILDLIFE.items():
                    if bounds[0] <= number <= bounds[1]:
                        self.species[taxon].append((code, compiled))

    def match(self, record):
        fields = source_fields(record)
        if record.get('source_provider') == 'iNaturalist':
            names = [(k, record.get(k)) for k in ('scientific_name', 'title') if record.get(k)]
            for code, pattern in self.species.get(record.get('iconic_taxon'), []):
                for field, value in names:
                    if pattern.search(str(value).replace('-', ' ')):
                        yield code, 'species_name_only', field, value
                        break
            return
        if EXCLUDED.search(' '.join(value for _, value in fields)):
            return
        seen = set()
        for field, value in fields:
            text = phrase(value)
            for token in set(words(value)):
                for code, needle in self.index[token]:
                    if code not in seen and needle in text:
                        seen.add(code)
                        yield code, 'explicit_source_phrase', field, value
            normalized = re.sub(r'[_/-]', ' ', value)
            for code, pattern in self.rules:
                if code in seen or not pattern.search(normalized):
                    continue
                number = int(code[-5:])
                if any(start <= number <= end for start, end in WILDLIFE.values()):
                    continue
                seen.add(code)
                yield code, 'source_pattern', field, value


def reconcile(s3, state, matcher, batch, errors, expected=None):
    before = state['inventory']
    current = inventory(s3)
    if set(before) - set(current):
        raise RuntimeError('R2 inventory lost previously verified SHA-256 entries')
    fresh = set(current) - set(before)
    new_bytes = sum(current[digest] for digest in fresh)
    if expected and (len(fresh), new_bytes) != expected:
        raise RuntimeError('First delta does not match the verified previous GitHub Actions inventory')
    codes = state['counts']
    first = set()
    matched_files = 0
    variants = 0
    species_only = 0
    pending_metadata = set(state['pending_metadata'])
    old_pending = set(pending_metadata)
    found = fresh | old_pending
    with ThreadPoolExecutor(max_workers=16) as pool:
        records = pool.map(lambda digest: metadata(s3, digest), sorted(found))
        for digest, record in zip(sorted(found), records):
            if not record:
                pending_metadata.add(digest)
                continue
            pending_metadata.discard(digest)
            matches = list(matcher.match(record))
            if matches:
                matched_files += 1
            for code, kind, field, evidence in matches:
                if code not in codes:
                    first.add(code)
                    codes[code] = [0, 0]
                codes[code][0] += 1
                codes[code][1] += 1
                variants += 1
                species_only += kind == 'species_name_only'
                state['evidence'].append({
                    'sha256': digest, 'id': code, 'type': kind, 'field': field, 'evidence': evidence,
                    'source': record.get('source_page'), 'license': record.get('license'),
                    'key': record.get('audio_storage_key'), 'batch': batch,
                })
    state['inventory'] = current
    state['pending_metadata'] = sorted(pending_metadata)
    summary = {'batch': batch, 'before': len(before), 'after': len(current), 'new_files': len(fresh),
               'new_bytes': new_bytes, 'matched_files': matched_files, 'first_codes': sorted(first),
               'estimated_variants_added': variants, 'species_only_matches': species_only,
               'covered_codes': len(codes), 'missing_codes': 1816 - len(codes),
               'missing_p0': sum(row[4] == 'P0' and row[0] not in codes for row in matcher.targets),
               'missing_metadata_in_delta': len(pending_metadata), 'source_errors': errors}
    state['reports'].append(summary)
    write_state(s3, state)
    emit('CHAIN_BATCH', summary)


def wildlife(page):
    child = subprocess.run([sys.executable, '-u', 'scripts/harvest_inaturalist_cc0_to_r2.py',
                            '--page', str(page), '--per-group', '60'],
                           capture_output=True, text=True, timeout=1500)
    line = next((line for line in child.stdout.splitlines() if line.startswith('INAT_FINAL ')), '')
    if child.returncode or not line:
        raise RuntimeError(f'iNaturalist page {page} did not complete; checkpoint preserved')
    return json.loads(line.removeprefix('INAT_FINAL '))


def search_commons(intake, download, target, continuation):
    code, _, english, _, _, _ = target
    query = ' '.join(re.findall(r'[\w-]+', english))
    if not query:
        raise ValueError('Empty source query')
    options = {'generator': 'search', 'gsrsearch': '"' + query + '" filetype:audio',
               'gsrnamespace': '6', 'gsrlimit': '50', 'prop': 'imageinfo',
               'iiprop': 'url|mime|size|sha1|extmetadata|user', **(continuation or {})}
    time.sleep(0.6)
    result = commons.get_json(options)
    if 'error' in result:
        raise RuntimeError('Wikimedia Commons returned an API error')
    needle = phrase(english)
    rejected = 0
    for item in result.get('query', {}).get('pages', []):
        row = commons.decide(item, code, 160 * 1024**2, allow_cc_by=True)
        if row['state'] != 'ELIGIBLE':
            continue
        info = item['imageinfo'][0]
        ext = info.get('extmetadata', {})
        title = row['file_name']
        description = commons.plain(commons.val(ext, 'ImageDescription'))
        tags = commons.val(ext, 'Categories').split('|')[:40]
        title_stem = title.rsplit('.', 1)[0]
        if (EXCLUDED.search(title + ' ' + description)
                or any(re.search(r'^(?:music|audio files of .*music\b)', tag, re.I) for tag in tags)
                or needle not in phrase(title_stem)):
            continue
        identity = row['direct_file_url'] + '\n' + (info.get('sha1') or str(row['size']))
        if intake.cached(identity):
            continue
        try:
            path, _, digest, duration, audio = download(row)
        except ValueError:
            rejected += 1
            continue
        except HTTPError as error:
            if error.code not in (404, 410):
                raise
            rejected += 1
            continue
        try:
            intake.save(path, identity, {
                'source_provider': 'Wikimedia Commons', 'source_page': row['source_url'],
                'license_evidence_url': row['rights_evidence_url'], 'download_url': row['direct_file_url'],
                'license': row['source_license'], 'license_url': row['license_url'],
                'creator': row['author'], 'attribution': row['attribution'],
                'copyright_notice': commons.plain(commons.val(ext, 'Copyright')),
                'original_filename': title, 'title': row['title'], 'description': description,
                'source_tags': tags, 'group_hint': code, 'discovery_hint': english,
            }, audio, duration, digest)
        finally:
            path.unlink(missing_ok=True)
    next_page = result.get('continue')
    capped = bool(next_page and int(next_page.get('gsroffset', 0)) > MAX_OFFSET)
    if next_page and next_page == continuation:
        raise RuntimeError('Wikimedia Commons repeated a continuation token')
    return (None if capped else next_page), capped, rejected


def queue_order(row, counts):
    number = int(row[0][-5:])
    nature = number <= 700
    return (row[4] != 'P0', row[0] in counts, not nature, row[4], number)


def main():
    intake = Intake()
    s3 = intake.s3
    bundle = load_input(s3)
    matcher = Matcher(bundle)
    state = read_state(s3)
    if state is None:
        previous = inventory(s3, BASELINE)
        if len(previous) != PREVIOUS_FILES or sum(previous.values()) != BASELINE_BYTES:
            raise RuntimeError('Cannot reconstruct the verified baseline from R2 timestamps')
        state = {'inventory': previous, 'counts': {r[0]: r[1:] for r in bundle['coverage']},
                 'evidence': [], 'reports': [], 'pending_metadata': [], 'completed': [],
                 'limited': [], 'continuations': {}, 'next_wildlife': 64, 'next_source': 'commons',
                 'baseline_workbook': bundle['source_workbook']}
        reconcile(s3, state, matcher, 'iNaturalist 52-63', 0, (FIRST_DELTA, FIRST_DELTA_BYTES))
    download = commons_media_downloader()
    deadline = time.monotonic() + 98 * 60
    while time.monotonic() < deadline:
        done = set(state['completed'])
        queue = sorted((row for row in matcher.targets if row[0] not in done),
                       key=lambda row: queue_order(row, state['counts']))
        page = state['next_wildlife']
        if not queue and page > 100:
            emit('CHAIN_FINISHED', {'covered_codes': len(state['counts']),
                                    'missing_codes': 1816 - len(state['counts']),
                                    'commons_queries_completed': len(done),
                                    'commons_queries_at_page_cap': len(state['limited']),
                                    'metadata_pending': len(state['pending_metadata'])})
            return True
        if page <= 100 and (state['next_source'] == 'wildlife' or not queue):
            final = min(page + 11, 100)
            failures = 0
            for number in range(page, final + 1):
                count = wildlife(number)['errors']
                if count:
                    time.sleep(25)
                    count = wildlife(number)['errors']
                failures += count
            if failures:
                raise RuntimeError(f'iNaturalist pages {page}-{final}: {failures} errors; checkpoint preserved')
            state['next_wildlife'] = final + 1
            state['next_source'] = 'commons'
            reconcile(s3, state, matcher, f'iNaturalist {page}-{final}', failures)
            continue
        completed = 0
        rejected = 0
        for target in queue[:DELTA_BATCH]:
            code = target[0]
            continuation, capped, rejected_media = search_commons(intake, download, target, state['continuations'].get(code))
            rejected += rejected_media
            if continuation:
                state['continuations'][code] = continuation
            else:
                state['continuations'].pop(code, None)
                state['completed'].append(code)
                completed += 1
                if capped:
                    state['limited'].append(code)
        state['next_source'] = 'wildlife'
        reconcile(s3, state, matcher, f'Commons {queue[0][0]}–{queue[min(len(queue), DELTA_BATCH)-1][0]} '
                                     f'({completed} queries closed)', rejected)
    emit('CHAIN_CHECKPOINT', {'next_wildlife': state['next_wildlife'], 'completed_queries': len(state['completed'])})
    return False


if __name__ == '__main__':
    try:
        done = main()
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            output.write(f"done={str(done).lower()}\n")
    except Exception as error:
        emit('CHAIN_ERROR', {'type': type(error).__name__, 'detail': str(error)[:260] if
                            isinstance(error, (RuntimeError, ValueError)) else 'See source or R2 status'})
        raise SystemExit(1)
