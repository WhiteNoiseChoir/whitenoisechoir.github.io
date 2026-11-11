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
  other: studioEnglish ? 'Other recordings' : 'Âm thanh khác',
};
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
  mix = from.pop();
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
    mix.tracks.push({asset:index,...(assets[index].id?{assetRef:assets[index].id}:{}),start: Math.min(position, mix.length - .01), gain: .35, loop: false, mute: false});
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
  const ticket = previewRequest;
  const audio = $('library-audio');
  for (const address of sourceAddresses(index)) {
    audio.src = address;
    try {
      await audio.play();
      if (ticket !== previewRequest) return;
      previewTimer = setTimeout(stopPreview, 10000);
      return;
    } catch {
      if (ticket !== previewRequest) return;
    }
  }
  stopPreview();
  $('library-status').textContent = tr('Không phát được bản nghe thử này.');
}

function durationText(seconds) {
  return seconds < 60 ? Math.max(.1, Math.round(seconds * 10) / 10) + ' s' : format(seconds);
}

function renderLibrary() {
  const query = searchable($('library-query').value.trim());
  const words = query.split(/\s+/).filter(Boolean);
  const group = $('library-group').value;
  const matches = catalog.map((entry, i) => ({...entry, i}))
    .filter(entry => !assets[entry.i].pending && (!group || group === entry.group) && words.every(word => entry.text.includes(word)));
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
  const mute = button('M', () => change(() => { track.mute = !track.mute; }), tr('Tắt tiếng lớp ') + (index + 1));
  mute.className = 'track-mute';
  mute.setAttribute('aria-pressed', track.mute);
  rail.append(select, mute);

  const lane = node('div', '', 'lane');
  lane.onclick = event => { if (event.target === lane) seekFromPointer(event, lane); };
  const clip = button(label, () => selectTrack(index), tr('Chọn đoạn ') + label);
  clip.className = 'clip' + (track.loop ? ' looped' : '');
  const place = time => {
    const length = clipDuration({...track, start: time}, asset.duration, mix.length);
    clip.hidden = length <= 0;
    clip.style.left = 100 * Math.min(time, mix.length) / mix.length + '%';
    clip.style.width = 100 * length / mix.length + '%';
    clip.title = label + ' · ' + format(time) + ' · ' + durationText(length);
  };
  place(track.start);
  let drag;
  clip.onpointerdown = event => {
    if (event.button !== 0) return;
    drag = {id: event.pointerId, x: event.clientX, start: track.start, target: track.start};
    clip.setPointerCapture(event.pointerId);
  };
  clip.onpointermove = event => {
    if (!drag || drag.id !== event.pointerId || Math.abs(event.clientX - drag.x) < 3) return;
    const scale = event.shiftKey ? 1 : 10;
    const time = drag.start + (event.clientX - drag.x) * mix.length / lane.clientWidth;
    drag.target = clamp(Math.round(time * scale) / scale, 0, mix.length - .01);
    clip.classList.add('dragging');
    place(drag.target);
  };
  clip.onpointerup = event => {
    if (!drag || drag.id !== event.pointerId) return;
    const target = drag.target;
    drag = undefined;
    clip.classList.remove('dragging');
    if (target !== track.start) change(() => { selected = index; track.start = target; });
    else place(track.start);
  };
  clip.onpointercancel = () => {
    drag = undefined;
    clip.classList.remove('dragging');
    place(track.start);
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
  fields.append(node('p', tr('Pan: −100 trái, 0 giữa, +100 phải. Solo chỉ dùng khi nghe thử.'), 'hint muted'));
  inspector.append(source, actions, fields);
}

function render(keepInspector = false) {
  $('title').value = mix.title;
  $('minutes').value = mix.length / 60;
  $('video-prompt').value = mix.videoPrompt || '';
  $('seek').max = mix.length;
  $('master').value = Math.round((mix.master ?? 1) * 100);
  $('master-value').value = $('master').value + '%';
  renderTimeline();
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
$('minutes').onchange = () => change(() => { mix.length = clamp(Number($('minutes').value) * 60, 6, 10800); });
$('video-prompt').onchange = () => change(() => { mix.videoPrompt = $('video-prompt').value; });
$('master').oninput = () => {
  $('master-value').value = $('master').value + '%';
  if (monitorGain) monitorGain.gain.value = Number($('master').value) / 100;
};
$('master').onchange = () => change(() => { mix.master = Number($('master').value) / 100; });
$('undo').onclick = () => restore(undoStack, redoStack);
$('redo').onclick = () => restore(redoStack, undoStack);
const recipeGroup=node('optgroup');
recipeGroup.label=studioEnglish?'Original listening presets':'Preset nghe liên tục cũ';
legacyStudioRecipes.forEach((recipe,index)=>{
  const option=node('option',recipe.title);
  option.value='legacy-'+index;
  recipeGroup.append(option);
});
$('preset').append(recipeGroup);
$('preset').onchange = () => {
  const get = presets[$('preset').value];
  if (get) replaceProject(get());
  $('preset').value = '';
};
$('clear').onclick = () => {
  $('clear').closest('details').open = false;
  replaceProject({title: tr('Bản phối chưa đặt tên'), length: 1800, tracks: []});
};
$('share').onclick = async () => {
  const url = new URL(location.href);
  url.hash = 'mix=' + encodeURIComponent(JSON.stringify(mix));
  history.replaceState(null, '', url);
  try { await navigator.clipboard.writeText(url.href); $('status').textContent = tr('Đã sao chép liên kết bản phối.'); }
  catch { $('status').textContent = tr('Sao chép liên kết bản phối từ thanh địa chỉ.'); }
};
$('save-project').onclick = () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(mix, null, 2)], {type: 'application/json'}));
  const link = node('a');
  link.href = url;
  link.download = (mix.title.replace(/[\\/:*?"<>|]/g, '-').trim() || 'ban-phoi') + '.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  $('save-project').closest('details').open = false;
};
$('open-project').onchange = async () => {
  const input = $('open-project');
  const file = input.files[0];
  input.value = '';
  if (!file) return;
  try {
    if (file.size > 100000) throw Error();
    const raw = JSON.parse(await file.text());
    const project = normalizeProject(raw);
    if (project.tracks.length !== raw.tracks.length) throw Error();
    replaceProject(project);
    $('status').textContent = tr('Đã mở dự án.');
    input.closest('details').open = false;
  } catch {
    $('status').textContent = tr('Tệp dự án không hợp lệ hoặc chứa nguồn âm thanh chưa có trong thư viện.');
  }
};
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
  mix = readMix();
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
