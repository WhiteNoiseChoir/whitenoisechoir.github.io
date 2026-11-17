# Dual Scene Studio — thử nghiệm A → B

Route: `/vi/dual-scene/`. This is a separate, non-indexed experimental UI. The original `/vi/` remains the unchanged single-mixer workflow except a navigation link and a no-op bridge script.

## Workflow

1. Mixer A: choose a generated introduction clip (e.g. 12s), set its timeline length to match, mix any required movement/steps/sea/fire, click **Xuất WAV**.
2. Mixer B: select a seamless ambience clip (e.g. 8s) with a locked camera, mix the resting scene, click **Xuất WAV**. For a 12s A project, B must be 588s.
3. Use **Đọc trạng thái** to confirm both WAVs and video clips are present. The A project and B project have independent localStorage keys.
4. Use **Kiểm tra hình cuối A / đầu B và vòng B** to inspect image endpoints. Match frames with Luma first-frame/last-frame inputs; any numerical threshold is advisory.
5. Choose **720p** for initial browser QA, then **1080p** for the main test, and click **Ghép 2 video + âm thanh**.
6. Review the final preview at both the A→B transition and the first B→B loop. Listen for audio clicks. Keep the two original project JSON exports.
7. If successful, download the 10-minute MP4 for the existing long-form extension workflow (10-hour creation is intentionally outside the browser compositor).

## Technical and safety notes

- Both existing mixers run isolated in same-origin iframes. `studio-engine.js` adds a scene suffix only when `?dual-scene=A` or `B` is present; ordinary `/vi/` projects are unaffected.
- A single FFmpeg pass encodes a short A+B stream (24fps H.264 without B-frames and a forced keyframe at the start of B). Mediabunny writes A packets once and repeats only B packets until 600 seconds, avoiding another 600-second video encode.
- Each mixer exports its own uncompressed WAV. FFmpeg joins those with independent 40ms endpoint fade-in/out to reduce hard clicks, and generates one 192kbps AAC stream.
- `postMessage` requires the exact origin and sender iframe. Selected media files do **not** upload to the server; encoding and output use browser memory/OPFS. FFmpeg and Mediabunny scripts are loaded from pinned CDN versions.
- A duration must be 6–60 seconds; total A+B exactly 600 seconds. A's selected clip must cover A's length. B's loop is repeated without artificial blending. Frame QA indicates image differences; it does **not** guarantee motion continuity.
- This experiment does not change source metadata, R2, audio quality rules, publication permissions, or public-site routes. No automatic Public step is included.

## Smoke tests

- Ordinary `/vi/` retains the original storage key and WAV+video pipeline.
- Opening a new dual project initializes A=12s and B=588s. Editing one must not alter the other.
- A and B JSONs independently import/export; source IDs remain unchanged.
- The composer refuses missing WAV, missing clip, invalid duration, undersized A video, or missing B keyframe.
- Confirm the final MP4 is exactly 600s and plays at 0:00, A→B boundary and first B repetition.
- Test input MP4 files differing in aspect ratio, audio tracks and frame rates; confirm normalized output is 24fps, muted input video, one AAC output.
- Check mobile memory constraints; if WebAssembly cannot complete, run 720p on desktop. Do not assert 1080p 10min support on every device until tested.
