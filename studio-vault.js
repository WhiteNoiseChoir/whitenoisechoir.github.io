const vaultRecipient = {"kty":"EC","crv":"P-256","x":"6SAkRtLdxwpy6K2YmE--le9vP1xCZuuQiNG1BHICJl0","y":"C4U7Sd-D7Fr9SxqWqnBxTSRUOXLpWG7yOfG8Rj9GIzA"};

const vaultUrl = 'https://media.whitenoisechoir.com/internal/studio-catalog/v1.json';
const vaultContext = new TextEncoder().encode('WhiteNoiseChoir Studio catalog v1');
const vaultStatus = document.getElementById('vault-status');
const vaultForm = document.getElementById('vault-form');
const vaultButton = document.getElementById('vault-submit');
const validKey = /^asset-library\/(?:commons|raw|kenney|cc0-github-mirror)\/sha256\/[a-f0-9]{2}\/[a-f0-9]{64}\.(?:wav|mp3|m4a|aac|flac|ogg|oga|opus|webm|mp4)$/i;

function base64Bytes(value) {
  return Uint8Array.from(atob(value.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
}

function privateKeyStore(mode, key) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('wnc-studio-vault',1);
    request.onupgradeneeded = () => request.result.createObjectStore('keys');
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction('keys',mode);
      const collection = transaction.objectStore('keys');
      const operation = mode === 'readonly' ? collection.get('catalog-v1') : collection.put(key,'catalog-v1');
      transaction.oncomplete = () => {db.close();resolve(operation.result);};
      transaction.onerror = transaction.onabort = () => {db.close();reject(transaction.error);};
    };
  });
}

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

function addVaultRows(rows) {
  for (const row of rows) {
    if (!row || !validKey.test(row.key || '') || row.id !== 'r2-' + rawDigest(row.key) ||
        typeof row.name !== 'string' || !Number.isFinite(row.duration) || row.duration <= 0) continue;
    const index = rawAssetIndex.get(row.id);
    const source = safeExternal(row.source);
    const licenseUrl = safeExternal(row.licenseUrl);
    if (!source) continue;
    if (index !== undefined && !assets[index].pending) continue;
    const item = {
      id:row.id, key:row.key, name:row.name, duration:row.duration, group:soundGroup(row),
      aliases:row.aliases || '', source, licenseUrl, license:row.license, credit:row.credit,
    };
    if (index === undefined) {
      rawAssetIndex.set(row.id,assets.length);
      assets.push(item);
    } else {
      assets[index] = item;
    }
  }
  rebuildCatalog();
  refreshLibraryGroups();
  renderLibrary();
  render();
}

function safeExternal(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : '';
  } catch { return ''; }
}

async function readVault(key) {
  const response = await fetch(vaultUrl,{cache:'no-store',signal:AbortSignal.timeout(45000)});
  if (!response.ok) throw Error('Chưa tải được chỉ mục R2.');
  const envelope = await response.json();
  if (envelope.v !== 1) throw Error('Định dạng chỉ mục R2 chưa được hỗ trợ.');
  const ephemeral = await crypto.subtle.importKey('jwk',envelope.ephemeral,{name:'ECDH',namedCurve:'P-256'},false,[]);
  const shared = new Uint8Array(await crypto.subtle.deriveBits({name:'ECDH',public:ephemeral},key,256));
  const input = new Uint8Array(shared.length + vaultContext.length);
  input.set(shared);
  input.set(vaultContext,shared.length);
  const digest = await crypto.subtle.digest('SHA-256',input);
  const aes = await crypto.subtle.importKey('raw',digest,'AES-GCM',false,['decrypt']);
  const clear = await crypto.subtle.decrypt({
    name:'AES-GCM',iv:base64Bytes(envelope.iv),additionalData:vaultContext,
  },aes,base64Bytes(envelope.cipher));
  const stream = new Blob([clear]).stream().pipeThrough(new DecompressionStream('gzip'));
  const catalog = await new Response(stream).json();
  if (catalog.version !== 1 || !Array.isArray(catalog.rows)) throw Error('Chỉ mục R2 không hợp lệ.');
  addVaultRows(catalog.rows);
  const formatted = value => new Intl.NumberFormat('vi-VN').format(value);
  const total = assets.filter(asset=>!asset.pending).length;
  vaultStatus.textContent = formatted(total) + ' nguồn trong Studio · Kho R2: ' +
    formatted(catalog.inventoryCount) + ' tệp duy nhất · ' +
    new Intl.DateTimeFormat('vi-VN',{dateStyle:'short',timeStyle:'short',timeZone:'Asia/Ho_Chi_Minh'}).format(new Date(catalog.generatedAt));
}

async function loadVault(unlock) {
  if(unlock) vaultStatus.closest('details').open = true;
  vaultButton.disabled = true;
  vaultStatus.textContent = 'Đang mở kho nội bộ…';
  try {
    let key;
    if (unlock) {
      if (!/^[A-Za-z0-9_-]{43}$/.test(unlock)) throw Error('Mã mở kho không hợp lệ.');
      key = await crypto.subtle.importKey('jwk',{...vaultRecipient,d:unlock},{name:'ECDH',namedCurve:'P-256'},false,['deriveBits']);
    } else {
      key = await privateKeyStore('readonly').catch(()=>null);
      if (!key) {
        vaultStatus.textContent = 'Mở liên kết riêng để tìm trong kho đã tải.';
        return;
      }
    }
    await readVault(key);
    if (unlock) await privateKeyStore('readwrite',key).catch(()=>{});
    document.getElementById('vault-key').value = '';
    vaultForm.hidden = true;
  } catch(error) {
    vaultStatus.textContent = error.name === 'OperationError' || error.name === 'DataError'
      ? 'Mã mở kho không khớp. Hãy dùng lại liên kết riêng.' : error.message;
  } finally {
    vaultButton.disabled = false;
  }
}

vaultForm.onsubmit = event => {
  event.preventDefault();
  const value = document.getElementById('vault-key').value.trim();
  loadVault(value);
};
const initialUnlock = /^#catalog=([A-Za-z0-9_-]{43})$/.exec(location.hash);
if (initialUnlock) {
  const clearUrl = new URL(location.href);
  clearUrl.hash = '';
  history.replaceState(null,'',clearUrl);
}
loadVault(initialUnlock?.[1]);
