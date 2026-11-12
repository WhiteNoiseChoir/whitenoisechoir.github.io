#!/usr/bin/env python3
"""Build and validate owner-approved WhiteNoiseChoir public releases.

Never auto-publish trial Studio projects. An owner-approved manifest with all
final assets is required. With --write, require live R2 HTTP Range/CORS checks.
This script creates SEO pages, a crawler-visible library grid and a sitemap.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/published-mixes.json"
GENERATED_INDEX = ROOT / "data/published-generated-slugs.json"
LIBRARY = ROOT / "library/index.html"
SITEMAP = ROOT / "sitemap.xml"
BASE = "https://whitenoisechoir.com"
R2 = "https://media.whitenoisechoir.com/"
SLUG = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
MEDIA = re.compile(r"^https://media\.whitenoisechoir\.com/[A-Za-z0-9_./-]+$")
DATE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:Z|[+-]\d\d:\d\d)$")
START = "<!-- PUBLISHED_GRID_START -->"
END = "<!-- PUBLISHED_GRID_END -->"
BANNER = "<!-- GENERATED_BY_WHITENOISECHOIR_PUBLICATION_PIPELINE -->"


def esc(value):
    return html.escape(str(value), quote=True)


def json_script(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def safe_slug(value):
    return isinstance(value, str) and SLUG.fullmatch(value) is not None


def valid_url(value):
    return isinstance(value, str) and MEDIA.fullmatch(value) is not None and ".." not in value


def check_range(url, expected):
    request = urllib.request.Request(url, headers={
        "Origin": BASE,
        "Range": "bytes=0-1023",
        "User-Agent": "WhiteNoiseChoir-PublicationGate/1.0",
    })
    with urllib.request.urlopen(request, timeout=35) as response:
        code = response.status
        mimetype = response.headers.get("Content-Type", "").split(";")[0].lower()
        cors = response.headers.get("Access-Control-Allow-Origin", "")
        data = response.read(1024)
    if code != 206 or not data:
        raise ValueError(f"R2 media not reachable by Range request: HTTP {code} - {url}")
    if cors not in ("*", BASE):
        raise ValueError(f"R2 media CORS invalid: {url}")
    if not any(mimetype.startswith(prefix) for prefix in expected):
        raise ValueError(f"Unexpected R2 MIME {mimetype}: {url}")


def approve(row, verify):
    slug = row.get("slug")
    if not safe_slug(slug):
        raise ValueError("Published releases require safe English URL slugs, for example Living-Forest-Creek.")
    if row.get("status") != "published" or row.get("ownerApproved") is not True:
        raise ValueError(f"{slug}: release requires status=published and ownerApproved=true.")
    if row.get("productionComplete") is not True or row.get("qaApproved") is not True:
        raise ValueError(f"{slug}: finished video/audio production and QA approval required.")
    if not isinstance(row.get("title"), str) or not (8 <= len(row["title"]) <= 100):
        raise ValueError(f"{slug}: add a real 8-100 character English title.")
    if not isinstance(row.get("description"), str) or not (100 <= len(row["description"]) <= 500):
        raise ValueError(f"{slug}: add a substantial unique English description.")
    if not isinstance(row.get("category"), str) or not row["category"]:
        raise ValueError(f"{slug}: category required.")
    if not DATE.fullmatch(str(row.get("datePublished", ""))):
        raise ValueError(f"{slug}: datePublished must be full ISO8601 with timezone.")
    seo = row.get("seo")
    if not isinstance(seo, dict):
        raise ValueError(f"{slug}: SEO metadata missing.")
    if not (25 <= len(seo.get("title", "")) <= 80):
        raise ValueError(f"{slug}: provide a unique SEO title (25-80 characters).")
    if not (100 <= len(seo.get("description", "")) <= 230):
        raise ValueError(f"{slug}: provide SEO description (100-230 characters).")
    keywords = row.get("keywords")
    if not isinstance(keywords, list) or not (2 <= len(keywords) <= 20) or not all(isinstance(k, str) for k in keywords):
        raise ValueError(f"{slug}: provide focused English keywords.")
    sections = row.get("article")
    if not isinstance(sections, list) or len(sections) < 2:
        raise ValueError(f"{slug}: provide at least two unique editorial article sections.")
    for sec in sections:
        if not isinstance(sec, dict) or len(sec.get("heading", "")) < 8 or len(sec.get("text", "")) < 70:
            raise ValueError(f"{slug}: write substantive and factually accurate section heading/text.")
    video, audio = row.get("video"), row.get("audio")
    if not isinstance(video, dict) or not isinstance(audio, dict):
        raise ValueError(f"{slug}: final video AND audio objects required.")
    urls = [
        (video.get("url"), ("video/mp4",)),
        (video.get("poster"), ("image/jpeg", "image/png", "image/webp")),
        (audio.get("url"), ("audio/mpeg", "audio/mp4", "audio/aac")),
        (audio.get("wavUrl"), ("audio/wav", "audio/x-wav", "audio/wave")),
    ]
    if not all(valid_url(url) for url, _ in urls):
        raise ValueError(f"{slug}: all four approved final media URLs must be hosted on our Cloudflare R2.")
    if not (595 <= float(video.get("durationSeconds", 0)) <= 610):
        raise ValueError(f"{slug}: complete final MP4 should be about 10 minutes.")
    if not (595 <= float(audio.get("durationSeconds", 0)) <= 610):
        raise ValueError(f"{slug}: audio must be the finished 10-minute mix.")
    timeline = row.get("timeline")
    if not isinstance(timeline, list) or not (1 <= len(timeline) <= 32):
        raise ValueError(f"{slug}: immutable timeline snapshot of 1-32 tracks required.")
    for track in timeline:
        if not isinstance(track, dict) or len(track.get("label", "")) < 3:
            raise ValueError(f"{slug}: every timeline track requires its real name.")
        if not (0 <= float(track.get("start", -1)) < 600):
            raise ValueError(f"{slug}: timeline starts must be inside 10 minutes.")
        if not (0 <= float(track.get("gain", -1)) <= 1):
            raise ValueError(f"{slug}: timeline gains must be in [0,1].")
        if not (0 < float(track.get("duration", 0)) <= 600):
            raise ValueError(f"{slug}: timeline durations must be positive.")
    if verify:
        for url, accepted in urls:
            check_range(url, accepted)
    return slug


def card_html(row):
    slug, title = esc(row["slug"]), esc(row["title"])
    poster = esc(row["video"]["poster"])
    summary = esc(row["description"][:190])
    category = esc(row["category"])
    url = esc(row["video"]["url"])
    return f"""<article class="published-video-card" data-published-slug="{slug}">
<a href="/{slug}/" class="published-video-cover" aria-label="Watch {title}"><video muted playsinline loop preload="none" poster="{poster}" data-video-url="{url}" aria-hidden="true"></video><span class="published-cover-label">WATCH &amp; LISTEN</span></a>
<div class="published-video-info"><h2><a href="/{slug}/">{title}</a></h2><p>{summary}</p><div class="published-video-meta">10-hour playback · {category}</div></div>
</article>"""


def render_timeline(row):
    tracks = []
    for track in row["timeline"]:
        start = float(track["start"])
        dur = min(float(track["duration"]), 600-start)
        left, width = start / 6, dur / 6
        group = re.sub("[^a-z]", "", str(track.get("group", "nature")).lower()) or "nature"
        if group not in ("nature", "wildlife", "rain", "fire"):
            group = "nature"
        muted = " muted" if track.get("mute") else ""
        label = esc(track["label"])
        tracks.append(
            f'<div class="release-track"><div class="release-track-name">{label}'
            f'<small>{int(start // 60):02d}:{int(start % 60):02d} · {round(float(track["gain"])*100,1)}% volume</small></div>'
            f'<div class="release-track-rail" aria-label="{label}, read-only">'
            f'<div class="release-track-clip {group}{muted}" style="left:{left:.3f}%;width:{width:.3f}%"></div></div></div>'
        )
    return "\n".join(tracks)


def render_release(row):
    slug, title = row["slug"], row["title"]
    canonical = f"{BASE}/{slug}/"
    seo = row["seo"]
    duration = float(row["video"]["durationSeconds"])
    schema_video = {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "@id": canonical + "#video",
        "name": title,
        "description": row["description"],
        "thumbnailUrl": [row["video"]["poster"]],
        "uploadDate": row["datePublished"],
        "duration": "PT10M",
        "contentUrl": row["video"]["url"],
        "embedUrl": canonical,
        "inLanguage": "en",
        "isAccessibleForFree": True,
        "publisher": {"@type": "Organization", "name": "WhiteNoiseChoir", "url": BASE + "/"},
    }
    schema_audio = {
        "@context": "https://schema.org",
        "@type": "AudioObject",
        "name": title + " audio-only ambience",
        "description": row["description"],
        "duration": "PT10M",
        "contentUrl": row["audio"]["url"],
        "inLanguage": "en",
    }
    schema_crumbs = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type":"ListItem", "position":1, "name":"Home", "item": BASE+"/"},
            {"@type":"ListItem", "position":2, "name":"Published mixes", "item":BASE+"/library/"},
            {"@type":"ListItem", "position":3, "name":title, "item":canonical},
        ],
    }
    editorial = "\n".join(
        f'<section><h2>{esc(sec["heading"])}</h2><p>{esc(sec["text"])}</p></section>'
        for sec in row["article"]
    )
    tags = " · ".join(esc(k) for k in row["keywords"][:6])
    return f"""<!doctype html>
{BANNER}
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(seo["title"])}</title>
<meta name="description" content="{esc(seo["description"])}">
<meta name="robots" content="index,follow,max-image-preview:large,max-video-preview:-1">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="video.other">
<meta property="og:site_name" content="WhiteNoiseChoir">
<meta property="og:title" content="{esc(seo["title"])}">
<meta property="og:description" content="{esc(seo["description"])}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(row["video"]["poster"])}">
<meta property="og:video" content="{esc(row["video"]["url"])}">
<meta property="og:video:type" content="video/mp4">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(seo["title"])}">
<meta name="twitter:description" content="{esc(seo["description"])}">
<meta name="twitter:image" content="{esc(row["video"]["poster"])}">
<link rel="stylesheet" href="/studio.css">
<link rel="stylesheet" href="/published-mixes.css">
<script type="application/ld+json">{json_script([schema_video, schema_audio, schema_crumbs])}</script>
</head>
<body>
<header class="studio-header"><a class="brand" href="/">WhiteNoiseChoir <span>Studio</span></a>
<nav class="studio-nav"><a href="/library/">Published mixes</a><a href="/">Create a WAV</a></nav></header>
<main class="published-shell">
<nav class="published-breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/library/">Published mixes</a> / {esc(title)}</nav>
<header class="release-intro"><p class="release-type">{esc(row["category"])} · Owner-approved ambience</p>
<h1>{esc(title)}</h1><p>{esc(row["description"])}</p></header>
<div class="release-content">
<div class="release-video-wrap">
<video id="release-video" controls loop playsinline preload="metadata" poster="{esc(row["video"]["poster"])}" src="{esc(row["video"]["url"])}" aria-label="{esc(title)} video"></video>
<audio id="release-audio" controls loop preload="none" hidden src="{esc(row["audio"]["url"])}" aria-label="{esc(title)} audio-only"></audio>
<div class="release-player-controls">
<h2>Long-form listening</h2>
<div class="release-player-options">
<label for="release-mode">Playback mode<select id="release-mode"><option value="video">Video + original mix</option><option value="audio">Audio only (better for background listening)</option></select></label>
<label for="release-hours">Sleep timer / listening length<select id="release-hours"><option value="1">1 hour</option><option value="3">3 hours</option><option value="5">5 hours</option><option value="8">8 hours</option><option value="10" selected>10 hours</option></select></label>
<button type="button" id="release-toggle" class="primary">Play</button>
</div>
<p id="release-clock" class="release-play-status" aria-live="polite">00:00:00 / 10:00:00</p>
<p id="release-message" class="release-play-status" role="status" aria-live="polite"></p>
<p class="release-help">The approved 10-minute video or audio repeats until your timer ends. We do not download or render a 10-hour file. Your browser, device sleep mode and network connection may interrupt playback; choose Audio only for background use.</p>
</div></div>
<aside class="release-notes"><h2>About this soundscape</h2><p>{esc(row["description"])}</p>
<dl class="release-facts"><div><dt>Original mix</dt><dd>10 minutes</dd></div><div><dt>Long playback</dt><dd>Up to 10 hours</dd></div>
<div><dt>Video</dt><dd>{int(row["video"].get("width", 1920))} × {int(row["video"].get("height", 1080))}</dd></div>
<div><dt>Audio</dt><dd>Mastered mix</dd></div></dl>
<p>{tags}</p><p><a href="{esc(row["audio"]["wavUrl"])}" rel="nofollow">Download approved WAV master</a></p>
<p><a href="/library/" class="release-article-link">Browse more finished videos</a></p>
</aside></div>
<section class="release-timeline" aria-label="Fixed finished audio arrangement">
<div class="release-timeline-header"><h2>Original sound arrangement</h2><p class="release-lock">LOCKED · Finished mix · Read-only</p></div>
<p>This is a snapshot of the approved 10-minute soundtrack. You can inspect the track layout but cannot move, mute, duplicate or edit these sound layers.</p>
{render_timeline(row)}
</section>
<article class="release-body">{editorial}</article>
</main>
<script type="application/json" id="release-data">{json_script(row)}</script>
<script src="/published-player.js"></script>
</body></html>
"""


def read_manifest(verify):
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("published-mixes.json must be an array")
    slug_seen = set()
    rows = []
    for row in raw:
        if not isinstance(row, dict):
            raise ValueError("Every published manifest entry must be an object.")
        # Manifest is intentionally published-only; no drafts are stored here.
        slug = approve(row, verify)
        if slug.lower() in slug_seen:
            raise ValueError("Duplicate case-insensitive publication slug " + slug)
        slug_seen.add(slug.lower())
        rows.append(row)
    return sorted(rows, key=lambda r: r["datePublished"], reverse=True)


def update_files(rows):
    old_generated = json.loads(GENERATED_INDEX.read_text(encoding="utf8")) if GENERATED_INDEX.exists() else []
    if not isinstance(old_generated, list):
        raise ValueError("Invalid previous published page index")
    library_html = LIBRARY.read_text(encoding="utf8")
    if library_html.count(START) != 1 or library_html.count(END) != 1:
        raise ValueError("Library must contain exactly one published grid marker pair.")
    cards = "\n".join(card_html(r) for r in rows)
    if not cards:
        cards = '<p class="published-empty">No finished soundscape videos have been approved for Public yet. Preview projects and unfinished mixes are not listed.</p>'
    new_grid = START + '\n<div class="published-grid" id="published-grid">\n' + cards + '\n</div>\n' + END
    target_library = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: new_grid,
                            library_html, flags=re.DOTALL)
    if target_library != library_html:
        LIBRARY.write_text(target_library, encoding="utf8")
    wanted = {row["slug"] for row in rows}
    for old in old_generated:
        if old in wanted or not safe_slug(old):
            continue
        dest = ROOT / old / "index.html"
        if dest.exists() and BANNER in dest.read_text(encoding="utf8"):
            dest.unlink()
            dest.parent.rmdir()
    for row in rows:
        dest = ROOT / row["slug"] / "index.html"
        dest.parent.mkdir(exist_ok=True)
        source = render_release(row)
        if not dest.exists() or dest.read_text(encoding="utf8") != source:
            if dest.exists() and BANNER not in dest.read_text(encoding="utf8"):
                raise ValueError("Refuse to overwrite an unrelated existing page: " + str(dest))
            dest.write_text(source, encoding="utf8")
    GENERATED_INDEX.write_text(json.dumps(sorted(wanted), indent=2)+"\n",encoding="utf8")
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    root = ET.parse(SITEMAP).getroot()
    previous_urls = {BASE+"/"+slug+"/" for slug in old_generated if safe_slug(slug)}
    for node in list(root):
        loc = node.find("{"+ns+"}loc")
        if loc is not None and loc.text in previous_urls:
            root.remove(node)
    existing = {n.text for n in root.findall(".//{"+ns+"}loc")}
    for row in rows:
        url = BASE+"/"+row["slug"]+"/"
        if url in existing:
            continue
        node = ET.SubElement(root, "{"+ns+"}url")
        ET.SubElement(node, "{"+ns+"}loc").text = url
        ET.SubElement(node, "{"+ns+"}lastmod").text = row["datePublished"][:10]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding="unicode")+"\n"
    SITEMAP.write_text(xml,encoding="utf8")
    print("PUBLICATION_GENERATED",json.dumps({"approved":len(rows),"urls":[BASE+"/"+s+"/" for s in sorted(wanted)]}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write",action="store_true",help="Generate live public page files (checks real R2 media)")
    parser.add_argument("--check",action="store_true",help="Read-only manifest validation")
    args = parser.parse_args()
    rows = read_manifest(verify=args.write and bool(rows_enabled()))
    if args.write:
        update_files(rows)
    else:
        print("PUBLICATION_MANIFEST_VALID",json.dumps({"approved":len(rows),"slugs":[r["slug"] for r in rows]}))


def rows_enabled():
    # Explicitly opt out of remote checks only during offline development.
    import os
    return os.environ.get("WNC_SKIP_REMOTE_PUBLICATION_CHECK") != "1"


if __name__ == "__main__":
    main()
