import assert from 'node:assert/strict';
import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createRequire} from 'node:module';

const root = fileURLToPath(new URL('../',import.meta.url));
const require = createRequire(import.meta.url);
const {chromium} = require('playwright');
const wav = Buffer.alloc(44 + 44100 * 8 * 2);
wav.write('RIFF',0); wav.writeUInt32LE(wav.length-8,4); wav.write('WAVEfmt ',8);
wav.writeUInt32LE(16,16); wav.writeUInt16LE(1,20); wav.writeUInt16LE(1,22); wav.writeUInt32LE(44100,24);
wav.writeUInt32LE(88200,28); wav.writeUInt16LE(2,32); wav.writeUInt16LE(16,34); wav.write('data',36);
wav.writeUInt32LE(wav.length-44,40);
for(let i=0;i<44100*8;i++) wav.writeInt16LE(Math.round(7200*Math.sin(2*Math.PI*330*i/44100)),44+i*2);

const mime = {'.html':'text/html; charset=utf-8','.js':'application/javascript','.css':'text/css'};
const server = http.createServer(async (req,res) => {
  try {
    let p = new URL(req.url,'http://localhost').pathname;
    if (p === '/') p = '/index.html';
    if (p.startsWith('/audio/')) {res.writeHead(200,{'Content-Type':'audio/wav'}); res.end(wav); return;}
    const file = path.resolve(root, '.' + (p.endsWith('/') ? p + 'index.html' : p));
    if (!file.startsWith(path.resolve(root) + path.sep)) {res.writeHead(404);res.end();return;}
    const content = await readFile(file);
    res.writeHead(200,{'Content-Type':mime[path.extname(file)] ?? 'application/octet-stream'});
    res.end(content);
  } catch {res.writeHead(404); res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const host='http://127.0.0.1:'+server.address().port;
let browser;
try {
  const executablePath = process.env.WNC_TEST_CHROMIUM || ['/usr/bin/google-chrome','/usr/bin/chromium'].find(existsSync);
  browser=await chromium.launch({executablePath,headless:true,args:['--disable-background-networking','--autoplay-policy=no-user-gesture-required']});
  const context=await browser.newContext({viewport:{width:1440,height:960},acceptDownloads:true});
  await context.route('https://media.whitenoisechoir.com/**',r=>r.fulfill({status:200,contentType:'audio/wav',headers:{'Access-Control-Allow-Origin':'*'},body:wav}));
  await context.route('https://fonts.googleapis.com/**',r=>r.fulfill({status:200,contentType:'text/css',body:''}));
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(host+'/vi/#mix=cabin-rain-night-v3');
  await page.locator('#layer-count').waitFor();
  assert.equal(await page.locator('#layer-count').textContent(),'24 lớp');
  assert.match(await page.locator('#library-count').textContent(), /^([1-9]\d*)\/\1$/);

  await page.locator('#library-query').fill('mua tren mai');
  assert.equal(await page.locator('.library-item strong').first().textContent(),'Mưa trên mái');
  await page.locator('#seek').evaluate(el=>{el.value='12.5';el.dispatchEvent(new Event('input'));});
  await page.getByRole('button',{name:'Thêm Mưa trên mái',exact:true}).click();
  assert.equal(await page.locator('#layer-count').textContent(),'25 lớp');
  assert.equal(await page.getByLabel('Bắt đầu (giây)',{exact:true}).inputValue(),'12.5');
  const volume=()=>page.getByLabel('Âm lượng (%)',{exact:true});
  const edit=async (field,value)=>{await field.fill(value);await field.press('Tab');};
  await edit(volume(),'42');
  await edit(page.getByLabel('Fade in (giây)',{exact:true}),'1.3');
  await page.locator('#undo').click();
  assert.equal(await page.getByLabel('Fade in (giây)',{exact:true}).inputValue(),'');
  await page.locator('#redo').click();
  assert.equal(await page.getByLabel('Fade in (giây)',{exact:true}).inputValue(),'1.3');
  await page.locator('#zoom').selectOption('4');
  assert.ok(await page.locator('#timeline-scroll').evaluate(el=>el.scrollWidth>el.clientWidth));
  await page.reload();
  assert.equal(await page.locator('#layer-count').textContent(),'25 lớp');
  await page.getByRole('button',{name:'Chọn lớp 25: Mưa trên mái',exact:true}).click();
  assert.equal(await volume().inputValue(),'42');
  assert.equal(await page.getByLabel('Fade in (giây)',{exact:true}).inputValue(),'1.3');
  console.log('PASS legacy preset, accentless search, place at playhead, edit, history, zoom and reload');

  await page.locator('.project-menu summary').click();
  const jsonDownload=page.waitForEvent('download');
  await page.locator('#save-project').click();
  const jsonFile=await jsonDownload;
  const saved=JSON.parse(await readFile(await jsonFile.path(),'utf8'));
  assert.equal(saved.tracks[24].gain,.42);
  assert.equal(saved.tracks[24].fadeIn,1.3);
  await page.locator('.project-menu summary').click();
  await page.locator('#clear').click();
  assert.equal(await page.locator('#layer-count').textContent(),'0 lớp');
  await page.locator('#open-project').setInputFiles({name:'test.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(saved))});
  await page.waitForFunction(()=>document.querySelector('#layer-count').textContent==='25 lớp');
  await page.locator('.project-menu summary').click();
  await page.locator('#clear').click();
  console.log('PASS project JSON download and import');

  await page.locator('#library-query').fill('ocean waves');
  assert.ok(await page.getByRole('button',{name:'Thêm Sóng biển',exact:true}).count());
  await page.getByRole('button',{name:'Nghe thử Sóng biển',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('#library-audio').paused);
  await page.getByRole('button',{name:'Dừng nghe Sóng biển',exact:true}).click();
  await page.getByRole('button',{name:'Thêm Sóng biển',exact:true}).click();
  await edit(page.locator('#minutes'),'0.1');
  await edit(volume(),'100');
  await edit(page.getByLabel('Pan đầu (%)',{exact:true}),'100');
  await edit(page.getByLabel('Fade in (giây)',{exact:true}),'1');
  await page.locator('#master').evaluate(el=>{el.value='50';el.dispatchEvent(new Event('input'));el.dispatchEvent(new Event('change'));});
  await page.locator('#play').click();
  await page.waitForFunction(()=>document.querySelector('#peak').value>-60);
  await page.locator('#play').click();
  await page.locator('#render').click();
  await page.locator('#audio-result a').waitFor();
  const rendered=page.waitForEvent('download');
  await page.locator('#audio-result a').click();
  const output=await readFile(await (await rendered).path());
  assert.equal(output.toString('ascii',0,4),'RIFF');
  assert.equal(output.readUInt16LE(22),2);
  assert.equal(output.readUInt32LE(24),44100);
  assert.equal(output.readUInt32LE(40)/4/44100,6);
  let left=0,right=0,opening=0;
  for(let i=44;i+4<=output.length;i+=4){
    left=Math.max(left,Math.abs(output.readInt16LE(i)));
    right=Math.max(right,Math.abs(output.readInt16LE(i+2)));
    if(i<44+44100*.1*4) opening=Math.max(opening,Math.abs(output.readInt16LE(i+2)));
  }
  assert.ok(left<15&&right>3300&&right<3900&&opening<450,JSON.stringify({left,right,opening}));
  console.log('PASS preview, live peak meter and 6-second stereo WAV master gain, fade and pan');

  const publicPage=await context.newPage();
  await publicPage.goto(host+'/');
  assert.equal(await publicPage.locator('html').getAttribute('lang'),'en');
  assert.equal(await publicPage.locator('h1').textContent(),'Sound Studio');
  assert.equal(await publicPage.locator('#vault-form,#video-studio,#video-input,#render-video,#mux-video,#video-prompt').count(),0);
  assert.ok(await publicPage.locator('#render').isVisible());
  assert.equal(await publicPage.locator('#preset optgroup option').count(),45);
  await publicPage.locator('#preset').selectOption('cabin-rain-night-v3');
  assert.equal(await publicPage.locator('#layer-count').textContent(),'24 tracks');
  assert.match(await publicPage.locator('#library-count').textContent(), /^([1-9]\d*)\/\1$/);
  await publicPage.goto(host+'/vi/cabin-rain-night-v3/');
  assert.equal(await publicPage.locator('#layer-count').textContent(),'24 lớp');
  assert.equal(await publicPage.locator('meta[name=robots]').getAttribute('content'),'noindex,nofollow');
  await publicPage.goto(host+'/sounds/');
  await publicPage.waitForURL(host+'/library/');
  const reviewed=JSON.parse(await readFile(path.join(root,'data/published-mixes.json'),'utf8')).filter(row=>row.status==='published');
  assert.equal(await publicPage.locator('article').count(),reviewed.length);
  assert.equal(await publicPage.locator('a[href*="/vi/cabin-rain-night-v3/"]').count(),0);
  console.log('PASS English audio mixer, Vietnamese trial and approval-only public library');
  const mobile=await context.newPage();
  await mobile.setViewportSize({width:390,height:844});
  await mobile.goto(host+'/vi/#mix=cabin-rain-night-v3');
  assert.equal(await mobile.locator('#layer-count').textContent(),'24 lớp');
  assert.ok(await mobile.evaluate(()=>document.documentElement.scrollWidth===innerWidth));
  const listener=await context.newPage();
  await listener.goto(host+'/sounds/rain-on-window/');
  await listener.waitForFunction(()=>window.WNCBridge?.rows?.length===45);
  await listener.evaluate(()=>window.WNCBridge.play(['rain-on-window-real'],'Rain on Window'));
  await listener.waitForFunction(()=>window.WNCBridge.snapshot().playing);
  await listener.locator('#wnc-mini-open').click();
  await listener.waitForURL(host+'/listen.html');
  assert.equal(await listener.evaluate(()=>window.WNCBridge.snapshot().playing),true);
  assert.equal(await listener.evaluate(()=>window.WNCBridge.recipes.length),45);
  await listener.goto(host+'/?sound=pink-noise');
  await listener.waitForURL(host+'/listen.html?sound=pink-noise');
  await listener.waitForFunction(()=>window.WNCBridge?.snapshot().activeIds[0]==='pink-noise');
  console.log('PASS the shared continuous player, 45 legacy presets and the old sound deep link');
  assert.deepEqual(errors,[]);
  console.log('PASS 390 px layout without horizontal page overflow');
} finally {await browser?.close();server.close();}
