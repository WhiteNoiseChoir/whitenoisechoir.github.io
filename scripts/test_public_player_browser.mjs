// Synthetic public release regression. Never creates a fake live URL.
import { chromium } from 'playwright-core';
import { readFile } from 'node:fs/promises';
const chromiumPath=process.env.CHROME_BIN||'/usr/bin/google-chrome';
const browser=await chromium.launch({headless:true,executablePath:chromiumPath,args:['--no-sandbox','--disable-dev-shm-usage']});
try{
  const page=await browser.newPage({viewport:{width:1250,height:850}});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.clock.install({time:new Date('2026-11-12T02:00:00Z')});
  const html='<html><body>'+
    '<video id="release-video"></video><audio id="release-audio" hidden></audio>'+
    '<select id="release-mode"><option value="video">Video</option><option value="audio">Audio</option></select>'+
    '<select id="release-hours"><option value="1">1</option><option value="3">3</option><option value="10" selected>10</option></select>'+
    '<button id="release-toggle">Play</button>'+
    '<p id="release-clock"></p><p id="release-message"></p>'+
    '<script id="release-data" type="application/json">'+
    '{"title":"Synthetic fixture","video":{"poster":"https://media.whitenoisechoir.com/demo/poster.jpg"},"audio":{"durationSeconds":600}}'+
    '</script></body></html>';
  await page.setContent(html,{waitUntil:'domcontentloaded'});
  await page.evaluate(()=>{
    const isPlaying=new WeakMap();
    Object.defineProperty(HTMLMediaElement.prototype,'paused',{configurable:true,get(){return !isPlaying.get(this);}});
    Object.defineProperty(HTMLMediaElement.prototype,'readyState',{configurable:true,get(){return 1;}});
    Object.defineProperty(HTMLMediaElement.prototype,'duration',{configurable:true,get(){return 600;}});
    HTMLMediaElement.prototype.play=function(){
      isPlaying.set(this,true);this.dispatchEvent(new Event('play'));
      this.dispatchEvent(new Event('playing'));return Promise.resolve();
    };
    HTMLMediaElement.prototype.pause=function(){
      if(isPlaying.get(this)){isPlaying.set(this,false);this.dispatchEvent(new Event('pause'));}
    };
  });
  await page.addScriptTag({content:await readFile('published-player.js','utf8')});
  const getClock=()=>page.locator('#release-clock').textContent();
  if(await getClock()!=='00:00:00 / 10:00:00')throw Error('10h default not initialized');
  if(!(await page.locator('#release-video').evaluate(v=>v.loop)) ||
     !(await page.locator('#release-audio').evaluate(a=>a.loop)))throw Error('Video/audio not looping');
  await page.click('#release-toggle');
  if(await page.locator('#release-toggle').textContent()!=='Pause')throw Error('Video play failed');
  await page.clock.fastForward(3600*1000);
  if(await getClock()!=='01:00:00 / 10:00:00')throw Error('Active clock wrong: '+await getClock());
  await page.locator('#release-hours').selectOption('1');
  if(!(await page.locator('#release-message').textContent()).includes('session is complete'))throw Error('Timer did not stop');
  if(await page.locator('#release-toggle').textContent()!=='Play')throw Error('Timer did not pause');
  await page.locator('#release-hours').selectOption('3');
  await page.click('#release-toggle');
  await page.locator('#release-mode').selectOption('audio');
  const ui=await page.evaluate(()=>({audioHidden:document.getElementById('release-audio').hidden,videoHidden:document.getElementById('release-video').hidden}));
  if(ui.audioHidden||!ui.videoHidden)throw Error('Audio-only controls not visible '+JSON.stringify(ui));
  await page.click('#release-toggle');
  const paused=await getClock();
  await page.clock.fastForward(7200*1000);
  if(await getClock()!==paused)throw Error('Paused clock advanced: '+paused+' -> '+await getClock());
  if(errors.length)throw Error('Page errors: '+errors.join(' | '));
  console.log('PUBLIC_PLAYER_BROWSER_PASS',JSON.stringify({default:'10h',videoLoop:true,audioLoop:true,stopAfterHour:true,audioControlsVisible:true,pausedClockStatic:true,errors:0}));
} finally {await browser.close();}
