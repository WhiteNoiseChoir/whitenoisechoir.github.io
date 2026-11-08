#!/usr/bin/env node
"use strict";
/* Schema/SEO/route/mix integrity for the 13-family expansion foundation. */
const fs=require("node:fs"),assert=require("node:assert/strict");
const file=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(file(p));
const fam=json("catalog/family-registry.json"),plan=json("catalog/planned-sounds.json"),mix=json("catalog/mix-proposals.json"),catalog=json("catalog/library.json");
const html=file("sounds/index.html"),home=file("index.html"),sitemap=file("sitemap.xml");
const families=fam.families,allPlans=plan.planned,planned=allPlans.filter(p=>!p.playable),released=allPlans.filter(p=>p.playable),proposals=mix.proposals,sounds=catalog.sounds;
const count=(arr,prop,value)=>arr.filter(x=>x[prop]===value).length;
assert.equal(families.length,13,"13 families, not 13 extra indexable URLs");
assert.equal(allPlans.length,70,"70 source concepts retained");
assert.equal(planned.length,64,"67 not-yet-playable sound concepts");
assert.equal(released.length,6,"3 newly approved and deployed first-wave sources");
assert.equal(proposals.length,34,"34 proposed mixes");
assert.equal(sounds.length,28,"22 original source IDs plus 3 approved rain sources");
assert.equal(catalog.categories.length,12,"Original 12 physical hubs preserved");
assert.equal(catalog.collec.length,7,"Seven intent collections retained");
assert.equal(count(allPlans,"priority","P0"),24);
assert.equal(count(planned,"priority","P0"),18);
assert.equal(count(allPlans,"priority","P1"),27);
assert.equal(count(allPlans,"priority","P2"),19);
assert.equal(count(proposals,"priority","P0"),18);
assert.equal(count(proposals,"priority","P1"),12);
assert.equal(count(proposals,"priority","P2"),4);
assert.equal(new Set(families.map(x=>x.id)).size,13,"unique family keys");
assert.equal(new Set(allPlans.map(x=>x.plan_id)).size,70,"unique plan IDs");
assert.equal(new Set(allPlans.map(x=>x.title)).size,70,"unique proposed source names");
assert.equal(new Set(proposals.map(x=>x.id)).size,34,"unique mix proposals");
const available=new Set(sounds.map(x=>x.id)),planId=new Set(planned.map(x=>x.plan_id)),all=new Set([...available,...planId]);
assert.equal(all.size,92,"Planned and current IDs do not overlap");
const grouped=families.flatMap(x=>x.existing_ids);
assert.equal(grouped.length,28,"all 25 current source IDs assigned exactly once to a primary family");
assert.equal(new Set(grouped).size,28,"no primary source assigned to multiple families");
assert.ok(grouped.every(x=>available.has(x)),"all family audio IDs exist in live catalog");
assert.ok(families.find(f=>f.id==="ocean")?.route==="/sounds/#ocean-waves","Ocean virtual family must not replace /sounds/ocean-waves/ sound page");
assert.ok(families.find(f=>f.id==="ocean")?.route_type==="virtual_family");
assert.ok(fs.existsSync("sounds/ocean-waves/index.html"),"Existing ocean Sound Page retained");
for(const f of families){
 assert.ok(f.existing_ids.every(id=>available.has(id)),"unknown current sound in "+f.id);
 const expected=planned.filter(p=>p.family_id===f.id).map(p=>p.plan_id);
 assert.deepEqual(f.planned_ids,expected,"planned inventory stays derived from registry "+f.id);
 if(f.route_type==="existing_hub"){
  assert.ok(/^\/sounds\/[a-z-]+\/$/.test(f.route),"local existing hub "+f.id);
  assert.ok(fs.existsSync(f.route.slice(1)+"index.html"),"existing hub retained "+f.route);
 }
 assert.ok(html.includes('data-wnc-family="'+f.id+'"'),"visible family "+f.id);
}
for(let i=0;i<allPlans.length;i++){
 const p=allPlans[i];
 assert.equal(p.plan_id,"NEW-"+String(i+1).padStart(2,"0"));
 if(p.playable){
  assert.equal(p.readiness,"released_audio_seo_pending");
  assert.ok(available.has(p.production_id));
  assert.equal(p.license,"CC0-1.0");
  assert.equal(p.qa.technical_status,"PASS");
  assert.match(p.owner_listening_approval,/^APPROVED_BY_OWNER_2026-11-(08|09)$/);
  assert.equal(p.seo_status,"noindex,follow");
  assert.ok(file(p.seo_page.slice(1)+"index.html").includes('name="robots" content="noindex,follow"'));
 }else{
 assert.equal(p.readiness,"planned");
 assert.equal(p.playable,false);
 assert.equal(p.production_id,null);
 assert.equal(p.audio_path,null);
 assert.equal(p.license,null);
 assert.equal(p.qa,null);
 assert.equal(p.owner_listening_approval,null);
 assert.equal(p.seo_page,null);
 }
 assert.ok(families.some(f=>f.id===p.family_id));
}
for(const m of proposals){
 assert.equal(m.readiness,"proposal_only");
 assert.equal(m.playable,false);
 assert.equal(m.seo_url,null);
 assert.ok(m.required_ids.length===2||m.required_ids.length===3);
 assert.ok(m.required_ids.every(id=>all.has(id)),"mix proposal depends on valid catalog/plan IDs: "+m.id);
 assert.ok(families.some(f=>f.id===m.family_id));
 assert.deepEqual(m.missing_sources,m.required_ids.filter(id=>planId.has(id)),"correct dependencies "+m.id);
}
const start=home.indexOf("var recipes=")+"var recipes=".length,end=home.indexOf("];",start)+1;
const recipes=JSON.parse(home.slice(start,end));
assert.equal(recipes.length,45,"45 live presets unchanged");
const signature=ids=>[...ids].sort().join("+");
const signatures=new Map();
for(const item of recipes){
 const key=signature(item.slice(2));const peers=signatures.get(key)||[];peers.push(item);signatures.set(key,peers);
}
const collisions=[];
for(const m of proposals){
 const hits=signatures.get(signature(m.required_ids))||[];
 assert.equal(!!m.collision,hits.length>0,"source-set collision classification "+m.id);
 if(hits.length){
  const exact=hits.some(hit=>JSON.stringify(hit.slice(2))===JSON.stringify(m.required_ids));
  assert.equal(m.collision.type,exact?"same_order":"same_sources_different_order",m.id+" ordering matters");
  collisions.push(m.id);
 }
}
assert.deepEqual(collisions,["MIX-05","MIX-09"],"Two current-45-source-set collisions documented");
assert.deepEqual(proposals.filter(m=>m.required_ids.length===3).map(m=>m.id),["MIX-31","MIX-34"],"3-layer concepts require future QA");
assert.ok(!/data-wnc-play="NEW-|data-sound="NEW-|\/audio\/NEW-/.test(html),"no unproduced audio can play");
assert.equal((html.match(/class="tile wnc-family-tile"/g)||[]).length,13);
assert.equal((html.match(/data-wnc-existing-id="/g)||[]).length,28);
assert.equal((html.match(/class="wnc-roadmap-family"/g)||[]).length,13);
assert.ok(html.includes('id="ocean-waves"'),"ocean anchor target exists on /sounds/");
assert.ok(html.includes("Green Noise")&&html.includes("listening review pending"),"Green pending disclosure");
assert.ok(html.includes('rel="canonical" href="https://whitenoisechoir.github.io/sounds/"'),"Preserve browse URL canonical");
assert.ok(!html.includes('name="robots" content="noindex'),"Library still indexable");
assert.ok(!sitemap.includes("/sounds/roadmap/"),"No thin roadmap URL");
assert.equal((sitemap.match(/<loc>/g)||[]).length,18,"Sitemap unchanged");
const indexed=sounds.filter(s=>!file("sounds/"+s.slug+"/index.html").includes('name="robots" content="noindex,follow"'));
assert.equal(indexed.length,10,"10 indexable Sound Pages unchanged");
assert.ok(file("sounds/green-noise/index.html").includes('name="robots" content="noindex,follow"'));
assert.ok(!sitemap.includes("/sounds/green-noise/"));
const css=file("assets/library.css");
assert.ok(css.includes(".wnc-roadmap-details")&&css.includes("@media(max-width:350px)"),"mobile layout for new foundation");
const bodyHtml=html.split("<!-- WNC_FOUNDATION_ROADMAP_BEGIN -->")[1]?.split("<!-- WNC_FOUNDATION_ROADMAP_END -->")[0];
assert.ok(bodyHtml&&!/data-wnc-play=|<audio\b|data-wnc-compare=/.test(bodyHtml),"roadmap offers no audio controls");
console.log("LIBRARY_FOUNDATION_QA_PASS "+JSON.stringify({families:13,currentSources:28,plannedSources:64,released:6,p0:18,p1:27,p2:19,mixProposals:34,presetsPreserved:45,collisions,indexableSourcePages:10,sitemap:18,virtualOceanPreserved:true}));
