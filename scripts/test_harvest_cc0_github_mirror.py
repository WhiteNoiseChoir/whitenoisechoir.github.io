#!/usr/bin/env python3
"""Offline smoke tests: pack whitelist and uninterpreted audio bytes."""
import pathlib
import tempfile
import sys
sys.path.insert(0,"scripts")
import harvest_cc0_github_mirror_to_r2 as h
assert len(h.PACKS)==14
assert "music-jingles" not in h.PACKS
assert "voiceover-pack" not in h.PACKS
assert "oga-levelup-powerup" not in h.PACKS
with tempfile.TemporaryDirectory() as tmp:
    root=pathlib.Path(tmp)
    for k in h.PACKS: (root/"audio"/k).mkdir(parents=True)
    (root/"audio"/"impact-sounds"/"impact.wav").write_bytes(b"1234")
    (root/"audio"/"music-jingles").mkdir(parents=True)
    (root/"audio"/"music-jingles"/"song.wav").write_bytes(b"abc")
    (root/"audio"/"oga-zombies"/"zombie.ogg").write_bytes(b"0"*201)
    found=list(h.iter_assets(root))
    assert len(found)==2,found
    assert h.sha256(found[0][0])!=h.sha256(found[1][0])
    assert all("music" not in item[1] for item in found)
print("PINNED_CC0_GITHUB_MIRROR_SMOKE_TEST_PASS")
