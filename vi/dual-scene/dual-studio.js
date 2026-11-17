/* WhiteNoiseChoir Dual Scene compositor. Experimental, local-only.
 * Avoid touching the stable Studio rendering, timeline, and media engine.
 * A is written once; B begins at an IDR and repeats by encoded packets.
 */
(() => {
'use strict';
const $=id=>document.getElementById(id);
const TOTAL_SECONDS=600, FPS=24;
const waiting=new Map(), state={A:null,B:null};
const pause=()=>new Promise(resolve=>setTimeout(resolve,0));
const format=n=>Number(n).toFixed(2).replace(/\.00$/,'');
const report=(message,progress)=>{
  $('join-status').textContent=message;
  if(Number.isFinite(progress))$('join-progress').value=Math.max(0,Math.min(100,progress));
};
const sceneFrame=id=>$('scene-'+id).contentWindow;
function request(id,action,extra={}){
  return new Promise((resolve,reject)=>{
    const requestId=crypto.randomUUID(),frame=sceneFrame(id);
    if(!frame)return reject(Error('Mixer '+id+' chưa sẵn sàng.'));
    const timer=setTimeout(()=>{waiting.delete(requestId);reject(Error('Mixer '+id+' không trả lời. Hãy tải lại trang.'));},16000);
    waiting.set(requestId,{resolve,reject,timer});
    frame.postMessage({scope:'wnc-dual',action,requestId,...extra},location.origin);
  });
}
window.addEventListener('message',event=>{
  if(event.origin!==location.origin)return;
  const id=event.data?.scene;
  if(!['A','B'].includes(id)||event.source!==sceneFrame(id)||event.data?.scope!=='wnc-dual')return;
  const message=event.data;
  if(message.type==='ready'){state[id]=message.data;paintStatus();return;}
  const item=waiting.get(message.requestId);
  if(!item)return;
  waiting.delete(message.requestId);clearTimeout(item.timer);
  if(message.ok){state[id]=message.data;paintStatus();item.resolve(message.data);}
  else item.reject(Error(message.error||'Không nhận được trạng thái mixer.'));
});
function paintStatus(){
  for(const id of ['A','B']){
    const s=state[id];
    $('state-'+id).textContent=s?(format(s.duration)+'s · WAV '+(s.hasWav?'✓':'chưa')+' · Clip '+(s.hasVideo?'✓':'chưa')):'Đang tải…';
  }
  if(state.A&&state.B){
    const total=state.A.duration+state.B.duration;
    $('duration-status').textContent='A '+format(state.A.duration)+'s + B '+format(state.B.duration)+'s = '+format(total)+'s '+(Math.abs(total-TOTAL_SECONDS)<.045?'✓':'(cần bằng 600s)');
  }
}
async function getStatuses(){
  const [a,b]=await Promise.all([request('A','status'),request('B','status')]);
  return [a,b];
}
$('refresh').onclick=()=>getStatuses().catch(e=>report(e.message));
$('sync-length').onclick=async()=>{
  try{
    const a=await request('A','status');
    const length=TOTAL_SECONDS-a.duration;
    if(!(length>=6&&length<=600))throw Error('Cảnh A phải ngắn hơn 594 giây.');
    const b=await request('B','status');
    if(b.duration!==length && !confirm('Đặt chiều dài mixer B thành '+format(length)+' giây? Bản phối B có thể cần chỉnh lại các clip.'))return;
    await request('B','set-duration',{seconds:length});
    report('Đã đồng bộ thời lượng B. Nếu WAV B đã xuất trước đó, hãy xuất lại.');
  }catch(e){report(e.message);}
};
async function metadata(file){
  return new Promise((resolve,reject)=>{
    const node=document.createElement('video'),url=URL.createObjectURL(file);
    const clean=()=>{node.pause();node.removeAttribute('src');node.load();URL.revokeObjectURL(url);};
    const timeout=setTimeout(()=>{clean();reject(Error('Không đọc được metadata clip.'));},20000);
    node.preload='metadata';node.muted=true;node.playsInline=true;
    node.onloadedmetadata=()=>{
      clearTimeout(timeout);
      const duration=node.duration;
      clean();
      if(!Number.isFinite(duration)||duration<=0)reject(Error('Thời lượng clip không hợp lệ.'));
      else resolve({duration});
    };
    node.onerror=()=>{clearTimeout(timeout);clean();reject(Error('Clip không giải mã được. Hãy dùng MP4 H.264.'));};
    node.src=url;
  });
}
async function frameImage(file,kind){
  const video=document.createElement('video');
  video.muted=true;video.playsInline=true;video.preload='auto';
  const url=URL.createObjectURL(file);
  const load=new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('Không giải mã được frame để kiểm tra.')),20000);
    video.onloadeddata=()=>{clearTimeout(timer);resolve();};
    video.onerror=()=>{clearTimeout(timer);reject(Error('Không xem được video trên trình duyệt.'));};
  });
  try{
    video.src=url;await load;
    const d=video.duration, at=kind==='end'?Math.max(0,d-1/FPS):0;
    if(at>0){
      await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>reject(Error('Không tua đến frame cuối.')),15000);
        video.onseeked=()=>{clearTimeout(timer);resolve();};
        video.currentTime=at;
      });
    }
    const canvas=document.createElement('canvas');canvas.width=320;canvas.height=180;
    const ctx=canvas.getContext('2d',{willReadFrequently:true});
    ctx.drawImage(video,0,0,320,180);
    return ctx.getImageData(0,0,320,180);
  }finally{video.pause();video.removeAttribute('src');video.load();URL.revokeObjectURL(url);}
}
function difference(a,b){
  let sum=0;for(let i=0;i<a.data.length;i+=4)sum+=Math.abs(a.data[i]-b.data[i])+Math.abs(a.data[i+1]-b.data[i+1])+Math.abs(a.data[i+2]-b.data[i+2]);
  return 100*sum/(a.data.length/4*3*255);
}
function displayFrame(id,bitmap){$(''+id).getContext('2d').putImageData(bitmap,0,0);}
async function checkSeams(a,b){
  const [lastA,firstB,lastB]=await Promise.all([frameImage(a,'end'),frameImage(b,'start'),frameImage(b,'end')]);
  displayFrame('exit-a',lastA);displayFrame('start-b',firstB);displayFrame('exit-b',lastB);displayFrame('loop-b',firstB);
  const ab=difference(lastA,firstB),bb=difference(lastB,firstB);
  $('seam-status').textContent='A→B: '+ab.toFixed(2)+'% · B→B: '+bb.toFixed(2)+'%'+(Math.max(ab,bb)>6?' · Khác biệt lớn, cần xem kỹ':' · Nên xem thử chuyển động');
  return {ab,bb};
}
$('check-seams').onclick=async()=>{
  const el=$('check-seams');el.disabled=true;
  try{
    const [a,b]=await Promise.all([request('A','collect'),request('B','collect')]);
    await checkSeams(a.video,b.video);
  }catch(e){$('seam-status').textContent=e.message;}
  finally{el.disabled=false;}
};
async function loadEncoder(){
  const base='https://cdn.jsdelivr.net/npm/',moduleBase=base+'@ffmpeg/ffmpeg@0.12.15/dist/esm/',core=base+'@ffmpeg/core@0.12.10/dist/esm/';
  const {FFmpeg}=await import(moduleBase+'index.js');
  const worker=URL.createObjectURL(new Blob(['import '+JSON.stringify(moduleBase+'worker.js')+';'],{type:'text/javascript'}));
  const ffmpeg=new FFmpeg();
  try{
    await ffmpeg.load({classWorkerURL:worker,coreURL:core+'ffmpeg-core.js',wasmURL:core+'ffmpeg-core.wasm'},{signal:AbortSignal.timeout(90000)});
    return {ffmpeg,release:()=>{ffmpeg.terminate();URL.revokeObjectURL(worker);}};
  }catch(error){
    ffmpeg.terminate();URL.revokeObjectURL(worker);
    throw Error('Không nạp được bộ xử lý FFmpeg. Hãy dùng máy tính và kiểm tra kết nối.');
  }
}
async function mountFiles(ffmpeg,items){
  await ffmpeg.createDir('/source');
  const data=items.map(([name,file])=>({name,data:file}));
  const mounted=await ffmpeg.mount('WORKERFS',{blobs:data},'/source');
  if(!mounted)for(const [name,blob] of items)await ffmpeg.writeFile('/source/'+name,new Uint8Array(await blob.arrayBuffer()));
}
async function execute(ffmpeg,args,description){
  const rc=await ffmpeg.exec(args);
  if(rc!==0)throw Error(description+' (FFmpeg exit '+rc+').');
}
async function runEncode(a,b,intro,bFrames,width,height){
  let encoder;
  try{
    report('Đang nạp FFmpeg…',4);encoder=await loadEncoder();
    const f=encoder.ffmpeg;
    await mountFiles(f,[['scene-a.mp4',a.video],['scene-b.mp4',b.video],['scene-a.wav',a.wav],['scene-b.wav',b.wav]]);
    const aFrames=Math.round(intro*FPS), vf='fps='+FPS+',scale='+width+':'+height+':force_original_aspect_ratio=decrease,pad='+width+':'+height+':(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p';
    const filter='[0:v]'+vf+',trim=end_frame='+aFrames+',setpts=PTS-STARTPTS[va];[1:v]'+vf+',trim=end_frame='+bFrames+',setpts=PTS-STARTPTS[vb];[va][vb]concat=n=2:v=1:a=0[v]';
    report('Đang mã hóa hai clip trong cùng một luồng H.264…',13);
    await execute(f,['-i','/source/scene-a.mp4','-i','/source/scene-b.mp4','-filter_complex',filter,'-map','[v]','-an','-r',String(FPS),'-c:v','libx264','-preset','superfast','-crf','17','-maxrate','14M','-bufsize','28M','-bf','0','-g','48','-sc_threshold','0','-pix_fmt','yuv420p','-force_key_frames',String(intro),'-movflags','+faststart','short.mp4'],'Không mã hóa được clip A+B');
    const joined=new Blob([await f.readFile('short.mp4')],{type:'video/mp4'});
    report('Đang xử lý WAV của hai phân cảnh…',42);
    const A=intro.toFixed(6),B=(TOTAL_SECONDS-intro).toFixed(6);
    // Explicit 40ms endpoint de-click; no audio packet copying across independent AAC encoders.
    const filterAudio='[0:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:'+A+',afade=t=out:st='+(intro-.04).toFixed(6)+':d=0.04[x];[1:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:'+B+',afade=t=in:st=0:d=0.04[y];[x][y]concat=n=2:v=0:a=1[out]';
    await execute(f,['-i','/source/scene-a.wav','-i','/source/scene-b.wav','-filter_complex',filterAudio,'-map','[out]','-vn','-ar','44100','-ac','2','-c:a','aac','-b:a','192k','sound.m4a'],'Không ghép được hai bản WAV');
    const audio=new Blob([await f.readFile('sound.m4a')],{type:'audio/mp4'});
    return {joined,audio,aFrames};
  }finally{if(encoder)encoder.release();}
}
async function loadMediabunny(){
  try{return await import('https://cdn.jsdelivr.net/npm/mediabunny@1.65.2/dist/bundles/mediabunny.mjs');}
  catch{throw Error('Không nạp được Mediabunny để xuất MP4.');}
}
async function clipPackets(mp4,blob){
  const input=new mp4.Input({formats:[mp4.MP4],source:new mp4.BlobSource(blob)});
  try{
    const track=await input.getPrimaryVideoTrack();
    if(!track)throw Error('Clip H.264 không có hình.');
    const config=await track.getDecoderConfig(),packets=[];
    for await(const packet of new mp4.EncodedPacketSink(track).packets())packets.push(packet);
    if(!config||!packets.length||packets[0].type!=='key')throw Error('Clip thiếu keyframe đầu.');
    return {packets,config};
  }finally{input.dispose();}
}
async function openOutput(mp4){
  let dir=null;
  try{
    const root=await navigator.storage.getDirectory();
    dir=await root.getDirectoryHandle('wnc-dual-exports',{create:true});
  }catch{}
  if(dir&&typeof FileSystemFileHandle!=='undefined'&&typeof FileSystemFileHandle.prototype.createWritable==='function'){
    const name=Date.now()+'-'+crypto.randomUUID()+'.mp4';
    const handle=await dir.getFileHandle(name,{create:true});
    const writer=await handle.createWritable();
    return {target:new mp4.StreamTarget(writer,{chunked:true}),
      finish:async()=>{const file=await handle.getFile();return file.slice(0,file.size,'video/mp4');},
      discard:async()=>{await writer.abort().catch(()=>{});await dir.removeEntry(name).catch(()=>{});}};
  }
  const target=new mp4.BufferTarget();
  return {target,finish:()=>new Blob([target.buffer],{type:'video/mp4'}),discard:async()=>{}};
}
async function compose(mp4,video,aac,aFrames){
  const intro=video.packets.slice(0,aFrames),loop=video.packets.slice(aFrames);
  if(intro.length!==aFrames||loop.length<2||loop[0].type!=='key')
    throw Error('Không xác nhận được keyframe bắt đầu B. Chưa ghép để tránh video hỏng.');
  const audioInput=new mp4.Input({formats:[mp4.MP4],source:new mp4.BlobSource(aac)});
  let stream=null,output=null,iterator=null;
  try{
    const audioTrack=await audioInput.getPrimaryAudioTrack();
    if(!audioTrack)throw Error('Tệp AAC thiếu luồng âm.');
    const audioConfig=await audioTrack.getDecoderConfig();
    if(!audioConfig)throw Error('Không đọc được codec AAC.');
    stream=await openOutput(mp4);
    output=new mp4.Output({target:stream.target,format:new mp4.Mp4OutputFormat({fastStart:'reserve'})});
    const picture=new mp4.EncodedVideoPacketSource('avc');
    const sound=new mp4.EncodedAudioPacketSource('aac');
    const frames=TOTAL_SECONDS*FPS;
    output.addVideoTrack(picture,{maximumPacketCount:frames});
    output.addAudioTrack(sound,{maximumPacketCount:Math.ceil(TOTAL_SECONDS*audioConfig.sampleRate/1024)+8});
    iterator=new mp4.EncodedPacketSink(audioTrack).packets();
    let next=(await iterator.next()).value,hasAudio=false;
    while(next?.timestamp<0)next=(await iterator.next()).value;
    await output.start();
    for(let i=0;i<frames;i++){
      const time=i/FPS,end=(i+1)/FPS;
      const source=i<aFrames?intro[i]:loop[(i-aFrames)%loop.length];
      await picture.add(source.clone({timestamp:time,duration:1/FPS}),i===0?{decoderConfig:video.config}:undefined);
      while(next&&next.timestamp<end){
        const dur=Math.min(next.duration,TOTAL_SECONDS-next.timestamp);
        if(dur>0){await sound.add(next.clone({duration:dur}),hasAudio?undefined:{decoderConfig:audioConfig});hasAudio=true;}
        next=(await iterator.next()).value;
      }
      if(i%FPS===0){
        report('Đang ghi MP4: A một lần, B lặp '+Math.floor((i-aFrames)/Math.max(1,loop.length)+1).toString()+' vòng…',65+33*i/frames);
        await pause();
      }
    }
    if(!hasAudio)throw Error('Không ghi được âm thanh vào MP4.');
    report('Đang hoàn tất MP4…',98);
    await output.finalize();
    const file=await stream.finish();
    if(!file.size)throw Error('MP4 cuối rỗng.');
    return file;
  }catch(e){
    if(output)await output.cancel().catch(()=>{});
    if(stream)await stream.discard().catch(()=>{});
    throw e;
  }finally{
    if(iterator)await iterator.return();
    audioInput.dispose();
  }
}
let downloadUrl=null;
$('join').onclick=async()=>{
  const button=$('join');button.disabled=true;
  $('download').classList.add('hide');
  try{
    const [a,b]=await Promise.all([request('A','collect'),request('B','collect')]);
    const intro=a.duration,main=b.duration;
    if(intro<6||intro>60||Math.abs(intro+main-TOTAL_SECONDS)>.045)throw Error('Yêu cầu A 6–60 giây và A+B đúng 600 giây. Dùng nút đồng bộ B.');
    if(Math.abs(intro*FPS-Math.round(intro*FPS))>.02)throw Error('Thời lượng A cần khớp khung hình 24 fps (ví dụ 6, 12, 18 giây).');
    report('Đọc thời lượng clip AI…',2);
    const [metaA,metaB]=await Promise.all([metadata(a.video),metadata(b.video)]);
    if(metaA.duration+1/FPS<intro)throw Error('Clip A ngắn hơn WAV A ('+format(metaA.duration)+'s < '+format(intro)+'s). Hãy chỉnh thời lượng A.');
    const bFrames=Math.floor(metaB.duration*FPS+.001);
    if(bFrames<24)throw Error('Clip B phải dài ít nhất 1 giây.');
    const [width,height]=$('resolution').value.split('x').map(Number);
    const result=await runEncode(a,b,intro,bFrames,width,height);
    report('Đang đọc frame mã hóa và âm thanh…',58);
    const mp4=await loadMediabunny(),video=await clipPackets(mp4,result.joined);
    const final=await compose(mp4,video,result.audio,result.aFrames);
    if(downloadUrl)URL.revokeObjectURL(downloadUrl);
    downloadUrl=URL.createObjectURL(final);
    const link=$('download');link.href=downloadUrl;link.classList.remove('hide');
    const preview=$('joined-preview');
    if(preview){preview.src=downloadUrl;preview.hidden=false;preview.load();}
    report('Hoàn thành: '+(final.size/1024/1024).toFixed(1)+' MB · MP4 10:00 · A không lặp, B lặp.',100);
  }catch(error){console.error('Dual Scene export',error);report('Chưa xuất được: '+String(error.message||error));}
  finally{button.disabled=false;}
};
})();