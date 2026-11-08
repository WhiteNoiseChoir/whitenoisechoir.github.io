#!/usr/bin/env node
"use strict";
/* Deterministic, static and crawlable family library build. Does not touch player. */
const fs=require("node:fs"),assert=require("node:assert/strict");
const file=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(file(p));
const escapeHTML=function escapeHTML(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")};
const renderFamilies=function renderFamilies(families,plans,mixProposals){
 return `<h2>Browse 13 sound families</h2><p class="lede">Explore the 22 current audio sources across 13 listening families. Another 70 independently reviewed candidates are on the production roadmap, not yet playable. The Ocean family has a separate browsing section and does not replace its existing Sound Page.</p><div class="grid" id="wnc-family-grid">${families.map(f=>{
 const pending=plans.filter(x=>x.family_id===f.id).length, mix=mixProposals.filter(m=>m.family_id===f.id).length;
 return `<a class="tile wnc-family-tile" href="${f.route}" data-wnc-family="${f.id}"><strong>${escapeHTML(f.title)}</strong><p>${escapeHTML(f.description)}</p><small>${f.existing_ids.length} catalog source${f.existing_ids.length===1?"":"s"} · ${pending} planned${mix?" · "+mix+" mix concepts":""}</small></a>`;
 }).join("")}</div>`;
};
const renderSources=function renderSources(sounds){
 return `<h2>22 current audio sources</h2><p class="lede">The source pages below are real catalog entries; Green Noise remains pending separate listening approval. Titles and provenance are taken from the current catalog, not from the 70 planned items.</p><div class="grid" id="wnc-catalog-grid">${sounds.map(s=>{
 let label=s.status==="dsp-review"?"Listening review pending · not curated":s.status==="arranged"?"CC0 arrangement · source duration disclosed":s.id.endsWith("-real")?"Owner-approved CC0 field recording":"Owner-approved original DSP";
 return `<a class="tile" href="/sounds/${s.slug}/" data-wnc-existing-id="${s.id}"><strong>${escapeHTML(s.title)}</strong><p>${escapeHTML(s.desc)}</p><small>${escapeHTML(label)}</small></a>`;
 }).join("")}</div>`;
};
const renderRoadmap=function renderRoadmap(families,plans,mixProposals,sounds){
 const byId=Object.fromEntries(sounds.map(s=>[s.id,s]));
 return `<section class="wnc-family-expansion" aria-labelledby="wnc-roadmap-heading"><span class="kicker">Library foundation · staged releases</span><h2 id="wnc-roadmap-heading">Explore sounds in development</h2><p class="lede">There are 24 first-wave (P0), 27 second-wave (P1), and 19 exploratory (P2) audio concepts. These are future recording requirements, <strong>not playable files or promised releases</strong>. New tracks need source/license checks, acoustic QA and listening approval before they join the library.</p><div class="wnc-roadmap-details">${families.map(f=>{
 const items=plans.filter(p=>p.family_id===f.id), first=items.filter(p=>p.priority==="P0");
 const later=items.filter(p=>p.priority==="P1").length, explore=items.filter(p=>p.priority==="P2").length,mix=mixProposals.filter(m=>m.family_id===f.id).length;
 const ready=f.existing_ids.filter(x=>byId[x]&&byId[x].status!=="dsp-review");
 const held=f.existing_ids.filter(x=>byId[x]&&byId[x].status==="dsp-review");
 return `<details class="wnc-roadmap-family" id="${f.id==="ocean"?"ocean-waves":"family-"+f.id}"${f.id==="ocean"?" open":""}><summary>${escapeHTML(f.title)} <small>${ready.length} approved · ${items.length} planned</small></summary><div class="wnc-roadmap-inner"><p>${escapeHTML(f.description)}. Selection themes: ${escapeHTML(f.facets.join(" / "))}.</p>${ready.length?`<p><strong>Current sound pages:</strong> ${ready.map(id=>`<a href="/sounds/${byId[id].slug}/">${escapeHTML(byId[id].title)}</a>`).join(" · ")}.</p>`:`<p><strong>No approved sources yet</strong> in this family.</p>`}${held.length?`<p><strong>Still pending listening review:</strong> ${held.map(id=>escapeHTML(byId[id].title)).join(", ")}. Excluded from recommended instant-play comparisons.</p>`:""}${first.length?`<p><strong>First recording targets (P0):</strong> ${first.map(p=>escapeHTML(p.title)).join(" · ")}. No preview audio is available yet.</p>`:""}<p class="wnc-roadmap-later">${later} P1 concepts · ${explore} P2 concepts · ${mix} proposed mixes (not published)</p></div></details>`;
 }).join("")}</div><p class="wnc-foundation-foot">Existing canonical sound pages, the seven intent collections, continuous playback, Sleep Timer and 45 current mixes remain unchanged. Planned IDs are scheduling identifiers only; no sound is created by listing it here.</p></section>`;
};
const fam=json("catalog/family-registry.json").families,plan=json("catalog/planned-sounds.json").planned,mix=json("catalog/mix-proposals.json").proposals,sounds=json("catalog/library.json").sounds;
const pairs=[
 ["<!-- WNC_FOUNDATION_FAMILIES_BEGIN -->","<!-- WNC_FOUNDATION_FAMILIES_END -->",renderFamilies(fam,plan,mix)],
 ["<!-- WNC_FOUNDATION_SOURCES_BEGIN -->","<!-- WNC_FOUNDATION_SOURCES_END -->",renderSources(sounds)],
 ["<!-- WNC_FOUNDATION_ROADMAP_BEGIN -->","<!-- WNC_FOUNDATION_ROADMAP_END -->",renderRoadmap(fam,plan,mix,sounds)]
];
let html=file("sounds/index.html"),changed=false;
for(const [start,end,body] of pairs){
 const begin=html.indexOf(start),finish=html.indexOf(end);
 assert.ok(begin>=0&&finish>begin,"Missing foundation HTML markers: "+start);
 const current=html.slice(begin+start.length,finish),expected="\n"+body+"\n";
 if(current!==expected){changed=true;html=html.slice(0,begin+start.length)+expected+html.slice(finish)}
}
if(process.argv.includes("--write")){
 if(changed)fs.writeFileSync("sounds/index.html",html);
 console.log("FOUNDATION_RENDER_WRITTEN "+JSON.stringify({changed,families:fam.length,planned:plan.length,mixes:mix.length,sounds:sounds.length}));
}else{
 assert.ok(!changed,"Static family HTML drifted from JSON registries. Run node scripts/build_sound_library_foundation.cjs --write");
 console.log("FOUNDATION_RENDER_MATCH "+JSON.stringify({families:fam.length,planned:plan.length,mixes:mix.length,sounds:sounds.length}));
}
