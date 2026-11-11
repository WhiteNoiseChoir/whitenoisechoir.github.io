const oldPlayerRequest = new URL(location.href);
if (!oldPlayerRequest.hash.startsWith('#mix=') && oldPlayerRequest.searchParams.has('sound')) {
  oldPlayerRequest.pathname = '/listen.html';
  location.replace(oldPlayerRequest.href);
}
const assets = [{"name":"Suối chảy gần","key":"asset-library/raw/sha256/be/be201d2fd0d110fc3ef5d8af060e5ac48439fd54e9f26ce6b69825182748a95b.wav","duration":68.889,"source":"https://commons.wikimedia.org/wiki/File:433589_jackthemurray_stream-river-water-up-close.wav"},{"name":"Ếch suối kêu","key":"asset-library/raw/sha256/0a/0a3c133128b94306396567cfc22ded8363645869d762c2bbc76b5c3519017cff.m4a","duration":11.865011,"source":"https://www.inaturalist.org/observations/111319279"},{"name":"Chim cổ đỏ Mỹ","key":"asset-library/raw/sha256/0b/0bf24b2b08299380add4e29b6ed0c9ed37ffaa26a19e3908e5b572d75ef7cabe.m4a","duration":24.960998,"source":"https://www.inaturalist.org/observations/402220192"},{"name":"Cú vằn","key":"asset-library/raw/sha256/06/06c95f291596cfc813ff54d636ae926493ed6cd9c8a10d30f049a70460048af1.mp3","duration":62.261875,"source":"https://www.inaturalist.org/observations/349447210"},{"name":"Ong nghệ","key":"asset-library/raw/sha256/2b/2b5e3902314cbb5d54c26164dc4264a1fdebf61f5012e6f378f6f3e313c7e91a.m4a","duration":23.04,"source":"https://www.inaturalist.org/observations/243621492"},{"name":"Lò sưởi tí tách","key":"audio/fireplace-real.mp3","duration":600,"source":"https://freesound.org/people/visionear/sounds/501417/","license":"CC0"},{"name":"Mưa trên cửa kính","key":"audio/rain-on-window-real.mp3","duration":600,"source":"https://freesound.org/people/ikayuka/sounds/273333/","license":"CC0"},{"name":"Sói tru ở Denali","key":"asset-library/raw/sha256/bf/bfc073e6226f2a21a87567b898c5e5674a53284353128da0d1e0f69b97e8b62f.mp3","duration":8.36,"source":"https://www.nps.gov/subjects/sound/sounds-wolf.htm","license":"NPS recording"},{"name":"Tàu hỏa đi qua ở xa","url":"https://upload.wikimedia.org/wikipedia/commons/transcoded/6/67/Train_passing_by_in_the_Wirikuta_Desert_(Mexico%2C_SLP).wav/Train_passing_by_in_the_Wirikuta_Desert_(Mexico%2C_SLP).wav.mp3","duration":154.25,"source":"https://commons.wikimedia.org/wiki/File:Train_passing_by_in_the_Wirikuta_Desert_(Mexico,_SLP).wav","license":"CC0"},{"name":"Mưa trên tán cây","key":"audio/rain-leaves-real.mp3","duration":600,"source":"https://freesound.org/people/Garuda1982/sounds/757276/"},{"name":"Mưa trên mái","key":"audio/rain-tin-roof-real.mp3","duration":600,"source":"https://freesound.org/people/archerjosiah/sounds/843483/"},{"name":"Sấm lăn từ xa","key":"audio/distant-thunder-real.mp3","duration":600,"source":"https://freesound.org/people/moxobna/sounds/107518/"},{"name":"Gỗ kẽo kẹt gần","url":"https://cdn.freesound.org/previews/506/506660_4921277-hq.mp3","duration":1.75,"source":"https://freesound.org/people/Rudmer_Rotteveel/sounds/506660/","license":"CC0"},{"name":"Nước nhỏ từ mái hiên","url":"https://cdn.freesound.org/previews/180/180948_2596329-hq.mp3","duration":33.25,"source":"https://freesound.org/people/jc144940/sounds/180948/","license":"CC0"},{"name":"Sói tru đáp từ xa","url":"https://upload.wikimedia.org/wikipedia/commons/transcoded/8/87/Wolf_howls.ogg/Wolf_howls.ogg.mp3","duration":28.35,"source":"https://commons.wikimedia.org/wiki/File:Wolf_howls.ogg","license":"Public domain"}];
assets.push(...studioPublishedAssets);
const rawAssetIndex = new Map();
const rawDigest = key => /\/([a-f0-9]{64})\.[a-z0-9]+$/i.exec(key || '')?.[1]?.toLowerCase();
assets.forEach((asset, index) => {
  const digest = rawDigest(asset.key);
  if (digest) rawAssetIndex.set('r2-' + digest, index);
  if (studioEnglish) {
    const title = originalEnglishNames[index] || asset.aliases || asset.name;
    asset.aliases = [asset.name, asset.aliases].filter(Boolean).join(' ');
    asset.name = title;
  }
});
function assetForRef(ref) {
  if (!/^r2-[a-f0-9]{64}$/.test(ref || '')) return undefined;
  let index = rawAssetIndex.get(ref);
  if (index === undefined) {
    index = assets.length;
    assets.push({id:ref, name:studioEnglish?'Locked source':'Nguồn chưa mở khóa', duration:0, group:'other', pending:true});
    rawAssetIndex.set(ref,index);
  }
  return index;
}
const media = 'https://media.whitenoisechoir.com/';
const $ = id => document.getElementById(id);
$('audio-check').src=media+assets[0].key;
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
const streamPrompt = 'Create an 8-second photorealistic 16:9 seamless loop of a shallow forest stream at dusk. Use a locked camera at bank level, with moss-covered stones and softly lit ferns framing the water. Keep exposure and focus fixed. Let only the flowing water and a few leaves move gently, with no sudden motion, cuts, people, text, or camera movement. Match the opening and closing composition and motion phase. Export a clean 1080p MP4 without audio.';
const sample = () => ({
  title: tr('Suối rừng'), length: 1800, videoPrompt:streamPrompt,
  tracks: assets.slice(0, 4).map((_, i) => ({asset:i, start:[0,42,105,180][i], gain:[.72,.23,.30,.18][i], loop:i===0, mute:false}))
});
const cabinSample = () => ({"title":tr("Cabin trong mưa đêm"),"length":600,"videoPrompt":"Generate an 8-second photorealistic seamless loop, 16:9, 1920×1080, 24 fps. Night inside a remote timber cabin. From a locked tripod at seated eye level with a 35 mm lens, frame a stone hearth on the left third and a rain-streaked window on the right third. Place a few split logs beside the hearth and a plain wool throw in the lower foreground. Outside the glass, show only dark spruce silhouettes and a faint blue-grey sky. Balance soft amber firelight against cool blue light at the window.\n\nKeep camera, focus, exposure and composition fixed. Animate low flames, a soft ember glow, subtle warm reflections on the wood and fine rain trailing down the window. Keep the motion gentle and continuous. Match the light and motion at the opening and closing so the clip repeats without a visible jump, reverse motion or fade to black. The wolf and the passing train stay off screen. No people, animals, vehicles, lightning, abrupt sparks, text or logos. Export MP4 without sound.","tracks":[{"asset":5,"start":0,"gain":0.46,"loop":true,"mute":false},{"asset":6,"start":0,"gain":0.34,"loop":true,"mute":false},{"asset":7,"start":135,"gain":0.18,"loop":false,"mute":false},{"asset":8,"start":305,"gain":0.14,"loop":false,"mute":false}]});
const cabinV2Sample = () => ({"title":tr("Cabin trong mưa đêm · V2"),"length":600,"videoPrompt":"Create a silent 8-second photorealistic ambient loop, 16:9, 1920×1080 at 24 fps. Use one continuous shot from inside a timber cabin at night. The camera stays on a locked tripod at seated eye level, aimed across the room. A stone fireplace with a low, steady amber fire fills the left side. A rain-streaked window fills the right side. Keep the window as a close interior detail: beads of water on the glass, soft blue darkness beyond it, no identifiable outdoor subjects. Warm firelight falls on the hearth, wood floor and nearby split logs.\n\nThe only visible motion is gentle flame flicker, subtle reflections on the wood, and rain tracking down the glass. Hold framing, exposure and focus steady. Match the overall light and motion at the end and beginning so the cut back to the first frame is unobtrusive. Do not pan, zoom, cut outside or show a train, track, headlights, passing lights, wolves, owls, people, lightning or any other event. No text, logos, fades or sound. This clip is a neutral indoor background that will repeat throughout a 10-minute soundscape. Export MP4.","tracks":[{"label":(studioEnglish?"Fireplace · close left":"Lò sưởi · sát bên trái"),"asset":5,"start":0,"gain":0.42,"loop":true,"mute":false,"pan":-0.28},{"label":(studioEnglish?"Rain · right window":"Mưa · cửa kính bên phải"),"asset":6,"start":0,"gain":0.27,"loop":true,"mute":false,"pan":0.35},{"label":(studioEnglish?"Rain · outside foliage":"Mưa · tán cây ngoài nhà"),"asset":9,"start":0,"gain":0.087,"loop":true,"mute":false,"pan":0.12,"lowpass":3400},{"label":(studioEnglish?"Owl · forest edge":"Cú · rìa rừng"),"asset":3,"start":54,"gain":0.2,"loop":false,"mute":false,"duration":27,"fadeIn":3,"fadeOut":9,"pan":-0.34,"lowpass":2300},{"label":(studioEnglish?"Rain building on the roof":"Mưa dày lên trên mái"),"asset":10,"start":80,"gain":0.16,"loop":false,"mute":false,"duration":66,"offset":17,"fadeIn":16,"fadeOut":24,"pan":0.18,"lowpass":4900},{"label":(studioEnglish?"Rolling thunder · behind the hill":"Sấm lăn · sau sườn đồi"),"asset":11,"start":102,"gain":0.16,"loop":false,"mute":false,"duration":54,"fadeIn":8,"fadeOut":20,"pan":0.24,"lowpass":1300},{"label":(studioEnglish?"Wolf howl · outside the valley":"Sói tru · ngoài thung lũng"),"asset":7,"start":165,"gain":0.22,"loop":false,"mute":false,"fadeIn":0.45,"fadeOut":2.4,"pan":-0.45,"lowpass":2600},{"label":(studioEnglish?"Kindling catching · indoors":"Củi bén lửa · trong phòng"),"asset":5,"start":199,"gain":0.095,"loop":false,"mute":false,"duration":26,"offset":213,"fadeIn":6,"fadeOut":8,"pan":-0.42},{"label":(studioEnglish?"Distant train · left to right":"Tàu · xa, đi từ trái sang phải"),"asset":8,"start":282,"gain":0.21,"loop":false,"mute":false,"fadeIn":24,"fadeOut":47,"pan":-0.44,"panEnd":0.43,"lowpass":2200},{"label":(studioEnglish?"Second pass of rain on the roof":"Mưa lướt trên mái · đợt hai"),"asset":10,"start":439,"gain":0.105,"loop":false,"mute":false,"duration":65,"offset":153,"fadeIn":15,"fadeOut":24,"pan":0.2,"lowpass":4600},{"label":(studioEnglish?"Owl · distant echo":"Cú · vọng lại xa hơn"),"asset":3,"start":512,"gain":0.125,"loop":false,"mute":false,"duration":23,"offset":32,"fadeIn":4,"fadeOut":10,"pan":0.29,"lowpass":1700}]});
function readClipOptions(track){
  const ranges={duration:[.01,10800],offset:[0,10800],fadeIn:[0,10800],fadeOut:[0,10800],
    pan:[-1,1],panEnd:[-1,1],highpass:[20,20000],lowpass:[80,20000]};
  const options={};
  for(const [name,[min,max]] of Object.entries(ranges)){
    if(Number.isFinite(track[name])) options[name]=clamp(track[name],min,max);
  }
  return options;
}
const cabinV3Sample = () => ({"title":tr("Cabin trong mưa đêm · V3"),"length":600,"videoPrompt":"Create a silent 8-second photorealistic ambient loop, 16:9, 1920×1080 at 24 fps. Use one continuous shot from inside a timber cabin at night. The camera stays on a locked tripod at seated eye level, aimed across the room. A stone fireplace with a low, steady amber fire fills the left side. A rain-streaked window fills the right side. Keep the window as a close interior detail: beads of water on the glass, soft blue darkness beyond it, no identifiable outdoor subjects. Warm firelight falls on the hearth, wood floor and nearby split logs.\n\nThe only visible motion is gentle flame flicker, subtle reflections on the wood, and rain tracking down the glass. Hold framing, exposure and focus steady. Match the overall light and motion at the end and beginning so the cut back to the first frame is unobtrusive. Do not pan, zoom, cut outside or show a train, track, headlights, passing lights, wolves, owls, people, lightning or any other event. No text, logos, fades or sound. This clip is a neutral indoor background that will repeat throughout a 10-minute soundscape. Export MP4.","tracks":[{"label":(studioEnglish?"Fire bed · near left":"Lửa nền · gần bên trái"),"asset":5,"start":0,"gain":0.4,"loop":true,"mute":false,"pan":-0.29},{"label":(studioEnglish?"Window rain · near right":"Mưa kính · gần bên phải"),"asset":6,"start":0,"gain":0.24,"loop":true,"mute":false,"pan":0.37},{"label":(studioEnglish?"Forest rain · outside the cabin":"Mưa trong rừng · ngoài cabin"),"asset":9,"start":0,"gain":0.087,"loop":true,"mute":false,"pan":0.13,"lowpass":3600},{"label":(studioEnglish?"Embers crackling by the hearth":"Than hồng · lách tách cạnh lò"),"asset":5,"start":16,"gain":0.1,"loop":false,"mute":false,"duration":17,"offset":118,"fadeIn":3,"fadeOut":6,"pan":-0.48},{"label":(studioEnglish?"Drops below the eaves":"Giọt nước dưới mái hiên"),"asset":13,"start":34,"gain":0.14,"loop":false,"mute":false,"duration":23,"offset":2,"fadeIn":3,"fadeOut":8,"pan":0.48,"lowpass":4700},{"label":(studioEnglish?"Indoor wood creak":"Gỗ trong nhà kẽo kẹt"),"asset":12,"start":48,"gain":0.14,"loop":false,"mute":false,"fadeIn":0.05,"fadeOut":0.18,"pan":-0.08,"lowpass":3600},{"label":(studioEnglish?"Owl · call from the forest edge":"Cú · gọi từ mép rừng"),"asset":3,"start":57,"gain":0.21,"loop":false,"mute":false,"duration":28,"fadeIn":2,"fadeOut":8,"pan":-0.34,"lowpass":2600},{"label":(studioEnglish?"Roof rain builds · first pass":"Mưa dồn trên mái · đợt đầu"),"asset":10,"start":79,"gain":0.165,"loop":false,"mute":false,"duration":74,"offset":17,"fadeIn":16,"fadeOut":24,"pan":0.17,"lowpass":5100},{"label":(studioEnglish?"Low thunder behind the hill":"Sấm trầm sau sườn đồi"),"asset":11,"start":101,"gain":0.175,"loop":false,"mute":false,"duration":59,"fadeIn":6,"fadeOut":20,"pan":0.19,"lowpass":1850},{"label":(studioEnglish?"Rain driving against the glass":"Mưa tạt qua mặt kính"),"asset":6,"start":137,"gain":0.08,"loop":false,"mute":false,"duration":25,"offset":172,"fadeIn":6,"fadeOut":11,"pan":0.48,"lowpass":6300},{"label":(studioEnglish?"Wolf · first howl":"Sói · tiếng tru đầu tiên"),"asset":7,"start":165,"gain":0.23,"loop":false,"mute":false,"fadeIn":0.35,"fadeOut":2,"pan":-0.48,"lowpass":2800},{"label":(studioEnglish?"Wolf · distant reply to the right":"Sói · tiếng đáp từ xa bên phải"),"asset":14,"start":186,"gain":0.12,"loop":false,"mute":false,"duration":28,"fadeIn":3,"fadeOut":10,"pan":0.36,"lowpass":1650},{"label":(studioEnglish?"Wood settling":"Thớ gỗ khẽ dịch"),"asset":12,"start":217,"gain":0.083,"loop":false,"mute":false,"duration":1.3,"offset":0.18,"fadeIn":0.06,"fadeOut":0.25,"pan":0.18,"lowpass":2600},{"label":(studioEnglish?"Kindling catching · indoors":"Củi bén lửa · trong phòng"),"asset":5,"start":223,"gain":0.095,"loop":false,"mute":false,"duration":22,"offset":213,"fadeIn":4,"fadeOut":6,"pan":-0.45},{"label":(studioEnglish?"Slow drops at the porch":"Giọt nước chậm ở hiên"),"asset":13,"start":246,"gain":0.1,"loop":false,"mute":false,"duration":19,"offset":12,"fadeIn":5,"fadeOut":7,"pan":0.41,"lowpass":4300},{"label":(studioEnglish?"Rain rustling through leaves":"Mưa xào xạc trên tán cây"),"asset":9,"start":263,"gain":0.079,"loop":false,"mute":false,"duration":33,"offset":265,"fadeIn":10,"fadeOut":13,"pan":-0.13,"lowpass":4200},{"label":(studioEnglish?"Train · approaching and passing left to right":"Tàu · tới gần rồi đi từ trái sang phải"),"asset":8,"start":282,"gain":0.225,"loop":false,"mute":false,"fadeIn":20,"fadeOut":48,"pan":-0.49,"panEnd":0.49,"lowpass":2500},{"label":(studioEnglish?"Fire continues as the train passes":"Lửa vẫn cháy gần trong lúc tàu qua"),"asset":5,"start":365,"gain":0.065,"loop":false,"mute":false,"duration":19,"offset":341,"fadeIn":5,"fadeOut":8,"pan":-0.43},{"label":(studioEnglish?"Roof rain returns after the train":"Mưa trên mái trở lại khi tàu khuất"),"asset":10,"start":428,"gain":0.13,"loop":false,"mute":false,"duration":63,"offset":153,"fadeIn":14,"fadeOut":24,"pan":0.2,"lowpass":4500},{"label":(studioEnglish?"Water dripping from the eaves":"Nước từ mái hiên nhỏ giọt"),"asset":13,"start":460,"gain":0.105,"loop":false,"mute":false,"duration":23,"offset":7,"fadeIn":6,"fadeOut":8,"pan":0.48,"lowpass":4100},{"label":(studioEnglish?"Thunder fading into the distance":"Sấm vọng xa dần"),"asset":11,"start":488,"gain":0.107,"loop":false,"mute":false,"duration":34,"offset":83,"fadeIn":5,"fadeOut":15,"pan":-0.22,"lowpass":1200},{"label":(studioEnglish?"Owl echo across the forest":"Cú vọng lại bên kia rừng"),"asset":3,"start":516,"gain":0.15,"loop":false,"mute":false,"duration":23,"offset":32,"fadeIn":3,"fadeOut":9,"pan":0.32,"lowpass":2100},{"label":(studioEnglish?"Embers crackle and soften":"Than lách tách rồi dịu xuống"),"asset":5,"start":548,"gain":0.083,"loop":false,"mute":false,"duration":26,"offset":421,"fadeIn":5,"fadeOut":11,"pan":-0.45},{"label":(studioEnglish?"Final drops outside the window":"Những giọt cuối ngoài cửa sổ"),"asset":13,"start":566,"gain":0.078,"loop":false,"mute":false,"duration":17,"offset":14,"fadeIn":5,"fadeOut":8,"pan":0.42,"lowpass":4100}]});
const presets = {
  streamside: sample,
  'cabin-rain-night': cabinSample,
  'cabin-rain-night-v2': cabinV2Sample,
  'cabin-rain-night-v3': cabinV3Sample,
};
legacyStudioRecipes.forEach((recipe,index)=>{
  presets['legacy-'+index]=()=>({title:recipe.title,length:1800,master:.28,tracks:structuredClone(recipe.tracks)});
});
const trialData = JSON.parse(document.getElementById('studio-trial')?.textContent || 'null');
const projectStorageKey = studioEnglish ? 'wnc.studio.project.en.v1'
  : (trialData ? 'wnc.studio.trial.' + trialData.slug : 'wnc.studio.project.v1');
function normalizeProject(saved) {
  if (!saved || !Number.isFinite(saved.length) || !Array.isArray(saved.tracks)) throw Error('Invalid project');
  const title = typeof saved.title === 'string' && saved.title.trim() ? saved.title.slice(0,100) : tr('Bản phối chưa đặt tên');
  const videoPrompt = typeof saved.videoPrompt === 'string' ? saved.videoPrompt.slice(0,3000)
    : (/suối|stream/i.test(title) ? streamPrompt : '');
  return {
    title, videoPrompt, length:clamp(saved.length,6,10800),
    ...(Number.isFinite(saved.master)?{master:clamp(saved.master,0,1)}:{}),
    tracks:saved.tracks.slice(0,32)
      .filter(t=>t && Number.isFinite(t.start) && Number.isFinite(t.gain))
      .map(t=>({t,index:t.assetRef ? assetForRef(t.assetRef) : Number(t.asset)}))
      .filter(({index})=>Number.isInteger(index) && assets[index])
      .map(({t,index})=>({
        asset:index,...(t.assetRef?{assetRef:t.assetRef}:{}),start:clamp(t.start,0,10800),gain:clamp(t.gain,0,1),loop:!!t.loop,mute:!!t.mute,
        ...(typeof t.label==='string'?{label:t.label.slice(0,100)}:{}),
        ...readClipOptions(t)
      }))
  };
}
function readMix() {
  try {
    if (location.hash.startsWith('#mix=')) {
      const code = location.hash.slice(5);
      if (Object.hasOwn(presets, code)) return presets[code]();
      return normalizeProject(JSON.parse(decodeURIComponent(code)));
    }
    const saved = localStorage.getItem(projectStorageKey);
    if (saved) return normalizeProject(JSON.parse(saved));
    if (trialData?.project) return normalizeProject(trialData.project);
    if (trialData?.preset && Object.hasOwn(presets,trialData.preset)) return presets[trialData.preset]();
  } catch {
    $('status').textContent = tr('Không đọc được bản phối. Đã mở bản Suối rừng.');
  }
  return sample();
}
let mix=readMix(),position=0,playing=false,loading=false,anchor=0,frame=0,generation=0;
let context, monitorGain, monitorAnalyser, monitorSamples, soloTrack;
const buffers=new Map(), active=[];
function stop(){
  generation++;
  playing=false;
  loading=false;
  $('peak').value=-60;
  cancelAnimationFrame(frame);
  for(const {node} of active.splice(0)) { try {node.stop();node.disconnect();} catch {} }
  $('play').textContent=tr('Phát');
}
function format(seconds){
  const whole=Math.floor(Math.max(0,seconds));
  const fields=[Math.floor(whole/60)%60,whole%60].map(value=>String(value).padStart(2,'0'));
  if(whole>=3600) fields.unshift(Math.floor(whole/3600));
  return fields.join(':');
}
function display(){
  $('seek').value=position;
  $('time').textContent=format(position)+' / '+format(mix.length);
  document.querySelectorAll('.needle').forEach(el=>el.style.left=(100*position/mix.length)+'%');
}
function tick(loopPreview=false){
  const elapsed=context.currentTime-anchor;
  const end=mix.length+(loopPreview?5:0);
  position=loopPreview && elapsed>=mix.length ? Math.min(5,elapsed-mix.length) : clamp(elapsed,0,mix.length);
  display();
  monitorAnalyser.getFloatTimeDomainData(monitorSamples);
  let peak=0;
  for(const sample of monitorSamples) peak=Math.max(peak,Math.abs(sample));
  $('peak').value=peak ? Math.max(-60,Math.min(0,20*Math.log10(peak))) : -60;
  if(elapsed>=end) stop();
  else frame=requestAnimationFrame(()=>tick(loopPreview));
}
// Approved 60-second Signature sources are a safe, same-origin fallback for
// corresponding ten-minute masters that a particular browser cannot decode.
const approvedAudioFallbacks = {
  'audio/fireplace-real.mp3': '/signature/audio/fireplace.mp3',
  'audio/rain-on-window-real.mp3': '/signature/audio/rain-window.mp3'
};
function sourceAddresses(i){
  const asset=assets[i];
  if(asset.pending) return [];
  const primary=asset.url || media+asset.key;
  const url=new URL(primary,location.origin);
  url.searchParams.set('studio-audio','20261111');
  const localMasters=new Set(['audio/fireplace-real.mp3','audio/rain-on-window-real.mp3',
    'audio/rain-leaves-real.mp3','audio/rain-tin-roof-real.mp3','audio/distant-thunder-real.mp3']);
  const sources=localMasters.has(asset.key) ? ['/'+asset.key,url.href] : [primary,url.href];
  if(approvedAudioFallbacks[asset.key]) sources.push(approvedAudioFallbacks[asset.key]);
  return [...new Set(sources)];
}
// Decode audio with the original decoder first. Some Chromium derivatives reject
// long MP3 files in OfflineAudioContext even when a regular AudioContext works.
async function decodeRecording(i,decoder,onSource){
  const asset=assets[i];
  if(asset.pending) throw Error(studioEnglish?'Unlock the source catalog in Vietnamese Studio.':'Mở kho âm thanh trong Studio tiếng Việt để tải nguồn.');
  const attempts=[];
  for(const address of sourceAddresses(i)){
    try{
      const response=await fetch(address,{cache:'no-store',signal:AbortSignal.timeout(60000)});
      if(!response.ok){attempts.push('HTTP '+response.status+' · '+new URL(address,location.href).pathname);continue;}
      const type=(response.headers.get('content-type')||'').toLowerCase();
      if(type.includes('text/html')||type.includes('application/json')){
        attempts.push('Trang HTML thay vì file âm thanh · '+new URL(address,location.href).pathname);
        continue;
      }
      const bytes=await response.arrayBuffer();
      if(bytes.byteLength<1024){
        attempts.push('File rỗng hoặc quá ngắn · '+new URL(address,location.href).pathname);
        continue;
      }
      let decoded, originalError;
      try{decoded=await decoder.decodeAudioData(bytes.slice(0));}
      catch(error){originalError=error;}
      if(!decoded){
        const AudioEngine=window.AudioContext||window.webkitAudioContext;
        if(AudioEngine){
          const fallbackDecoder=new AudioEngine({sampleRate:44100});
          try{decoded=await fallbackDecoder.decodeAudioData(bytes.slice(0));}
          catch(error){originalError=error;}
          finally{await fallbackDecoder.close().catch(()=>{});}
        }
      }
      if(decoded && decoded.duration>0 && decoded.numberOfChannels){
        if(onSource)onSource({address,fallback:address===approvedAudioFallbacks[asset.key],duration:decoded.duration});
        return decoded;
      }
      attempts.push('Không giải mã được '+Math.round(bytes.byteLength/1024)+' KB · '+new URL(address,location.href).pathname+
        (originalError?.name?' ('+originalError.name+')':''));
    }catch(error){
      attempts.push((error.name==='TimeoutError'||error.name==='AbortError'?'Tải quá thời gian chờ':
        error.message||'Lỗi mạng hoặc quyền truy cập tệp')+' · '+new URL(address,location.href).pathname);
    }
  }
  throw Error(asset.name+' · '+attempts.join(' | '));
}
function load(i){
  if(!buffers.has(i)) buffers.set(i,decodeRecording(i,context).catch(error=>{
    buffers.delete(i);throw error;
  }));
  return buffers.get(i);
}
function clipOffset(track,sourceDuration){
  const wanted=track.offset || 0;
  // A short approved fallback may be used instead of the original ten-minute
  // master; retain the event and choose a valid section inside the fallback.
  if(wanted<sourceDuration) return wanted;
  const length=Math.min(track.duration || 1,sourceDuration);
  return wanted%Math.max(1,sourceDuration-length);
}
function clipDuration(track,sourceDuration,projectLength){
  const available=track.loop ? Infinity : sourceDuration-clipOffset(track,sourceDuration);
  return Math.max(0,Math.min(projectLength-track.start,track.duration ?? Infinity,available));
}
function scheduleTrack(engine,buffer,track,from,to,base,projectLength,destination=engine.destination){
  const duration=clipDuration(track,buffer.duration,projectLength);
  const start=Math.max(from,track.start);
  const finish=Math.min(to,track.start+duration);
  if(finish<=start) return null;
  const when=Math.max(0,base+start), elapsed=start-track.start, span=finish-start;
  const source=engine.createBufferSource();
  const gain=engine.createGain();
  source.buffer=buffer;source.loop=track.loop;
  gain.gain.value=track.gain;
  source.connect(gain);
  let output=gain;
  for(const type of ['highpass','lowpass']){
    if(!track[type]) continue;
    const filter=engine.createBiquadFilter();
    filter.type=type;filter.frequency.value=track[type];filter.Q.value=Math.SQRT1_2;
    output.connect(filter);output=filter;
  }
  if((track.pan!==undefined || track.panEnd!==undefined) && engine.createStereoPanner){
    const panner=engine.createStereoPanner();
    const startPan=track.pan ?? 0;
    const panAt=t=>startPan+((track.panEnd ?? startPan)-startPan)*clamp(t/duration,0,1);
    panner.pan.setValueAtTime(panAt(elapsed),when);
    if(track.panEnd!==undefined) panner.pan.linearRampToValueAtTime(panAt(elapsed+span),when+span);
    output.connect(panner);output=panner;
  }
  if(track.fadeIn || track.fadeOut){
    const envelope=engine.createGain();
    const fadeIn=Math.min(track.fadeIn || 0,duration/2);
    const fadeOut=Math.min(track.fadeOut || 0,duration/2);
    const envelopeAt=t=>clamp(Math.min(fadeIn?t/fadeIn:1,fadeOut?(duration-t)/fadeOut:1),0,1);
    envelope.gain.setValueAtTime(envelopeAt(elapsed),when);
    for(const point of [fadeIn,duration-fadeOut,elapsed+span]){
      if(point>elapsed && point<=elapsed+span)
        envelope.gain.linearRampToValueAtTime(envelopeAt(point),when+point-elapsed);
    }
    output.connect(envelope);output=envelope;
  }
  output.connect(destination);
  const offset=clipOffset(track,buffer.duration)+elapsed;
  source.start(when,track.loop ? offset%buffer.duration : offset,span);
  return {node:source,gain,track};
}
async function play(loopPreview=false){
  if(playing || loading){stop();$('status').textContent='';return;}
  stopPreview();
  const tracks=mix.tracks.filter(t=>!t.mute && t.gain>0 && (!soloTrack || t===soloTrack));
  if(!tracks.length){$('status').textContent=tr('Hãy bật ít nhất một lớp âm thanh.');return;}
  if(position>=mix.length) position=0;
  const token=++generation;
  loading=true;
  $('play').textContent=tr('Dừng tải');
  $('status').textContent=tr('Đang tải âm thanh…');
  try {
    const AudioEngine=window.AudioContext || window.webkitAudioContext;
    context ||= new AudioEngine();
    if(!monitorGain){
      monitorGain=context.createGain();
      monitorAnalyser=context.createAnalyser();
      monitorAnalyser.fftSize=256;
      monitorSamples=new Float32Array(monitorAnalyser.fftSize);
      monitorGain.connect(monitorAnalyser);
      monitorAnalyser.connect(context.destination);
    }
    monitorGain.gain.value=mix.master ?? 1;
    await context.resume();
    const decoded=await Promise.allSettled(tracks.map(t=>load(t.asset)));
    if(token!==generation) return;
    const now=context.currentTime+.05;
    anchor=now-position;
    function schedule(from,to,base){
      tracks.forEach((track,i)=>{
        const buffer=decoded[i].value;
        if(!buffer) return;
        const entry=scheduleTrack(context,buffer,track,from,to,base,mix.length,monitorGain);
        if(entry) active.push(entry);
      });
    }
    schedule(position,mix.length,anchor);
    if(loopPreview) schedule(0,5,anchor+mix.length);
    if(decoded.every(r=>r.status==='rejected')) throw decoded[0].reason;
    loading=false;
    playing=true;$('play').textContent=tr('Tạm dừng');
    const skipped=tracks.filter((_,i)=>decoded[i].status==='rejected').map(t=>assets[t.asset].name);
    $('status').textContent=skipped.length?tr('Không tải được các lớp: ')+[...new Set(skipped)].join(', '):'';
    tick(loopPreview);
  } catch(e){if(token===generation){stop();$('status').textContent=e.message || tr('Không tải được âm thanh. Hãy thử lại hoặc đổi nguồn.');}}
}
function locate(value){
  const resume=playing || loading;
  stop();position=clamp(value,0,mix.length);display();
  if(resume) play();
}
async function buildWav(project,progress){
  const bySource=new Map();
  for(const track of project.tracks){
    if(track.mute || track.gain<=0 || track.start>=project.length) continue;
    if(!bySource.has(track.asset)) bySource.set(track.asset,[]);
    bySource.get(track.asset).push(track);
  }
  if(!bySource.size) throw Error(tr('Hãy bật ít nhất một lớp âm thanh.'));
  const Offline=window.OfflineAudioContext || window.webkitOfflineAudioContext;
  if(!Offline) throw Error(tr('Trình duyệt này không hỗ trợ xuất âm thanh.'));
  const rate=44100, frames=Math.ceil(project.length*rate), blockSize=30*rate;
  const decoder=new Offline(2,1,rate);
  const mixLeft=new Float32Array(frames), mixRight=new Float32Array(frames);
  const sourceCount=bySource.size;
  const fallbackSources=[];
  let sourceNumber=0;
  for(const [id,tracks] of bySource){
    const name=assets[id].name;
    progress(sourceNumber/sourceCount*86,tr('Đang tải nguồn ')+(sourceNumber+1)+'/'+sourceCount+' · '+name);
    const buffer=await decodeRecording(id,decoder,details=>{
      if(details.fallback)fallbackSources.push(name+' ('+Math.round(details.duration)+'s Signature)');
    });
    for(let first=0;first<frames;first+=blockSize){
      const count=Math.min(blockSize,frames-first);
      const lead=Math.min(first,Math.round(rate*.25));
      const from=(first-lead)/rate, to=(first+count)/rate;
      const audible=tracks.filter(t=>t.start<to && t.start+clipDuration(t,buffer.duration,project.length)>from);
      if(audible.length){
        const offline=new Offline(2,count+lead,rate);
        for(const track of audible) scheduleTrack(offline,buffer,track,from,to,-from,project.length);
        const rendered=await offline.startRendering();
        const left=rendered.getChannelData(0), right=rendered.getChannelData(1);
        for(let i=0;i<count;i++){
          mixLeft[first+i]+=left[i+lead];
          mixRight[first+i]+=right[i+lead];
        }
      }
      progress((sourceNumber+(first+count)/frames)/sourceCount*86,tr('Đang phối nguồn ')+(sourceNumber+1)+'/'+sourceCount+' · '+name);
    }
    sourceNumber++;
  }
  const header=new DataView(new ArrayBuffer(44));
  const tag=(offset,value)=>{for(let i=0;i<value.length;i++) header.setUint8(offset+i,value.charCodeAt(i));};
  tag(0,'RIFF');header.setUint32(4,36+frames*4,true);tag(8,'WAVE');tag(12,'fmt ');
  header.setUint32(16,16,true);header.setUint16(20,1,true);header.setUint16(22,2,true);
  header.setUint32(24,rate,true);header.setUint32(28,rate*4,true);
  header.setUint16(32,4,true);header.setUint16(34,16,true);tag(36,'data');
  header.setUint32(40,frames*4,true);
  const parts=[header.buffer], tailStart=Math.max(0,frames-10*rate);
  const master=project.master ?? 1;
  let quiet=0,longest=0,peak=0;
  for(let first=0;first<frames;first+=blockSize){
    const count=Math.min(blockSize,frames-first);
    const pcm=new DataView(new ArrayBuffer(count*4));
    for(let i=0;i<count;i++){
      const index=first+i,left=mixLeft[index]*master,right=mixRight[index]*master;
      const amplitude=Math.max(Math.abs(left),Math.abs(right));
      peak=Math.max(peak,amplitude);
      pcm.setInt16(i*4,Math.round(clamp(left,-1,1)*32767),true);
      pcm.setInt16(i*4+2,Math.round(clamp(right,-1,1)*32767),true);
      if(index>=tailStart){
        quiet=amplitude<.001?quiet+1:0;
        longest=Math.max(longest,quiet);
      }
    }
    parts.push(pcm.buffer);
    progress(86+(first+count)/frames*13,tr('Đang đóng gói tệp WAV'));
    await new Promise(resolve=>setTimeout(resolve,0));
  }
  return {blob:new Blob(parts,{type:'audio/wav'}),silence:longest/rate,clipped:peak>1,duration:frames/rate,fallbackSources};
}
const videoEnabled = Boolean($('video-input'));
let exporting=false, audioExport=null, videoExport=null, clipUrl=null;
const durationLabel=seconds=>{
  const ms=Math.round(seconds*1000);
  const whole=Math.floor(ms/1000);
  return format(whole)+(ms%1000?','+String(ms%1000).padStart(3,'0').replace(/0+$/,''):'');
};
function progressStage(step,percent,message){
  const bar=$(step+'-progress');
  if(percent===null) bar.removeAttribute('value');
  else bar.value=Math.round(clamp(percent,0,100));
  $(step+'-status').textContent=message+(percent>0&&percent<100?' · '+bar.value+'%':'');
}
function stageError(step,error){
  const progress=$(step+'-progress'),status=$(step+'-status').textContent.split(' · ')[0];
  console.error('WhiteNoiseChoir export',step,status,error);
  const detail=typeof error==='string'?error:error?.message;
  let message=detail || tr('Trình duyệt dừng xử lý. Hãy thử lại bước này.');
  if(error?.name==='QuotaExceededError'){
    message=tr('Không đủ dung lượng lưu tệp MP4 trên thiết bị.');
  } else if(/out of memory|memory access out of bounds|array buffer allocation|allocation failed|^Aborted\(\)/i.test(detail || '')){
    message=tr('Trình duyệt hết bộ nhớ khi xử lý tệp.');
  }
  progressStage(step,progress.hasAttribute('value')?progress.value:0,tr('Lỗi ở bước «')+status+'» · '+message);
}
function clearResult(step){
  const result=$(step+'-result');
  const previous=result.querySelector('a');
  if(previous) URL.revokeObjectURL(previous.href);
  result.replaceChildren();
}
function showDownload(step,blob,title,extension,label){
  clearResult(step);
  const link=document.createElement('a');
  link.href=URL.createObjectURL(blob);
  link.download=(title.replace(/[\\/:*?"<>|]/g,'-').trim() || 'ban-phoi')+'.'+extension;
  link.textContent=label;
  $(step+'-result').append(link);
}
const audioSignature=project=>JSON.stringify([project.length,project.master ?? 1,project.tracks]);
function resetVideo(){
  if(!videoEnabled) return;
  videoExport=null;
  clearResult('video');clearResult('mux');
  progressStage('video',0,audioExport
    ? ($('video-input').files.length?tr('Đã chọn clip. Có thể kéo dài đến ')+durationLabel(audioExport.duration)+'.':tr('Chọn clip để kéo dài đến ')+durationLabel(audioExport.duration)+'.')
    : tr('Xuất WAV và chọn clip để bắt đầu.'));
  progressStage('mux',0,tr('Đang chờ video nền.'));
}
function syncWorkflow(){
  if(!exporting && audioExport && audioExport.signature!==audioSignature(mix)){
    audioExport=null;
    clearResult('audio');
    progressStage('audio',0,tr('Bản phối đã thay đổi. Hãy xuất lại WAV.'));
    resetVideo();
  }
  $('mix-controls').inert=exporting;
  $('mix-editor').inert=exporting;
  $('minutes').disabled=exporting;
  $('render').disabled=exporting;
  if(!videoEnabled) return;
  $('video-input').disabled=exporting;
  $('render-video').disabled=exporting || !audioExport || !$('video-input').files.length;
  $('mux-video').disabled=exporting || !audioExport || !videoExport;
}
function exportBusy(value){
  exporting=value;
  if(value){stop();stopPreview();buffers.clear();}
  syncWorkflow();
}
$('render').onclick=async()=>{
  if(exporting) return;
  const project=structuredClone(mix);
  audioExport=null;clearResult('audio');resetVideo();exportBusy(true);
  progressStage('audio',0,tr('Đang chuẩn bị xuất ')+durationLabel(project.length)+tr(' âm thanh'));
  try {
    const result=await buildWav(project,(percent,message)=>progressStage('audio',percent,message));
    audioExport={...result,title:project.title,signature:audioSignature(project)};
    const silence=result.silence.toFixed(3).replace('.',',');
    progressStage('audio',100,tr('Đã xuất WAV · ')+durationLabel(result.duration)+
      tr(' · Khoảng lặng dài nhất ở 10 giây cuối: ')+silence+tr(' giây dưới −60 dBFS.')+
      (result.clipped?tr(' Có đỉnh âm bị cắt.'):'')+
      (result.fallbackSources.length?' · Đã dùng nguồn dự phòng: '+result.fallbackSources.join(', '):''));
    showDownload('audio',result.blob,project.title,'wav',tr('Tải WAV'));
    resetVideo();
  } catch(error) {stageError('audio',error);}
  finally {exportBusy(false);}
};
if(videoEnabled) $('copy-prompt').onclick=async()=>{
  const prompt=$('video-prompt');
  if(!prompt.value){prompt.focus();return;}
  try {await navigator.clipboard.writeText(prompt.value);$('prompt-status').textContent=tr('Đã sao chép câu lệnh.');}
  catch {prompt.select();$('prompt-status').textContent=tr('Hãy sao chép phần văn bản đã chọn.');}
};
if(videoEnabled) $('video-input').onchange=()=>{
  const file=$('video-input').files[0], preview=$('video-preview');
  if(clipUrl) URL.revokeObjectURL(clipUrl);
  clipUrl=file ? URL.createObjectURL(file) : null;
  preview.hidden=!file;
  if(file) preview.src=clipUrl;
  else {preview.removeAttribute('src');preview.load();}
  $('clip-name').textContent=file?.name || tr('Chưa chọn clip');
  resetVideo();
  syncWorkflow();
};
async function withEncoder(work){
  let ffmpeg,worker;
  try {
    const cdn='https://cdn.jsdelivr.net/npm/';
    const moduleBase=cdn+'@ffmpeg/ffmpeg@0.12.15/dist/esm/';
    const core=cdn+'@ffmpeg/core@0.12.10/dist/esm/';
    const {FFmpeg}=await import(moduleBase+'index.js');
    worker=URL.createObjectURL(new Blob(['import '+JSON.stringify(moduleBase+'worker.js')+';'],{type:'text/javascript'}));
    ffmpeg=new FFmpeg();
    const deadline=AbortSignal.timeout(90000);
    await ffmpeg.load({classWorkerURL:worker,coreURL:core+'ffmpeg-core.js',wasmURL:core+'ffmpeg-core.wasm'},{signal:deadline});
  } catch {
    if(ffmpeg) ffmpeg.terminate();
    if(worker) URL.revokeObjectURL(worker);
    throw Error(tr('Không tải được bộ xuất video. Hãy kiểm tra kết nối rồi thử lại.'));
  }
  try {return await work(ffmpeg);}
  finally {ffmpeg.terminate();URL.revokeObjectURL(worker);}
}
async function encodeStage(ffmpeg,args,step,message,length,start,end,errorMessage){
  let latest=start;
  progressStage(step,Number.isFinite(length)&&length>0?start:null,message);
  const update=({time})=>{
    if(!(length>0) || !Number.isFinite(time)) return;
    latest=Math.max(latest,start+(end-start)*clamp(time/1e6/length,0,.99));
    progressStage(step,latest,message);
  };
  ffmpeg.on('progress',update);
  try {if(await ffmpeg.exec(args)!==0) throw Error(errorMessage);}
  finally {ffmpeg.off('progress',update);}
  progressStage(step,end,message);
}
const exportFps=24;
const clipArgs=()=>['-i','/source/clip','-map','0:v:0','-an','-vf','scale=trunc(iw/2)*2:trunc(ih/2)*2',
  '-r',String(exportFps),'-c:v','libx264','-preset','ultrafast','-crf','21','-maxrate','3M','-bufsize','6M',
  '-bf','0','-pix_fmt','yuv420p','short.mp4'];
const audioArgs=()=>['-i','/source/mix.wav','-map','0:a:0','-c:a','aac','-b:a','192k','sound.m4a'];
async function mountEncoderInput(ffmpeg,name,blob){
  await ffmpeg.createDir('/source');
  const mounted=await ffmpeg.mount('WORKERFS',{blobs:[{name,data:blob}]},'/source');
  if(!mounted) await ffmpeg.writeFile('/source/'+name,new Uint8Array(await blob.arrayBuffer()));
}
async function readMp4(ffmpeg,name){
  const data=await ffmpeg.readFile(name);
  if(!data.byteLength) throw Error(tr('Tệp trung gian bị rỗng.'));
  return new Blob([data],{type:'video/mp4'});
}
async function loadMp4(){
  try {return await import('https://cdn.jsdelivr.net/npm/mediabunny@1.65.2/dist/bundles/mediabunny.mjs');}
  catch {throw Error(tr('Không tải được bộ ghi MP4. Hãy kiểm tra kết nối rồi thử lại.'));}
}
async function readClip(mp4,blob){
  const input=new mp4.Input({formats:[mp4.MP4],source:new mp4.BlobSource(blob)});
  try {
    const track=await input.getPrimaryVideoTrack();
    if(!track) throw Error(tr('Clip đã chuẩn hóa không có luồng hình.'));
    const decoderConfig=await track.getDecoderConfig();
    const packets=[];
    for await(const packet of new mp4.EncodedPacketSink(track).packets()) packets.push(packet);
    if(!decoderConfig || packets[0]?.type!=='key') throw Error(tr('Clip đã chuẩn hóa thiếu khung hình mở đầu.'));
    return {packets,decoderConfig};
  } finally {input.dispose();}
}
let exportDirectory;
async function openMp4Target(mp4){
  if(!exportDirectory){
    exportDirectory=(async()=>{
      try {
        const root=await navigator.storage.getDirectory();
        const dir=await root.getDirectoryHandle('wnc-video-exports',{create:true});
        const cutoff=Date.now()-2*24*60*60*1000;
        for await(const [name,handle] of dir.entries()){
          if(handle.kind==='file' && Number(name.split('-')[0])<cutoff){
            await dir.removeEntry(name).catch(()=>{});
          }
        }
        return dir;
      } catch {return null;}
    })();
  }
  const dir=await exportDirectory;
  if(dir && typeof FileSystemFileHandle.prototype.createWritable==='function'){
    const name=Date.now()+'-'+crypto.randomUUID()+'.mp4';
    const handle=await dir.getFileHandle(name,{create:true});
    try {
      const writer=await handle.createWritable();
      return {
        target:new mp4.StreamTarget(writer,{chunked:true}),
        finish:async()=>{const file=await handle.getFile();return file.slice(0,file.size,'video/mp4');},
        discard:async()=>{await writer.abort().catch(()=>{});await dir.removeEntry(name).catch(()=>{});}
      };
    } catch(error){
      await dir.removeEntry(name).catch(()=>{});
      throw error;
    }
  }
  const target=new mp4.BufferTarget();
  return {target,finish:()=>new Blob([target.buffer],{type:'video/mp4'})};
}
async function writeVideoMp4(mp4,clip,duration,step,aac){
  const start=aac?72:55, message=aac?tr('Đang ghép âm thanh và ghi MP4'):tr('Đang lặp clip và ghi video nền');
  progressStage(step,start,message);
  const frames=Math.ceil(duration*exportFps);
  let input,audioTrack,audioPackets,output,destination;
  try {
    if(aac){
      input=new mp4.Input({formats:[mp4.MP4],source:new mp4.BlobSource(aac)});
      audioTrack=await input.getPrimaryAudioTrack();
      if(!audioTrack) throw Error(tr('Bản phối đã mã hóa không có luồng âm thanh.'));
    }
    destination=await openMp4Target(mp4);
    output=new mp4.Output({target:destination.target,format:new mp4.Mp4OutputFormat({fastStart:'reserve'})});
    const videoSource=new mp4.EncodedVideoPacketSource('avc');
    output.addVideoTrack(videoSource,{maximumPacketCount:frames});
    const audioSource=audioTrack?new mp4.EncodedAudioPacketSource('aac'):null;
    let audioConfig,nextAudio,hasAudio=false;
    if(audioSource){
      audioConfig=await audioTrack.getDecoderConfig();
      if(!audioConfig) throw Error(tr('Không đọc được thông số âm thanh AAC.'));
      const maxAudioPackets=Math.ceil(duration*audioConfig.sampleRate/1024)+4;
      output.addAudioTrack(audioSource,{maximumPacketCount:maxAudioPackets});
      audioPackets=new mp4.EncodedPacketSink(audioTrack).packets();
      nextAudio=(await audioPackets.next()).value;
      // The AAC encoder may expose a negative-timestamp priming packet.
      while(nextAudio?.timestamp<0) nextAudio=(await audioPackets.next()).value;
    }
    await output.start();
    for(let frame=0;frame<frames;frame++){
      const timestamp=frame/exportFps, end=Math.min(duration,(frame+1)/exportFps);
      const packet=clip.packets[frame%clip.packets.length];
      await videoSource.add(packet.clone({timestamp,duration:end-timestamp}),frame===0?{decoderConfig:clip.decoderConfig}:undefined);
      while(nextAudio && nextAudio.timestamp<end){
        const packetDuration=Math.min(nextAudio.duration,duration-nextAudio.timestamp);
        await audioSource.add(nextAudio.clone({duration:packetDuration}),hasAudio?undefined:{decoderConfig:audioConfig});
        hasAudio=true;
        nextAudio=(await audioPackets.next()).value;
      }
      if(frame%exportFps===0){
        progressStage(step,start+(97-start)*frame/frames,message);
        await new Promise(resolve=>setTimeout(resolve,0));
      }
    }
    if(audioSource && !hasAudio) throw Error(tr('Không tìm thấy gói âm thanh để ghép.'));
    progressStage(step,98,tr('Đang hoàn tất tệp MP4'));
    await output.finalize();
    const blob=await destination.finish();
    if(!blob.size) throw Error(tr('Tệp MP4 xuất ra bị rỗng.'));
    return blob;
  } catch(error){
    if(output) await output.cancel().catch(()=>{});
    if(destination?.discard) await destination.discard();
    throw error;
  } finally {
    if(audioPackets) await audioPackets.return();
    if(input) input.dispose();
  }
}
if(videoEnabled) $('render-video').onclick=async()=>{
  const file=$('video-input').files[0], audio=audioExport;
  if(exporting || !file || !audio) return;
  const clipDuration=$('video-preview').duration;
  $('video-preview').pause();
  resetVideo();exportBusy(true);
  progressStage('video',null,tr('Đang tải bộ xuất video'));
  try {
    const mp4=await loadMp4();
    const short=await withEncoder(async ffmpeg=>{
      progressStage('video',4,tr('Đang mở clip đã chọn'));
      await mountEncoderInput(ffmpeg,'clip',file);
      await encodeStage(ffmpeg,clipArgs(),'video',tr('Đang chuẩn hóa clip và bỏ tiếng gốc'),clipDuration,8,52,
        tr('Không đọc hoặc mã hóa được clip đã chọn.'));
      return readMp4(ffmpeg,'short.mp4');
    });
    const clip=await readClip(mp4,short);
    const blob=await writeVideoMp4(mp4,clip,audio.duration,'video');
    showDownload('video',blob,audio.title+' - video nen','mp4',tr('Tải video nền'));
    videoExport={clip};
    progressStage('video',100,tr('Video nền đã sẵn sàng · ')+durationLabel(audio.duration)+tr(' · Không có tiếng.'));
    progressStage('mux',0,tr('Có thể ghép bản WAV vào video nền.'));
  } catch(error){stageError('video',error);}
  finally {exportBusy(false);}
};
if(videoEnabled) $('mux-video').onclick=async()=>{
  const audio=audioExport, video=videoExport;
  if(exporting || !audio || !video) return;
  clearResult('mux');exportBusy(true);
  progressStage('mux',null,tr('Đang tải bộ xuất video'));
  try {
    const mp4=await loadMp4();
    const aac=await withEncoder(async ffmpeg=>{
      progressStage('mux',4,tr('Đang mở bản WAV'));
      await mountEncoderInput(ffmpeg,'mix.wav',audio.blob);
      await encodeStage(ffmpeg,audioArgs(),'mux',tr('Đang mã hóa âm thanh AAC'),audio.duration,8,70,
        tr('Không mã hóa được âm thanh từ bản WAV.'));
      return readMp4(ffmpeg,'sound.m4a');
    });
    const blob=await writeVideoMp4(mp4,video.clip,audio.duration,'mux',aac);
    showDownload('mux',blob,audio.title,'mp4',tr('Tải MP4 thành phẩm'));
    progressStage('mux',100,tr('Đã xuất video có âm thanh · ')+durationLabel(audio.duration)+'.');
  } catch(error){stageError('mux',error);}
  finally {exportBusy(false);}
};
$('export-link').onclick=()=>($('audio-studio') || $('video-studio')).scrollIntoView({behavior:'smooth'});
