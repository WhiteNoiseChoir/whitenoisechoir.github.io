#!/usr/bin/env node
import assert from 'node:assert/strict';
import http from 'node:http';
import {readFile,writeFile,mkdtemp,rm} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import path from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright-core';

const root=fileURLToPath(new URL('../',import.meta.url));
const mime={'.html':'text/html;charset=utf-8','.js':'application/javascript','.css':'text/css'};
const server=http.createServer(async(req,res)=>{
  try{
    const pathname=new URL(req.url,'http://localhost').pathname;
    const file=path.resolve(root,'.'+(pathname.endsWith('/')?pathname+'index.html':pathname));
    if(!file.startsWith(path.resolve(root)+path.sep))throw Error('Outside repo');
    const data=await readFile(file);
    res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream'});
    res.end(data);
  }catch{res.writeHead(404);res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url='http://127.0.0.1:'+server.address().port+'/vi/';
const chrome=process.env.CHROME_BIN||['/usr/bin/google-chrome','/usr/bin/chromium'].find(existsSync);
const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
const tmp=await mkdtemp(path.join(tmpdir(),'wnc-intent-test-'));
try{
  const context=await browser.newContext({acceptDownloads:true,viewport:{width:1440,height:940}});
  await context.route('https://fonts.googleapis.com/**',r=>r.fulfill({status:200,contentType:'text/css',body:''}));
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url,{waitUntil:'domcontentloaded'});
  await page.locator('#library-intent').waitFor();
  assert.equal(await page.locator('#library-intent option').count(),6);
  assert.equal(await page.locator('#library-count').isVisible(),true);
  await page.locator('#library-intent').selectOption('baby');
  assert.match(await page.locator('.intent-caution').textContent(),/không bảo đảm an toàn thính giác/i);
  assert.equal(await page.locator('.baby-demo-action').isVisible(),true);
  assert.equal(await page.locator('.frequency-lab').isVisible(),false);
  await page.evaluate(()=>{window.confirm=()=>true;});
  await page.locator('.baby-demo-action').click();
  assert.equal(await page.locator('#layer-count').textContent(),'2 lớp');
  assert.equal(await page.evaluate(()=>mix.intent),'baby');
  assert.match(await page.locator('#mix-review').textContent(),/không bảo đảm mức âm an toàn/i);
  const sources=await page.evaluate(()=>mix.tracks.map(t=>assets[t.asset].name));
  assert(sources.some(s=>/hồng|pink/i.test(s))&&sources.some(s=>/mưa nhẹ/i.test(s)));
  await page.locator('#library-intent').selectOption('meditation');
  assert.equal(await page.locator('.frequency-lab').isVisible(),true);
  await page.locator('.frequency-lab summary').click();
  await page.locator('.frequency-lab select').selectOption('binaural');
  const values=page.locator('.frequency-lab input');
  await values.nth(0).fill('200');
  await values.nth(1).fill('6');
  await page.locator('.frequency-lab-fields button').click();
  assert.equal(await page.locator('#layer-count').textContent(),'3 lớp');
  const last=await page.evaluate(()=>({track:mix.tracks.at(-1),asset:assets[mix.tracks.at(-1).asset]}));
  assert.equal(last.asset.synthetic.mode,'binaural');
  assert.equal(last.track.loop,true);
  assert(!last.track.assetRef,'Synthesized sources must never claim R2 SHA');
  await page.locator('#minutes').fill('0.1');
  await page.locator('#minutes').press('Tab');
  await page.locator('.project-menu summary').click();
  const [download]=await Promise.all([page.waitForEvent('download'),page.click('#save-project')]);
  const save=path.join(tmp,'mix.json');await download.saveAs(save);
  const saved=JSON.parse(await readFile(save,'utf8'));
  assert.equal(saved.length,6);
  assert(saved.tracks[0].assetKey && saved.tracks[1].assetKey,'Legacy catalog export must contain stable assetKey');
  assert.equal(saved.tracks.at(-1).generated.mode,'binaural');
  await page.locator('.project-menu summary').click();
  await page.locator('#open-project').setInputFiles({name:'saved.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(saved))});
  await page.waitForFunction(()=>/Đã mở dự án|không hợp lệ/i.test(document.querySelector('#status')?.textContent||''),{timeout:15000});
  assert.match(await page.locator('#status').textContent(),/định danh nguồn ổn định/i);
  assert.equal(await page.locator('#layer-count').textContent(),'3 lớp');
  // A pure synthesized track can render locally without ever fetching a remote asset.
  await page.evaluate(()=>{
    const id=assetForGenerated({mode:'pure',carrierHz:432,beatHz:0});
    rebuildCatalog();
    mix={title:'Tone-only QA',length:6,master:.25,tracks:[{asset:id,start:0,duration:6,gain:.2,loop:true,mute:false}]};
    selected=0;render();
  });
  await page.locator('#render').click();
  await page.waitForFunction(()=>document.querySelector('#audio-status')?.textContent.includes('Đã xuất WAV'),{timeout:90000});
  const status=await page.locator('#audio-status').textContent();
  assert(!status.includes('đỉnh âm bị cắt'),status);
  await page.goto(url+'#mix=cabin-rain-night-v3',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#layer-count')?.textContent==='24 lớp',{timeout:20000});
  assert.equal(await page.locator('#tracks .timeline-row').count(),24);
  assert.deepEqual(errors,[], 'No page exception permitted');
  console.log('STUDIO_INTENT_BROWSER_PASS',JSON.stringify({filters:6,babyTracks:2,generatedTone:true,
    savedTracks:3,roundtrip:true,wavSixSeconds:true,errors:0}));
  await context.close();
}catch(e){console.error('STUDIO_INTENT_BROWSER_FAIL',e.stack||String(e));process.exitCode=1;}
finally{await browser.close();await new Promise(resolve=>server.close(resolve));await rm(tmp,{recursive:true,force:true});}
