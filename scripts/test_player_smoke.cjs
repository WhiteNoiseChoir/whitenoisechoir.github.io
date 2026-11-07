#!/usr/bin/env node
// Dependency-free smoke tests for WhiteNoiseChoir's browser player, native audio loop and sleep deadline.
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const html=fs.readFileSync("index.html","utf8");
const matches=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
assert.equal(matches.length,1,"Expected one inline player script");
new vm.Script(matches[0][1],{filename:"index.html:inline-script"});

let now=Date.UTC(2026,10,7,0,0,0), id=1;
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
  play(){this.paused=false;return Promise.resolve()}
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
  assert.equal(get("cards").children.length,21,"Sound catalog changed unexpectedly");
  assert.equal(get("mixlist").children.length,45,"Mixer preset count changed");
  assert.match(html,/value="28800">8 hours/);
  assert.match(html,/value="43200">12 hours/);
  const card=name=>get("cards").children.find(c=>c.children[1].textContent===name);
  assert.ok(card("Rain on Window (Real Recording)"),"Rain card missing");
  assert.ok(card("Fireplace (Real Recording)"),"Fireplace card missing");

  get("timer").value="28800";
  card("Rain on Window (Real Recording)").children[3].onclick();
  await flush();
  assert.equal(audioInstances.length,1);
  assert.ok(audioInstances[0].loop,"Use native HTMLMediaElement loop in background");
  assert.match(audioInstances[0].src,/rain-on-window-real\.mp3\?v=long-master/);
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
  assert.match(audioInstances[1].src,/fireplace-real\.mp3\?v=long-master/);
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
    assert.match(audio.src,new RegExp(id+"\\\\.mp3\\\\?v=color-master-v1-20261107"),"Must bust stale 72s source cache for "+label);
    assert.ok(audio.loop,"Native loop remains enabled for "+label);
  }
  console.log("PASS: native loops, 21 sounds, 45 mixes, absolute timer, mixer headroom, 3 ten-minute colored-noise cache versions");
})().catch(e=>{console.error(e);process.exit(1)});
