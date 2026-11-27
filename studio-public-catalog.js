// Public CC0 / CC BY Nature & SFX Studio catalog.
// Only reads the separately published, sanitized R2 index. Never touches Music Private.
(() => {
  'use strict';
  const endpoint = 'https://media.whitenoisechoir.com/studio-public-catalog/v1.json';
  const status = document.getElementById('public-catalog-status');
  const sha = /^r2-[0-9a-f]{64}$/;
  const key = /^asset-library\/(?:commons|raw|kenney|cc0-github-mirror)\/sha256\/[0-9a-f]{2}\/[0-9a-f]{64}\.(?:wav|mp3|m4a|aac|flac|ogg|oga|opus|webm|mp4)$/i;
  const licenses = new Set(['CC0', 'CC0-1.0', 'PUBLIC DOMAIN', 'PUBLIC-DOMAIN', 'CC-BY-3.0', 'CC-BY-4.0']);
  const displayNumber = n => n.toLocaleString(document.documentElement.lang || 'en');
  const clean = value => typeof value === 'string' ? value.trim() : '';
  const safeLink = value => {
    try {
      const u = new URL(value);
      return u.protocol === 'https:' && !u.username && !u.password ? u.href : '';
    } catch { return ''; }
  };
  const groupFor = row => {
    if (row.taxon && row.taxon !== 'unknown') return 'wildlife';
    const text = [row.name, row.aliases].join(' ').toLowerCase();
    if (/\b(piano|guitar|music|melody|instrumental|instrument|orchestra)\b/.test(text)) return 'music';
    if (/\b(rain|thunder|storm)\b/.test(text)) return 'rain';
    if (/\b(ocean|river|stream|waterfall|creek|water|wave|lake)\b/.test(text)) return 'water';
    if (/\b(bird|owl|frog|wolf|animal|insect|cricket|katydid|cicada|wildlife)\b/.test(text)) return 'wildlife';
    if (/\b(fire|crackle|fireplace|woodstove)\b/.test(text)) return 'fire';
    if (/\b(wind|breeze|gust|leaves)\b/.test(text)) return 'wind';
    if (/\b(fan|ventilation|air.condition)\b/.test(text)) return 'fan';
    return 'other';
  };
  const validate = row => {
    if (row && (row.id === 'r2-c7f275e6d02069f8f45f20b6c5e5dfdaa3cfc1d908e8498da111f158a15bf74b' || String(row.source || '').replace(/\/$/, '') === 'https://www.inaturalist.org/observations/384097330')) return null;
    if (!row || !sha.test(row.id || '') || !key.test(row.key || '') ||
      row.id !== 'r2-' + rawDigest(row.key) || !clean(row.name) ||
      !Number.isFinite(row.duration) || row.duration <= 0 || row.duration > 86400)
      return null;
    const license = clean(row.license);
    if (!licenses.has(license.toUpperCase())) return null;
    const source = safeLink(row.source);
    if (!source) return null;
    const licenseUrl = safeLink(row.licenseUrl);
    const credit = clean(row.credit);
    if (license.toUpperCase().startsWith('CC-BY') && (!credit || !licenseUrl)) return null;
    return {
      id: row.id, key: row.key, name: clean(row.name).slice(0, 180),
      duration: row.duration, source, license,
      licenseUrl, credit: credit.slice(0, 280),
      group: groupFor(row), aliases: clean(row.aliases).slice(0, 360),
      assetStatus: 'PUBLIC_LICENSE_DECLARED_LISTENING_QA_NOT_GUARANTEED',
      privateMusic: false
    };
  };
  const fail = message => { if (status) status.textContent = message; };
  async function load() {
    fail(document.documentElement.lang === 'vi'
      ? 'Đang tải thư viện âm thanh công khai…' : 'Loading public sound library…');
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 60000);
      let response;
      try { response = await fetch(endpoint, {signal: controller.signal, cache: 'no-store'}); }
      finally { clearTimeout(timeout); }
      if (!response.ok || !(response.headers.get('content-type') || '').includes('application/json'))
        throw Error('Catalog not reachable (HTTP ' + response.status + ')');
      const payload = await response.json();
      if (payload.schema !== 'wnc_public_studio_catalog_v1' || payload.version !== 1 ||
          !Array.isArray(payload.rows) || payload.rows.length < 1000 ||
          payload.rows.length > 100000) throw Error('Invalid public catalog');
      let added = 0;
      for (const row of payload.rows) {
        const asset = validate(row);
        if (!asset) continue;
        const at = rawAssetIndex.get(asset.id);
        if (at !== undefined) {
          if (assets[at].pending === true) { assets[at] = asset; added++; }
          continue;
        }
        rawAssetIndex.set(asset.id, assets.length);
        assets.push(asset);
        added++;
      }
      rebuildCatalog();
      refreshLibraryGroups();
      renderLibrary();
      render();
      fail((document.documentElement.lang === 'vi' ? 'Thư viện công khai: ' : 'Public sound library: ') +
        displayNumber(payload.rows.length) +
        (document.documentElement.lang === 'vi' ? ' nguồn có metadata giấy phép. Không cần mã. Đã bổ sung ' : ' license-declared sources. No unlock code. Added ') +
        displayNumber(added) + '.');
    } catch (error) {
      console.warn('Public catalog unavailable:', error);
      fail(document.documentElement.lang === 'vi'
        ? 'Chưa tải được catalog công khai; các nguồn có sẵn vẫn dùng được. Thử tải lại trang.'
        : 'Could not load the public catalog. Built-in audio still works. Try refreshing.');
    }
  }
  load();
})();
