'use strict';

const legacySound = new URL(location.href).searchParams.get('sound');
if (legacySound && /^[a-z0-9-]{1,120}$/.test(legacySound)) {
  location.replace('/listen.html?sound=' + encodeURIComponent(legacySound));
} else {
  startPublicSounds();
}

async function startPublicSounds() {
  const get = id => document.getElementById(id);
  const query = get('sound-query');
  const category = get('sound-category');
  const list = get('sound-list');
  const status = get('sound-status');
  const feedback = get('sound-feedback');
  const player = get('sound-player');
  const more = get('sound-more');
  const categories = new Map();
  const pageSize = 40;
  let shown = pageSize;
  let sounds = [];
  let current = null;
  let challenge;
  let challengeWidget;
  let turnstileScript;

  const normalize = value => value.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim();
  const filter = () => {
    const terms = normalize(query.value).split(/\s+/).filter(Boolean);
    return sounds.filter(row => (!category.value || row.cat === category.value) &&
      terms.every(term => row.search.includes(term)));
  };
  function setCurrent(row, button) {
    if (current?.button) {
      current.button.textContent = 'Preview';
      current.button.setAttribute('aria-pressed', 'false');
    }
    current = row ? {row, button} : null;
    if (button) {
      button.textContent = 'Stop';
      button.setAttribute('aria-pressed', 'true');
    }
  }
  async function preview(row, button) {
    if (current?.row === row) {
      player.pause();
      setCurrent(null);
      return;
    }
    feedback.textContent = '';
    if (row.protected && !await canReadCatalogAudio()) return;
    setCurrent(row, button);
    player.src = row.audio;
    try {
      await player.play();
    } catch {
      if (current?.row !== row) return;
      feedback.textContent = 'Preview could not start. Please try again.';
      setCurrent(null);
    }
  }
  function soundItem(row) {
    const li = document.createElement('li');
    li.className = 'panel public-sound';
    const details = document.createElement('div');
    const title = document.createElement('h2');
    title.textContent = row.title;
    const summary = document.createElement('p');
    summary.textContent = categories.get(row.cat) || '';
    details.append(title, summary);
    if (row.credit || row.license) {
      const credit = document.createElement('p');
      if (row.credit) credit.append(row.credit+' · ');
      const license = publicLink(row.licenseUrl, row.license || 'License');
      credit.append(license || row.license || '');
      const source = publicLink(row.source, 'Original source');
      if (source) credit.append(' · ',source);
      details.append(credit);
    }
    const actions = document.createElement('div');
    actions.className = 'public-sound-actions';
    const listen = document.createElement('button');
    listen.type = 'button';
    listen.textContent = current?.row === row ? 'Stop' : 'Preview';
    listen.setAttribute('aria-label', 'Preview ' + row.title);
    listen.setAttribute('aria-pressed', String(current?.row === row));
    if (current?.row === row) current.button = listen;
    listen.addEventListener('click', () => preview(row, listen));
    const download = document.createElement('a');
    download.href = row.download;
    download.download = row.id + '.mp3';
    download.textContent = 'Download MP3';
    download.setAttribute('aria-label', 'Download ' + row.title + ' MP3');
    if (row.protected) download.addEventListener('click',async event=>{
      event.preventDefault();
      if (await canReadCatalogAudio()) location.assign(row.download);
    });
    actions.append(listen, download);
    li.append(details, actions);
    return li;
  }
  function render() {
    const rows = filter();
    status.textContent = rows.length ? new Intl.NumberFormat('en').format(rows.length) + ' MP3 sounds' : 'No matching sounds.';
    list.replaceChildren(...rows.slice(0, shown).map(soundItem));
    more.hidden = rows.length <= shown;
  }
  function reset() {
    shown = pageSize;
    render();
  }

  function publicLink(address, title) {
    try {
      const url = new URL(address);
      if (url.protocol!=='https:' || url.username || url.password) return null;
      const link = document.createElement('a');
      link.href = url.href;
      link.rel = 'noopener noreferrer';
      link.target = '_blank';
      link.textContent = title;
      return link;
    } catch { return null; }
  }
  function refreshCategories() {
    const present = new Set(sounds.map(row=>row.cat));
    const value = category.value;
    category.replaceChildren(new Option('All categories',''));
    for (const [slug,title] of categories) if (present.has(slug)) category.add(new Option(title,slug));
    if (present.has(value)) category.value = value;
  }
  async function loadProtectedCatalog() {
    try {
      const response = await fetch('/api/studio/catalog');
      if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) return;
      const data = await response.json();
      if (data.version!==1 || !Array.isArray(data.sounds)) return;
      for (const row of data.sounds) {
        if (!/^[a-f0-9]{32}$/.test(row.id) || typeof row.title!=='string' || !row.title) continue;
        const label = typeof row.category==='string' && row.category ? row.category : 'Recordings';
        const cat = 'field:'+normalize(label);
        categories.set(cat,label);
        const audio = '/api/studio/mp3/'+row.id;
        sounds.push({...row,cat,audio,download:audio+'?download=1',protected:true,
          search:normalize([row.title,row.keywords||'',label].join(' '))});
      }
      refreshCategories();
      render();
    } catch { /* The existing public MP3 masters are still available. */ }
  }
  function loadTurnstile() {
    if (window.turnstile) return Promise.resolve(window.turnstile);
    if (!turnstileScript) turnstileScript = new Promise((resolve,reject)=>{
      const script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.onload = ()=>resolve(window.turnstile);
      script.onerror = reject;
      document.head.append(script);
    }).catch(error=>{turnstileScript=null;throw error;});
    return turnstileScript;
  }
  async function canReadCatalogAudio() {
    try {
      const check = await fetch('/api/studio/session',{cache:'no-store'});
      if (check.ok) return true;
      if (check.status!==401) throw Error();
      if (!challenge) {
        challenge = document.createElement('div');
        feedback.after(challenge);
      }
      const needsReset = challenge.hidden;
      challenge.hidden = false;
      feedback.textContent = 'Verify once to preview or download catalog MP3s.';
      if (challengeWidget===undefined) {
        const provider = await loadTurnstile();
        if (challengeWidget===undefined) challengeWidget = provider.render(challenge,{
          sitekey:'0x4AAAAAAF8gZh-xEgWUNBmX',action:'media_access',
          callback:async token=>{
            try {
              const response = await fetch('/api/studio/session',{
                method:'POST',headers:{'Content-Type':'text/plain'},body:token,
              });
              if (!response.ok) throw Error();
              challenge.hidden = true;
              feedback.textContent = 'Verified. Select Preview or Download MP3 to continue.';
            } catch {
              feedback.textContent = 'Verification did not complete. Please retry.';
              provider.reset(challengeWidget);
            }
          },
          'expired-callback':()=>provider.reset(challengeWidget),
        });
      } else if (needsReset) {
        window.turnstile.reset(challengeWidget);
      }
    } catch {
      feedback.textContent = 'Verification is unavailable. Please try again.';
    }
    return false;
  }

  player.addEventListener('ended', () => setCurrent(null));
  query.addEventListener('input', reset);
  category.addEventListener('change', reset);
  more.addEventListener('click', () => { shown += pageSize; render(); });

  try {
    const response = await fetch('/catalog/library.json');
    if (!response.ok) throw Error('Catalog unavailable');
    const catalog = await response.json();
    for (const row of catalog.categories) categories.set(row.slug, row.title);
    sounds = catalog.sounds.filter(row => /^[a-z0-9-]{1,120}$/.test(row.id) && row.title)
      .map(row => ({
        ...row, search: normalize([row.title, row.desc || '', categories.get(row.cat) || ''].join(' ')),
        audio: '/audio/' + row.id + '.mp3', download: '/audio/' + row.id + '.mp3',
      }));
    refreshCategories();
    render();
    loadProtectedCatalog();
  } catch {
    status.textContent = 'The sound catalog could not load. Reload to try again.';
  }
}
