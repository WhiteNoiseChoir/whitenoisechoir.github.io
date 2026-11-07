#!/usr/bin/env node
"use strict";
/* Fast DOM-based smoke tests for the public iPhone loop-check slider. */
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const html=fs.readFileSync("loop-check.html","utf8");
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
assert.equal(scripts.length,1,"Expected a single diagnostics script");
const source=scripts[0][1];
new vm.Script(source,{filename:"loop-check.html:inline"});

let canHLS=true;
const nodeMap={};
class FakeElement{
  constructor(id){this.id=id;this.textContent="";this.value="";this.max="";this.disabled=false;this.handlers={};}
  addEventListener(name,fn){this.handlers[name]=fn;}
  dispatch(name){assert.equal(typeof this.handlers[name],"function",name+" listener missing");this.handlers[name]();}
}
function get(id){
  if(!nodeMap[id])nodeMap[id]=new FakeElement(id);
  return nodeMap[id];
}
get("testMode").value="quick";
get("seek").value="0";
const created=[];
class MockAudio{
  constructor(){
    this.handlers={};this.readyState=0;this.currentTime=0;this.duration=NaN;
    this.paused=true;this.loop=false;created.push(this);
  }
  addEventListener(name,fn){this.handlers[name]=fn;}
  set src(value){this._src=value;this.duration=value.includes("/quick/")?1200:value.includes(".m3u8")?604800:600;}
  get src(){return this._src;}
  play(){this.readyState=1;this.paused=false;this.handlers.loadedmetadata?.();return Promise.resolve();}
  pause(){this.paused=true;}
  removeAttribute(name){if(name==="src")this._src="";}
  load(){}
}
const document={
  getElementById:get,
  createElement(tag){return tag==="audio"?{canPlayType(){return canHLS?"maybe":""}}:new FakeElement(tag);}
};
const window={events:{},addEventListener(name,fn){this.events[name]=fn;}};
vm.runInNewContext(source,{
  document,window,Audio:MockAudio,navigator:{audioSession:{type:""}},console,Math,Number,String,
});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  assert.equal(get("seek").disabled,false,"The seek slider must have been initialized in a usable state after playback");
  // Quick HLS: drag directly to the end of the 20-minute stream.
  get("play").dispatch("click");await flush();
  assert.ok(created[0].src.includes("/quick/continuous.m3u8"),"Quick HLS must use original short-loop playlist");
  assert.equal(get("seek").max,"1200","Quick stream: first twenty minutes seekable");
  get("seek").value="1195";get("seek").dispatch("input");get("seek").dispatch("change");
  assert.equal(created[0].currentTime,1195,"Touch slider must seek to 19:55");
  assert.match(get("position").textContent,/19:55/);
  get("stop").dispatch("click");
  assert.equal(created[0].paused,true);

  // Production HLS: jump into 10-minute source boundary in the 7-day playlist.
  get("testMode").value="production";get("testMode").dispatch("change");
  get("play").dispatch("click");await flush();
  assert.ok(created[1].src.includes("/white-noise/continuous.m3u8"),"Production test must use real HLS");
  get("tenMinute").dispatch("click");
  assert.equal(created[1].currentTime,595,"Production shortcut must seek to 9:55");
  get("nearEnd").dispatch("click");
  assert.equal(created[1].currentTime,1195,"Second shortcut must seek to 19:55");
  get("stop").dispatch("click");

  // Chrome/other non-HLS browser: do not expose inaccessible 20-minute target.
  canHLS=false;
  get("testMode").value="quick";get("testMode").dispatch("change");
  get("play").dispatch("click");await flush();
  assert.ok(created[2].src.includes("white-noise.mp3"),"Without HLS, original MP3 fallback is used");
  assert.equal(get("seek").max,"600");
  assert.equal(get("nearEnd").disabled,true,"Do not seek beyond MP3's real duration");
  get("tenMinute").dispatch("click");
  assert.equal(created[2].currentTime,595,"Fallback should still allow 9:55 boundary test");
  get("stop").dispatch("click");
  console.log("PASS: 20-minute slider, 19:55 jump, 9:55 master jump, 7-day stream window and MP3 fallback");
})().catch(err=>{console.error(err);process.exit(1);});
