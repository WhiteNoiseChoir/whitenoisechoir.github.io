#!/usr/bin/env python3
"""Offline publication regression: no fake live content, real validation and SEO."""
from __future__ import annotations
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_builder", BASE/"scripts/build_published_mixes.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

record = {
    "status": "published",
    "ownerApproved": True,
    "productionComplete": True,
    "qaApproved": True,
    "slug": "Living-Forest-Creek",
    "title": "Living Forest Creek - Rain and Wildlife",
    "description": "Listen to a peaceful creek flowing through lush forest foliage while gentle rain touches the water and distant frogs call from the shaded riverbank at dusk. The warm ambience offers a quiet natural setting for rest, relaxation and focus.",
    "category": "Forest creek & wildlife",
    "datePublished": "2026-11-12T10:00:00+07:00",
    "seo": {
        "title": "Living Forest Creek: Rain and Wildlife | WhiteNoiseChoir",
        "description": "Relax to a flowing forest stream, light rain, frogs and subtle distant night wildlife, with immersive nature video and up to ten hours of long-form listening."
    },
    "keywords": ["forest stream", "rain ambience", "frog calls", "sleep sounds"],
    "video": {"url": "https://media.whitenoisechoir.com/releases/living-forest-creek/final.mp4", "poster": "https://media.whitenoisechoir.com/releases/living-forest-creek/poster.jpg", "durationSeconds":600, "width":1920, "height":1080},
    "audio": {"url": "https://media.whitenoisechoir.com/releases/living-forest-creek/loop.mp3", "wavUrl": "https://media.whitenoisechoir.com/releases/living-forest-creek/master.wav", "durationSeconds":600},
    "timeline": [
        {"label": "Forest creek - main layer", "start":0, "duration":600, "gain":0.42, "group":"nature"},
        {"label": "Frogs beside the stream", "start":45, "duration":24, "gain":0.18, "group":"wildlife"}
    ],
    "article": [
        {"heading":"A living forest soundscape for relaxation", "text":"The water runs continuously around moss-covered rocks, while gentle rainfall reaches the leaves and surface of the creek. Distant wildlife calls contribute natural detail without overwhelming the central water ambience."},
        {"heading":"Long-form playback and responsible sound production", "text":"The approved ten-minute video is played repeatedly in the browser for a configurable listening session. No giant ten-hour MP4 is served. In audio-only mode a compressed mastered recording plays in a loop."}
    ]
}


def expect_invalid(doc, msg):
    try:
        mod.approve(doc, False)
    except ValueError:
        return
    raise AssertionError(msg)


def main():
    assert mod.approve(record, False) == record["slug"]
    expect_invalid({**record, "ownerApproved": False}, "Unapproved content accepted")
    expect_invalid({**record, "slug": "../bad"}, "Traversal slug accepted")
    expect_invalid({**record, "video": {**record["video"], "url":"https://other.example/video.mp4"}}, "Offsite media accepted")
    with tempfile.TemporaryDirectory(prefix="wnc-publisher-test-") as dirname:
        root = Path(dirname)
        (root/"data").mkdir()
        (root/"library").mkdir()
        shutil.copy2(BASE/"library/index.html", root/"library/index.html")
        shutil.copy2(BASE/"sitemap.xml", root/"sitemap.xml")
        (root/"data/published-mixes.json").write_text(json.dumps([record]), encoding="utf8")
        (root/"data/published-generated-slugs.json").write_text("[]\n", encoding="utf8")
        mod.ROOT = root
        mod.MANIFEST = root/"data/published-mixes.json"
        mod.GENERATED_INDEX = root/"data/published-generated-slugs.json"
        mod.LIBRARY = root/"library/index.html"
        mod.SITEMAP = root/"sitemap.xml"
        approved=mod.read_manifest(False)
        assert len(approved)==1
        mod.update_files(approved)
        path=root/"Living-Forest-Creek/index.html"
        assert path.exists()
        page=path.read_text(encoding="utf8")
        assert '<link rel="canonical" href="https://whitenoisechoir.com/Living-Forest-Creek/">' in page
        assert "max-video-preview:-1" in page
        assert '"@type":"VideoObject"' in page
        assert 'id="release-video"' in page and 'id="release-audio"' in page
        assert "LOCKED · Finished mix · Read-only" in page
        assert "Frogs beside the stream" in page
        assert 'id="release-hours"' in page
        assert "/Living-Forest-Creek/" in (root/"sitemap.xml").read_text(encoding="utf8")
        assert "/Living-Forest-Creek/" in (root/"library/index.html").read_text(encoding="utf8")
        old=page
        mod.update_files(approved)
        assert path.read_text(encoding="utf8")==old
        mod.update_files([])
        assert not path.exists()
        assert "/Living-Forest-Creek/" not in (root/"sitemap.xml").read_text(encoding="utf8")
        assert "No finished soundscape videos" in (root/"library/index.html").read_text(encoding="utf8")
    print("PUBLISHED_MIX_QA_PASS: approval gate, media allowlist, SEO, immutable timeline, grid, sitemap, idempotence and unpublish")


if __name__ == "__main__":
    main()
