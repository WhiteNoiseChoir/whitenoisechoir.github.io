#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),assert=require("node:assert/strict"),fs=require("node:fs");
(async()=>{
 const path=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(fs.existsSync);
 const browser=await chromium.launch({headless:true,executablePath:path,args:["--no-sandbox"]});
 try{
  const page=await browser.newPage({viewport:{width:390,height:800}}),errs=[];
  page.on("pageerror",e=>errs.push(String(e)));
  await page.goto("http://127.0.0.1:8787/signature/pond-wildlife-review/",{waitUntil:"domcontentloaded"});
  assert.equal(await page.locator('meta[name="robots"]').getAttribute("content"),"noindex,nofollow");
  assert.equal(await page.locator("button[data-track]").count(),2);
  assert.equal(await page.locator("#audio").evaluate(a=>a.paused),true);
  assert.ok((await page.locator("main").innerText()).includes("Nature"));
  for(const width of [320,390,760]){
   await page.setViewportSize({width,height:810});
   const d=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
   assert.ok(d<=1,"horizontal overflow "+width+": "+d);
  }
  await page.locator('button[data-track="pond-spring-review"]').click();
  await page.waitForFunction(()=>document.getElementById("audio").duration>=599,{timeout:30000});
  assert.equal(await page.locator("#audio").evaluate(a=>a.loop),true);
  await page.locator("#near").click();
  await page.waitForFunction(()=>!document.getElementById("audio").seeking&&document.getElementById("audio").currentTime>=594,{timeout:17000});
  await page.locator("#stop").click();
  assert.equal(await page.locator("#audio").evaluate(a=>a.paused),true);
  await page.locator('button[data-track="pond-night-review"]').click();
  await page.waitForFunction(()=>document.getElementById("audio").duration>=599,{timeout:30000});
  await page.locator("#verdict").selectOption("REWORK");
  await page.locator("#notes").fill("Check frogs, crickets, absence of traffic or voices, and seam.");
  await page.locator("#save").click();
  await page.reload({waitUntil:"domcontentloaded"});
  await page.locator('button[data-track="pond-night-review"]').click();
  assert.equal(await page.locator("#verdict").inputValue(),"REWORK");
  assert.equal(await page.locator("#notes").inputValue(),"Compare high surf impact and wind with Gentle Ocean Waves.");
  assert.deepEqual(errs,[]);
  console.log("POND_WILDLIFE_BROWSER_PASS two 600s masters, no autoplay, 9:55 seek, stop, 320/390/760 mobile, saved owner feedback.");
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
