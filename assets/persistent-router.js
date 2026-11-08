/* WhiteNoiseChoir persistent UI router, v1. Retains the already-tested player
 * closure and its native HLS/MP3 transport; only HTML main content changes. */
(()=>{"use strict";
const origin=location.origin;
const supported=/^\/(?:$|sounds\/|collections\/|soundscapes\/|audio-tools\/)/;
const $=id=>document.getElementById(id);
let bridge=null,host=null,homeMain=null,routeMain=document.querySelector("main");
let homeTemplate=null,initPromise=null,catalog=null,searchState={q:"",cat:"all"},blocked=false;
const originalHome=!!$("playingTitle");
if(originalHome){homeMain=routeMain;homeTemplate=new DOMParser().parseFromString(document.documentElement.outerHTML,"text/html");}
const mini=document.createElement("aside");
mini.id="wnc-mini";mini.setAttribute("aria-label","Persistent audio player");
mini.innerHTML='<div class="wnc-mini-inner"><div class="wnc-mini-info"><strong id="wnc-mini-title">White Noise</strong><small id="wnc-mini-status" aria-live="polite">Ready</small></div><button type="button" id="wnc-mini-toggle" aria-label="Play or pause">▶</button><label class="wnc-mini-volume">Volume <input id="wnc-mini-volume" type="range" min="0" max="100" value="28" aria-label="Volume"></label><label class="wnc-mini-timer">Timer <select id="wnc-mini-timer" aria-label="Sleep timer"><option value="0">Off</option><option value="900">15 min</option><option value="1800">30 min</option><option value="3600">1 hour</option><option value="7200">2 hours</option><option value="14400">4 hours</option><option value="28800">8 hours</option><option value="43200">12 hours</option></select></label><button type="button" id="wnc-mini-options" aria-label="Volume and timer settings" aria-expanded="false">⚙</button><button type="button" id="wnc-mini-dark" aria-label="Dark screen">☾</button><button type="button" id="wnc-mini-stop" aria-label="Stop sound">■</button></div>';
document.body.append(mini);
const dark=document.createElement("div");dark.id="wnc-screen-dark";dark.hidden=true;
dark.innerHTML='<strong id="wnc-screen-title">WhiteNoiseChoir</strong><p>Dark screen mode. System lock-screen playback still depends on your device.</p><button type="button" id="wnc-screen-toggle">Pause / Play</button><button type="button" id="wnc-screen-exit">Exit dark screen</button>';
document.body.append(dark);
const notify=()=>{if(bridge&&typeof bridge.snapshot==="function")sync()};
window.WNCAppSync=notify;
function sync(){
 if(!bridge)return;const s=bridge.snapshot();mini.classList.toggle("has-track",!!s.hasAudio||!!s.loading||s.playing);
 $("wnc-mini-title").textContent=s.name||"White Noise";
 $("wnc-mini-status").textContent=s.playing?"Playing continuously":s.hasAudio?"Paused":"Ready to listen";
 $("wnc-mini-toggle").textContent=s.playing?"❚❚":"▶";
 $("wnc-mini-toggle").setAttribute("aria-label",s.playing?"Pause sound":"Play sound");
 $("wnc-screen-title").textContent=s.name||"WhiteNoiseChoir";
 $("wnc-mini-volume").value=s.volume;
 $("wnc-mini-timer").value=s.timer;
 document.querySelectorAll("[data-wnc-play]").forEach(b=>{
  const target=b.dataset.wncPlay;
  const active=s.activeIds&&s.activeIds.length===1&&s.activeIds[0]===target&&s.playing;
  b.textContent=active?"❚❚ Pause":"▶ Listen";
  b.setAttribute("aria-label",active?"Pause "+(b.dataset.title||"audio"):"Play "+(b.dataset.title||"audio"));
 });
 document.querySelectorAll("[data-wnc-status]").forEach(e=>{e.textContent=(s.playing?"Playing: ":s.hasAudio?"Paused: ":"Ready: ")+(s.name||"White Noise")});
 document.querySelectorAll("[data-wnc-page-volume]").forEach(e=>{if(document.activeElement!==e)e.value=s.volume});
 document.querySelectorAll("[data-wnc-page-timer]").forEach(e=>{e.value=s.timer});
 document.querySelectorAll("[data-wnc-compare]").forEach(a=>{
  const active=s.activeIds?.length===1&&s.activeIds[0]===a.dataset.wncCompare;
  a.classList.toggle("is-active",!!active);if(active)a.setAttribute("aria-current","true");else a.removeAttribute("aria-current");
 });
 const message=document.querySelector("[data-wnc-compare-status]");
 if(message)message.textContent=s.playing?"Now playing: "+(s.name||"sound")+". Tap another color to compare.":s.hasAudio?"Paused: "+(s.name||"sound")+".":"Choose a color to compare. Audio never starts automatically.";
}
async function bootBridge(){
 if(window.WNCBridge){bridge=window.WNCBridge;sync();return bridge;}
 if(initPromise)return initPromise;
 initPromise=(async()=>{
  const res=await fetch("/",{credentials:"same-origin"});
  if(!res.ok)throw Error("Cannot load audio player ("+res.status+")");
  const doc=new DOMParser().parseFromString(await res.text(),"text/html");
  homeTemplate=doc;
  host=document.createElement("div");host.id="wnc-player-host";host.hidden=true;
  const nodes=[".player","#sounds","#mixes","#dock","#black"];
  for(const sel of nodes){const node=doc.querySelector(sel);if(!node)throw Error("Player host missing "+sel);host.appendChild(node)}
  document.body.append(host);
  const inline=[...doc.querySelectorAll("script:not([src])")].find(s=>s.textContent.includes("var rows=")&&s.textContent.includes("function playTracks"));
  if(!inline)throw Error("Trusted homepage player script unavailable");
  // On a deep URL, keep the exact audio files and HLS playlists rooted at /audio/.
  const src=inline.textContent.replaceAll('"audio/','"/audio/');
  const script=document.createElement("script");script.textContent=src;host.appendChild(script);
  if(!window.WNCBridge)throw Error("Player bridge initialization failed");
  bridge=window.WNCBridge;
  sync();return bridge;
 })().catch(err=>{
  initPromise=null;
  console.warn("Player host unavailable; native MP3 controls remain available.",err);
  return null;
 });
 return initPromise;
}
function ensureSharedStyles(doc){
 if(!document.querySelector('link[data-wnc-library-css]')&&!document.querySelector('link[href="/assets/library.css"]')){
  const link=document.createElement("link");link.rel="stylesheet";link.href="/assets/library.css";link.dataset.wncLibraryCss="1";document.head.append(link);
 }
 if(doc&&doc.querySelector("style")&&!$("wnc-home-style")&&!originalHome){
  const s=document.createElement("style");s.id="wnc-home-style";s.textContent=doc.querySelector("style").textContent;document.head.append(s);
 }
}
function setHead(doc){
 document.title=doc.title;
 for(const key of ["description","robots"]){
  const from=doc.querySelector('meta[name="'+key+'"]'),existing=document.querySelector('meta[name="'+key+'"]');
  if(existing)existing.remove();if(from)document.head.append(from.cloneNode(true));
 }
 const from=doc.querySelector('link[rel="canonical"]'),existing=document.querySelector('link[rel="canonical"]');
 if(existing)existing.remove();if(from)document.head.append(from.cloneNode(true));
 document.querySelectorAll('head script[type="application/ld+json"]').forEach(node=>node.remove());
 doc.querySelectorAll('head script[type="application/ld+json"]').forEach(node=>document.head.append(node.cloneNode(true)));
}
function installMenu(){
 const h=document.querySelector("header"),n=h&&h.querySelector("nav");
 if(!h||!n||h.querySelector(".wnc-menu-button"))return;
 const b=document.createElement("button");b.type="button";b.className="wnc-menu-button";b.textContent="☰ Menu";b.setAttribute("aria-expanded","false");b.setAttribute("aria-controls","wnc-site-nav");
 n.id="wnc-site-nav";h.insertBefore(b,n);
 b.onclick=()=>{const open=document.body.classList.toggle("wnc-menu-open");b.setAttribute("aria-expanded",String(open))};
}
function routePath(url){return url.pathname+url.search+url.hash}
function normalizeClick(e){
 const a=e.target.closest&&e.target.closest("a[href]");if(!a||e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||a.target||a.hasAttribute("download"))return null;
 const url=new URL(a.href,location.href);
 if(url.origin!==origin||!supported.test(url.pathname)||/\.(?:mp3|m3u8|json|xml|txt|png|pdf|zip)$/i.test(url.pathname))return null;
 if(url.pathname===location.pathname&&url.search===location.search&&url.hash)return null;
 return url;
}
async function navigate(url,push=true){
 if(blocked)return;
 blocked=true;
 try{
  const b=await bootBridge();if(!b){location.assign(url.href);return}
  const path=url.pathname,goHome=path==="/";
  let doc,main;
  if(goHome&&originalHome&&homeMain){doc=homeTemplate;main=homeMain}
  else{
   const res=await fetch(url.pathname+url.search,{credentials:"same-origin"});
   if(!res.ok||!res.headers.get("content-type")?.includes("text/html"))throw Error("Page unavailable");
   doc=new DOMParser().parseFromString(await res.text(),"text/html");
   main=doc.querySelector("main");if(!main)throw Error("Page main missing");
  }
  // Keep original engine controls alive. It uses Audio() objects not DOM audio.
  if(!goHome&&!originalHome&&homeMain&&routeMain===homeMain&&host){
   for(const sel of [".player","#sounds","#mixes"]){const el=homeMain.querySelector(sel);if(el)host.append(el)}
   for(const sel of ["#dock","#black"]){const el=$(sel);if(el)host.append(el)}
   homeMain.remove();homeMain=null;
  }
  if(goHome&&!originalHome){
   if(!host)throw Error("Player host missing");
   ensureSharedStyles(doc);
   for(const sel of [".player","#sounds","#mixes"]){
    const existing=main.querySelector(sel),live=host.querySelector(sel);
    if(!existing||!live)throw Error("Home shell mismatch "+sel);
    existing.replaceWith(live);
   }
   for(const sel of ["#dock","#black"]){const live=host.querySelector(sel);if(live)document.body.append(live)}
   homeMain=main;
  }
  if(routeMain&&routeMain!==homeMain)routeMain.remove();
  if(goHome&&originalHome&&homeMain)homeMain.hidden=false;
  else if(main!==homeMain||!originalHome){
   if(originalHome&&homeMain)homeMain.hidden=true;
   const footer=document.querySelector("footer");
   (footer||document.body).before(main);
  }
  routeMain=main;
  ensureSharedStyles(doc);
  setHead(doc);
  document.body.classList.toggle("wnc-route-library",!goHome);
  document.body.classList.toggle("wnc-route-home",goHome);
  if(push)history.pushState({wnc:true},"",routePath(url));
  document.body.classList.remove("wnc-menu-open");
  const mb=document.querySelector(".wnc-menu-button");if(mb)mb.setAttribute("aria-expanded","false");
  if(goHome){
   const requested=url.searchParams.get("sound");if(requested&&(!bridge.snapshot().hasAudio)&&typeof bridge.prepare==="function")bridge.prepare(requested);
   sync();
  }else enhance(main);
  document.querySelectorAll("header nav a").forEach(a=>{const selected=path==="/"?a.getAttribute("href")==="/":path.startsWith(new URL(a.href).pathname);if(selected)a.setAttribute("aria-current","page");else a.removeAttribute("aria-current")});
  if(url.hash){const target=document.getElementById(decodeURIComponent(url.hash.slice(1)));if(target)target.scrollIntoView({block:"start",behavior:"auto"});else window.scrollTo({top:0,behavior:"auto"})}else window.scrollTo({top:0,behavior:"auto"});
  const h1=main.querySelector("h1");if(h1){h1.setAttribute("tabindex","-1");h1.focus({preventScroll:true})}
 }catch(err){console.warn("Route navigation fallback",err);location.assign(url.href)}
 finally{blocked=false}
}
function playOne(id,title){
 if(!bridge){bootBridge().then(b=>{if(b)b.play([id],title)});return}
 const s=bridge.snapshot();if(s.playing&&s.activeIds?.length===1&&s.activeIds[0]===id)bridge.pause();
 else if(s.activeIds?.length===1&&s.activeIds[0]===id&&!s.playing)bridge.resume();
 else bridge.play([id],title,true);
 sync();
}
function enhance(main){
 if(!main)return;
 const audio=main.querySelector("audio[data-sound]");
 if(audio&&bridge){
  const id=audio.dataset.sound,title=audio.dataset.title||id;
  if(audio.paused){
   audio.removeAttribute("controls");audio.hidden=true;audio.classList.add("wnc-native-fallback-hidden");
   const box=audio.closest(".playerbox")||audio.parentElement;
   if(!box.querySelector("[data-wnc-play]")){
    const row=document.createElement("div");row.className="wnc-page-actions";
    const btn=document.createElement("button");btn.type="button";btn.className="wnc-primary";btn.dataset.wncPlay=id;btn.dataset.title=title;btn.textContent="▶ Listen";btn.onclick=()=>playOne(id,title);
    const hint=document.createElement("span");hint.dataset.wncStatus="1";hint.className="wnc-play-hint";hint.textContent="Start playback, then keep browsing.";
    row.append(btn,hint);audio.after(row);
    const prefs=document.createElement("div");prefs.className="wnc-page-settings";
    prefs.innerHTML='<label>Volume <input type="range" min="0" max="100" aria-label="Volume" data-wnc-page-volume></label><label>Sleep timer <select data-wnc-page-timer aria-label="Sleep timer"><option value="0">Off</option><option value="900">15 minutes</option><option value="1800">30 minutes</option><option value="3600">1 hour</option><option value="7200">2 hours</option><option value="14400">4 hours</option><option value="28800">8 hours</option><option value="43200">12 hours</option></select></label><button type="button" class="wnc-dark-action">☾ Dark screen</button>';
    row.after(prefs);
    prefs.querySelector("[data-wnc-page-volume]").oninput=e=>{bridge.setVolume(e.target.value);sync()};
    prefs.querySelector("[data-wnc-page-timer]").onchange=e=>{bridge.setTimer(e.target.value);sync()};
    prefs.querySelector(".wnc-dark-action").onclick=()=>{dark.hidden=false};
   }
  }
 }
 // Progressive enhancement: comparison links remain normal links without JS.
 for(const a of main.querySelectorAll("[data-wnc-compare]")){
  a.addEventListener("click",e=>{
   if(!bridge||e.defaultPrevented||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||e.button!==0)return;
   e.preventDefault();playOne(a.dataset.wncCompare,a.dataset.title||"Noise");sync();
  });
 }
 // Replace link-only cards with clickable listen buttons plus an independent detail link.
 const cards=[...main.querySelectorAll('a.tile[href^="/sounds/"]')];
 const catalogSounds=catalog?.sounds||[];
 for(const link of cards){
  const path=link.getAttribute("href"),entry=catalogSounds.find(s=>"/sounds/"+s.slug+"/"===path);
  if(!entry||link.parentElement?.classList.contains("wnc-sound-card"))continue;
  const wrapper=document.createElement("div");wrapper.className="wnc-sound-card";
  link.parentElement.insertBefore(wrapper,link);wrapper.append(link);
  const b=document.createElement("button");b.type="button";b.className="wnc-card-play";b.dataset.wncPlay=entry.id;b.dataset.title=entry.title;b.textContent="▶ Listen";b.onclick=()=>playOne(entry.id,entry.title);wrapper.append(b);
 }
 // Library search only; browsing destinations stay in crawlable static HTML.
 const title=main.querySelector("h1"),isSounds=title&&title.textContent.trim()==="Explore sounds";
 if(isSounds){
  const grids=main.querySelectorAll(".grid");if(grids.length>1){
   const list=grids[1];
   if(!$("wnc-library-search")){
    const controls=document.createElement("div");controls.className="wnc-search-controls";
    controls.innerHTML='<label for="wnc-library-search">Find a sound</label><input type="search" id="wnc-library-search" placeholder="Search white noise, rain, fan..." autocomplete="off"><div class="wnc-filter-row" role="group" aria-label="Filter sound category"></div><p id="wnc-result-count" class="wnc-play-hint" aria-live="polite"></p>';
    list.before(controls);
    const cats=["all",...new Set(catalogSounds.map(s=>s.cat))];
    const labels=Object.fromEntries((catalog?.categories||[]).map(c=>[c.slug,c.title]));
    for(const c of cats){const b=document.createElement("button");b.type="button";b.className="wnc-filter";b.textContent=c==="all"?"All Sounds":(labels[c]||c);b.dataset.filter=c;b.onclick=()=>{searchState.cat=c;filterSounds()};controls.querySelector(".wnc-filter-row").append(b)}
    const search=controls.querySelector("input");search.value=searchState.q;search.oninput=()=>{searchState.q=search.value;filterSounds()};
    function filterSounds(){
     let count=0;for(const child of list.children){const a=child.querySelector("a.tile"),entry=catalogSounds.find(s=>"/sounds/"+s.slug+"/"===a?.getAttribute("href"));const hit=!!entry&&(searchState.cat==="all"||entry.cat===searchState.cat)&&(entry.title+" "+entry.desc+" "+entry.cat).toLowerCase().includes(searchState.q.toLowerCase().trim());child.hidden=!hit;if(hit)count++}
     controls.querySelector("#wnc-result-count").textContent=count+" sounds shown";
     for(const chip of controls.querySelectorAll("[data-filter]"))chip.classList.toggle("chosen",chip.dataset.filter===searchState.cat);
    }
    filterSounds();
   }
   // Keep empty, planned-only categories accessible but out of the primary list.
   const catGrid=grids[0],planned=[...catGrid.querySelectorAll("a.tile")].filter(a=>/0 available/.test(a.textContent));
   if(planned.length){const details=document.createElement("details");details.className="wnc-planned-categories";details.innerHTML="<summary>Planned categories (no audio yet)</summary>";const group=document.createElement("div");group.className="grid";planned.forEach(x=>group.append(x));details.append(group);catGrid.after(details)}
  }
 }
 sync();
}
function installEvents(){
 $("wnc-mini-toggle").onclick=()=>{bridge?.toggle();sync()};
 $("wnc-mini-stop").onclick=()=>{bridge?.stop();sync()};
 $("wnc-mini-volume").oninput=e=>{bridge?.setVolume(e.target.value);sync()};
 $("wnc-mini-timer").onchange=e=>{bridge?.setTimer(e.target.value);sync()};
 $("wnc-mini-dark").onclick=()=>{dark.hidden=false};
 $("wnc-mini-options").onclick=()=>{const open=document.body.classList.toggle("wnc-mini-expanded");$("wnc-mini-options").setAttribute("aria-expanded",String(open))};
 $("wnc-screen-exit").onclick=()=>{dark.hidden=true};
 $("wnc-screen-toggle").onclick=()=>{bridge?.toggle();sync()};
 document.addEventListener("click",e=>{
  const url=normalizeClick(e);if(!url)return;
  e.preventDefault();navigate(url,true);
 });
 window.addEventListener("popstate",()=>navigate(new URL(location.href),false));
 window.addEventListener("pageshow",sync);
 window.addEventListener("focus",sync);
 document.addEventListener("visibilitychange",sync);
 window.addEventListener("keydown",e=>{if(e.key==="Escape"&&!dark.hidden)dark.hidden=true});
 setInterval(()=>{if(bridge&&!document.hidden)sync()},15000);
}
document.body.classList.add(originalHome?"wnc-route-home":"wnc-route-library","wnc-router-ready");
installEvents();installMenu();
(async()=>{
 try{
  const r=await fetch("/catalog/library.json",{credentials:"same-origin"});if(r.ok)catalog=await r.json();
 }catch(e){}
 const b=await bootBridge();if(b&&!originalHome)enhance(routeMain);
})();
})();