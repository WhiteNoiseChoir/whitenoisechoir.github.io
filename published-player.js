'use strict';
// Finished release player: an approved 10-minute final MP4 / compressed audio
// can repeat up to 10 hours without generating a 10-hour downloadable file.
// Browser/background restrictions can still interrupt video; audio-only mode
// is offered for long sessions and media controls.
(function(){
  const dataElement=document.getElementById('release-data');
  if(!dataElement)return;
  let release;
  try{release=JSON.parse(dataElement.textContent);}catch{return;}
  const video=document.getElementById('release-video');
  const audio=document.getElementById('release-audio');
  const start=document.getElementById('release-toggle');
  const mode=document.getElementById('release-mode');
  const length=document.getElementById('release-hours');
  const clock=document.getElementById('release-clock');
  const message=document.getElementById('release-message');
  if(!video||!audio||!start||!mode||!length||!clock)return;
  video.loop=true;audio.loop=true;video.playsInline=true;
  const duration=Number(release.audio?.durationSeconds)||600;
  let accrued=0,startedAt=null,ended=false,switching=false;
  let active=video;
  function syncModeVisibility(){
    video.hidden=active!==video;
    audio.hidden=active!==audio;
  }
  const format=seconds=>{
    const total=Math.max(0,Math.floor(seconds));
    return [Math.floor(total/3600),Math.floor(total/60)%60,total%60].map(x=>String(x).padStart(2,'0')).join(':');
  };
  const elapsed=()=>accrued+(startedAt===null?0:(Date.now()-startedAt)/1000);
  const budget=()=>Number(length.value)*3600;
  function checkpoint(){
    if(startedAt!==null){accrued=elapsed();startedAt=null;}
  }
  function render(){
    const done=Math.min(budget(),elapsed());
    clock.textContent=format(done)+' / '+format(budget());
    start.textContent=active.paused?'Play':'Pause';
    if(done>=budget()&&!ended)stopAfterTimer();
  }
  function status(text){if(message)message.textContent=text;}
  function stopAfterTimer(){
    checkpoint();ended=true;
    video.pause();audio.pause();
    video.currentTime=0;audio.currentTime=0;
    status('The '+(Number(length.value))+'-hour listening session is complete. Press Play to start a new session.');
    render();
  }
  function trackPlay(element){
    if(switching||element!==active)return;
    if(ended){ended=false;accrued=0;}
    if(startedAt===null)startedAt=Date.now();
    status(element===video?'Video and soundscape playing.':'Audio-only listening playing.');
    render();
  }
  function trackPause(element){
    if(switching||element!==active)return;
    checkpoint();render();
  }
  for(const element of [video,audio]){
    element.addEventListener('play',()=>trackPlay(element));
    element.addEventListener('pause',()=>trackPause(element));
    element.addEventListener('error',()=>{
      if(element!==active)return;
      checkpoint();
      status('Playback could not load. Check your network or switch to audio-only mode.');
      render();
    });
    element.addEventListener('waiting',()=>{
      if(element!==active||switching)return;
      checkpoint();status('Buffering media. The listening timer is paused until playback resumes.');
      render();
    });
    element.addEventListener('stalled',()=>{
      if(element!==active||switching)return;
      checkpoint();status('Connection interrupted. Timer paused until playback resumes.');
      render();
    });
    element.addEventListener('playing',()=>{
      if(element!==active||switching||ended)return;
      if(startedAt===null)startedAt=Date.now();
      status(element===video?'Video and soundscape playing.':'Audio-only listening playing.');
      render();
    });
    element.addEventListener('timeupdate',render);
  }
  async function changeMode(next){
    if(next===active)return;
    checkpoint();
    const previous=active;
    const wasPlaying=!previous.paused;
    switching=true;
    const relative=Math.max(0,previous.currentTime||0);
    previous.pause();active=next;
    syncModeVisibility();
    if(next.readyState===0){
      await new Promise(resolve=>{
        const finish=()=>{next.removeEventListener('loadedmetadata',finish);next.removeEventListener('error',finish);resolve();};
        next.addEventListener('loadedmetadata',finish,{once:true});
        next.addEventListener('error',finish,{once:true});
        next.load();
      });
    }
    const mediaDuration=Number.isFinite(next.duration)&&next.duration>0?next.duration:duration;
    try{next.currentTime=relative%mediaDuration;}catch{}
    switching=false;
    if(wasPlaying){
      try{await next.play();}catch{status('Tap Play to continue in this mode.');}
    }
    render();
  }
  start.addEventListener('click',async()=>{
    if(ended){ended=false;accrued=0;startedAt=null;}
    if(active.paused){
      try{await active.play();}catch{status('Playback was blocked. Use the media controls or try audio-only.');}
    } else active.pause();
    render();
  });
  mode.addEventListener('change',()=>changeMode(mode.value==='audio'?audio:video).catch(err=>{
    status('Unable to switch players: '+(err.message||'unknown error'));
  }));
  length.addEventListener('change',()=>{
    if(elapsed()>=budget()){stopAfterTimer();return;}
    render();
  });
  document.addEventListener('visibilitychange',render);
  window.addEventListener('pagehide',checkpoint);
  if('mediaSession'in navigator){
    try{
      navigator.mediaSession.metadata=new MediaMetadata({
        title:release.title,artist:'WhiteNoiseChoir',album:'Published Soundscapes',
        ...(release.video.poster?{artwork:[{src:release.video.poster}]}:{})
      });
      navigator.mediaSession.setActionHandler('play',()=>active.play().catch(()=>{}));
      navigator.mediaSession.setActionHandler('pause',()=>active.pause());
    }catch{}
  }
  setInterval(render,1000);
  syncModeVisibility();
  render();
})();