# Studio Private Music opt-in — NOT ACTIVE

This branch prepares a **separate, opt-in** browser transport for Cloudflare Access-protected Music. It is *not* loaded by `vi/index.html` or the English homepage and cannot add or play Music in current production.

## Current condition
- Private R2: `wnc-music-private` holds two Scott Buckley Music originals, verified through WS6 + WS5.
- Private WS4 R2 catalog has the two technical candidates, `studio_ready=false`, and requires an Access gateway.
- Worker was manually deployed with protected workers.dev URL and verified owner playback and anonymous Access refusal in Chrome screenshot, as user confirmed. Implementation was committed in Private repo `WhiteNoiseChoir/wnc-metadata-index` (PR #13), and has been deployed on Cloudflare.
- Planned hostname `https://wnc-private-music-gateway.whitescreen-dev.workers.dev` has a live tested catalog and MP3 audition endpoint, but browser cross-origin CORS/cookie use from Studio remains unverified.

## What's prepared
- `studio-private-music-optin.mjs` verifies full private-catalog schema, exact SHA-based R2 key, source/attribution/CC BY license and "not approved" statuses before offering tracks. Requests catalog with `credentials: include` and redirect refusal.
- `studio-engine.js` routes `privateMusic=true` assets only to exact `https://wnc-private-music-gateway.whitescreen-dev.workers.dev/v1/audio/<sha>`, includes Access cookies and does not fall back to public `media.whitenoisechoir.com` for those assets.
- Existing Nature and Studio catalog sources continue to use their original URLs and fetch semantics.
- The two Studio script version tags are bumped for cache invalidation. UI is still **off by default** and appears only with `?private-music=1`. Clicking `Tải 2 bản Music Private` is required to fetch any private catalog; the Access login link opens in a separate first-party tab. Existing Nature audio remains untouched.

## Activation prerequisites (separate review)
1. Create Cloudflare Worker + `MUSIC_R2` binding to bucket `wnc-music-private`, enable Cloudflare Access on **every** endpoint, exact email allowlist, correct Audience tag, and only the protected custom hostname. No `workers.dev` or preview URLs.
2. Verify anonymous/unauthorized HTTP 403 and authorized /v1/catalog 200 plus /v1/audio/<sha> Range 206. Set Access CORS for `https://whitenoisechoir.com` with credentialed requests, and handle preflight OPTIONS at the Access layer; avoid a global Access bypass for the catalog or MP3. Cloudflare docs: https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/cors/
3. Test on both Safari and Chrome including any cross-site cookie constraints. Verify audio decode and WAV export for an exact 10:00 test mix. Do not claim verified until real end-to-end browser QA succeeds.
4. After these checks, a **separate** reviewed PR may load `studio-private-music-optin.mjs` from `vi/index.html` and use `retrievePrivateMusic({enabled: true, pageOrigin: location.origin})` + `registerMusicRows(...)` with the existing Studio refresh callbacks.
5. Keep the existing Nature catalog behavior, stable asset IDs, no automatic publication. The opt-in metadata and Music playback are **not** equivalent to listening QA, global SHA dedupe or YouTube release clearance.

Do not put Cloudflare credentials, Access JWT, allowlist emails, raw private Music catalog, or private audio in the public GitHub repository.

## Owner manual integration pilot
- In Studio open `https://whitenoisechoir.com/vi/?private-music=1`. No auto-loading or external requests occur from this flag alone.
- Click `1. Đăng nhập Music Gateway` and authenticate as the owner in that first-party tab. Close or leave tab open.
- Click `2. Tải 2 bản Music Private` to fetch catalog with `credentials: include`. CORS / third-party cookie blocking may prevent this on current hostname. If blocked, STOP: no Access policy bypass; handle via protected same-site hostname/domain ownership later.
- After import: select `Nhạc cụ & âm nhạc`, audition one record, add it to timeline, export a 10:00 WAV locally (do not Public). Check sound, gain, loop seams, attribution.
- All private assets remain `studioReady=false`, `publicationApproved=false`; this is only owner audition and preflight.
