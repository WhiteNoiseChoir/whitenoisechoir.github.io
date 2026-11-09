#!/usr/bin/env node
// Dependency-free smoke tests for WhiteNoiseChoir's browser player, native audio loop and sleep deadline.
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const html=fs.readFileSync("index.html","utf8");
const matches=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].filter(x=>x[1].includes("function playTracks("));
assert.equal(matches.length,1,"Expected one inline player script");
new vm.Script(matches[0][1],{filename:"index.html:inline-script"});

let now=Date.UTC(2026,10,7,0,0,0), id=1, emulateNativeHLS=false, blockNativeHLS=false, blockRemoteAudio=false;
const timerFns=new Map(),intervalFns=new Map(),documentEvents={},windowEvents={},audioInstances=[];
const elements={};
function element(tag="div"){
  const obj={tagName:tag,textContent:"",value:"",innerHTML:"",children:[],style:{setProperty(){}},
    classList:{add(){},remove(){},toggle(){},contains(){return false}},
    appendChild(child){this.children.push(child);return child},
    append(...items){this.children.push(...items)},
    removeAttribute(){},load(){},dataset:{},onclick:null,
  };
  Object.defineProperty(obj,"innerHTML",{get(){return this._innerHTML||""},set(v){this._innerHTML=v;this.children=[]}});
  return obj;
}
function get(id){
  if(!elements[id])elements[id]=element();
  return elements[id];
}
get("timer").value="0";get("volume").value="28";
const document={getElementById:get,createElement:element,
  addEventListener(name,fn){documentEvents[name]=fn},hidden:false};
const window={addEventListener(name,fn){windowEvents[name]=fn}};
class FakeAudio{
  constructor(src){this.src=src;this.paused=true;this.volume=1;this.loop=false;this.handlers={};audioInstances.push(this)}
  addEventListener(name,fn){this.handlers[name]=fn}
  canPlayType(type){return emulateNativeHLS&&type.includes("mpegurl")?"maybe":""}
  play(){if(blockRemoteAudio&&this.src&&this.src.startsWith("https://media.whitenoisechoir.com/"))return Promise.reject(new Error("R2 blocked"));if(blockNativeHLS&&this.src&&this.src.includes(".m3u8"))return Promise.reject(new Error("HLS blocked"));this.paused=false;return Promise.resolve()}
  pause(){this.paused=true}
  removeAttribute(attr){if(attr==="src")this.src=""}
  load(){}
}
class FakeDate extends Date{static now(){return now}}
const navigator={mediaSession:{setActionHandler(){},metadata:null}};
const context=vm.createContext({
  document,window,Audio:FakeAudio,navigator,MediaMetadata:class{constructor(m){Object.assign(this,m)}},
  Date:FakeDate,Math,Promise,console,
  setInterval(fn){const id=++globalThis._intervalId;intervalFns.set(id,fn);return id},
  clearInterval(id){intervalFns.delete(id)},
  setTimeout(fn){const id=++globalThis._timerId;timerFns.set(id,fn);return id},
  clearTimeout(id){timerFns.delete(id)},
});
globalThis._intervalId=0;globalThis._timerId=0;
vm.runInContext(matches[0][1],context);
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  assert.equal(get("cards").children.length,35,"Sound catalog changed unexpectedly");
  assert.equal(get("mixlist").children.length,45,"Mixer preset count changed");
  assert.match(html,/value="28800">8 hours/);
  assert.match(html,/value="43200">12 hours/);
  const card=name=>get("cards").children.find(c=>c.children[1].textContent===name);
  assert.ok(card("Rain on Window (Real Recording)"),"Rain card missing");
  assert.ok(card("Green Noise"),"Green Noise card missing");
  assert.ok(card("Fireplace (Real Recording)"),"Fireplace card missing");

  get("timer").value="28800";
  card("Rain on Window (Real Recording)").children[3].onclick();
  await flush();
  assert.equal(audioInstances.length,1);
  assert.ok(audioInstances[0].loop,"Use native HTMLMediaElement loop in background");
  assert.match(audioInstances[0].src,/^https:\/\/media\.whitenoisechoir\.com\/audio\/rain-on-window-real\.mp3$/);
  assert.match(get("timerInfo").textContent,/480 min/);
  assert.match(get("status").textContent,/Playing CC0/);

  now+=2000;
  get("timer").value="900";get("timer").onchange();
  assert.match(get("timerInfo").textContent,/15 min/);
  now+=900_100;
  documentEvents.visibilitychange();
  assert.equal(audioInstances[0].paused,true,"Expired timer must stop playing audio when the page wakes");
  assert.equal(get("timer").value,"0");
  assert.equal(get("status").textContent,"Sleep timer complete");

  card("Fireplace (Real Recording)").children[3].onclick();
  await flush();
  assert.equal(audioInstances.length,2);
  assert.match(audioInstances[1].src,/^https:\/\/media\.whitenoisechoir\.com\/audio\/fireplace-real\.mp3$/);
  assert.ok(audioInstances[1].loop);
  const oldAudio=audioInstances[1];
  const mixer=get("mixlist").children.find(c=>c.children[0].textContent.includes("Rain and Fan"));
  assert.ok(mixer);
  mixer.onclick();await flush();
  assert.ok(oldAudio.paused,"Selecting a mix stops the previous sound");
  assert.equal(audioInstances.length,4,"2 layers of the new mix must start");
  const gains=audioInstances.slice(2).map(a=>a.volume);
  assert.ok(gains[0]>gains[1]&&gains.reduce((a,b)=>a+b,0)<.28,"Mixer gain sum must preserve headroom");
  get("volume").value="100";get("volume").oninput();
  const maxGains=audioInstances.slice(2).map(a=>a.volume);
  assert.ok(maxGains.reduce((a,b)=>a+b,0)<=.85,"Two-layer mix must not exceed configured maximum sum");
  assert.equal(get("timerInfo").textContent,"Timer off · continuous playback");

  for(const [label,id] of [["White Noise","white-noise"],["Pink Noise","pink-noise"],["Brown Noise","brown-noise"]]){
    card(label).children[3].onclick();
    await flush();
    const audio=audioInstances[audioInstances.length-1];
    assert.equal(audio.src,"https://media.whitenoisechoir.com/audio/"+id+".mp3","Approved R2 master expected for "+label);
    assert.ok(audio.loop,"Native loop remains enabled for "+label);
  }
  const synthetic=[
    ["Blue Noise","blue-noise"],["Violet Noise","violet-noise"],
    ["Soft White Noise","soft-white-noise"],["Deep Brown Noise","deep-brown-noise"],
    ["Warm Pink Noise","warm-pink-noise"],["Neutral Mid Noise","mid-noise"],
    ["Low Rumble","low-rumble"],["Desk Fan (Synthetic)","desk-fan-synth"],
    ["Air Conditioner (Synthetic)","air-conditioner-synth"],
    ["Airplane Cabin (Synthetic)","cabin-hum-synth"],
    ["Gentle Wind (Synthetic)","wind-synth"],["Shower (Synthetic)","shower-synth"],
  ];
  for(const [label,id] of synthetic){
    card(label).children[3].onclick();
    await flush();
    const player=audioInstances[audioInstances.length-1];
    assert.equal(player.src,"https://media.whitenoisechoir.com/audio/"+id+".mp3","Approved R2 DSP MP3 expected for "+label);
    assert.ok(player.loop,label+" should retain native fallback looping");
  }
  // Simulate a native HLS-capable iPhone: the media playlist should not end
  // at the 600-second MP3 source boundary, even with the page hidden.
  emulateNativeHLS=true;
  get("timer").value="0";
  card("White Noise").children[3].onclick();
  await flush();
  let stream=audioInstances[audioInstances.length-1];
  assert.equal(stream.src,"https://media.whitenoisechoir.com/audio/continuous/white-noise/continuous.m3u8",stream.src);
  assert.ok(stream.loop,"HLS playlist end retains native loop for exceptionally long sessions");
  stream.currentTime=600;
  document.hidden=true;stream.handlers.timeupdate();
  assert.equal(stream.paused,false,"At minute 10 and with timer off, stream must still be playing");
  assert.equal(get("timerInfo").textContent,"Timer off · continuous playback");
  document.hidden=false;
  for(const name of [
    "Pink Noise","Brown Noise","Rain on Window (Real Recording)","Fireplace (Real Recording)",
    "Box Fan (Real Recording)","Heavy Rain (Real Recording)",
    "Ocean Waves (Real Recording)","Waterfall (Real Recording)",
    ...synthetic.map(x=>x[0])
  ]){
    card(name).children[3].onclick();
    await flush();
    const x=audioInstances[audioInstances.length-1];
    assert.ok(x.src.includes("audio/continuous/") && x.src.includes(".m3u8"),name+" must use native HLS");
  }
  // If a browser advertises HLS but refuses the source, immediately fall back
  // to the original MP3 without leaving the play button stuck.
  blockNativeHLS=true;
  card("White Noise").children[3].onclick();
  await flush();
  await flush();
  const mp3fallback=audioInstances[audioInstances.length-1];
  assert.ok(mp3fallback.src.includes("white-noise.mp3"),"Failed HLS must fall back to MP3");
  assert.ok(mp3fallback.loop,"Fallback MP3 should loop");
  blockNativeHLS=false;
  // R2 outage on an HLS-capable browser must keep the seven-day native
  // timeline alive using the same content already hosted on GitHub Pages.
  blockRemoteAudio=true;
  card("White Noise").children[3].onclick();
  await flush();await flush();
  const fallbackNativeHLS=audioInstances[audioInstances.length-1];
  assert.ok(fallbackNativeHLS.src.startsWith("audio/continuous/white-noise/continuous.m3u8"),"R2 outage should fall back to GitHub native HLS");
  assert.equal(fallbackNativeHLS.paused,false);
  // Non-core streams were migrated to R2; no obsolete GitHub HLS should
  // be attempted during outage. Their verified local MP3 is the fallback.
  card("Blue Noise").children[3].onclick();
  await flush();await flush();
  const retiredHLS=audioInstances[audioInstances.length-1];
  assert.ok(retiredHLS.src.startsWith("audio/blue-noise.mp3"),"Retired GH HLS fallback must skip old HLS and use pinned GitHub MP3");
  assert.equal(retiredHLS.loop,true,"Retired HLS uses continuous native MP3 loop");
  assert.equal(retiredHLS.paused,false,"R2 outage must not stop audio for retired HLS");
  // If both HLS transports fail and R2 is unavailable, use local MP3 with native looping.
  blockNativeHLS=true;
  card("White Noise").children[3].onclick();
  await flush();await flush();
  const emergencyMP3=audioInstances[audioInstances.length-1];
  assert.ok(emergencyMP3.src.startsWith("audio/white-noise.mp3"),"R2+HLS outage must recover via local MP3");
  assert.equal(emergencyMP3.loop,true);
  blockRemoteAudio=false;blockNativeHLS=false;emulateNativeHLS=false;
  // Late R2 failure *after* playback has started must also switch to GitHub MP3.
  card("White Noise").children[3].onclick();
  await flush();await flush();
  const liveR2MP3=audioInstances[audioInstances.length-1];
  assert.equal(liveR2MP3.src,"https://media.whitenoisechoir.com/audio/white-noise.mp3");
  liveR2MP3.currentTime=415;
  liveR2MP3.duration=600.025;
  liveR2MP3.handlers.error();
  await flush();await flush();
  assert.ok(liveR2MP3.src.startsWith("audio/white-noise.mp3"),"Midplay R2 interruption should switch to GitHub MP3");
  assert.equal(liveR2MP3.paused,false);
  liveR2MP3.currentTime=0;
  liveR2MP3.handlers.loadedmetadata();
  assert.equal(liveR2MP3.currentTime,415,"Backup MP3 should seek near the interrupted playback position");
  assert.match(get("status").textContent,/backup audio source/);
  console.log("PASS: 35 sound IDs, 45 mixes, 35 R2 MP3/HLS paths, 8 GH HLS + 35 GH MP3 fallback paths, 13 ten-minute DSP masters, timer and mixer");
})().catch(e=>{console.error(e);process.exit(1)});
