// Real browser QA for the exact six nature assets in the Rainy Valley mix.
// No local piano: detects whether nature layers can decode and actually play.
import {chromium} from 'playwright-core';
const base=process.env.STUDIO_URL_BASE||'https://whitenoisechoir.com';
const chrome=process.env.CHROME_BIN||'/usr/bin/google-chrome';
const browser=await chromium.launch({
  executablePath:chrome,headless:true,
  args:['--no-sandbox','--disable-dev-shm-usage','--autoplay-policy=no-user-gesture-required']
});
const nature=[
 ['audio/rain-on-window-real.mp3',0.53],
 ['audio/heavy-rain-real.mp3',0.47],
 ['audio/rain-leaves-real.mp3',0.23],
 ['audio/forest-stream-real.mp3',0.13],
 ['audio/fireplace-real.mp3',0.045],
 ['audio/wind-synth.mp3',0.035]
];
const payload={title:'Rainy Valley nature playback QA',length:600,master:0.72,
 tracks:nature.map(([assetKey,gain])=>({assetKey,gain,start:0,loop:true,mute:false}))};
const context=await browser.newContext({viewport:{width:1440,height:900}});
const page=await context.newPage();
try {
  const logs=[];
  page.on('console',m=>{if(m.type()==='error')logs.push(m.text().slice(0,240))});
  page.on('pageerror',e=>logs.push(e.message.slice(0,240)));
  const response=await page.goto(base+'/vi/?qa=rainy-nature-'+Date.now(),{waitUntil:'domcontentloaded',timeout:75000});
  console.log('RAINY_BROWSER_PAGE',response?.status(),page.url());
  await page.waitForSelector('#open-project',{timeout:30000});
  await page.locator('#open-project').setInputFiles({
    name:'rainy-nature-qa.json',mimeType:'application/json',
    buffer:Buffer.from(JSON.stringify(payload))
  });
  await page.waitForFunction(()=>document.querySelectorAll('#tracks .timeline-row').length===6,{timeout:30000});
  await page.locator('#play').click({timeout:12000});
  await page.waitForFunction(()=>{
    const btn=document.querySelector('#play')?.textContent||'';
    const msg=document.querySelector('#status')?.textContent||'';
    return btn.includes('Tạm dừng') || msg.includes('Không tải được');
  },{timeout:175000});
  const report=await page.evaluate(()=>{
    const d=document.querySelector('#source-diagnostics');
    return {
      status:document.querySelector('#status')?.textContent,
      button:document.querySelector('#play')?.textContent,
      diagnostics:d?.querySelector('summary')?.textContent,
      errors:[...(d?.querySelectorAll('.source-diagnostic-row.failed')||[])].map(x=>x.textContent),
      allRows:[...(d?.querySelectorAll('.source-diagnostic-row')||[])].map(x=>x.textContent),
      effectiveSolo:typeof soloTrack === 'undefined'? 'unavailable':!!soloTrack
    };
  });
  console.log('RAINY_BROWSER_RESULT',JSON.stringify(report));
  console.log('RAINY_BROWSER_CONSOLE',JSON.stringify(logs.slice(0,20)));
  if(report.errors.length || !report.button?.includes('Tạm dừng') || !/6\/6/.test(report.diagnostics||''))process.exitCode=1;
} catch(e){
  console.error('RAINY_BROWSER_ERROR',String(e.stack||e));
  process.exitCode=1;
} finally {await context.close();await browser.close();}
