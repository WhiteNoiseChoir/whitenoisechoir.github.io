#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),assert=require("node:assert/strict"),fs=require("node:fs");
const URL="http://127.0.0.1:8787/framework-preview/c6-listening/";
(async()=>{
const preferred=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(p=>fs.existsSync(p));
const browser=await chromium.launch({headless:true,...(preferred?{executablePath:preferred}:{}),args:["--no-sandbox"]});
const errors=[];
try{
const page=await browser.newPage({viewport:{width:390,height:844}});
page.on("pageerror",e=>errors.push(String(e)));
await page.goto(URL+"?sound=SND-0039",{waitUntil:"domcontentloaded"});
await page.waitForFunction(()=>document.querySelector("#track option")?.value==="SND-0039",{timeout:30000});
assert.equal(await page.locator("#track option").count(),10);
assert.ok((await page.locator("#stage").textContent()).includes("SND-0039"));
assert.ok((await page.locator("#rights").textContent()).includes("NOT VERIFIED"));
assert.equal(await page.locator("#seek").isDisabled(),true);
assert.equal(await page.locator("#near-end").isDisabled(),true);
assert.equal(await page.locator("#play").isDisabled(),true);
assert.equal(await page.locator("#loop").isDisabled(),true);
assert.equal(await page.locator("audio").getAttribute("src"),null);
assert.equal(await page.locator("audio").isHidden(),true);
await page.locator("#track").selectOption("SND-0040");
assert.ok((await page.locator("#stage").textContent()).includes("SND-0040"));
assert.equal(await page.locator("#near-end").isDisabled(),true,"metadata lead must never unlock audio");
await page.goto(URL+"?sound=SND-0046",{waitUntil:"domcontentloaded"});
await page.waitForFunction(()=>document.querySelector("#stage")?.textContent.includes("SND-0046"),{timeout:30000});
assert.ok((await page.locator("#brief").textContent()).includes("Womb-like"));
assert.equal(await page.locator("#play").isDisabled(),true);
for(const width of [320,390,768]){
await page.setViewportSize({width,height:844});
const over=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
assert.ok(over<=2,"C6 layout horizontal overflow "+width+": "+over);
}
assert.deepEqual(errors,[],"C6 browser page errors");
console.log("C6_BROWSER_PASS: 10 candidates, no fake audio, 320/390/768 responsive, seek/play locked, no JS errors");
}finally{await browser.close()}
})().catch(e=>{console.error(e.stack||e);process.exit(1)});
