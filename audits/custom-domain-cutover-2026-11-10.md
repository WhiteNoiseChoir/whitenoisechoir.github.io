# WhiteNoiseChoir.com — coordinated GitHub Pages cutover

Prepared 2026-11-10. **STAGED ONLY — DO NOT MERGE BEFORE THE CLOUDFLARE DNS HANDOFF.**

## Verified baseline

- GitHub source repository: WhiteNoiseChoir/whitenoisechoir.github.io, branch main; production site https://whitenoisechoir.github.io.
- Cloudflare R2 has 395 verified production media objects: https://media.whitenoisechoir.com. Keep this subdomain intact.
- Current public https://whitenoisechoir.com and https://www.whitenoisechoir.com still serve an old iNET/OneSite produce/vegetables site.
- Main branch lacks a root CNAME; all canonical, sitemap and robots references originally pointed to github.io.
- 35 approved playable sources, 45 presets, HLS/MP3 failover, stop and Sleep Timer are production-critical.
- Existing Oxmail MX gw.oxmail.vn, SPF, DKIM, DMARC and mail.oxmail.vn must remain untouched.

## Prepared GitHub PR

- Root CNAME is `whitenoisechoir.com`.
- 60 public HTML pages migrated to the new domain for canonical, links, JSON-LD.
- AudioObject contentUrl now points to verified R2 `https://media.whitenoisechoir.com/audio/` URLs.
- Sitemap 18 unchanged paths, now `https://whitenoisechoir.com`; robots references sitemap under .com.
- No changes to published audio/HLS, 35-source catalog, 45 presets or production player.
- New CI gates test all pages, canonical, JSON-LD, noindex, production player, selective sitemap, GH emergency rollback, R2 and browser navigator.

## Cloudflare DNS changes (only account owner or authenticated Cloudflare session can do them)

In **whitenoisechoir.com DNS Records**, only replace old website records, **not** email or media:
1. Remove existing OneSite/proxy apex `@` A records and stale `@` AAAA records.
2. Add four `@` A records (Cloudflare gray-cloud **DNS only** for initial HTTPS verification):
   - 185.199.108.153
   - 185.199.109.153
   - 185.199.110.153
   - 185.199.111.153
3. Optionally add GitHub's four published AAAA records for IPv6:
   - 2606:50c0:8000::153
   - 2606:50c0:8001::153
   - 2606:50c0:8002::153
   - 2606:50c0:8003::153
   Do not keep the old OneSite AAAA.
4. Remove conflicting `www` A / AAAA, then add `www` CNAME to `whitenoisechoir.github.io` (DNS only).
5. Leave `media` CNAME (R2), mail CNAME DNS-only, MX and all SPF/DKIM/DMARC TXT unchanged.
6. Do not disable the zone, modify NS at iNET or enable an arbitrary redirect rule.

GitHub's documentation: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site

## Coordinated release order

- Keep this PR as draft while old website appears at .com; merging now may redirect GitHub.io listeners to the wrong old site.
- Change DNS in a coordinated window and immediately finalize PR merge; keep the delay short to limit the interval where GitHub Pages has not claimed the new hostname.
- Confirm GitHub Pages deployment SUCCESS for exact merge SHA, Pages custom domain assigned and TLS certificate ready (HTTPS enforced once available).
- Check https://whitenoisechoir.com/ for real WhiteNoiseChoir, http->https, www->apex and github.io->apex redirects, 60 public page links, 18 sitemap locs, robots, 35 R2 streams and relevant Sleep Timer/iPhone locks.
- Confirm live email MX/SPF/DKIM/DMARC and R2 custom hostname were not impacted.
- Submit the new canonical sitemap into the dedicated Google Search Console domain property when ready.

## Rollback

- In case of GitHub Pages hostname/TLS error, retain current GitHub Pages source and audio; do not delete media.
- Revert the CNAME and SEO cutover commit only if necessary, and return DNS web records to the previously recorded OneSite values; never touch Oxmail/R2 records. Recheck HTTPS and email.
- Page redirects, custom-domain property and caching may require time; rollback should be deliberate and measured.

## Security

A root CNAME is valid for a **branch-published GitHub Pages site**. If the repository changes to a custom GitHub Actions artifact publisher, update the Pages setting through an administrator (CNAME files are ignored by some Actions-based publishers). Verify site ownership with GitHub when practical. Avoid wildcard CNAMEs.

