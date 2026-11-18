const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const sha = "9756ade3d2f95a353cc82d5bd0cbad0ce450cada5bc6f1aca09192255e80254f";
const ref = "r2-" + sha;
let uploaded;
const anchor = { insertAdjacentElement(_where, element) { uploaded = element; } };
function element(tag) {
  return {
    tag, files: [], style:{}, children:[], textContent:"",
    append(...nodes) { this.children.push(...nodes); },
    setAttribute() {}, addEventListener(name, callback) { this[name] = callback; }
  };
}
const document = { createElement: element, getElementById(id) { return id==="library-status" ? anchor : null; }};
const assets = [{ id: ref, pending: true, name: "Nguồn chưa mở khóa" }];
const rawAssetIndex = new Map([[ref, 0]]);
const mix = { tracks: [{ asset:0 }] };
let redraws = 0;
const fakeFile = {name:"clavier-music-relaxing-piano-music-248868.mp3",size:4072704,
  async arrayBuffer(){ return new Uint8Array(4096).buffer; }};
const hash = Buffer.from(sha,"hex");
const context = {
  location:{pathname:"/vi/", search:"?local-piano=1"},
  URLSearchParams,document,assets,rawAssetIndex,mix,Blob,
  crypto:{subtle:{async digest(){return new Uint8Array(hash).buffer;}}},
  URL:{createObjectURL(){return "blob:test-piano"},revokeObjectURL(){}},
  Audio:class { constructor(url){this.src=url;this.duration=127.272;} load(){queueMicrotask(()=>this.onloadedmetadata());}},
  stop(){},rebuildCatalog(){},refreshLibraryGroups(){},renderLibrary(){},render(){redraws++},
  addSource(){throw Error("Must not insert a duplicate piano track")},
  console
};
vm.runInNewContext(fs.readFileSync("studio-local-piano-audition.js","utf8"),context);
assert(uploaded,"Owner opt-in panel exists");
const picker=uploaded.children[2];
picker.files=[fakeFile];
Promise.resolve(picker.change()).then(()=>{
  assert.equal(assets.length,1);
  assert.equal(assets[0].pending,undefined);
  assert.equal(assets[0].url,"blob:test-piano");
  assert.equal(assets[0].localAudition,true);
  assert.equal(assets[0].assetStatus,"LOCAL_BROWSER_ONLY_NOT_R2_NOT_PUBLICATION_APPROVED");
  assert.equal(mix.tracks.length,1);
  assert(redraws>0);
  console.log("Local piano audition recovers pending track");
}).catch(e=>{console.error(e);process.exitCode=1;});
