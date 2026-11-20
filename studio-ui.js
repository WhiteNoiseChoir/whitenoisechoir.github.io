const studioGroups = {
  rain: tr('Mưa & sấm'),
  water: tr('Nước & đại dương'),
  wildlife: tr('Động vật'),
  fire: tr('Lửa & vật liệu'),
  wind: tr('Gió & thời tiết'),
  noise: tr('Màu tiếng ồn'),
  fan: tr('Quạt & thiết bị'),
  transit: tr('Phương tiện'),
  human: tr('Nhịp cơ thể'),
  hum: tr('Âm nền & rung'),
  music: studioEnglish ? 'Music instruments' : 'Nhạc cụ & âm nhạc',
  frequency: studioEnglish ? 'Frequency synthesis' : 'Âm tần tổng hợp',
  other: studioEnglish ? 'Other recordings' : 'Âm thanh khác',
};
const intentModes = {
  all: [['all','Tất cả']],
  sleep: [['all','Tất cả'],['rain','Mưa êm'],['noise','Nền tiếng ồn'],['music','Nhạc nhẹ']],
  relaxing: [['all','Tất cả'],['nature','Thiên nhiên'],['music','Âm nhạc'],['ambience','Không gian êm']],
  meditation: [['all','Tất cả'],['soundbath','Sound bath / nhạc cụ'],['drone','Drone / ambient'],['nature','Thiên nhiên'],['frequency','Âm tần tổng hợp']],
  focus: [['all','Tất cả'],['steady','Âm ổn định'],['nature','Thiên nhiên'],['music','Nhạc không lời']],
  baby: [['all','Gợi ý tổng quan'],['noise','Nền âm đều'],['calming','Shushing / womb-like'],['lullaby','Nhạc ru / piano'],['nature','Thiên nhiên êm']]
};
let libraryIntent='all',libraryMode='all';
// Relevance filter only; NEVER mark a recording as clinically safe or QA-approved.
function matchesIntent(asset,intent,mode){
  if(intent==='all') return true;
  const name=searchable([asset.name,asset.aliases,asset.group].filter(Boolean).join(' '));
  const group=asset.group||'other';
  const has=pattern=>pattern.test(name);
  const rain=group==='rain'&&!has(/thunder|storm|sam|hail|lightning/);
  const water=group==='water'&&!has(/crash|rushing|xi[ei]t|violent/);
  const music=group==='music';
  const ambient=group==='hum'||group==='fan'||group==='noise';
  const nature=rain||water||group==='wind'||group==='wildlife';
  if(intent==='baby'){
    if(has(/thunder|sam|storm|wolf|owl|coi|firework|alarm|shout|scream/) || group==='frequency') return false;
    const steady=group==='noise'&&!has(/violet|blue noise|tim|xanh duong|nhi[eễ]u radio/);
    const calming=group==='human'&&has(/womb|su[yị]t|shush|heart|nhip tim|breath|hoi tho|bung me/);
    const lullaby=music&&(has(/lullab|piano|music box|ru ngu|music/) || asset.babyIntent==='lullaby');
    const quietNature=rain||group==='wind'||water&&!has(/rush|crash|xi[eế]t/);
    return mode==='all' ? steady||calming||lullaby||quietNature||group==='fan'
      : mode==='noise' ? steady||group==='fan'
      : mode==='calming' ? calming
      : mode==='lullaby' ? lullaby
      : quietNature;
  }
  if(intent==='meditation'){
    const bath=music&&has(/bowl|gong|handpan|chime|bell|singing|harp|flute|sao|chuong|tambura|tanpura/);
    const drone=music&&has(/ambient|drone|pad|synth|organ|sustain/);
    if(mode==='frequency')return group==='frequency';
    if(mode==='soundbath')return bath;
    if(mode==='drone')return drone;
    if(mode==='nature')return nature;
    return nature||music||group==='frequency';
  }
  if(intent==='focus'){
    if(mode==='steady')return ambient||rain;
    if(mode==='nature')return nature;
    if(mode==='music')return music;
    return ambient||nature||music;
  }
  if(intent==='sleep'){
    if(mode==='rain')return rain;
    if(mode==='noise')return ambient;
    if(mode==='music')return music;
    return rain||ambient||music||group==='wind';
  }
  if(mode==='nature')return nature;
  if(mode==='music')return music;
  if(mode==='ambience')return ambient||rain||group==='wind';
  return nature||music||ambient;
}
const mixReview=node('p','','message mix-review');
mixReview.id='mix-review';
mixReview.hidden=true;
$('status').insertAdjacentElement('beforebegin',mixReview);
const originalFacets = [
  ['water', 'stream creek brook water suối rừng'], ['wildlife', 'frog amphibian ếch suối'],
  ['wildlife', 'bird robin chim hót'], ['wildlife', 'owl bird cú đêm'],
  ['wildlife', 'bee bumblebee insect côn trùng'], ['fire', 'fireplace campfire crackle lửa củi'],
  ['rain', 'rain window glass mưa kính'], ['wildlife', 'wolf howl chó sói'],
  ['transit', 'train railway đường sắt'], ['rain', 'rain leaves forest mưa lá rừng'],
  ['rain', 'rain tin roof mưa mái tôn'], ['rain', 'thunder storm sấm dông'],
  ['fire', 'wood creak gỗ kêu'], ['water', 'water drip droplet nước nhỏ giọt'],
  ['wildlife', 'wolf howl sói tru'],
];
const searchable = value => value.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replace(/đ/g, 'd');
let catalog = [];
function rebuildCatalog(){ catalog = assets.map((asset, i) => {
  const [group, aliases] = originalFacets[i] || [asset.group, asset.aliases];
  return {group, name:searchable(asset.name), text:searchable([asset.name, aliases, asset.aliases, asset.id, studioGroups[group]].join(' '))};
}); }
rebuildCatalog();
const undoStack = [];
const redoStack = [];
let selected = mix.tracks.length ? 0 : -1;
let zoom = 1;
let previewId = -1;
let previewTimer;
let previewRequest = 0;
let tonePreview = null;
const libraryPageSize = 80;
let libraryPage = 1;

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text) el.textContent = text;
  if (className) el.className = className;
  return el;
}

function button(text, action, label = text) {
  const el = node('button', text);
  el.type = 'button';
  el.setAttribute('aria-label', label);
  el.onclick = action;
  return el;
}

function saveLocal() {
  try { localStorage.setItem(projectStorageKey, JSON.stringify(mix)); }
  catch { $('status').textContent = tr('Trình duyệt không lưu được dự án. Có thể tải dự án JSON để giữ bản sao.'); }
  if (location.hash) {
    const url = new URL(location.href);
    url.hash = '';
    history.replaceState(null, '', url);
  }
}

function refreshHistory() {
  $('undo').disabled = !undoStack.length;
  $('redo').disabled = !redoStack.length;
}

function change(update, keepInspector = false) {
  if (exporting) return;
  const previous = structuredClone(mix);
  const resume = playing || loading;
  update();
  mix=restrictHomeMix(mix);
  if (JSON.stringify(previous) === JSON.stringify(mix)) return;
  stop();
  undoStack.push(previous);
  if (undoStack.length > 40) undoStack.shift();
  redoStack.length = 0;
  normalizeSelection();
  saveLocal();
  render(keepInspector);
  if (resume) play();
}

function restore(from, to) {
  if (exporting || !from.length) return;
  stop();
  to.push(structuredClone(mix));
  mix = restrictHomeMix(from.pop());
  soloTrack = null;
  normalizeSelection();
  saveLocal();
  render();
}

function normalizeSelection() {
  position = clamp(position, 0, mix.length);
  if (!mix.tracks.includes(soloTrack)) soloTrack = null;
  selected = mix.tracks.length ? clamp(selected, 0, mix.tracks.length - 1) : -1;
}

function selectTrack(index) {
  if (selected === index) return;
  selected = index;
  for (const row of $('tracks').children) row.classList.toggle('selected', Number(row.dataset.track) === index);
  renderInspector();
}

function addSource(index) {
  if (mix.tracks.length >= 32) {
    $('status').textContent = tr('Mỗi bản phối có tối đa 32 lớp.');
    return;
  }
  change(() => {
    selected = mix.tracks.length;
    mix.tracks.push({asset:index,...(assets[index].id?{assetRef:assets[index].id}:{}),
      start:Math.min(position,mix.length-.01),gain:assets[index].synthetic?.mode? .15:.35,
      loop:!!assets[index].synthetic,mute:false});
  });
  $('tracks').lastElementChild?.scrollIntoView({block: 'nearest', inline: 'nearest'});
}

function refreshPreviewButtons() {
  $('library').querySelectorAll('[data-preview]').forEach(control => {
    const id = Number(control.dataset.preview);
    control.textContent = id === previewId ? tr('Dừng') : tr('Nghe');
    control.setAttribute('aria-label', (id === previewId ? tr('Dừng nghe ') : tr('Nghe thử ')) + assets[id].name);
  });
}

function stopPreview() {
  if(tonePreview){
    try{tonePreview.source.stop();}catch{}
    tonePreview.context.close().catch(()=>{});
    tonePreview=null;
  }
  previewRequest++;
  clearTimeout(previewTimer);
  const audio = $('library-audio');
  audio.pause();
  audio.removeAttribute('src');
  audio.load();
  previewId = -1;
  refreshPreviewButtons();
}

async function audition(index) {
  const wasPreviewing = previewId === index;
  stopPreview();
  if (wasPreviewing) return;
  stop();
  $('library-status').textContent = '';
  previewId = index;
  refreshPreviewButtons();
  setSourceHealth(index,'loading','Đang kiểm tra bản nghe thử');
  const ticket = previewRequest;
  if(assets[index].synthetic){
    try{
      const Engine=window.AudioContext||window.webkitAudioContext;
      const engine=new Engine();
      const buffer=await decodeRecording(index,engine);
      if(ticket!==previewRequest){engine.close();return;}
      const source=engine.createBufferSource();
      source.buffer=buffer;source.loop=true;
      const volume=engine.createGain();volume.gain.value=.3;
      source.connect(volume);volume.connect(engine.destination);
      tonePreview={source,context:engine};await engine.resume();source.start();
      $('library-status').textContent=tr('Nghe thử tín hiệu tổng hợp · âm lượng nhỏ · không phải điều trị');
      previewTimer=setTimeout(stopPreview,8000);
    }catch(err){setSourceHealth(index,'failed',String(err?.message||err));}
    return;
  }
  const audio = $('library-audio');
  // Credentialed Access cookies are needed only for owner-initiated Music Private.
  if(assets[index]?.privateMusic===true) audio.crossOrigin='use-credentials';
  else audio.removeAttribute('crossorigin');
  for (const address of sourceAddresses(index)) {
    audio.src = address;
    try {
      await audio.play();
      if (ticket !== previewRequest) return;
      setSourceHealth(index,'ready','Bản nghe thử đã phát được từ '+new URL(address,location.href).hostname);
      previewTimer = setTimeout(stopPreview, 10000);
      return;
    } catch {
      if (ticket !== previewRequest) return;
    }
  }
  stopPreview();
  $('library-status').textContent = tr('Không phát được bản nghe thử này.');
  setSourceHealth(index,'failed','Không phát được các đường dẫn nguồn. Thử bấm Phát để kiểm tra thêm lỗi tải hoặc giải mã.');
}

function durationText(seconds) {
  return seconds < 60 ? Math.max(.1, Math.round(seconds * 10) / 10) + ' s' : format(seconds);
}

function renderLibrary() {
  const query = searchable($('library-query').value.trim());
  const words = query.split(/\s+/).filter(Boolean);
  const group = $('library-group').value;
  const matches = catalog.map((entry, i) => ({...entry, i}))
    .filter(entry=>!assets[entry.i].pending && (!group||group===entry.group)
      && matchesIntent(assets[entry.i],libraryIntent,libraryMode) && words.every(word=>entry.text.includes(word)));
  if (query) {
    const rank = entry => {
      const name = entry.name;
      if (name.startsWith(query)) return 0;
      if (name.includes(query)) return 1;
      return 2;
    };
    matches.sort((a, b) => rank(a) - rank(b));
  }
  const available = assets.filter(asset=>!asset.pending).length;
  $('library-count').textContent = matches.length.toLocaleString(document.documentElement.lang) + '/' + available.toLocaleString(document.documentElement.lang);
  $('library-more').hidden = matches.length <= libraryPage * libraryPageSize;
  $('library').replaceChildren();
  if (!matches.length) {
    $('library').append(node('p', tr('Không tìm thấy âm thanh phù hợp.'), 'message'));
    return;
  }
  for (const {i, group: category} of matches.slice(0,libraryPage * libraryPageSize)) {
    const asset = assets[i];
    const item = node('div', '', 'library-item');
    const name = node('div');
    name.append(node('strong', asset.name), node('small', studioGroups[category] + ' · ' + durationText(asset.duration)));
    // Source attribution remains visible in the public Studio for CC BY audio.
    // A license declaration is not listening QA or YouTube release clearance.
    if (asset.license) {
      const credit = node('small', asset.license + (asset.credit ? ' · ' + asset.credit : ''));
      credit.className = 'library-license';
      name.append(credit);
      if (asset.source && /^https:\/\//.test(asset.source)) {
        const source = document.createElement('a');
        source.href = asset.source;
        source.textContent = studioEnglish ? 'Source & rights' : 'Nguồn và giấy phép';
        source.target = '_blank';
        source.rel = 'noopener noreferrer';
        source.className = 'library-license-source';
        name.append(source);
      }
    }
    const controls = node('div', '', 'library-buttons');
    const preview = button(tr('Nghe'), () => audition(i), tr('Nghe thử ') + asset.name);
    preview.dataset.preview = i;
    const add = button('+', () => addSource(i), tr('Thêm ') + asset.name);
    add.className = 'add-source';
    add.title = tr('Thêm tại vị trí phát');
    controls.append(preview, add);
    item.append(name, controls);
    $('library').append(item);
  }
  refreshPreviewButtons();
}

function seekFromPointer(event, element) {
  const bounds = element.getBoundingClientRect();
  if (bounds.width > 0) locate((event.clientX - bounds.left) / bounds.width * mix.length);
}

// Reordering layers changes only their display/array order; it never changes
// playback times, source IDs, gains, fades or other audio-mix parameters.
function reorderTrack(from, to, focusHandle = false) {
  if (exporting || from === to || from < 0 || to < 0 ||
      from >= mix.tracks.length || to >= mix.tracks.length) return false;
  change(() => {
    const [moving] = mix.tracks.splice(from, 1);
    mix.tracks.splice(to, 0, moving);
    selected = to;
  });
  if (focusHandle) $('tracks').children[to]?.querySelector('.track-reorder')?.focus({preventScroll: true});
  return true;
}
function attachTrackReorder(handle, row, index, label) {
  let drag = null;
  const container = $('timeline-scroll');
  const rows = () => Array.from($('tracks').querySelectorAll('.timeline-row'));
  const dropTarget = y => {
    const all = rows();
    for (let i = 0; i < all.length; i++) {
      const rect = all[i].getBoundingClientRect();
      if (y < rect.top + rect.height / 2) return i;
    }
    return Math.max(0, all.length - 1);
  };
  const highlight = target => {
    rows().forEach((item, i) => {
      item.classList.toggle('reorder-origin', i === index);
      item.classList.toggle('reorder-target', i === target && i !== index);
    });
  };
  function moveVisual() {
    if (!drag) return;
    drag.to = dropTarget(drag.y);
    if (drag.ghost) {
      drag.ghost.textContent = (index + 1) + ' → ' + (drag.to + 1) + ' · ' + label;
      drag.ghost.style.top = drag.y + 12 + 'px';
      drag.ghost.style.left = drag.x + 12 + 'px';
    }
    highlight(drag.to);
  }
  function autoScroll() {
    if (!drag) return;
    if (drag.started) {
      const bounds = container.getBoundingClientRect();
      const top = bounds.top + 42; // Keep the sticky time ruler clear.
      const bottom = bounds.bottom - 26;
      const speed = drag.y < top ? -Math.min(18, 5 + (top - drag.y) / 4)
        : drag.y > bottom ? Math.min(18, 5 + (drag.y - bottom) / 4) : 0;
      if (speed) container.scrollTop += speed;
      moveVisual();
    }
    drag.frame = requestAnimationFrame(autoScroll);
  }
  function cleanup() {
    const state = drag;
    if (!state) return null;
    cancelAnimationFrame(state.frame);
    drag = null;
    handle.classList.remove('reordering');
    handle.removeAttribute('aria-grabbed');
    row.classList.remove('reorder-origin');
    rows().forEach(item => item.classList.remove('reorder-origin','reorder-target'));
    state.ghost?.remove();
    return state;
  }
  handle.onpointerdown = event => {
    if (event.button !== 0 || exporting || mix.tracks.length < 2) return;
    event.preventDefault();
    const ghost = node('div', '', 'track-reorder-ghost');
    ghost.setAttribute('aria-hidden','true');
    document.body.append(ghost);
    drag = {id:event.pointerId,x:event.clientX,y:event.clientY,y0:event.clientY,to:index,started:false,ghost,frame:0};
    handle.classList.add('reordering');
    handle.setAttribute('aria-grabbed','true');
    selectTrack(index);
    moveVisual();
    try {handle.setPointerCapture(event.pointerId);} catch {}
    drag.frame=requestAnimationFrame(autoScroll);
  };
  handle.onpointermove = event => {
    if (!drag || drag.id !== event.pointerId) return;
    drag.x = event.clientX;drag.y = event.clientY;
    if (!drag.started && Math.abs(event.clientY - drag.y0) > 5) drag.started = true;
    if (drag.started) moveVisual();
    event.preventDefault();
  };
  handle.onpointerup = event => {
    if (!drag || drag.id !== event.pointerId) return;
    const wasMoved=drag.started;
    const target=wasMoved ? dropTarget(event.clientY) : index;
    cleanup();
    try {if(handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);} catch {}
    if (wasMoved) reorderTrack(index,target);
    else selectTrack(index);
  };
  handle.onpointercancel = cleanup;
  handle.onlostpointercapture = cleanup;
  handle.onkeydown = event => {
    if (exporting || !event.altKey || !['ArrowUp','ArrowDown'].includes(event.key)) return;
    event.preventDefault();
    const target=clamp(index+(event.key==='ArrowUp'?-1:1),0,mix.tracks.length-1);
    reorderTrack(index,target,true);
  };
  handle.onclick = event => {event.preventDefault();}; // Prevent a synthetic post-drag click.
}
function trackRow(track, index) {
  const asset = assets[track.asset];
  const row = node('div', '', 'timeline-row');
  row.dataset.track = index;
  row.dataset.group = catalog[track.asset].group;
  row.classList.toggle('selected', selected === index);
  row.classList.toggle('muted-row', track.mute || Boolean(soloTrack && soloTrack !== track));
  const label = track.label || asset.name;
  const rail = node('div', '', 'track-column');
  const select = button(label, () => selectTrack(index), tr('Chọn lớp ') + (index + 1) + ': ' + label);
  select.className = 'track-select';
  select.title = label;
  const reorder = button('⠿', () => {}, studioEnglish
    ? 'Reorder track ' + (index + 1) + ': ' + label
    : 'Sắp xếp lớp ' + (index + 1) + ': ' + label);
  reorder.className = 'track-reorder';
  reorder.title = studioEnglish
    ? 'Drag up or down to reorder this sound. Alt+↑/↓ also works.'
    : 'Kéo lên hoặc xuống để đổi vị trí lớp. Có thể dùng Alt+↑/↓.';
  reorder.setAttribute('aria-keyshortcuts','Alt+ArrowUp Alt+ArrowDown');
  attachTrackReorder(reorder, row, index, label);
  const mute = button('M', () => change(() => { track.mute = !track.mute; }), tr('Tắt tiếng lớp ') + (index + 1));
  mute.className = 'track-mute';
  mute.setAttribute('aria-pressed', track.mute);
  rail.append(reorder, select, mute);

  const lane = node('div', '', 'lane');
  lane.onclick = event => { if (event.target === lane) seekFromPointer(event, lane); };

  // Sound identity is already visible in the left column. Clips are visual
  // signal blocks, with full labels available through accessible metadata.
  let suppressClick = false;
  const clip = button('', event => {
    if (suppressClick) { suppressClick = false; event.preventDefault(); return; }
    selectTrack(index);
  }, (studioEnglish ? 'Move sound clip: ' : 'Kéo đoạn âm thanh: ') + label);
  clip.className = 'clip' + (track.loop ? ' looped' : '');
  clip.dataset.track = index;
  clip.setAttribute('aria-keyshortcuts', 'ArrowLeft ArrowRight');
  clip.setAttribute('aria-description', studioEnglish
    ? 'Drag left or right to change its start time. Arrow keys move one second; Shift plus arrow moves 0.1 second.'
    : 'Kéo trái/phải để đổi thời điểm bắt đầu. Phím mũi tên dịch 1 giây; Shift và mũi tên dịch 0,1 giây.');
  const visual = node('span', '', 'clip-signal');
  visual.setAttribute('aria-hidden', 'true');
  for (let i = 0; i < 5; i++) visual.append(node('span', '', 'clip-signal-bar'));
  clip.append(visual);

  const place = time => {
    const length = clipDuration({...track, start: time}, asset.duration, mix.length);
    clip.hidden = length <= 0;
    clip.style.left = 100 * Math.min(time, mix.length) / mix.length + '%';
    clip.style.width = 100 * length / mix.length + '%';
    const positionText = format(time) + ' · ' + durationText(length);
    clip.title = label + ' · ' + positionText;
  };
  place(track.start);
  let drag;
  clip.onpointerdown = event => {
    if (event.button !== 0 || exporting) return;
    suppressClick = false;
    drag = {id: event.pointerId, x: event.clientX, start: track.start, target: track.start, moved: false};
    selectTrack(index);
    try { clip.setPointerCapture(event.pointerId); } catch {}
  };
  clip.onpointermove = event => {
    if (!drag || drag.id !== event.pointerId) return;
    if (!drag.moved && Math.abs(event.clientX - drag.x) < 4) return;
    drag.moved = true;
    const scale = event.shiftKey ? 1 : 10;
    const time = drag.start + (event.clientX - drag.x) * mix.length / Math.max(1, lane.getBoundingClientRect().width);
    drag.target = clamp(Math.round(time * scale) / scale, 0, mix.length - .01);
    clip.classList.add('dragging');
    clip.setAttribute('aria-grabbed', 'true');
    place(drag.target);
    event.preventDefault();
  };
  clip.onpointerup = event => {
    if (!drag || drag.id !== event.pointerId) return;
    const {target, moved} = drag;
    drag = undefined;
    clip.classList.remove('dragging');
    clip.removeAttribute('aria-grabbed');
    if (moved) {
      suppressClick = true;
      if (target !== track.start) change(() => { selected = index; track.start = target; });
      else place(track.start);
    } else place(track.start);
    try { if (clip.hasPointerCapture(event.pointerId)) clip.releasePointerCapture(event.pointerId); } catch {}
  };
  clip.onpointercancel = () => {
    drag = undefined;
    clip.classList.remove('dragging');
    clip.removeAttribute('aria-grabbed');
    place(track.start);
  };
  clip.onkeydown = event => {
    if (!['ArrowLeft','ArrowRight'].includes(event.key) || exporting) return;
    event.preventDefault();
    const step = event.shiftKey ? .1 : 1;
    const direction = event.key === 'ArrowRight' ? 1 : -1;
    const target = clamp(Math.round((track.start + direction * step) * 10) / 10, 0, mix.length - .01);
    if (target !== track.start) {
      change(() => { selected = index; track.start = target; });
      $('tracks').children[index]?.querySelector('.clip')?.focus({preventScroll: true});
    }
  };
  lane.append(clip, node('div', '', 'needle'));
  row.append(rail, lane);
  return row;
}

function renderTimeline() {
  const canvas = $('timeline-canvas');
  const ruler = $('time-ruler');
  const labelWidth = parseFloat(getComputedStyle(canvas).getPropertyValue('--track-column'));
  const width = $('timeline-scroll').clientWidth;
  canvas.style.width = zoom === 1 ? '100%' : Math.max(width, (width - labelWidth) * zoom + labelWidth) + 'px';
  const divisions = Math.min(24, zoom * 4);
  canvas.style.setProperty('--grid-step', 100 / divisions + '%');
  ruler.replaceChildren();
  for (let i = 0; i < divisions; i++) {
    const tick = node('div', '', 'ruler-tick');
    tick.style.left = 100 * i / divisions + '%';
    tick.append(node('span', format(mix.length * i / divisions)));
    ruler.append(tick);
  }
  $('tracks').replaceChildren(...mix.tracks.map(trackRow));
  if (!mix.tracks.length) $('tracks').append(node('div', tr('Chọn âm thanh trong thư viện để bắt đầu.'), 'timeline-empty'));
  $('layer-count').textContent = mix.tracks.length + tr(' lớp');
  display();
}

function addNumber(fields, label, track, key, config) {
  const wrapper = node('label', label);
  const input = node('input');
  input.type = 'number';
  input.min = config.min;
  input.max = config.max;
  input.step = config.step;
  const factor = config.factor || 1;
  const formatValue = () => track[key] === undefined ? '' : Number((track[key] * factor).toFixed(3));
  input.value = formatValue();
  if (config.placeholder) input.placeholder = config.placeholder;
  input.onchange = () => {
    const raw = input.value.trim();
    const value = raw === '' ? config.defaultValue : Number(raw);
    change(() => {
      if (value === undefined) delete track[key];
      else if (Number.isFinite(value)) track[key] = clamp(value, config.min, config.max) / factor;
    }, true);
    input.value = formatValue();
  };
  wrapper.append(input);
  fields.append(wrapper);
}

function removeSelected() {
  if (selected < 0) return;
  change(() => { mix.tracks.splice(selected, 1); });
}

function renderInspector() {
  const inspector = $('inspector');
  inspector.replaceChildren();
  const track = mix.tracks[selected];
  if (!track) {
    inspector.append(node('p', tr('Chọn một lớp trên dòng thời gian.'), 'message'));
    return;
  }
  const asset = assets[track.asset];
  const source = node('div', '', 'inspector-source');
  source.append(node('strong', asset.name));
  if (asset.source) {
    const link = node('a', asset.license ? asset.license + tr(' · Nguồn') : tr('Xem nguồn'));
    link.href = asset.source;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    source.append(link);
    if(asset.credit) source.append(node('p',asset.credit,'message'));
    if(asset.licenseUrl){const rights=node('a',asset.license);rights.href=asset.licenseUrl;rights.target='_blank';rights.rel='noopener noreferrer';source.append(rights);}
  } else if (asset.license) source.append(node('small', asset.license));
  const actions = node('div', '', 'inspector-actions');
  const mute = button(tr('Tắt tiếng'), () => change(() => { track.mute = !track.mute; }));
  mute.setAttribute('aria-pressed', track.mute);
  const loop = button(tr('Lặp'), () => change(() => { track.loop = !track.loop; }));
  loop.setAttribute('aria-pressed', track.loop);
  const solo = button('Solo', () => {
    const resume = playing || loading;
    stop();
    soloTrack = soloTrack === track ? null : track;
    render();
    if (resume) play();
  }, tr('Solo để nghe thử'));
  solo.setAttribute('aria-pressed', soloTrack === track);
  solo.title = tr('Solo chỉ áp dụng khi nghe thử');
  const duplicate = button(tr('Nhân bản'), () => {
    if (mix.tracks.length >= 32) { $('status').textContent = tr('Mỗi bản phối có tối đa 32 lớp.'); return; }
    change(() => { mix.tracks.splice(selected + 1, 0, structuredClone(track)); selected++; });
  });
  actions.append(mute, loop, solo, duplicate, button(tr('Xóa'), removeSelected, tr('Xóa lớp đã chọn')));

  const fields = node('div', '', 'inspector-fields');
  const name = node('label', tr('Tên lớp'), 'full');
  const label = node('input');
  label.type = 'text';
  label.maxLength = 100;
  label.value = track.label || '';
  label.placeholder = asset.name;
  label.onchange = () => change(() => {
    if (label.value.trim()) track.label = label.value.trim();
    else delete track.label;
  }, true);
  name.append(label);
  fields.append(name);
  const seconds = {min: 0, max: 10800, step: .1};
  addNumber(fields, tr('Bắt đầu (giây)'), track, 'start', {...seconds, max: mix.length, defaultValue: 0});
  addNumber(fields, tr('Âm lượng (%)'), track, 'gain', {min: 0, max: 100, step: 1, factor: 100, defaultValue: 0});
  addNumber(fields, tr('Bỏ đầu nguồn (giây)'), track, 'offset', {...seconds, max: Math.max(0, asset.duration - .01), placeholder: '0'});
  addNumber(fields, tr('Độ dài đoạn (giây)'), track, 'duration', {...seconds, min: .01, placeholder: tr('Tự động')});
  addNumber(fields, tr('Fade in (giây)'), track, 'fadeIn', {...seconds, placeholder: '0'});
  addNumber(fields, tr('Fade out (giây)'), track, 'fadeOut', {...seconds, placeholder: '0'});
  const stereo = {min: -100, max: 100, step: 1, factor: 100, placeholder: '0'};
  addNumber(fields, tr('Pan đầu (%)'), track, 'pan', stereo);
  addNumber(fields, tr('Pan cuối (%)'), track, 'panEnd', {...stereo, placeholder: tr('Theo pan đầu')});
  addNumber(fields, tr('Cắt tần số thấp (Hz)'), track, 'highpass', {min: 20, max: 20000, step: 10, placeholder: tr('Tắt')});
  addNumber(fields, tr('Cắt tần số cao (Hz)'), track, 'lowpass', {min: 80, max: 20000, step: 10, placeholder: tr('Tắt')});
  if(asset.synthetic){
    const panel=node('div','','frequency-track-panel');
    const modeLabel=node('label','Phương pháp tạo tín hiệu');
    const mode=document.createElement('select');mode.id='frequency-track-mode';
    for(const [key,name] of [['pure','Pure tone'],['binaural','Binaural · tai nghe'],['monaural','Monaural beats'],['isochronic','Isochronic']])
      mode.append(new Option(name,key));
    mode.value=asset.synthetic.mode;modeLabel.append(mode);panel.append(modeLabel);
    const field=(id,name,value)=>{
      const label=node('label',name),input=document.createElement('input');
      input.type='number';input.min=id==='frequency-track-beat'?'0.5':'40';
      input.max=id==='frequency-track-beat'?'30':'1500';input.step='.1';input.value=value;input.id=id;
      label.append(input);panel.append(label);return input;
    };
    const carrier=field('frequency-track-carrier','Tần số nền (Hz)',asset.synthetic.carrierHz);
    const beat=field('frequency-track-beat','Nhịp chênh (Hz)',asset.synthetic.beatHz||6);
    const updateEnabled=()=>{beat.disabled=mode.value==='pure';};
    mode.onchange=updateEnabled;updateEnabled();
    const apply=button('Áp dụng tần số cho lớp này',()=>{
      const id=assetForGenerated({mode:mode.value,carrierHz:Number(carrier.value),beatHz:Number(beat.value)});
      if(!Number.isInteger(id)){$('status').textContent='Tần số không hợp lệ (40–1500 Hz; nhịp 0,5–30 Hz).';return;}
      change(()=>{track.asset=id;delete track.assetRef;track.loop=true;});
      rebuildCatalog();refreshLibraryGroups();renderLibrary();
    });
    apply.id='frequency-track-apply';panel.append(apply);
    panel.append(node('p','Điều chỉnh lớp tổng hợp cục bộ. Không ghi file R2 và không bảo đảm tác dụng sinh lý.','hint muted'));
    fields.append(panel);
  }
  fields.append(node('p', tr('Pan: −100 trái, 0 giữa, +100 phải. Solo chỉ dùng khi nghe thử. Fade tự giới hạn tối đa nửa độ dài lớp; gain không phải LUFS.'), 'hint muted'));
  inspector.append(source, actions, fields);
}

function render(keepInspector = false) {
  $('title').value = mix.title;
  $('minutes').value = homepageWavOnly?10:mix.length / 60;
  if ($('video-prompt')) $('video-prompt').value = mix.videoPrompt || '';
  $('seek').max = mix.length;
  $('master').value = Math.round((mix.master ?? 1) * 100);
  $('master-value').value = $('master').value + '%';
  renderTimeline();
  renderSourceDiagnostics();
  const review=$('mix-review');
  if(review){
    const baby=mix.intent==='baby';
    const alerts=baby?mix.tracks.filter(t=>{
      const source=assets[t.asset]||{};
      return source.synthetic||/thunder|storm|sấm|wolf|sói|alarm|crash/i.test(source.name||'');
    }).length:0;
    review.hidden=!baby;
    if(baby)review.textContent='Baby QA: chỉ dùng để thử nghiệm, không bảo đảm mức âm an toàn. '+(alerts
      ? alerts+' lớp có nguy cơ âm tần/sự kiện đột ngột cần xem lại. '
      : 'Chưa đo SPL tại vị trí trẻ. ')+'Giữ loa xa trẻ, giảm âm lượng, giới hạn thời gian và kiểm nghe điểm lặp.';
  }
  if (!keepInspector) renderInspector();
  refreshHistory();
  syncWorkflow();
}

function replaceProject(project) {
  change(() => { mix = project; soloTrack = null; selected = 0; position = 0; });
}

$('play').onclick = () => play();
$('reset').onclick = () => locate(0);
$('tail').onclick = () => {
  stop();
  position = Math.max(0, mix.length - 5);
  display();
  play(true);
};
$('seek').oninput = () => locate(Number($('seek').value));
$('time-ruler').onclick = event => seekFromPointer(event, $('time-ruler'));
$('zoom').onchange = () => { zoom = Number($('zoom').value); renderTimeline(); };
$('title').onchange = () => change(() => { mix.title = $('title').value.trim() || tr('Bản phối chưa đặt tên'); });
$('minutes').onchange = () => {
  if(homepageWavOnly){$('minutes').value='10';return;}
  change(() => { mix.length = clamp(Number($('minutes').value) * 60, dualSceneSlot==='A'?1:6, 10800); });
};
if ($('video-prompt')) $('video-prompt').onchange = () => change(() => { mix.videoPrompt = $('video-prompt').value; });
$('master').oninput = () => {
  $('master-value').value = $('master').value + '%';
  if (monitorGain) monitorGain.gain.value = Number($('master').value) / 100;
};
$('master').onchange = () => change(() => { mix.master = Number($('master').value) / 100; });
$('undo').onclick = () => restore(undoStack, redoStack);
$('redo').onclick = () => restore(redoStack, undoStack);
// Only owner-approved, finished MP4+WAV mixes appear in the public picker.
// Existing internal presets remain parsable for historical project links but
// are intentionally never presented to website visitors.
function mountPublishedPicker(){
  document.querySelectorAll('.preset-picker').forEach(el=>el.remove());
  const host=document.querySelector('.project-actions');
  if(!host)return;
  fetch('/data/published-mixes.json',{cache:'no-store'}).then(async r=>{
    if(!r.ok)throw Error('Published list unavailable');
    const rows=await r.json();
    if(!Array.isArray(rows))return;
    const ready=rows.filter(r=>r.status==='published' && r.ownerApproved===true && r.productionComplete===true && r.qaApproved===true && /^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$/.test(r.slug)
      && r.video?.url && r.video?.poster && r.audio?.url && r.audio?.wavUrl);
    if(!ready.length)return;
    const label=node('label','','preset-picker');
    const caption=node('span',studioEnglish?'Published mixes':'Bản đã công khai');
    const select=node('select');
    select.id='published-picker';
    select.setAttribute('aria-label',studioEnglish?'Open a published mix':'Mở bản phối đã công khai');
    select.append(new Option(studioEnglish?'Choose a published mix':'Chọn bản đã Public',''));
    ready.forEach(r=>select.append(new Option(r.title,r.slug)));
    select.onchange=()=>{
      const slug=select.value;
      if(ready.some(r=>r.slug===slug))location.assign('/'+slug+'/');
    };
    label.append(caption,select);
    host.prepend(label);
  }).catch(()=>{}); // Empty or unavailable feed means no published picker.
}
mountPublishedPicker();
$('clear').onclick = () => {
  $('clear').closest('details').open = false;
  replaceProject({title: tr('Bản phối chưa đặt tên'), length: homepageWavOnly?600:1800, tracks: []});
};
$('share').onclick = async () => {
  const url = new URL(location.href);
  url.hash = 'mix=' + encodeURIComponent(JSON.stringify(mix));
  history.replaceState(null, '', url);
  try { await navigator.clipboard.writeText(url.href); $('status').textContent = tr('Đã sao chép liên kết bản phối.'); }
  catch { $('status').textContent = tr('Sao chép liên kết bản phối từ thanh địa chỉ.'); }
};
$('save-project').onclick = () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(projectForDownload(mix), null, 2)], {type: 'application/json'}));
  const link = node('a');
  link.href = url;
  link.download = (mix.title.replace(/[\\/:*?"<>|]/g, '-').trim() || 'ban-phoi') + '.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  $('save-project').closest('details').open = false;
};
// Owner-generated AI Music is fetched only from the Access-protected Worker.
// Never load raw private R2 into public script data or fall back to media R2.
let ownerMusicLoadPromise=null;
async function loadOwnerMusic({refresh=false}={}) {
  if(studioEnglish || location.pathname.replace(/\/+$/,'')!=="/vi")
    return {count:0,added:0};
  if(refresh)ownerMusicLoadPromise=null;
  if(!ownerMusicLoadPromise) {
    ownerMusicLoadPromise=(async()=>{
      const {retrieveOwnerMusic,registerOwnerMusicRows}=
        await import("/studio-private-music-optin.mjs?v=owner-ai-20261119");
      const result=await retrieveOwnerMusic({enabled:true,pageOrigin:location.origin});
      const added=registerOwnerMusicRows(result.rows,{
        assets,rawAssetIndex,rebuildCatalog,refreshLibraryGroups,renderLibrary,render
      });
      return {count:result.rows.length,added};
    })().catch(err=>{ownerMusicLoadPromise=null;throw err});
  }
  return ownerMusicLoadPromise;
}
$('open-project').onchange = async () => {
  const input = $('open-project');
  const file = input.files[0];
  input.value = '';
  if (!file) return;
  try {
    if (file.size > 100000) throw Error();
    const raw = JSON.parse(await file.text());
    const hasOwnerAI = Array.isArray(raw.tracks) && raw.tracks.some(t =>
      typeof t?.assetKey==="string" &&
      t.assetKey.startsWith("internal/owner-generated/flow-music/inbox/"));
    if(hasOwnerAI)await loadOwnerMusic({refresh:true});
    const project = normalizeProject(raw);
    if (project.tracks.length !== raw.tracks.length) throw Error();
    replaceProject(project);
    const legacy=raw.tracks.some(t=>!t.generated&&!t.assetKey&&!t.assetRef);
    $('status').textContent = legacy
      ? tr('Đã mở JSON cũ theo ID số: vui lòng xác minh từng nguồn âm thanh trước khi xuất WAV.')
      : tr('Đã mở dự án với định danh nguồn ổn định.');
    input.closest('details').open = false;
  } catch {
    $('status').textContent = tr('Tệp dự án không hợp lệ hoặc chứa nguồn âm thanh chưa có trong thư viện. Nếu là nhạc AI riêng tư, hãy đăng nhập Music Gateway rồi nhấn Đồng bộ nhạc AI.');
  }
};
// Intent-aware discovery is a local catalog filter; the private metadata index is not exposed here.
(function setupIntentAudioControls(){
  const group=$('library-group');
  const container=node('div','','intent-controls');
  const label=node('label',studioEnglish?'Listening intent':'Mục đích nghe');
  const intent=document.createElement('select');
  intent.id='library-intent';
  for(const [id,title] of [['all','Tất cả'],['sleep','Sleep / Ngủ'],['relaxing','Relaxing / Thư giãn'],
    ['meditation','Meditation / Thiền'],['focus','Focus / Tập trung'],['baby','Baby Sleep & Calming']])
    intent.append(new Option(title,id));
  label.append(intent);
  const modeLabel=node('label',studioEnglish?'Style':'Phong cách âm');
  const mode=document.createElement('select');mode.id='library-intent-mode';modeLabel.append(mode);
  const warning=node('p','','intent-caution');
  warning.textContent='Bộ lọc chỉ gợi ý nguồn đã hiển thị trong Studio; không xác nhận QA hay quyền phát hành.';
  function updateModes(){
    mode.replaceChildren(...intentModes[libraryIntent].map(([id,title])=>new Option(title,id)));
    libraryMode='all'; mode.value='all';
    warning.textContent=libraryIntent==='baby'
      ? 'Baby: chỉ là gợi ý sơ bộ; không bảo đảm an toàn thính giác. Giữ âm lượng thiết bị thấp, đặt nguồn phát xa trẻ và kiểm tra thời lượng nghe.'
      : libraryIntent==='meditation'
      ? 'Meditation: âm tần tổng hợp cần kiểm tra stereo và tần số, không phải liệu pháp chữa bệnh.'
      : 'Gợi ý theo intent, chưa xác nhận nghe QA hoặc quyền phát hành. Metadata private không tải vào trình duyệt.';
    libraryPage=1;renderLibrary();
  }
  intent.onchange=()=>{libraryIntent=intent.value;updateModes();};
  mode.onchange=()=>{libraryMode=mode.value;libraryPage=1;renderLibrary();};
  container.append(label,modeLabel,warning);
  group.insertAdjacentElement('afterend',container);
  updateModes();
  const lab=document.createElement('details');lab.className='frequency-lab';
  lab.innerHTML='<summary>Acoustic Lab · Tạo âm tần</summary>';
  const body=node('div','','frequency-lab-fields');
  const make=(name,type,min,max,step,value)=>{
    const label=node('label',name);
    const input=document.createElement('input');input.type=type;
    if(min!==null)input.min=min;if(max!==null)input.max=max;
    if(step!==null)input.step=step;input.value=value;label.append(input);body.append(label);return input;
  };
  const typeLabel=node('label','Loại tín hiệu');
  const type=document.createElement('select');
  for(const [id,title] of [['pure','Pure tone'],['binaural','Binaural beats · cần tai nghe'],
    ['monaural','Monaural beats'],['isochronic','Isochronic tones']])type.append(new Option(title,id));
  typeLabel.append(type);body.append(typeLabel);
  const carrier=make('Tần số nền (Hz)','number',40,1500,.1,432);
  const beat=make('Nhịp chênh (Hz)','number',.5,30,.1,6);
  beat.disabled=true;
  type.onchange=()=>{beat.disabled=type.value==='pure';};
  const buttonEl=button('Thêm âm tần vào timeline',()=>{
    if(libraryIntent==='baby'){ $('status').textContent='Baby Mode không thêm tín hiệu âm tần tự động.';return;}
    const id=assetForGenerated({mode:type.value,carrierHz:Number(carrier.value),beatHz:Number(beat.value)});
    if(!Number.isInteger(id)){ $('status').textContent='Tần số phải từ 40–1500 Hz, bước 0,1 Hz; nhịp 0,5–30 Hz.';return;}
    rebuildCatalog();refreshLibraryGroups();addSource(id);renderLibrary();
    $('status').textContent='Đã tạo tín hiệu cục bộ. Kiểm tra bằng tai nghe và đo WAV; không có file R2 được tạo.';
  });
  body.append(buttonEl,node('p','Mỗi tín hiệu là sóng tổng hợp cục bộ 10 giây nối vòng, không phải tài sản âm thanh đã nhập R2 hoặc chứng nhận hiệu quả y khoa.','hint muted'));
  lab.append(body);container.insertAdjacentElement('afterend',lab);
  const babyDemo=button('Bản mẫu Baby 10 phút (cần QA)',()=>{
    if(!window.confirm('Tạo bản mẫu Baby mới? Dự án đang mở sẽ được thay thế; hãy tải JSON trước khi đổi.'))return;
    const pink=assets.findIndex(x=>x.key==='audio/pink-noise.mp3');
    const rain=assets.findIndex(x=>x.key==='audio/light-rain-real.mp3');
    if(pink<0||rain<0){$('status').textContent='Thiếu nguồn Baby mẫu trong catalog.';return;}
    const project={title:'Gentle Night Nursery · Draft / Needs QA',intent:'baby',length:600,master:.35,tracks:[
      {asset:pink,start:0,duration:600,gain:.16,loop:true,mute:false,fadeIn:2,fadeOut:2,label:'Pink Noise · nhẹ'},
      {asset:rain,start:0,duration:600,gain:.085,loop:true,mute:false,fadeIn:3,fadeOut:3,label:'Mưa nhẹ · nền'}
    ]};
    replaceProject(project);
    $('status').textContent='Bản mẫu chỉ dành để nghe QA, không phải chứng nhận an toàn cho trẻ.';
  });
  babyDemo.className='baby-demo-action';
  container.append(babyDemo);
  const toggleBaby=()=>{babyDemo.hidden=libraryIntent!=='baby';lab.hidden=libraryIntent==='baby';};
  const originalChange=intent.onchange;
  intent.onchange=()=>{originalChange();toggleBaby();};
  toggleBaby();
})();

$('library-query').oninput = $('library-group').onchange = () => {libraryPage=1;renderLibrary();};
$('library-more').onclick=()=>{libraryPage++;renderLibrary();};
$('library-audio').onended = stopPreview;
function refreshLibraryGroups(){
const current=$('library-group').value;
$('library-group').replaceChildren($('library-group').options[0]);
for (const [key, title] of Object.entries(studioGroups)) {
  if (!catalog.some(item => item.group === key)) continue;
  const option = node('option', title);
  option.value = key;
  $('library-group').append(option);
}
$('library-group').value=current;
}
refreshLibraryGroups();
window.addEventListener('hashchange', () => {
  stop();
  mix = restrictHomeMix(readMix());
  position = 0;
  selected = 0;
  soloTrack = null;
  undoStack.length = 0;
  redoStack.length = 0;
  normalizeSelection();
  render();
});
window.addEventListener('resize', () => { if (zoom !== 1) renderTimeline(); });
document.addEventListener('keydown', event => {
  if (event.defaultPrevented || exporting || event.target.closest?.('input, textarea, select, button, summary, [contenteditable]')) return;
  if (event.key === '/' && !event.ctrlKey && !event.metaKey) { event.preventDefault(); $('library-query').focus(); }
  else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
    event.preventDefault();
    if (event.shiftKey) restore(redoStack, undoStack);
    else restore(undoStack, redoStack);
  } else if (event.code === 'Space' && !event.altKey) { event.preventDefault(); play(); }
  else if (event.key === 'Delete' && selected >= 0) { event.preventDefault(); removeSelected(); }
});
renderLibrary();
render();
// Explicitly opt-in to Cloudflare Access-protected Music only on /vi/?private-music=1.
// No cross-site request is made until the owner clicks the import button.
// The Nature catalog, existing mixer and all production URLs remain unchanged.
(function setupPrivateMusicAudition() {
  const enabled = !studioEnglish && location.pathname.replace(/\/+$/, '') === '/vi' &&
    new URLSearchParams(location.search).get('private-music') === '1';
  if (!enabled) return;
  const gateway='https://wnc-private-music-gateway.whitescreen-dev.workers.dev/v1/catalog';
  const holder=document.createElement('div');
  holder.className='private-music-optin';
  holder.style.cssText='padding:12px;margin:12px 0;border:1px solid #7775;border-radius:8px;';
  const caption=document.createElement('p');
  caption.textContent='Music Private — chỉ nghe thử và phối nội bộ, chưa duyệt xuất bản.';
  const auth=document.createElement('a');
  auth.href=gateway;auth.target='_blank';auth.rel='noopener noreferrer';
  auth.textContent='1. Đăng nhập Music Gateway (mở tab riêng)';
  const load=document.createElement('button');
  load.type='button';load.textContent='2. Tải 2 bản Music Private';
  const status=document.createElement('p');status.setAttribute('role','status');
  status.setAttribute('aria-live','polite');status.textContent='Chưa kết nối Music Gateway.';
  holder.append(caption,auth,load,status);
  $('library-status').insertAdjacentElement('beforebegin',holder);
  load.addEventListener('click',async()=>{
    load.disabled=true;
    status.textContent='Đang xác thực và đọc catalog Music Private…';
    try {
      const {retrievePrivateMusic,registerMusicRows}=await import('/studio-private-music-optin.mjs?v=ws4-20261117');
      const result=await retrievePrivateMusic({enabled:true,pageOrigin:location.origin});
      const newlyAdded=registerMusicRows(result.rows,{
        assets,rawAssetIndex,rebuildCatalog,refreshLibraryGroups,renderLibrary,render
      });
      status.textContent='Music Private: '+result.rows.length+' bản được xác minh; '+newlyAdded+
        ' bản mới trong thư viện. Chưa được duyệt xuất bản.';
    } catch(error) {
      status.textContent='Chưa kết nối được Music Private. Mở tab đăng nhập Music Gateway rồi thử lại. Nếu vẫn lỗi, kiểm tra cookie bên thứ ba/CORS của Cloudflare Access.';
      console.warn('Private Music opt-in not connected:',String(error?.message||error));
    } finally { load.disabled=false; }
  });
})();

// Owner Music is not published: the only sound bytes are served through
// authenticated Cloudflare Access. This control cannot circumvent Access.
(function setupOwnerAIMusic(){
  if(studioEnglish || location.pathname.replace(/\/+$/,"")!=="/vi")return;
  const holder=document.createElement("section");
  holder.className="owner-ai-music-sync";
  holder.style.cssText="padding:10px;margin:10px 0;border:1px solid #79ab9d80;border-radius:8px;";
  const title=document.createElement("strong");
  title.textContent="Nhạc AI trong R2 riêng tư";
  const text=document.createElement("p");
  text.textContent="Tự đọc catalog nhạc AI đã tải lên; không phải chọn lại MP3 trên máy.";
  const link=document.createElement("a");
  link.href="https://wnc-private-music-gateway.whitescreen-dev.workers.dev/v1/owner/catalog";
  link.target="_blank";link.rel="noopener noreferrer";
  link.textContent="Đăng nhập Music Gateway";
  const action=document.createElement("button");
  action.type="button";action.textContent="Đồng bộ nhạc AI từ R2";
  const state=document.createElement("p");
  state.setAttribute("role","status");state.setAttribute("aria-live","polite");
  state.textContent="Đang kiểm tra danh mục nhạc AI…";
  holder.append(title,text,link,document.createTextNode(" · "),action,state);
  $('library-status').insertAdjacentElement("beforebegin",holder);
  async function sync(refresh=false){
    action.disabled=true;
    try{
      const result=await loadOwnerMusic({refresh});
      state.textContent="Đã nhận "+result.count+" bản AI trong R2 riêng tư (+"+
        result.added+" mới). Chỉ nghe thử nội bộ, chưa duyệt phát hành.";
    }catch(err){
      state.textContent="Chưa kết nối Music Gateway được. Mở link đăng nhập phía trên "+
        "rồi bấm Đồng bộ nhạc AI. Không cần tải lại MP3.";
    }finally{action.disabled=false}
  }
  action.addEventListener("click",()=>sync(true));
  void sync();
})();
