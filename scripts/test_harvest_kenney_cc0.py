#!/usr/bin/env python3
"""Cheap offline tests for official CC0 ZIP intake and path filtering."""
import sys
import zipfile
sys.path.insert(0, "scripts")
import harvest_kenney_cc0_to_r2 as h

page = '''
<h1>Interface Sounds</h1><div>License Creative Commons CC0</div>
<a href="/media/pages/assets/interface-sounds/testhash/kenney_interface-sounds.zip">Continue without donating</a>
'''
link = h.pack_zip_url("interface-sounds", page)
assert h.check_zip_url(link, "interface-sounds")
assert not h.check_zip_url("https://example.com/other.zip", "interface-sounds")
assert not h.check_zip_url("https://kenney.nl/media/pages/assets/other/abc/a.zip", "interface-sounds")
try:
    h.pack_zip_url("interface-sounds", page.replace("CC0", "CC BY"))
    raise AssertionError("Non-CC0 publisher page accepted")
except ValueError:
    pass
class Info:
    def __init__(self, filename, file_size=1000, is_dir=False):
        self.filename = filename
        self.file_size = file_size
        self._is_dir = is_dir
    def is_dir(self):
        return self._is_dir
assert h.sound_entry(Info("Audio/click.ogg"), 10000)
assert h.sound_entry(Info("Audio/click.wav"), 10000)
assert not h.sound_entry(Info("../../escape.wav"), 10000)
assert not h.sound_entry(Info("Images/cover.png"), 10000)
assert not h.sound_entry(Info("__MACOSX/audio.wav"), 10000)
assert not h.sound_entry(Info("music.mp3", 100000), 10000)
assert sum(p[2] for p in h.PACKS) == 510
print("KENNEY_CC0_PACK_FILTER_TEST_PASS")
