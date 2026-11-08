#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const ROOT="http://127.0.0.1:8787";
(async()=>{
const executablePath=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(fs.existsSync);
const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
try{
 const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
 const errors=[];page.on("pageerror",e=>errors.push(String(e)));
 await page.goto(ROOT+"/signature/rain-wave2-review/",{waitUntil:"domcontentloaded"});
 assert.equal(await page.locator('meta[name="robots"]').getAttribute("content"),"noindex,nofollow");
 assert.equal(await page.locator("button[data-track]").count(),3);
 assert.equal(await page.locator("audio#audio").evaluate(e=>e.paused),true);
 for(const width of [320,390]){
  await page.setViewportSize({width,height:760});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
  assert.ok(overflow<=1,"no 320/390 overflow: "+width+" overflow="+overflow);
 }
 await page.locator('button[data-track="rain-on-tent-review"]').click();
 await page.waitForFunction(()=>document.querySelector("#audio").duration>=599,null,{timeout:25000});
 assert.equal(await page.locator("#audio").evaluate(e=>e.loop),true);
 await page.locator("#near").click();
 await page.waitForFunction(()=>{const a=document.querySelector("#audio");return !a.seeking&&a.currentTime>=594},null,{timeout:16000});
 await page.locator("#stop").click();
 assert.equal(await page.locator("#audio").evaluate(e=>e.paused),true);
 await page.locator('button[data-track="rain-car-roof-review"]').click();
 await page.waitForFunction(()=>document.querySelector("#audio").duration>=599,null,{timeout:25000});
 await page.locator("#verdict").selectOption("REWORK");
 await page.locator("#notes").fill("Original source is mono; preserve clear car roof identity and evaluate repetition.");
 await page.locator("#save").click();
 await page.reload({waitUntil:"domcontentloaded"});
 await page.locator('button[data-track="rain-car-roof-review"]').click();
 assert.equal(await page.locator("#verdict").inputValue(),"REWORK");
 assert.equal(await page.locator("#notes").inputValue(),"Original source is mono; preserve clear car roof identity and evaluate repetition.");
 await page.locator('button[data-track="rolling-thunder-review"]').click();
 await page.waitForFunction(()=>document.querySelector("#audio").duration>=599,null,{timeout:25000});
 assert.equal(await page.locator("#audio").getAttribute("src"),"./rolling-thunder-review.mp3");
 assert.equal(errors.length,0,"browser JS errors: "+errors.join(" | "));
 console.log("RAIN_WAVE2_BROWSER_PASS: no autoplay, 3 real 600s MP3, 9:55 seek, owner review local storage, 320/390 widths, noindex");
}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
