#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),assert=require("node:assert/strict"),fs=require("node:fs");
const BASE="http://127.0.0.1:8787";
(async()=>{
const executablePath=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(x=>fs.existsSync(x));
const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
try{
const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
const errors=[];page.on("pageerror",e=>errors.push(String(e)));
await page.goto(BASE+"/signature/rain-review/",{waitUntil:"domcontentloaded"});
assert.equal(await page.locator('meta[name="robots"]').getAttribute("content"),"noindex,nofollow");
assert.equal(await page.locator("button[data-select]").count(),5,"three original auditions + two production references");
assert.ok((await page.locator("body").innerText()).includes("−48,9 dBFS"),"Tin Roof low loudness transparently flagged");
for(const width of [320,390]){
 await page.setViewportSize({width,height:780});
 const over=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
 assert.ok(over<=1,"width "+width+": no horizontal page overflow "+over);
}
assert.equal(await page.locator("#player").evaluate(x=>x.paused),true,"no autoplay at page load");
await page.locator('[data-select="light-rain-review"]').click();
await page.waitForFunction(()=>document.querySelector("#player").duration>=599,null,{timeout:30000});
assert.equal(await page.locator("#player").evaluate(x=>x.loop),true,"native MP3 looping available");
await page.locator("#near").click();
const nearSnap=await page.evaluate(()=>{const p=document.querySelector("#player");return {duration:p.duration,at:p.currentTime,ready:p.readyState,network:p.networkState,seekable:p.seekable.length?{start:p.seekable.start(0),end:p.seekable.end(0)}:null,status:document.querySelector("#message").textContent}});
console.log("RAIN_REVIEW_SEEK_DIAGNOSTIC",JSON.stringify(nearSnap));
await page.waitForFunction(()=>{const p=document.querySelector("#player");return p.currentTime>=594&&!p.seeking;},null,{timeout:20000});
await page.locator("#stop").click();
assert.equal(await page.locator("#player").evaluate(x=>x.paused),true);
await page.locator('[data-select="rain-tin-roof-review"]').click();
await page.waitForFunction(()=>document.querySelector("#player").duration>=599,null,{timeout:30000});
await page.locator("#verdict").selectOption("REWORK");
await page.locator("#notes").fill("Very quiet average level versus transient peaks; needs listening review.");
await page.locator("#save").click();
await page.reload({waitUntil:"domcontentloaded"});
await page.locator('[data-select="rain-tin-roof-review"]').click();
assert.equal(await page.locator("#notes").inputValue(),"Very quiet average level versus transient peaks; needs listening review.");
assert.equal(await page.locator("#verdict").inputValue(),"REWORK");
await page.locator('[data-select="distant-thunder-review"]').click();
await page.waitForFunction(()=>document.querySelector("#player").duration>=599,null,{timeout:30000});
assert.equal(await page.locator("#player").getAttribute("src"),"/audio/distant-thunder-real.mp3");
assert.equal(errors.length,0,"JavaScript errors: "+errors.join(" | "));
console.log("RAIN_REVIEW_BROWSER_QA_PASS three actual MP3s, seek 9:55, native loop, no autoplay, mobile widths, notes saved");
}finally{await browser.close();}
})().catch(x=>{console.error(x);process.exit(1)});
