#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const BASE="http://127.0.0.1:8787";
(async()=>{
 const executablePath=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(x=>fs.existsSync(x));
 const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox"]});
 const errors=[];
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
  // Exercise the legacy browser against its archived listing.
  await page.route(BASE+"/sounds/",route=>route.continue({url:BASE+"/sounds/archive.html"}));
  page.on("pageerror",e=>errors.push(String(e)));
  await page.goto(BASE+"/sounds/explore/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelector("#stat-items")?.textContent==="532",{timeout:30000}).catch(async()=>{
    throw new Error("Inventory did not render: "+(await page.locator("#count").textContent()));
  });
  assert.equal(await page.locator("#stat-groups").textContent(),"28");
  assert.equal(await page.locator("#stat-live").textContent(),"35");
  assert.equal(await page.locator("#hub-list .hub").count(),18);
  assert.equal(await page.locator("#hub-list a").count(),18,"12 old hubs plus six new planned hubs");
  assert.equal(await page.locator('#hub-list a[href="/sounds/bird-sounds/"]').count(),1,"new birds hub reachable");
  assert.equal(await page.locator("audio").count(),0,"never fake playable controls");
  assert.ok((await page.locator("#count").textContent()).includes("532 matching"));
  await page.locator("#q").fill("Rain");
  assert.ok((await page.locator("#count").textContent()).match(/\b[1-9][0-9]* matching/),"rain search has results");
  assert.ok(!(await page.locator("#count").textContent()).includes("532 matching"),"search actually filters");
  await page.locator("#q").fill("");
  await page.locator("#group").selectOption("insects-amphibians");
  const options=await page.locator("#subgroup option").allTextContents();
  assert.ok(options.some(x=>x.toLowerCase().includes("insects")),"insects subgroup");
  assert.ok(options.some(x=>x.toLowerCase().includes("amphibians")),"amphibians subgroup");
  await page.locator("#subgroup").selectOption("amphibians");
  assert.ok((await page.locator("#count").textContent()).includes("matching editorial records"),"subgroup filter works");
  await page.locator("#reset").click();
  await page.locator('[data-intent="sleep"]').click();
  assert.equal(await page.locator('[data-intent="sleep"]').getAttribute("aria-pressed"),"true");
  assert.ok(!(await page.locator("#count").textContent()).includes("532 matching"),"sleep suggestions reduce records");
  await page.locator('[data-intent="baby"]').click();
  assert.equal(await page.locator('[data-intent="baby"]').getAttribute("aria-pressed"),"true");
  await page.locator("#reset").click();
  await page.locator("#status").selectOption("live");
  assert.ok((await page.locator("#count").textContent()).includes("35 matching"),"production filter maps 35 real catalog IDs");
  assert.ok((await page.locator("a").evaluateAll(els=>els.some(e=>e.textContent?.includes("Open existing sound page")))),"live entries link to sound pages");
  await page.locator("#status").selectOption("planned");
  assert.equal(await page.locator('a:has-text("Open existing sound page")').count(),0,"planned cards not playable");
  for(const width of [320,390,768]){
    await page.setViewportSize({width,height:820});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
    assert.ok(overflow<=2,"horizontal overflow at "+width+": "+overflow);
  }
  await page.goto(BASE+"/sounds/",{waitUntil:"domcontentloaded"});
  assert.equal(await page.locator('a[href="/sounds/explore/"]').count(),1,"hub visibly links to public explorer");
  assert.deepEqual(errors,[],"no browser console JavaScript errors");
  console.log("PASS browser: 532 records / 28 groups / 35 actual, intent and subgroup filters, no fake audio, 320/390px responsive");
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack||e);process.exit(1)});
