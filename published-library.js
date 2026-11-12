'use strict';
// Published library: controlled solely by reviewed data/published-mixes.json.
// No Studio previews, unfinished WAVs, or internal timeline projects here.
(async function(){
  const root=document.getElementById('published-grid');
  const output=document.getElementById('published-count');
  const search=document.getElementById('published-query');
  if(!root||!output||!search)return;
  const format=new Intl.NumberFormat('en');
  const safeSlug=s=>typeof s==='string'&&/^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$/.test(s);
  const validMedia=url=>typeof url==='string'&&/^https:\/\/media\.whitenoisechoir\.com\/[a-zA-Z0-9_./-]+$/.test(url);
  let entries=[];
  function createCard(item){
    const card=document.createElement('article');card.className='published-video-card';
    const a=document.createElement('a');a.href='/'+item.slug+'/';a.className='published-video-cover';
    a.setAttribute('aria-label','Watch '+item.title);
    const video=document.createElement('video');
    video.muted=true;video.loop=true;video.playsInline=true;video.preload='none';video.setAttribute('aria-hidden','true');
    if(validMedia(item.video.poster))video.poster=item.video.poster;
    a.append(video);
    const overlay=document.createElement('span');overlay.className='published-cover-label';
    overlay.textContent='WATCH & LISTEN';a.append(overlay);
    card.append(a);
    const info=document.createElement('div');info.className='published-video-info';
    const title=document.createElement('h2'),link=document.createElement('a');
    link.href=a.href;link.textContent=item.title;title.append(link);
    const summary=document.createElement('p');summary.textContent=item.description||'Natural ambient soundscape for relaxation and sleep.';
    const meta=document.createElement('div');meta.className='published-video-meta';
    meta.textContent='10-hour playback · '+(item.category||'Nature ambience');
    info.append(title,summary,meta);card.append(info);
    // The browser only fetches a potentially large MP4 on real pointer hover.
    if(matchMedia('(hover: hover)').matches){
      a.addEventListener('mouseenter',()=>{
        if(!video.src)video.src=item.video.url;
        video.play().catch(()=>{});
      });
      a.addEventListener('mouseleave',()=>{video.pause();video.currentTime=0;});
      a.addEventListener('focusout',()=>{video.pause();});
    }
    return card;
  }
  function render(){
    const query=search.value.toLowerCase().trim();
    const filtered=entries.filter(row=>[row.title,row.description,row.category,...(row.keywords||[])].join(' ').toLowerCase().includes(query));
    if(!filtered.length){
      const p=document.createElement('p');p.className='published-empty';
      p.textContent=entries.length?'No published soundscapes match your search.':'No finished soundscape videos have been approved for Public yet. Preview projects are not listed.';
      root.replaceChildren(p);
    } else root.replaceChildren(...filtered.map(createCard));
    output.textContent=entries.length?format.format(filtered.length)+' published video'+(filtered.length===1?'':'s'):'0 public releases';
  }
  search.addEventListener('input',render);
  try{
    const response=await fetch('/data/published-mixes.json',{cache:'no-store'});
    if(!response.ok)throw Error('Published feed unavailable');
    const rows=await response.json();
    if(!Array.isArray(rows))throw Error('Invalid published feed');
    entries=rows.filter(row=>row.status==='published'&&safeSlug(row.slug)&&typeof row.title==='string'
      &&validMedia(row.video?.url)&&validMedia(row.audio?.url))
      .sort((a,b)=>String(b.datePublished||'').localeCompare(String(a.datePublished||'')));
    render();
  }catch(err){
    // Keep build-time prerendered cards, if present; otherwise fail visibly.
    if(!root.querySelector('article'))output.textContent='Published catalog could not load. Please try again.';
    console.error('WhiteNoiseChoir library',err);
  }
})();