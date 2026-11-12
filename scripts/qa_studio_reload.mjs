// Verify that V4/V5 remain playable through an F5-equivalent reload.
// Runs in a real headless Chromium browser, not a static JS syntax checker.
import { chromium } from 'playwright-core';

const base=process.env.STUDIO_URL_BASE||'https://whitenoisechoir.com';
const chrome=process.env.CHROME_BIN||'/usr/bin/google-chrome';
const browser=await chromium.launch({
  headless:true, executablePath:chrome,
  args:['--no-sandbox','--disable-dev-shm-usage','--autoplay-policy=no-user-gesture-required']
});
const contexts=[];
let failures=0;
try {
  for(const [slug,expected] of [['Living-Forest-Creek',30],['The-Forest-Is-Alive-Tonight',31]]){
    const context=await browser.newContext({viewport:{width:1440,height:900}});
    contexts.push(context);
    const page=await context.newPage();
    const logs=[];
    page.on('pageerror',error=>logs.push('PAGE_ERROR '+error.message));
    page.on('console',message=>{if(message.type()==='error')logs.push('CONSOLE '+message.text().slice(0,250));});
    const url=base+'/vi/'+slug+'/?qa=reload-'+Date.now();
    await page.goto(url,{waitUntil:'domcontentloaded',timeout:75000});
    await page.waitForFunction(()=>document.querySelector('#tracks')?.children.length>5,{timeout:35000});
    const first=await page.locator('#tracks .timeline-row').count();
    if(first!==expected)throw Error(slug+' Unexpected tracks '+first+' expected '+expected);
    // Reproduce a user with an existing localStorage mix from the earlier
    // version, when only 28/29 tracks were present.
    await page.evaluate(()=>{
      const trial=document.querySelector('#studio-trial');
      const slug=JSON.parse(trial.textContent).slug;
      const key='wnc.studio.trial.'+slug;
      let old=JSON.parse(localStorage.getItem(key)||trial.textContent);
      if(old.project)old=old.project;
      if(old.tracks.length>2)old.tracks=old.tracks.slice(0,-2);
      localStorage.setItem(key,JSON.stringify(old));
    });
    for(let attempt=1;attempt<=2;attempt++){
      await page.reload({waitUntil:'domcontentloaded',timeout:75000});
      await page.waitForFunction(()=>document.querySelector('#tracks')?.children.length>5,{timeout:30000});
      await page.click('#play',{timeout:12000});
      await page.waitForFunction(()=>{
        const button=document.querySelector('#play');
        const label=button?.textContent||'';
        const status=document.querySelector('#status')?.textContent||'';
        if(status.includes('Không tải được các lớp:')||status.includes('Không tải được âm thanh'))return true;
        return label.includes('Tạm dừng');
      },{timeout:160000});
      const report=await page.evaluate(()=>{
        const source=document.querySelector('#source-diagnostics');
        const errorNodes=[...source.querySelectorAll('.source-diagnostic-row.failed')].map(x=>x.textContent);
        const statuses=[...source.querySelectorAll('.source-diagnostic-row')].map(x=>x.textContent);
        return {
          label:document.querySelector('#play')?.textContent,
          status:document.querySelector('#status')?.textContent,
          summary:source.querySelector('summary')?.textContent,
          errors:errorNodes,
          warningCount:statuses.filter(x=>x.includes('Nguồn yếu')).length,
          tracks:document.querySelector('#tracks')?.children.length
        };
      });
      console.log('STUDIO_BROWSER_RELOAD_QA',JSON.stringify({slug,attempt,...report}));
      if(!report.label?.includes('Tạm dừng')||report.errors.length)
        throw Error(slug+' on attempt '+attempt+' : '+JSON.stringify(report));
      await page.click('#play');
    }
    if(logs.length)console.log('STUDIO_BROWSER_CONSOLE',JSON.stringify({slug,logs:logs.slice(0,15)}));
  }
} catch(e){
  failures++;
  console.error('STUDIO_BROWSER_RELOAD_FAIL',String(e?.stack||e));
  process.exitCode=1;
} finally {
  await Promise.allSettled(contexts.map(c=>c.close()));
  await browser.close();
}
console.log('STUDIO_BROWSER_RELOAD_SUMMARY',JSON.stringify({failures}));
