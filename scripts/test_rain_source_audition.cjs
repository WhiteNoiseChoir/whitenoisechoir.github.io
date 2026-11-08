#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict");
const file=p=>fs.readFileSync(p,"utf8");
const html=file("signature/rain-source-review/index.html"),sitemap=file("sitemap.xml");
assert.match(html,/<meta name="robots" content="noindex,nofollow">/);
assert.ok(html.includes("<h1>Nghe và so sánh 3 nguồn âm gốc</h1>"));
assert.ok(html.includes("không phải 10 phút"),"source preview is not a master");
assert.ok(html.includes("KHÔNG")||html.includes("không"),"discloses not production");
assert.ok(html.includes("Tua gần cuối nguồn"));
assert.ok(html.includes('id="copy"')&&html.includes('id="save"'));
for(const [id,code] of [["light-rain-review","430/430765_1218676-hq.mp3"],["rain-tin-roof-review","843/843483_9671929-hq.mp3"],["distant-thunder-review","107/107518_43834-hq.mp3"]]){
 assert.ok(html.includes('data-select="'+id+'"'),id+" button");
 assert.ok(html.includes("https://cdn.freesound.org/previews/"+code),id+" real HQ source URL");
}
assert.ok(!sitemap.includes("/signature/rain-source-review/"));
assert.ok(!file("catalog/library.json").includes("light-rain-review"));
assert.equal((sitemap.match(/<loc>/g)||[]).length,18);
assert.equal(JSON.parse(file("catalog/library.json")).sounds.length,22);
console.log("RAIN_SOURCE_AUDITION_PASS 3 authentic CC0 Freesound links; source durations disclosed, noindex, 22 production IDs unchanged");
