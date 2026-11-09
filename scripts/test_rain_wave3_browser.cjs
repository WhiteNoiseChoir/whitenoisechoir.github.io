#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {chromium}=require("playwright");
(async()=>{
 const executablePath=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(fs.existsSync);
 const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox"]});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on("pageerror",x=>errors.push(String(x)));
  await page.goto("http://127.0.0.1:8787/signature/rain-wave3-review/",{waitUntil:"domcontentloaded"});
  assert.equal(await page.locator('meta[name="robots"]').getAttribute("content"),"noindex,nofollow");
  assert.equal(await page.locator("button[data-track]").count(),2);
  assert.equal(await page.locator("#audio").evaluate(el=>el.paused),true,"no autoplay");
  for(const width of [320,390]){
   await page.setViewportSize({width,height:740});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
   assert.ok(overflow<=1,"mobile overflow at "+width+": "+overflow);
  }
  await page.locator('button[data-track="rain-leaves-review"]').click();
  await page.waitForFunction(()=>document.getElementById("audio").duration>=599,{timeout:30000});
  assert.equal(await page.locator("#audio").evaluate(x=>x.loop),true);
  await page.locator("#near").click();
  await page.waitForFunction(()=>!document.getElementById("audio").seeking&&document.getElementById("audio").currentTime>=594,{timeout:16000});
  await page.locator("#stop").click();
  assert.equal(await page.locator("#audio").evaluate(x=>x.paused),true);
  await page.locator('button[data-track="rain-lake-review"]').click();
  await page.waitForFunction(()=>document.getElementById("audio").duration>=599,{timeout:30000});
  await page.locator("#verdict").selectOption("REWORK");
  await page.locator("#notes").fill("Review loop and lake water identity.");
  await page.locator("#save").click();
  await page.reload({waitUntil:"domcontentloaded"});
  await page.locator('button[data-track="rain-lake-review"]').click();
  assert.equal(await page.locator("#verdict").inputValue(),"REWORK");
  assert.equal(await page.locator("#notes").inputValue(),"Review loop and lake water identity.");
  assert.equal(errors.length,0,"browser JS errors: "+errors.join(" | "));
  console.log("RAIN_WAVE3_BROWSER_PASS two real 10-min masters; no autoplay; 9:55 seek; mobile 320/390; persisted owner verdict.");
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
