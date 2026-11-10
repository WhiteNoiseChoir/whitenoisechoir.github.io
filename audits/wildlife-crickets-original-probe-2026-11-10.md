# WREC-015 — Automated original-file probe

Source: https://commons.wikimedia.org/wiki/File:Crickets_choir.ogg

Research branch only. The native audio file is retrieved from Wikimedia Commons by a temporary GitHub Actions worker, not checked into GitHub or uploaded to Cloudflare R2. The worker runs `ffprobe`, whole-file `volumedetect`, and silence-interval detection; it publishes a short text artifact for review.

**The audio is CC BY-SA 4.0, not CC0.** Before any adapted MP3 is distributed, preserve creator (Serg Childed), title, source URL, license link, adaptation notice, and legal review of ShareAlike obligations. Explicit human listening and owner approval remain mandatory.

Workflow: `.github/workflows/wildlife_source_probe.yml`. Manual mode is possible; branch pushes targeting this workflow also invoke the probe. The source is ~46.3MB / 21m44s on the Commons page. Source bytes are deleted after measurements. No direct production change, review-page publication or audio release is authorized. If the worker cannot retrieve the file, logs should show DOWNLOAD_BLOCKED instead of pretending QA passed.
