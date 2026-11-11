function soundGroup(row) {
  if (row.taxon && row.taxon !== 'unknown') return 'wildlife';
  const hints = searchable([row.name,row.aliases].join(' '));
  const groups = [
    ['rain',/\b(rain|thunder|storm|mua|sam)\b/],
    ['water',/\b(water|ocean|river|stream|wave|waterfall|suoi|bien)\b/],
    ['wildlife',/\b(bird|owl|frog|wolf|insect|bee|dog|animal|wildlife|chim)\b/],
    ['fire',/\b(fireplace|fire|crackle|wood|lua)\b/],
    ['wind',/\b(wind|breeze|gust|gio)\b/],
    ['fan',/\b(fan|ventilation|appliance|quat)\b/],
    ['transit',/\b(train|car|airplane|engine|transport|vehicle)\b/],
    ['human',/\b(heartbeat|breath|human|footstep|steps)\b/],
    ['noise',/\b(noise|static)\b/],
    ['hum',/\b(hum|drone|rumble)\b/],
  ];
  return groups.find(([,pattern])=>pattern.test(hints))?.[0] || 'other';
}

function safeExternal(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : '';
  } catch { return ''; }
}



(() => {
  const gate = {active:false, verify};
  window.WNCPublicCatalog = gate;
  let expiresAt = 0;
  let verifying;
  let turnstileScript;
  const target = $('library-status');

  function provider() {
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
  async function challenge() {
    const cf = await provider();
    const widget = document.createElement('div');
    target.after(widget);
    target.textContent = 'Verify your browser to use the shared sound catalog.';
    let widgetId;
    let deadline;
    try {
      const token = await new Promise((resolve,reject)=>{
        const fail = ()=>reject(Error('Browser verification did not finish. Please try again.'));
        deadline = setTimeout(fail,90000);
        widgetId = cf.render(widget,{
          sitekey:'0x4AAAAAAF8gZh-xEgWUNBmX',action:'media_access',appearance:'interaction-only',
          callback:resolve,'error-callback':fail,'expired-callback':fail,'timeout-callback':fail,
        });
      });
      const response = await fetch('/api/studio/session',{
        method:'POST',headers:{'Content-Type':'text/plain'},body:token,signal:AbortSignal.timeout(10000),
      });
      if (!response.ok) throw Error('Browser verification did not finish. Please try again.');
      return response.json();
    } finally {
      clearTimeout(deadline);
      if (widgetId!==undefined) cf.remove(widgetId);
      widget.remove();
      target.textContent = '';
    }
  }
  async function session() {
    const response = await fetch('/api/studio/session',{cache:'no-store',signal:AbortSignal.timeout(10000)});
    if (response.ok) return response.json();
    if (response.status===401) return challenge();
    throw Error('The shared catalog is temporarily unavailable.');
  }
  async function verify() {
    if (expiresAt>Date.now()+10000) return;
    verifying ||= session().then(value=>{
      expiresAt = Number(value.expiresAt)*1000;
      if (!Number.isFinite(expiresAt) || expiresAt<=Date.now()) throw Error('Browser verification expired.');
    }).finally(()=>{verifying=null;});
    await verifying;
  }

  async function builtInAliases() {
    const aliases = new Map();
    await Promise.all(assets.map(async (asset,index)=>{
      if (!asset.id?.startsWith('r2-')) return;
      const input = new TextEncoder().encode('wnc-public-source-v1/'+asset.id);
      const hash = new Uint8Array(await crypto.subtle.digest('SHA-256',input));
      const id = [...hash.slice(0,16)].map(byte=>byte.toString(16).padStart(2,'0')).join('');
      aliases.set(id,index);
    }));
    return aliases;
  }
  async function loadCatalog() {
    const response = await fetch('/api/studio/catalog',{signal:AbortSignal.timeout(25000)});
    if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) return;
    const catalog = await response.json();
    if (catalog.version!==1 || !Array.isArray(catalog.sounds)) return;
    const aliases = await builtInAliases();
    for (const row of catalog.sounds) {
      if (!/^[a-f0-9]{32}$/.test(row.id || '') || typeof row.name!=='string' || !row.name ||
          !Number.isFinite(row.duration) || row.duration<=0) continue;
      const id = 'public-'+row.id;
      const existing = rawAssetIndex.get(id);
      const builtin = aliases.get(row.id);
      if (builtin!==undefined && existing===undefined) {
        rawAssetIndex.set(id,builtin);
        continue;
      }
      if (existing!==undefined && !assets[existing].pending) continue;
      const entry = {
        id, name:row.name, duration:row.duration, group:soundGroup(row),
        aliases:row.aliases || '', source:safeExternal(row.source), licenseUrl:safeExternal(row.licenseUrl),
        license:row.license, credit:row.credit, url:location.origin+'/api/studio/sources/'+row.id, publicMedia:true,
      };
      if (existing!==undefined) assets[existing] = entry;
      else {
        rawAssetIndex.set(id,assets.length);
        assets.push(entry);
      }
    }
    gate.active = true;
    const check = sourceAddresses(0)[0];
    if (check) $('audio-check').src = check;
    rebuildCatalog();
    refreshLibraryGroups();
    renderLibrary();
    render();
  }
  loadCatalog().catch(()=>{});
})();
