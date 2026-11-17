# Dual Scene Studio — preserve external B (owner experiment)

Entry point: `/vi/dual-scene/`. This is a separate noindex tool; the original `/vi/` and its individual mixer functions are preserved.

## Chosen production rule (option 1)

- Keep the **full original duration** of video A and video B, even if the result exceeds 10 minutes.
- Example: A 8 seconds + externally rendered B 10 minutes = final MP4 **10 minutes 8 seconds**.
- Never cut, stretch, re-time or loop externally rendered B. B appears once in the final MP4.
- Each mixer runs independently: Mixer A duration follows actual A MP4 metadata; Mixer B duration follows actual B MP4 metadata. No more `B = 600 - A`.
- The user exports each mix's WAV. The compositor joins A→B video, discards uploaded video source audio, and replaces it with a single AAC derived from both WAVs.

## Workflow

1. Create intro clip A with Luma (start/end keyframes).
2. Render the entire background clip B **outside** WhiteNoiseChoir, with its opening frame matching the last frame of A.
3. Upload MP4 A to Mixer A and completed MP4 B to Mixer B. The checkbox *Tự đồng bộ khi chọn video A hoặc B* reads their real duration. Both mixer timelines change independently and previously exported WAV is invalidated only when that mix's duration changed.
4. Compose each soundscape using unchanged mixer functionality; export WAV A and WAV B. The individual WAVs must match the input videos.
5. Click *Kiểm tra điểm nối A → B* to view endpoint frames; no WAV is needed for this preview.
6. Click *Ghép video A + B, giữ nguyên thời lượng*. The A and B images are not decoded or re-encoded by the compositor when compatible. The output length is A+B. Review the resulting MP4 preview and audio.

## Audio join diagnostics (2026-11-17)

- A and B are separate mixer sessions; therefore preserving image duration does **not** automatically preserve audio source phase.
- If A's real MP4 duration is 15.125 seconds while an older B project was created with 8-second offsets, a common source (piano, ocean, fire) will jump backward by 7.125 seconds at the seam.
- **Kiểm tra pha piano / sóng / lửa** examines common active, looping tracks that begin at 0 in both scenes and reports the expected B offset: `(A.sourceOffset + A.duration) modulo sourceDuration`.
- **Căn pha âm A → B** edits B offsets for those uniquely matched looping tracks only; it invalidates B WAV and requires a fresh WAV export. It cannot automatically fix unrelated effects, a wrong piano source, different master gain, mismatched track gain, or generative video motion.
- Export is blocked if these unique common tracks have a phase mismatch greater than ~55ms. When they are phase-matched with the same gain/pan/master, FFmpeg concatenates WAVs continuously rather than fading both to zero for 40ms.
- A verified audio seam still does **not** prove a visually seamless A→B transition. The video stream-copy pipeline performs no optical-flow interpolation or frame blending. Inspect the image endpoint comparison and a short exported seam video.

## Limitations and QA

- **Strict stream-copy compatibility:** Both videos must have the same H.264 AVC decoder configuration (codec, coded width and height, AVC description/SPS-PPS). Otherwise the compositor refuses instead of silently re-encoding B or writing a potentially broken MP4. Convert to matching specs outside the tool if necessary.
- Source MP4 may contain its own soundtrack; that track is discarded in favor of the internal mixes.
- The video is processed as encoded packets with Mediabunny and written into OPFS if available. The large final video is not held in a single JS array when OPFS is supported; Firefox/other browsers and large files may fail.
- Audio rendering is still performed by each existing mixer as WAV, which can use substantial RAM for long durations; the compositor uses ffmpeg.wasm to encode one AAC stream. No guarantee of 1h+ output stability.
- A: 1–60 seconds. B: 6–10800 seconds, subject to browser resources and existing Studio WAV constraints. There is **no enforced 600-second total**.
- The first video packet in each source must be a keyframe. Two similarly framed stills do not guarantee perfect motion continuity; inspect the final junction.
- No production audio assets, R2 metadata, mixer workflow, published mixes, or public routes are changed. No automatic publish action.
- Before claiming production stability, test with two real Luma/external-rendered MP4 files, inspect the full export (not just UI), and verify correct duration, codec, playback around A→B and absence of clicks.

## Regression checks

- Selecting A 8 seconds and B 600 seconds must show independent mixer lengths and final 608 seconds.
- Replacing B with a different duration does not change mixer A.
- The auto-sync toggle disables automatic mutation; manual action still syncs both selected videos.
- Mismatched H.264 codec configs must fail with an actionable warning, never silently transcode B.
- Both original studio timelines, JSON import/export, and WAV rendering must still work as before.
