/* Same-origin, owner-only bridge between independent Audio Studio mixers and Dual Scene.
 * The existing mixer owns all audio and WAV exports. No video is uploaded.
 */
(function () {
  'use strict';
  const scene=new URLSearchParams(location.search).get('dual-scene');
  if (!['A','B'].includes(scene)||window.parent===window) return;
  const origin=location.origin, FPS=24;
  const input=document.getElementById('video-input');
  const respond=data=>window.parent.postMessage({scope:'wnc-dual',scene,...data},origin);
  document.querySelector('.studio-nav a[href="/vi/dual-scene/"]')?.remove();
  // The A mixer may have a sub-six-second clip. Normal /vi/ is untouched.
  if (scene==='A') {
    document.getElementById('minutes')?.setAttribute('min','0.0166667');
    document.getElementById('minutes')?.setAttribute('step','any');
  }
  let videoInfo=null,probeTicket=0;

  try {
    // Namespaced storage is provided by studio-engine.js; initialize only new slots.
    if (!localStorage.getItem(projectStorageKey)) {
      const seconds=scene==='A'?12:600;
      mix={title:scene==='A'?'Intro · Phân cảnh A':'Ambience · Phân cảnh B',
        length:seconds,master:1,tracks:[],videoPrompt:''};
      saveLocal();render();
    }
  } catch (error) {console.error('Dual Scene initialization',error);}

  function status() {
    const valid=Boolean(audioExport&&audioExport.signature===audioSignature(mix));
    const file=input?.files?.[0]||null;
    const detected=file&&videoInfo?.file===file ? videoInfo : null;
    return {duration:mix.length,title:mix.title,hasWav:valid,hasVideo:Boolean(file),
      videoName:file?.name||'',wavDuration:valid?audioExport.duration:null,
      videoRawDuration:detected?.rawDuration??null,
      videoAlignedDuration:detected?.alignedDuration??null,
      videoFrameCount:detected?.frames??null};
  }
  function readDuration(file) {
    return new Promise((resolve,reject)=>{
      const probe=document.createElement('video'),url=URL.createObjectURL(file);
      let complete=false;
      const finish=(error,duration)=>{
        if(complete)return;complete=true;clearTimeout(timer);
        probe.removeAttribute('src');probe.load();URL.revokeObjectURL(url);
        if(error)reject(error);else resolve(duration);
      };
      const timer=setTimeout(()=>finish(Error('Quá thời gian đọc metadata MP4.')),25000);
      probe.preload='metadata';probe.muted=true;probe.playsInline=true;
      probe.onloadedmetadata=()=>{
        const duration=probe.duration;
        if(!Number.isFinite(duration)||duration<=0)finish(Error('Clip không có thời lượng hợp lệ.'));
        else finish(null,duration);
      };
      probe.onerror=()=>finish(Error('Không đọc được clip. Hãy dùng MP4 H.264 hợp lệ.'));
      probe.src=url;
    });
  }
  async function probeClip() {
    const file=input?.files?.[0];
    const ticket=++probeTicket;
    videoInfo=null;
    if(!file){
      respond({type:'clip-cleared',data:status()});
      throw Error('Chưa chọn clip '+scene+'.');
    }
    const rawDuration=await readDuration(file);
    if(ticket!==probeTicket||input.files?.[0]!==file)throw Error('Clip đã thay đổi trong lúc đọc metadata.');
    // Preserve full MP4 duration; frames are informative, never used to trim video.
    const frames=Math.floor(rawDuration*FPS+0.00001);
    if(rawDuration<1)throw Error('Clip quá ngắn (cần ít nhất 1 giây).');
    const alignedDuration=rawDuration;
    videoInfo={file,rawDuration,frames,alignedDuration};
    const data=status();
    respond({type:'clip-duration',data});
    return data;
  }
  input?.addEventListener('change',()=>{
    probeClip().catch(error=>{
      if(input?.files?.length)respond({type:'clip-error',error:String(error.message||error)});
    });
  });

  window.addEventListener('message',async event=>{
    if(event.origin!==origin||event.source!==window.parent)return;
    const msg=event.data;
    if(!msg||msg.scope!=='wnc-dual'||!msg.requestId)return;
    try {
      if(msg.action==='status'){
        respond({requestId:msg.requestId,ok:true,data:status()});
      }else if(msg.action==='probe-clip'){
        const file=input?.files?.[0];
        const data=(file&&videoInfo?.file===file)?status():await probeClip();
        respond({requestId:msg.requestId,ok:true,data});
      }else if(msg.action==='set-duration'){
        const seconds=Number(msg.seconds);
        const min=scene==='A'?1:6,max=scene==='A'?60:10800;
        if(!Number.isFinite(seconds)||seconds<min||seconds>max)
          throw Error('Mixer '+scene+': thời lượng phải trong '+min+'–'+max+' giây.');
        if(exporting)throw Error('Mixer '+scene+' đang xuất file. Hãy thử lại sau khi xuất.');
        // Existing change() invalidates the old WAV, preserves track gain/positions,
        // updates localStorage and re-renders the timeline.
        if(Math.abs(mix.length-seconds)>0.000001)change(()=>{mix.length=seconds;});
        respond({requestId:msg.requestId,ok:true,data:status()});
      }else if(msg.action==='collect-video'){
        const file=input?.files?.[0]||null;
        if(!file)throw Error('Mixer '+scene+': chưa chọn clip video.');
        respond({requestId:msg.requestId,ok:true,data:{...status(),video:file}});
      }else if(msg.action==='collect'){
        const info=status(),file=input?.files?.[0];
        if(!info.hasWav)throw Error('Mixer '+scene+': timeline đã đổi hoặc chưa xuất WAV. Hãy Xuất WAV lại.');
        if(!file)throw Error('Mixer '+scene+': chưa chọn clip video.');
        if(Math.abs(audioExport.duration-mix.length)>0.06)
          throw Error('Mixer '+scene+': WAV không đúng thời lượng, cần xuất lại.');
        respond({requestId:msg.requestId,ok:true,data:{...info,wav:audioExport.blob,video:file}});
      }
    }catch(error){
      respond({requestId:msg.requestId,ok:false,error:String(error.message||error)});
    }
  });
  respond({type:'ready',data:status()});
})();