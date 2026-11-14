#!/usr/bin/env node
// WhiteNoiseChoir real Studio engine + actual R2 audio in headless Chromium.
// Serve checkout files at the real site origin; does not bypass a user's login.
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';
const root=process.cwd();
const title='cabin-beside-waterfall-v1';
const chrome=process.env.CHROME_BIN||'/usr/bin/google-chrome';
const report={slug:title,uniqueSourcesExpected:5,tracks:0,summary:null,errors:[],status:null,playButton:null,pass:false,siteFilesFromCheckout:true,realR2:true};
const browser=await chromium.launch({headless:true,executablePath:chrome,args:['--no-sandbox','--disable-dev-shm-usage','--autoplay-policy=no-user-gesture-required']});
const context=await browser.newContext({viewport:{width:1440,height:900}});
const page=await context.newPage();
const failures=[],badResponses=[],consoleErrors=[];
page.on('response',r=>{if(r.status()>=400)badResponses.push({url:r.url(),status:r.status()});});
page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text());});
page.on('pageerror',error=>failures.push(error.message));
try{
 await page.route('https://whitenoisechoir.com/**',async route=>{
  const url=new URL(route.request().url());
  let name=decodeURIComponent(url.pathname).replace(/^\/+/,'');
  if(!name||name.endsWith('/'))name+='index.html';
  const file=path.resolve(root,name);
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file))return route.fulfill({status:404,body:'Not found'});
  const type=file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.json')?'application/json':'text/html';
  return route.fulfill({status:200,contentType:type,body:fs.readFileSync(file)});
 });
 await page.goto('https://whitenoisechoir.com/vi/'+title+'/',{waitUntil:'domcontentloaded',timeout:40000});
 report.beforeWait=await page.evaluate(()=>({url:location.href,title:document.title,readyState:document.readyState,tracks:document.querySelectorAll('#tracks .timeline-row').length,hasTracks:!!document.querySelector('#tracks'),scripts:[...document.scripts].map(x=>x.src||x.id),bodyText:document.body?.innerText?.slice(0,400)}));
 await page.waitForFunction(()=>document.querySelectorAll('#tracks .timeline-row').length===10,null,{timeout:45000});
 report.tracks=await page.locator('#tracks .timeline-row').count();
 await page.click('#play',{timeout:12000});
 await page.waitForFunction(()=>{
  const b=document.querySelector('#play')?.textContent||'';
  const status=document.querySelector('#status')?.textContent||'';
  if(status.includes('Không tải được')||status.includes('không phát')||status.includes('thất bại'))return true;
  return b.includes('Tạm dừng');
 },{timeout:170000});
 const info=await page.evaluate(()=>{
  const el=document.querySelector('#source-diagnostics');
  return {summary:el?.querySelector('summary')?.textContent||'',status:document.querySelector('#status')?.textContent||'',playButton:document.querySelector('#play')?.textContent||'',errors:[...(el?.querySelectorAll('.source-diagnostic-row.failed')||[])].map(x=>x.textContent)};
 });
 Object.assign(report,info);
 report.pass=report.tracks===10 && info.errors.length===0 && info.summary.includes('5/5 nguồn đã tải') && info.playButton.includes('Tạm dừng') && failures.length===0;
 if(!report.pass)throw Error('Studio did not reach playing without source errors');
 await page.click('#play');
}catch(e){report.error=String(e.message||e);report.pass=false;report.afterFailure=await page.evaluate(()=>({url:location.href,title:document.title,tracks:document.querySelectorAll('#tracks .timeline-row').length,bodyText:document.body?.innerText?.slice(0,1000),status:document.querySelector('#status')?.textContent})).catch(()=>null);}
finally{report.pageErrors=failures.slice(0,10);report.badResponses=badResponses.slice(0,10);report.consoleErrors=consoleErrors.slice(0,10);await context.close();await browser.close();}
fs.writeFileSync('cabin-waterfall-studio-browser-qa.json',JSON.stringify(report,null,2));
fs.writeFileSync('cabin-waterfall-studio-browser-qa.md',
 '## Cabin Beside Waterfall V1 · real Studio + R2 browser test\n\n- Tracks: '+report.tracks+
 '\n- Player: '+report.playButton+'\n- Sources: '+report.summary+
 '\n- Result: '+(report.pass?'PASS':'FAIL')+'\n- Error: '+(report.error||'none')+
 '\n\nThis test loads actual Studio source files from the PR at site origin and the actual R2 audio. It does NOT prove authenticated live deploy or Safari playback.\n');
console.log('SLEEPING_LAKE_STUDIO_BROWSER_QA',JSON.stringify(report));
if(!report.pass)process.exitCode=1;
