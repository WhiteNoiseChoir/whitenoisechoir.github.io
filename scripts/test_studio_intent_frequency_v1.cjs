#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const root=__dirname+'/..';
const engine=fs.readFileSync(root+'/studio-engine.js','utf8');
const ui=fs.readFileSync(root+'/studio-ui.js','utf8');
const page=fs.readFileSync(root+'/vi/index.html','utf8');
assert(page.includes('studio-ui.js?v=owner-ai-r2-20261119&amp;public=20261120'),
  'Vietnamese Studio must load the owner-music-compatible UI with a fresh public-catalog cache key');
const catalog=fs.readFileSync(root+'/studio-catalog.js','utf8');
const matches=catalog.match(/const studioPublishedAssets\s*=\s*(\[[\s\S]*?\]);/);
assert(matches,'Catalog must be parseable');
const entries=JSON.parse(matches[1]);
assert(entries.length>=98,'Append-only existing Studio assets must survive');
const assets=[{name:'Old source',key:'audio/first.mp3',duration:600},...entries];
const a=engine.indexOf('const generatedToneIds = new Map()');
const b=engine.indexOf('const rawAssetIndex = new Map()',a);
const partial=engine.slice(a,b);
assert(a>=0&&b>a,'Generated asset functions must exist');
const context={assets,Map,Number,Math};
vm.runInNewContext(partial+'\nthis.testApi={toneSpec,assetForGenerated};',context);
const good=context.testApi.toneSpec({mode:'binaural',carrierHz:200,beatHz:6});
assert(good && good.beatHz===6 && good.carrierHz===200);
assert.equal(context.testApi.toneSpec({mode:'binaural',carrierHz:200,beatHz:900}),null);
assert.equal(context.testApi.toneSpec({mode:'pure',carrierHz:0,beatHz:0}),null);
const i=context.testApi.assetForGenerated(good);
assert.equal(context.testApi.assetForGenerated(good),i,'Same tone must use stable asset entry');
assert.equal(assets[i].group,'frequency');
const start=engine.indexOf('async function decodeRecording(');
const stop=engine.indexOf('\nfunction load(',start);
assert(start>=0&&stop>start,'decodeRecording must exist');
const mocks={
  assets,
  setSourceHealth(){},
  sourceAddresses(){throw Error('Generated tone must never load a network URL')},
  Number,Math,Float32Array,ArrayBuffer,Promise
};
vm.runInNewContext(engine.slice(start,stop)+'\nthis.testDecode=decodeRecording;',mocks);
(async()=>{
  const decoder={
    sampleRate:44100,
    createBuffer(channels,frames){
      const data=Array.from({length:channels},()=>new Float32Array(frames));
      return {length:frames,duration:frames/44100,numberOfChannels:channels,
        getChannelData(index){return data[index];}};
    }
  };
  const buffer=await mocks.testDecode(i,decoder);
  assert.equal(buffer.numberOfChannels,2);
  assert.equal(buffer.length,441000);
  const left=buffer.getChannelData(0),right=buffer.getChannelData(1);
  const crosses=x=>{let c=0;for(let n=1;n<44100;n++)if(x[n-1]<=0&&x[n]>0)c++;return c;};
  assert(Math.abs(crosses(left)-200)<=1,'Left channel must be 200Hz');
  assert(Math.abs(crosses(right)-206)<=1,'Right channel must be 206Hz');
  assert(Math.abs(left[0]-left.at(-1))<.01,'Loop left boundary must be smooth');
  assert(Math.abs(right[0]-right.at(-1))<.01,'Loop right boundary must be smooth');

  assert(engine.includes('assetForKey(t.assetKey)'), 'Stable key lookup required');
  assert(engine.includes('projectForDownload(mix)')||ui.includes('projectForDownload(mix)'), 'Stable JSON export required');
  assert(ui.includes('Baby Sleep & Calming')&&ui.includes('matchesIntent('),'Intent filter must exist');
  assert(ui.includes('Baby Mode không thêm tín hiệu âm tần'),'Baby must not auto-add tones');
  assert(ui.includes('Fade tự giới hạn'),'Fade limitation disclosed');
  console.log('STUDIO_INTENT_FREQUENCY_V1_PASS',JSON.stringify({catalogAssets:entries.length,
    syntheticChannels:2,loopSeconds:10,measuredLeftHz:crosses(left),measuredRightHz:crosses(right),
    intentFilters:true,babyGuardrails:true}));
})().catch(e=>{console.error(e);process.exitCode=1;});
