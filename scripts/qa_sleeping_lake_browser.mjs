#!/usr/bin/env node
// Actual headless Chromium WebAudio.decodeAudioData check with the real R2 media URL.
import fs from "node:fs";
import { chromium } from "playwright-core";
const rows=[
 ["issyk_lake","asset-library/raw/sha256/a5/a512974fcff448950f86fa26d07fbb8d52b55e8cbdf24e8d721f42161a1d7f53.ogg"],
 ["gem_wind","asset-library/raw/sha256/aa/aa4bd8042d04eb6b956bc1721fe6856145526bda5ff89edd8bc78559cd38451c.mp3"],
 ["park_wind","asset-library/raw/sha256/5c/5c381856745b4706e7eba55eb9271a61a530e90c05df8126adb2db89ecfa6c5a.wav"],
 ["yellowstone_lake","asset-library/raw/sha256/60/602ab26a5e5f8a3a99b254bd03af0676d94eb04a679b95a8f7219700a991d3fd.mp3"]
];
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BIN||"/usr/bin/google-chrome",args:["--no-sandbox","--disable-dev-shm-usage","--autoplay-policy=no-user-gesture-required"]});
const report=[];
for(const [name,key] of rows){
 const context=await browser.newContext();
 const page=await context.newPage();
 await page.route("https://whitenoisechoir.com/audio-qa-stub",r=>r.fulfill({status:200,contentType:"text/html",body:"<!doctype html><html><title>R2 decode QA</title></html>"}));
 const row={name,key};
 try{
  await page.goto("https://whitenoisechoir.com/audio-qa-stub",{waitUntil:"domcontentloaded",timeout:30000});
  const x=await page.evaluate(async key=>{
   const url="https://media.whitenoisechoir.com/"+key;
   const response=await fetch(url,{mode:"cors",cache:"no-store",signal:AbortSignal.timeout(150000)});
   if(!response.ok)throw Error("HTTP "+response.status);
   const bytes=await response.arrayBuffer();
   const context=new AudioContext();
   const buffer=await context.decodeAudioData(bytes);
   const c=buffer.getChannelData(0);let sum=0,count=0,peak=0;
   for(let i=0;i<c.length;i+=1024){sum+=c[i]*c[i];peak=Math.max(peak,Math.abs(c[i]));count++;}
   const out={decoded:true,seconds:buffer.duration,sampleRate:buffer.sampleRate,channels:buffer.numberOfChannels,bytes:bytes.byteLength,rmsSample:Math.sqrt(sum/count),peakSample:peak};
   await context.close();
   return out;
  },key);
  Object.assign(row,x);
 }catch(e){row.decoded=false;row.error=String(e.message||e).slice(0,400);}
 report.push(row);
 console.log("SLEEPING_LAKE_BROWSER",JSON.stringify(row));
 await context.close();
}
await browser.close();
fs.writeFileSync("sleeping-lake-browser-qa.json",JSON.stringify(report,null,2));
const md=["## Sleeping Lake — Chromium WebAudio decode report",""];
for(const x of report)md.push("- "+x.name+": "+(x.decoded?"PASS":"FAIL")+"; "+(x.error||("seconds="+x.seconds+"; rate="+x.sampleRate+"; channels="+x.channels)));
md.push("","Test runs in headless Chromium with CORS origin whitenoisechoir.com. It does not prove Safari, Chrome desktop audio quality, or complete Studio timeline playback.");
fs.writeFileSync("sleeping-lake-browser-summary.md",md.join("\n"));
if(report.some(x=>!x.decoded))process.exitCode=1;
