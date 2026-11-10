#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const config=JSON.parse(fs.readFileSync("catalog/framework-hubs-c4.json","utf8"));
const BASE="http://127.0.0.1:8787";
(async()=>{
 const executablePath=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(x=>fs.existsSync(x));
 const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox"]});
 const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"}),errors=[];
 page.on("pageerror",err=>errors.push(String(err)));
 try{
  for(const hub of config.hubs){
   await page.goto(BASE+hub.route,{waitUntil:"domcontentloaded"});
   assert.equal(await page.locator("h1").textContent(),hub.title);
   assert.equal(await page.locator('[data-sound-row]').count(),config.expected_counts[hub.id]);
   assert.equal(await page.locator("audio").count(),0);
   assert.equal(await page.locator('meta[name="robots"]').getAttribute("content"),"noindex,follow");
   const first=await page.locator('[data-sound-row] h3').first().textContent();
   await page.locator("#q").fill(first);
   const visible=await page.locator('[data-sound-row]:visible').count();
   assert.ok(visible>=1&&visible<config.expected_counts[hub.id],"client search must filter "+hub.slug);
   await page.locator("#clear").click();
   assert.equal(await page.locator('[data-sound-row]:visible').count(),config.expected_counts[hub.id]);
   if(hub.id==="insects-amphibians"){
    await page.locator("#subgroup").selectOption("amphibians");
    assert.ok((await page.locator('[data-sound-row]:visible').count())>0,"amphibians subgroup has items");
    assert.ok((await page.locator('[data-sound-row]:visible').count())<config.expected_counts[hub.id],"subgroup filters other creatures");
   }
   await page.locator("#clear").click();
   for(const width of [320,390,768]){
    await page.setViewportSize({width,height:840});
    const over=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
    assert.ok(over<=2,hub.slug+" overflow at "+width+"px: "+over);
   }
  }
  await page.goto(BASE+"/sounds/explore/?group=birds-birdsong",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelector("#stat-items")?.textContent==="532",{timeout:30000});
  assert.equal(await page.locator("#group").inputValue(),"birds-birdsong","deep link presets 28-group filter");
  assert.equal(await page.locator('#hub-list a').count(),18);
  assert.deepEqual(errors,[],"no browser JavaScript errors");
  console.log("PASS C4 browser: six public hub pages, filtering and 320/390/768 responsive; explorer deep link selects correct family");
 }finally{await browser.close();}
})().catch(err=>{console.error(err.stack||err);process.exit(1)});
