/* WhiteNoiseChoir Dual Scene: full-length A+B, no B loop, no video transcode.
 * MP4 video packets are remuxed intact when H.264 decoder configs match.
 * Audio from two independent mixers is joined once into AAC. Browser OPFS
 * streams the final output, so the compositor need not decode rendered B.
 */
(() => {
'use strict';
const $=id=>document.getElementById(id);
const state={A:null,B:null},waiting=new Map(),lastClip={A:null,B:null},tickets={A:0,B:0};
const round=n=>Number.isFinite(n)?Number(n).toFixed(3).replace(/0+$/,'').replace(/\.$/,''):'—';
const clock=n=>{if(!Number.isFinite(n))return '—';const h=Math.floor(n/3600),m=Math.floor(n%3600/60),s=(n%60).toFixed(3).replace(/0+$/,'').replace(/\.$/,'');return (h?h+':':'')+String(m).padStart(h?2:1,'0')+':'+s.padStart(2,'0');};
const report=(message,progress)=>{ $('join-status').textContent=message; if(Number.isFinite(progress))$('join-progress').value=Math.max(0,Math.min(100,progress)); };
const sceneFrame=id=>$('scene-'+id).contentWindow;
const pause=()=>new Promise(resolve=>setTimeout(resolve,0));
function request(id,action,extra={}){
  return new Promise((resolve,reject)=>{
    const requestId=crypto.randomUUID(),frame=sceneFrame(id);
    if(!frame)return reject(Error('Mixer '+id+' chưa tải xong.'));
    const timer=setTimeout(()=>{waiting.delete(requestId);reject(Error('Mixer '+id+' không phản hồi. Hãy tải lại trang.'));},20000);
    waiting.set(requestId,{resolve,reject,timer});
    frame.postMessage({scope:'wnc-dual',requestId,action,...extra},location.origin);
  });
}
window.addEventListener('message',event=>{
  if(event.origin!==location.origin)return;
  const id=event.data?.scene,msg=event.data;
  if(!['A','B'].includes(id)||event.source!==sceneFrame(id)||msg.scope!=='wnc-dual')return;
  if(msg.type==='ready'){state[id]=msg.data;paint();return;}
  if(msg.type==='clip-cleared'){
    lastClip[id]=null;tickets[id]++;state[id]=msg.data;paint();
    $('clip-sync-status').textContent='Đã gỡ clip '+id+'. Chọn lại video để cập nhật thời lượng.';return;
  }
  if(msg.type==='clip-error'){
    $('clip-sync-status').textContent='Không đọc được video '+id+': '+msg.error;return;
  }
  if(msg.type==='clip-duration'){
    state[id]=msg.data;lastClip[id]=msg.data;paint();
    if($('auto-clip-sync').checked)sync(id,msg.data);
    else $('clip-sync-status').textContent='Đã đọc clip '+id+' ('+round(msg.data.videoRawDuration)+' giây). Bấm Đồng bộ theo video A/B.';
    return;
  }
  const job=waiting.get(msg.requestId);if(!job)return;
  waiting.delete(msg.requestId);clearTimeout(job.timer);
  if(!msg.ok)job.reject(Error(msg.error||'Mixer không trả lời.'));
  else {if(msg.action==='status'||msg.action==='set-duration')state[id]=msg.data;paint();job.resolve(msg.data);}
});
function paint(){
  for(const id of ['A','B']){
    const s=state[id];
    $('state-'+id).textContent=s?clock(s.duration)+' · WAV '+(s.hasWav?'✓':'chưa')+' · MP4 '+(s.hasVideo?'✓':'chưa'):'Đang tải…';
  }
  if(state.A&&state.B){
    const total=state.A.duration+state.B.duration;
    $('duration-status').textContent='Mixer A '+clock(state.A.duration)+' + Mixer B '+clock(state.B.duration)+' = '+clock(total)+' (không giới hạn 10 phút)';
  }
}
async function getStatuses(){return Promise.all([request('A','status'),request('B','status')]);}
async function sync(id,info){
  const ticket=++tickets[id];
  try {
    const raw=Number(info?.videoRawDuration);
    const max=id==='A'?60:10800,min=id==='A'?1:6;
    if(!Number.isFinite(raw)||raw<min||raw>max)throw Error('Video '+id+' phải dài '+min+'–'+max+' giây.');
    const current=await request(id,'status');
    if(ticket!==tickets[id])return;
    if(current.videoName!==info.videoName||Math.abs(current.videoRawDuration-raw)>.01)throw Error('Clip '+id+' đã đổi trong lúc đọc.');
    if(Math.abs(current.duration-raw)<.0001){
      $('clip-sync-status').textContent='Video '+id+': '+round(raw)+'s. Mixer đã khớp, WAV còn hợp lệ nếu bản phối không đổi.';
      return;
    }
    await request(id,'set-duration',{seconds:raw});
    if(ticket!==tickets[id])return;
    $('clip-sync-status').textContent='Đã đồng bộ video '+id+' theo MP4 thực tế '+round(raw)+'s. '
      +(current.hasWav?'WAV cũ không còn hợp lệ; hãy Xuất WAV lại.':'Hãy xuất WAV sau khi phối âm.')
      +' Không sửa độ dài video '+(id==='A'?'B.':'A.');
  }catch(e){if(ticket===tickets[id])$('clip-sync-status').textContent=String(e.message||e);}
}
$('refresh').onclick=()=>getStatuses().catch(e=>report(e.message));
$('auto-clip-sync').onchange=()=>{
  if($('auto-clip-sync').checked)for(const id of ['A','B'])if(lastClip[id])sync(id,lastClip[id]);
  else $('clip-sync-status').textContent='Tự đồng bộ đã tắt. Bạn có thể bấm Đồng bộ theo video A/B.';
};
$('sync-from-clip').onclick=async()=>{
  for(const id of ['A','B']){
    try{const data=await request(id,'probe-clip');lastClip[id]=data;await sync(id,data);}
    catch(e){$('clip-sync-status').textContent='Video '+id+': '+String(e.message||e);}
  }
};
async function viewFrame(file,kind){
  const video=document.createElement('video'),url=URL.createObjectURL(file);
  video.preload='auto';video.muted=true;video.playsInline=true;
  let timer;
  try{
    await new Promise((resolve,reject)=>{
      timer=setTimeout(()=>reject(Error('Không đọc được khung hình video.')),25000);
      video.onloadeddata=()=>{clearTimeout(timer);resolve();};
      video.onerror=()=>{clearTimeout(timer);reject(Error('Không giải mã được clip MP4.'));};
      video.src=url;
    });
    const target=kind==='end'?Math.max(0,video.duration-0.04):0;
    if(target>0)await new Promise((resolve,reject)=>{
      timer=setTimeout(()=>reject(Error('Không tua được đến cuối video.')),20000);
      video.onseeked=()=>{clearTimeout(timer);resolve();};
      video.currentTime=target;
    });
    const cv=document.createElement('canvas');cv.width=320;cv.height=180;
    const ctx=cv.getContext('2d',{willReadFrequently:true});
    ctx.drawImage(video,0,0,320,180);return ctx.getImageData(0,0,320,180);
  }finally{clearTimeout(timer);video.pause();video.removeAttribute('src');video.load();URL.revokeObjectURL(url);}
}
function diff(a,b){let sum=0;for(let i=0;i<a.data.length;i+=4)sum+=Math.abs(a.data[i]-b.data[i])+Math.abs(a.data[i+1]-b.data[i+1])+Math.abs(a.data[i+2]-b.data[i+2]);return sum*100/(a.data.length/4*3*255);}
$('check-seams').onclick=async()=>{
  const control=$('check-seams');control.disabled=true;
  try{
    const [a,b]=await Promise.all([request('A','collect-video'),request('B','collect-video')]);
    const [lastA,firstB,lastB]=await Promise.all([viewFrame(a.video,'end'),viewFrame(b.video,'start'),viewFrame(b.video,'end')]);
    for(const [id,frame] of [['exit-a',lastA],['start-b',firstB],['exit-b',lastB]])$(id).getContext('2d').putImageData(frame,0,0);
    const score=diff(lastA,firstB);
    $('seam-status').textContent='Độ khác biệt frame cuối A / đầu B: '+score.toFixed(2)+'%. '+(score>6?'Cần kiểm tra chuyển cảnh.':'Kiểm tra thêm chuyển động thực tế.');
  }catch(e){$('seam-status').textContent=String(e.message||e);}
  finally{control.disabled=false;}
};
async function loadMp4(){
  try{return await import('https://cdn.jsdelivr.net/npm/mediabunny@1.65.2/dist/bundles/mediabunny.mjs');}
  catch{throw Error('Không tải được thư viện ghép MP4 Mediabunny.');}
}
async function videoSource(mp4,file){
  const input=new mp4.Input({formats:[mp4.MP4],source:new mp4.BlobSource(file)});
  try{
    const track=await input.getPrimaryVideoTrack();
    if(!track)throw Error('File '+file.name+' không có luồng hình.');
    const cfg=await track.getDecoderConfig();
    if(!cfg||!cfg.codec?.startsWith('avc1.'))throw Error('File '+file.name+' phải là H.264/AVC MP4 để ghép không mã hóa lại.');
    const reader=new mp4.EncodedPacketSink(track).packets();
    const first=(await reader.next()).value;
    if(!first||first.type!=='key')throw Error('File '+file.name+' không bắt đầu bằng keyframe hợp lệ.');
    return {input,cfg,reader,first,file};
  }catch(e){input.dispose();throw e;}
}
function sameConfiguration(a,b){
  if(a.codec!==b.codec||a.codedWidth!==b.codedWidth||a.codedHeight!==b.codedHeight)return false;
  const aa=a.description?new Uint8Array(a.description):null,bb=b.description?new Uint8Array(b.description):null;
  if(!aa||!bb)return !aa&&!bb;
  return aa.length===bb.length&&aa.every((x,i)=>x===bb[i]);
}
async function loadEncoder(){
  const cdn='https://cdn.jsdelivr.net/npm/',base=cdn+'@ffmpeg/ffmpeg@0.12.15/dist/esm/',core=cdn+'@ffmpeg/core@0.12.10/dist/esm/';
  const {FFmpeg}=await import(base+'index.js');
  const worker=URL.createObjectURL(new Blob(['import '+JSON.stringify(base+'worker.js')+';'],{type:'text/javascript'}));
  const ffmpeg=new FFmpeg();
  try{
    await ffmpeg.load({classWorkerURL:worker,coreURL:core+'ffmpeg-core.js',wasmURL:core+'ffmpeg-core.wasm'},{signal:AbortSignal.timeout(90000)});
    return {ffmpeg,release:()=>{ffmpeg.terminate();URL.revokeObjectURL(worker);}};
  }catch(e){ffmpeg.terminate();URL.revokeObjectURL(worker);throw Error('Không nạp được FFmpeg để mã hóa WAV thành AAC.');}
}
async function encodeAudio(a,b){
  report('Đang mã hóa hai bản WAV thành một luồng AAC…',5);
  const encoder=await loadEncoder(),f=encoder.ffmpeg;
  try{
    await f.createDir('/source');
    const files=[{name:'a.wav',data:a.wav},{name:'b.wav',data:b.wav}];
    const mounted=await f.mount('WORKERFS',{blobs:files},'/source');
    if(!mounted)for(const item of files)await f.writeFile('/source/'+item.name,new Uint8Array(await item.data.arrayBuffer()));
    const durA=a.duration,durB=b.duration;
    const fade=Math.min(0.04,durA/4,durB/4);
    const af='[0:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:'+durA.toFixed(6)+',afade=t=out:st='+(durA-fade).toFixed(6)+':d='+fade.toFixed(6)+'[x];[1:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:'+durB.toFixed(6)+',afade=t=in:st=0:d='+fade.toFixed(6)+'[y];[x][y]concat=n=2:v=0:a=1[out]';
    const args=['-i','/source/a.wav','-i','/source/b.wav','-filter_complex',af,'-map','[out]','-vn','-c:a','aac','-b:a','192k','-ar','44100','-ac','2','sound.m4a'];
    if(await f.exec(args)!==0)throw Error('FFmpeg không ghép được hai bản WAV.');
    const bytes=await f.readFile('sound.m4a');
    if(!bytes.byteLength)throw Error('Tệp AAC rỗng.');
    return new Blob([bytes],{type:'audio/mp4'});
  }finally{encoder.release();}
}
async function targetFor(mp4,total){
  try{
    const root=await navigator.storage.getDirectory(),dir=await root.getDirectoryHandle('wnc-dual-exports',{create:true});
    const name=Date.now()+'-'+crypto.randomUUID()+'.mp4';
    const handle=await dir.getFileHandle(name,{create:true}),writer=await handle.createWritable();
    return {target:new mp4.StreamTarget(writer,{chunked:true}),finish:async()=>{const file=await handle.getFile();return file.slice(0,file.size,'video/mp4');},
      discard:async()=>{await writer.abort().catch(()=>{});await dir.removeEntry(name).catch(()=>{});}};
  }catch(e){
    if(total>900)throw Error('Xuất dài hơn 15 phút cần trình duyệt hỗ trợ lưu trực tiếp (OPFS). Hãy thử Chrome hoặc Edge trên máy tính.');
    const t=new mp4.BufferTarget();
    return {target:t,finish:()=>new Blob([t.buffer],{type:'video/mp4'}),discard:async()=>{}};
  }
}
async function remux(mp4,a,b,soundFile){
  const [va,vb]=await Promise.all([videoSource(mp4,a.video),videoSource(mp4,b.video)]);
  let audioInput=null,iterator=null,output=null,dest=null;
  try{
    if(!sameConfiguration(va.cfg,vb.cfg))
      throw Error('Hai MP4 khác cấu hình H.264 (codec / độ phân giải / SPS-PPS). Không thể stream-copy an toàn. Hãy chuẩn hóa hai file bằng cùng thông số ngoài Studio, rồi tải lại; video B sẽ không bị mã hóa lại tại đây.');
    audioInput=new mp4.Input({formats:[mp4.MP4],source:new mp4.BlobSource(soundFile)});
    const audioTrack=await audioInput.getPrimaryAudioTrack();
    if(!audioTrack)throw Error('Không tìm thấy âm thanh AAC.');
    const audioConfig=await audioTrack.getDecoderConfig();
    if(!audioConfig)throw Error('Thiếu thông số decoder AAC.');
    const total=a.duration+b.duration;
    dest=await targetFor(mp4,total);
    output=new mp4.Output({target:dest.target,format:new mp4.Mp4OutputFormat({fastStart:'reserve'})});
    const video=new mp4.EncodedVideoPacketSource('avc'),audio=new mp4.EncodedAudioPacketSource('aac');
    output.addVideoTrack(video,{maximumPacketCount:Math.ceil(total*150)+200});
    output.addAudioTrack(audio,{maximumPacketCount:Math.ceil(total*audioConfig.sampleRate/1024)+16});
    iterator=new mp4.EncodedPacketSink(audioTrack).packets();
    let audioNext=(await iterator.next()).value,hasAudio=false,packetCount=0;
    while(audioNext&&audioNext.timestamp<0)audioNext=(await iterator.next()).value;
    await output.start();
    async function pushSound(until){
      while(audioNext&&audioNext.timestamp<=until){
        const p=audioNext;
        const usable=Math.min(p.duration,Math.max(0,total-p.timestamp));
        if(usable>0){
          await audio.add(p.clone({duration:usable}),hasAudio?undefined:{decoderConfig:audioConfig});
          hasAudio=true;
        }
        audioNext=(await iterator.next()).value;
      }
    }
    async function pushScene(scene,offset,isFirst){
      const base=scene.first.timestamp;
      let packet=scene.first;
      while(packet){
        // Clone packets only: no decoding or reencoding of already rendered video B.
        const ts=offset+packet.timestamp-base;
        if(ts<-.001)throw Error('Video có timestamp âm không phù hợp với nối trực tiếp.');
        await video.add(packet.clone({timestamp:ts}),isFirst&&packetCount===0?{decoderConfig:scene.cfg}:undefined);
        packetCount++;
        await pushSound(ts+packet.duration);
        if(packetCount%180===0){report('Đang ghép nguyên bản video '+(isFirst?'A':'B')+' · '+clock(ts)+' / '+clock(total),25+70*Math.min(1,ts/total));await pause();}
        packet=(await scene.reader.next()).value;
      }
    }
    await pushScene(va,0,true);
    await pushScene(vb,a.duration,false);
    await pushSound(Infinity);
    if(!hasAudio)throw Error('Không có dữ liệu AAC trong video thành phẩm.');
    report('Đang hoàn tất MP4 (giữ nguyên hình ảnh)…',98);
    await output.finalize();
    const finished=await dest.finish();
    if(!finished.size)throw Error('MP4 cuối bị rỗng.');
    return finished;
  }catch(error){if(output)await output.cancel().catch(()=>{});if(dest)await dest.discard().catch(()=>{});throw error;}
  finally{
    if(iterator)await iterator.return();
    if(audioInput)audioInput.dispose();
    for(const v of [va,vb]){await v.reader.return?.();v.input.dispose();}
  }
}
let downloadUrl=null;
$('join').onclick=async()=>{
  const btn=$('join');btn.disabled=true;$('download').classList.add('hide');
  try{
    const [a,b]=await Promise.all([request('A','collect'),request('B','collect')]);
    if(a.duration<1||a.duration>60||b.duration<6||b.duration>10800)throw Error('Thời lượng A phải 1–60s và B 6–10800s.');
    if(!Number.isFinite(a.videoRawDuration)||!Number.isFinite(b.videoRawDuration))
      throw Error('Cần tải hai clip A và B và chờ hệ thống đọc thời lượng thực tế.');
    if(Math.abs(a.duration-a.videoRawDuration)>.02||Math.abs(b.duration-b.videoRawDuration)>.02)
      throw Error('Timeline âm thanh chưa khớp video. Hãy bấm Đồng bộ theo video A/B, rồi xuất lại WAV.');
    const mp4=await loadMp4();
    const sound=await encodeAudio(a,b);
    report('Đang ghép A + B không mã hóa lại video…',22);
    const file=await remux(mp4,a,b,sound);
    if(downloadUrl)URL.revokeObjectURL(downloadUrl);
    downloadUrl=URL.createObjectURL(file);
    const link=$('download');link.href=downloadUrl;link.classList.remove('hide');link.download=(a.title||'Dual-Scene').replace(/[\\/:*?"<>|]/g,'-')+'-A+B.mp4';
    const preview=$('joined-preview');preview.src=downloadUrl;preview.hidden=false;preview.load();
    report('Hoàn tất: '+clock(a.duration+b.duration)+' · A phát một lần, B giữ nguyên, video stream-copy · '+(file.size/1048576).toFixed(1)+' MiB.',100);
  }catch(e){console.error('Dual Scene',e);report('Chưa ghép được: '+String(e.message||e));}
  finally{btn.disabled=false;}
};
})();
