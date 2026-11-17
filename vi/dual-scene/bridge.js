/* Owner-only dual scene iframe bridge. Existing audio mixer remains authoritative. */
(function(){
  'use strict';
  const scene=new URLSearchParams(location.search).get('dual-scene');
  if(!['A','B'].includes(scene)||window.parent===window) return;
  const origin=location.origin;
  document.querySelector('.studio-nav a[href="/vi/dual-scene/"]')?.remove();
  const respond=(data)=>window.parent.postMessage({scope:'wnc-dual',scene,...data},origin);
  try{
    // The namespaced key is declared by studio-engine.js. Only initialize empty projects.
    if(!localStorage.getItem(projectStorageKey)){
      const seconds=scene==='A'?12:588;
      mix={title:scene==='A'?'Intro · Phân cảnh A':'Ambience · Phân cảnh B',length:seconds,master:1,tracks:[],videoPrompt:''};
      saveLocal();render();
    }
  }catch(e){console.error('Dual Scene initialization',e);}
  function status(){
    const valid=Boolean(audioExport&&audioExport.signature===audioSignature(mix));
    const file=document.getElementById('video-input')?.files?.[0]||null;
    return {duration:mix.length,title:mix.title,hasWav:valid,hasVideo:Boolean(file),videoName:file?.name||'',wavDuration:valid?audioExport.duration:null};
  }
  window.addEventListener('message',event=>{
    if(event.origin!==origin||event.source!==window.parent) return;
    const msg=event.data;
    if(!msg||msg.scope!=='wnc-dual'||!msg.requestId) return;
    try{
      if(msg.action==='status')respond({requestId:msg.requestId,ok:true,data:status()});
      else if(msg.action==='set-duration'){
        const seconds=Number(msg.seconds);
        if(!Number.isFinite(seconds)||seconds<6||seconds>600)throw Error('Thời lượng phải nằm trong 6–600 giây.');
        change(()=>{mix.length=seconds;});
        respond({requestId:msg.requestId,ok:true,data:status()});
      }else if(msg.action==='collect'){
        const info=status(), file=document.getElementById('video-input')?.files?.[0];
        if(!info.hasWav)throw Error('Mixer '+scene+': hãy nhấn Xuất WAV sau khi hoàn thiện bản phối.');
        if(!file)throw Error('Mixer '+scene+': chưa chọn clip video.');
        if(Math.abs(audioExport.duration-mix.length)>.06)throw Error('Mixer '+scene+': WAV không đúng thời lượng, cần xuất lại.');
        respond({requestId:msg.requestId,ok:true,data:{...info,wav:audioExport.blob,video:file}});
      }
    }catch(e){respond({requestId:msg.requestId,ok:false,error:String(e.message||e)});}
  });
  // Let the parent access the same origin, without exposing assets to cross-origin messages.
  respond({type:'ready',data:status()});
})();