#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const origin = 'https://whitenoisechoir.com';
const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const read = file => fs.readFileSync(path.join(root,file),'utf8');
const escape = value => String(value ?? '').replace(/[&<>"']/g,ch=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
})[ch]);
function write(file,content) {
  const destination = path.join(root,file);
  fs.mkdirSync(path.dirname(destination),{recursive:true});
  fs.writeFileSync(destination,content.endsWith('\n') ? content : content+'\n');
}
function list(file) {
  const value = JSON.parse(read(file));
  if (!Array.isArray(value)) throw Error(file+' must contain a JSON array');
  const ids = new Set();
  for (const record of value) {
    if (!slugPattern.test(record?.slug) || ids.has(record.slug) || typeof record.title !== 'string' || !record.title.trim()) {
      throw Error('Invalid or duplicate mix in '+file);
    }
    ids.add(record.slug);
  }
  return value;
}
function removeStaleRoutes(section,records,marker) {
  const active = new Set(records.map(record=>record.slug));
  for (const entry of fs.readdirSync(path.join(root,section),{withFileTypes:true})) {
    if (!entry.isDirectory() || !slugPattern.test(entry.name) || active.has(entry.name)) continue;
    const index = path.join(root,section,entry.name,'index.html');
    if (fs.existsSync(index) && fs.readFileSync(index,'utf8').includes(marker)) fs.unlinkSync(index);
  }
}
const signIn = read('scripts/templates/studio-sign-in.html');
function validPublicMedia(value) {
  const link = new URL(value);
  return link.protocol === 'https:' && link.hostname === 'media.whitenoisechoir.com' &&
    !link.port && !link.username && !link.password &&
    /^\/(?:published-mixes|mixes)\/[A-Za-z0-9_/-]+\.(mp3|m4a|ogg|wav|mp4)$/i.test(link.pathname);
}
function libraryPage(route,title,description,body) {
  return '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<title>'+escape(title)+' · WhiteNoiseChoir</title><meta name="description" content="'+escape(description)+'">'+
    '<link rel="canonical" href="'+origin+route+'"><link rel="stylesheet" href="/studio.css"></head><body>'+
    '<header class="studio-header"><a class="brand" href="/">WhiteNoiseChoir <span>Studio</span></a>'+
    '<nav class="studio-nav" aria-label="Navigation"><a href="/">MP3 Sounds</a><a href="/vi/" lang="vi">Studio nội bộ</a></nav></header>'+
    '<main class="published-library">'+body+'</main></body></html>';
}
write('index.html',read('scripts/templates/public-sounds.html'));
write('vi/index.html',signIn);
const trials = list('data/studio-trials.json');
for (const trial of trials) {
  if (Boolean(trial.preset)===Boolean(trial.project)) throw Error('A trial needs one preset or project');
  if (trial.project && (!Number.isFinite(trial.project.length)||!Array.isArray(trial.project.tracks))) throw Error('Invalid trial project');
  write('vi/'+trial.slug+'/index.html',signIn.replace('<html lang="vi">','<html lang="vi">\n<!-- Generated Studio trial -->')
    .replace('/vi/">Mở','/vi/'+trial.slug+'/">Mở'));
}
const published = list('data/published-mixes.json').filter(m=>m.status==='published');
for (const mix of published) {
  if (!validPublicMedia(mix.media) || !mix.approvedAt || !Number.isFinite(Date.parse(mix.approvedAt))) {
    throw Error('A published mix needs an approval date and an exported media URL');
  }
  const player = new URL(mix.media).pathname.toLowerCase().endsWith('.mp4')?'video':'audio';
  const route = '/library/'+mix.slug+'/';
  write(route.slice(1)+'index.html',libraryPage(route,mix.title,mix.description,
    '<!-- Generated published mix --><a href="/library/">Published mixes</a><h1>'+escape(mix.title)+'</h1><p>'+escape(mix.description)+'</p>'+
    '<'+player+' controls preload="metadata" src="'+escape(mix.media)+'"></'+player+'>'));
}
removeStaleRoutes('vi',trials,'<!-- Generated Studio trial -->');
removeStaleRoutes('library',published,'<!-- Generated published mix -->');
const cards=published.map(mix=>'<article class="panel published-card"><h2><a href="/library/'+mix.slug+'/">'+escape(mix.title)+'</a></h2><p>'+escape(mix.description)+'</p></article>').join('');
write('library/index.html',libraryPage('/library/','Published mixes','A collection of reviewed and published WhiteNoiseChoir mixes.',
  '<h1>Published mixes</h1><p>Soundscapes created and reviewed in WhiteNoiseChoir Studio.</p>'+
  (cards?'<div class="published-grid">'+cards+'</div>':'<p class="panel published-card">No mixes have been published yet.</p>')));
write('sounds/index.html','<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0; url=/library/"><link rel="canonical" href="'+origin+'/library/"><title>Published mixes · WhiteNoiseChoir</title></head><body><a href="/library/">Open published mixes</a></body></html>');
const urls=['/','/library/',...published.map(mix=>'/library/'+mix.slug+'/')];
write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+
  urls.map(route=>'  <url><loc>'+origin+route+'</loc></url>').join('\n')+'\n</urlset>');
