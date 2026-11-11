const validKey = /^asset-library\/(?:commons|raw|kenney|cc0-github-mirror)\/sha256\/[a-f0-9]{2}\/[a-f0-9]{64}\.(?:wav|mp3|m4a|aac|flac|ogg|oga|opus|webm|mp4)$/i;

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

function addOwnerRows(rows) {
  for (const row of rows) {
    if (!row || !validKey.test(row.key || '') || row.id !== 'r2-' + rawDigest(row.key) ||
        typeof row.name !== 'string' || !Number.isFinite(row.duration) || row.duration <= 0) continue;
    const publicId = /^public-[a-f0-9]{32}$/.test(row.publicId || '') ? row.publicId : null;
    const nativeIndex = rawAssetIndex.get(row.id);
    const publicIndex = publicId ? rawAssetIndex.get(publicId) : undefined;
    const index = nativeIndex ?? publicIndex;
    const source = safeExternal(row.source);
    const licenseUrl = safeExternal(row.licenseUrl);
    if (!source) continue;
    if (index !== undefined && !assets[index].pending) {
      if (publicId) rawAssetIndex.set(publicId,index);
      if (publicIndex!==undefined && publicIndex!==index && assets[publicIndex].pending) assets[publicIndex]={...assets[index],aliasOnly:true};
      continue;
    }
    const item = {
      id:row.id, key:row.key, name:row.name, duration:row.duration, group:soundGroup(row),
      aliases:row.aliases || '', source, licenseUrl, license:row.license, credit:row.credit,
    };
    const slot = index ?? assets.length;
    rawAssetIndex.set(row.id,slot);
    if (publicId) rawAssetIndex.set(publicId,slot);
    assets[slot] = item;
    if (publicIndex!==undefined && publicIndex!==slot && assets[publicIndex].pending) assets[publicIndex]={...item,aliasOnly:true};
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


const ownerCatalogStatus = $('owner-catalog-status');
const ownerDialog = $('owner-dialog');
const ownerForm = $('owner-form');
const ownerSlug = $('owner-slug');
const ownerSubmit = $('owner-submit');
const ownerFeedback = $('owner-feedback');
const ownerMedia = $('owner-media');
const ownerResult = $('owner-result');
const mediaExtensions = new Map([['mp3','audio/mpeg'],['wav','audio/wav'],['m4a','audio/mp4'],['mp4','video/mp4']]);
const ownerSlugOf = title => title.toLowerCase().replaceAll('đ','d').normalize('NFD')
  .replace(/\p{M}/gu,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,100).replace(/-$/,'');
let publishMode = false;

async function loadOwnerCatalog() {
  try {
    const response = await fetch('/vi/api/catalog',{cache:'no-store'});
    if (!response.ok) throw Error();
    const catalog = await response.json();
    if (!Array.isArray(catalog.rows)) throw Error();
    addOwnerRows(catalog.rows);
    ownerCatalogStatus.textContent = assets.filter(asset=>!asset.pending && !asset.aliasOnly).length.toLocaleString('vi-VN')+' nguồn trong Studio.';
  } catch {
    ownerCatalogStatus.textContent = 'Danh mục R2 chưa tải được. Hãy tải lại trang để thử lại.';
  }
}
loadOwnerCatalog();

function showOwnerForm(publish) {
  publishMode = publish;
  const slug = /^\/vi\/([a-z0-9-]+)\/?$/.exec(location.pathname)?.[1];
  ownerSlug.value = slug || ownerSlugOf(mix.title);
  ownerSlug.readOnly = Boolean(slug);
  ownerMedia.value = '';
  $('owner-publish-fields').hidden = !publish;
  ownerMedia.required = publish;
  ownerFeedback.textContent = '';
  $('owner-dialog-title').textContent = publish ? 'Public bản phối' : 'Lưu bản thử';
  ownerSubmit.textContent = publish ? 'Public bản phối' : 'Lưu bản thử';
  ownerDialog.showModal();
}
$('owner-save').addEventListener('click',()=>showOwnerForm(false));
$('owner-publish').addEventListener('click',()=>showOwnerForm(true));
$('owner-cancel').addEventListener('click',()=>ownerDialog.close());

async function ownerRequest(url, options) {
  const response = await fetch(url,{...options,redirect:'error'});
  if (!response.ok) {
    const issue = await response.json().catch(()=>({}));
    throw Error(issue.error || (response.status===413?'Tệp vượt giới hạn tải lên của Cloudflare.':'Yêu cầu thất bại (HTTP '+response.status+').'));
  }
  return response.json();
}
function showPublished(path) {
  const link = document.createElement('a');
  link.href = path;
  link.textContent = 'Mở bản phối công khai';
  ownerResult.replaceChildren('Đã Public bản phối. ',link);
}

ownerForm.addEventListener('submit',async event => {
  event.preventDefault();
  if (ownerSubmit.disabled) return;
  const slug = ownerSlug.value.trim();
  const url = '/vi/api/drafts/'+encodeURIComponent(slug);
  const project = structuredClone(mix);
  const file = ownerMedia.files[0];
  const mime = file && mediaExtensions.get(file.name.split('.').at(-1).toLowerCase());
  if (publishMode && !mime) {
    ownerFeedback.textContent = 'Chọn tệp MP3, WAV, M4A hoặc MP4 thành phẩm.';
    return;
  }
  ownerSubmit.disabled = true;
  $('owner-cancel').disabled = true;
  ownerFeedback.textContent = 'Đang lưu bản thử…';
  try {
    const saved = await ownerRequest(url,{
      method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({project}),
    });
    if (publishMode) {
      ownerFeedback.textContent = 'Đang tải tệp và Public bản phối…';
      const released = await ownerRequest(url+'/publish',{
        method:'POST',headers:{'Content-Type':mime,'X-Studio-Draft':saved.revision},body:file,
      });
      showPublished(released.url);
    } else if (location.pathname!==saved.url) {
      location.assign(saved.url);
    } else {
      ownerResult.textContent = 'Đã lưu bản thử tại '+saved.url;
    }
    ownerDialog.close();
  } catch (error) {
    ownerFeedback.textContent = error.message;
  } finally {
    ownerSubmit.disabled = false;
    $('owner-cancel').disabled = false;
  }
});
ownerDialog.addEventListener('cancel',event=>{if(ownerSubmit.disabled) event.preventDefault();});
