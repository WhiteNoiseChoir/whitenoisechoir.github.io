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
    for (const [value, title] of categories) {
      if (!sounds.some(row => row.cat === value)) continue;
      category.add(new Option(title, value));
    }
    render();
  } catch {
    status.textContent = 'The sound catalog could not load. Reload to try again.';
  }
}
