#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict"),vm=require("node:vm");
const read=p=>fs.readFileSync(p,"utf8"),data=JSON.parse(read("framework-preview/master-inventory.json")),config=JSON.parse(read("catalog/framework-hubs-c4.json")),lib=JSON.parse(read("catalog/library.json"));
const columns=Object.fromEntries(data.columns.map((c,i)=>[c,i]));
const sitemap=read("audits/sitemap-before-studio.xml"),explorer=read("sounds/explore/index.html"),index=read("sounds/archive.html");
assert.equal(config.hubs.length,6);assert.equal(config.expected_total_records,182);
assert.equal(data.rows.length,532);assert.equal(lib.sounds.length,35);
assert.ok(!sitemap.includes("/sounds/explore/"));
assert.match(explorer,/<meta name="robots" content="noindex,nofollow,noarchive">/);
for(const hub of config.hubs){
 const path="sounds/"+hub.slug+"/index.html",html=read(path);
 const rows=data.rows.filter(r=>r[columns.family_id]===hub.id);
 assert.equal(rows.length,config.expected_counts[hub.id],hub.id+" row count");
 assert.match(html,/<meta name="robots" content="noindex,follow">/,hub.slug+" not indexable");
 assert.ok(!html.includes('rel="canonical"'),hub.slug+" has no premature canonical");
 assert.ok(!sitemap.includes(hub.route),hub.slug+" absent sitemap");
 assert.ok(index.includes('href="'+hub.route+'"'),hub.slug+" linked from main /sounds/");
 assert.ok(explorer.includes('"route":"'+hub.route+'"'),hub.slug+" routed from /sounds/explore/");
 assert.ok(html.includes('href="/sounds/explore/?group='+hub.id+'"'),hub.slug+" filters full library");
 const matches=[...html.matchAll(/<article class="tile" data-sound-row /g)].length;
 assert.equal(matches,rows.length,hub.slug+" includes all real editorial records");
 for(const r of rows)assert.ok(html.includes(r[columns.id]),hub.slug+" lost "+r[columns.id]);
 assert.ok(!/<audio\\b/i.test(html),hub.slug+" cannot have fake playback");
 assert.ok(!/<button[^>]*data-wnc-play/.test(html));
 const js=html.split("<script>")[1]?.split("</script>")[0];
 assert.ok(js,"inline filter logic for "+hub.slug);
 new vm.Script(js,{filename:path});
 for(const target of config.hubs)if(target.slug!==hub.slug)assert.ok(html.includes('href="'+target.route+'"'),"related link "+target.slug);
}
assert.ok(read("sounds/nature/index.html").includes('href="/sounds/bird-sounds/"'));
assert.ok(read("sounds/nature/index.html").includes('href="/sounds/animal-sounds/"'));
assert.ok(!sitemap.includes("industrial-sounds"),"industrial page not indexed prematurely");
console.log("PASS C4: six noindex hubs / 182 classified rows / links from library, nature and explorer / 35 untouched production sounds");
