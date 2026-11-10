#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const BASE="http://127.0.0.1:8787";
(async()=>{
 const executablePath=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(p=>fs.existsSync(p));
 const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox"]});
 const errors=[];
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
  page.on("pageerror",e=>errors.push(String(e)));
  await page.goto(BASE+"/framework-preview/sound-detail/?sound=SND-0040",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelector("#record-id")?.textContent==="SND-0040",{timeout:30000});
  assert.equal(await page.locator("#sound-list option").count(),532,"532 selectable IDs");
  assert.equal(await page.locator("audio").count(),0,"no pretend audio preview");
  assert.ok((await page.locator("#media-action").textContent()).includes("No approved audio"));
  assert.equal(await page.locator("#existing-route a").count(),0,"planned source must have no audio link");
  await page.locator("#sound-lookup").fill("SND-0001");
  await page.locator("#load").click();
  assert.equal(await page.locator("#record-id").textContent(),"SND-0001");
  assert.equal(await page.locator("#existing-route a").getAttribute("href"),"/sounds/white-noise/");
  assert.ok((await page.locator("#rights").textContent()).includes("NOT VERIFIED"),"unknown license not approved");
  await page.locator("#sound-lookup").fill("Light Rain");
  await page.locator("#load").click();
  assert.ok((await page.locator("#rights").textContent()).includes("PLAN LICENSE"),"released plan evidence shown");
  assert.ok((await page.locator("#technical").textContent()).includes("PASS"),"plan QA evidence shown");
  await page.locator("#sound-lookup").fill("Green Noise");
  await page.locator("#load").click();
  assert.ok((await page.locator("#stage").textContent()).includes("PENDING LISTENING"));
  assert.ok((await page.locator("#owner").textContent()).includes("PENDING LISTENING REVIEW"));
  await page.locator("#sound-lookup").fill("UNKNOWN-RECORD");
  await page.locator("#load").click();
  assert.equal(await page.locator("#record").isHidden(),true,"invalid ID shows no fabricated details");
  for(const width of [320,390,768]){
   await page.setViewportSize({width,height:840});
   const over=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
   assert.ok(over<=2,"horizontal overflow at "+width+": "+over);
  }
  await page.goto(BASE+"/sounds/explore/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelector("#stat-items")?.textContent==="532",{timeout:30000});
  const review=page.locator('a:has-text("View production / SEO checklist")').first();
  assert.ok((await review.getAttribute("href")).includes("/framework-preview/sound-detail/?sound="),"links include record ID");
  await review.click();
  await page.waitForURL(/framework-preview\/sound-detail\/\?sound=SND-/,{timeout:15000});
  assert.equal(await page.locator("#record").isHidden(),false);
  assert.deepEqual(errors,[],"browser scripts have no page errors");
  console.log("PASS C5 browser: 532 record previews, rights/QA/owner evidence gates, planned vs real links, 320/390/768 responsive");
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack||e);process.exit(1)});
