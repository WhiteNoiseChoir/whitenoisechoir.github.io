// PRIVATE Music: optional authenticated Studio integration.
// This module is NOT referenced from HTML until the protected Cloudflare Worker
// and its Access policy pass browser QA. There are no credentials in this file.
export const MUSIC_GATEWAY_ORIGIN = "https://music.whitenoisechoir.com";
const ROOT = MUSIC_GATEWAY_ORIGIN + "/v1";
const SHA_RE = /^[a-f0-9]{64}$/;
const BUCKET = "wnc-music-private";
const PAGE_ORIGIN = "https://whitenoisechoir.com";

export function validateMusicEntry(item) {
  if (!item || typeof item !== "object") return null;
  const sha=item.sha256;
  if (typeof sha!=="string" || !SHA_RE.test(sha) ||
      item.assetRef!=="r2-"+sha ||
      item.r2_bucket!==BUCKET ||
      item.r2_key!==`internal/licensed-music/v1/sha256/${sha.slice(0,2)}/${sha}.mp3` ||
      item.group!=="music" ||
      item.license!=="CC BY 4.0" ||
      item.technical_status!=="MEASURED_NOT_LISTENING_APPROVED" ||
      item.playback_status!=="PRIVATE_AUTH_GATEWAY_REQUIRED" ||
      item.studio_ready!==false ||
      item.publication_approved!==false ||
      typeof item.name!=="string" || !item.name.trim() ||
      typeof item.creator!=="string" || !item.creator.trim() ||
      typeof item.attribution!=="string" || !item.attribution.trim() ||
      typeof item.source_url!=="string" ||
      !item.source_url.startsWith("https://www.scottbuckley.com.au/library/") ||
      !Number.isFinite(item.duration_seconds) || item.duration_seconds<=0 ||
      item.duration_seconds>7200) return null;
  return Object.freeze({
    sha256:sha,assetRef:item.assetRef,r2_bucket:BUCKET,r2_key:item.r2_key,
    source_url:item.source_url,creator:item.creator.trim(),attribution:item.attribution,
    duration_seconds:item.duration_seconds,
    technical_status:item.technical_status,playback_status:item.playback_status,
    studio_ready:false,publication_approved:false,
    id:item.assetRef,
    key:item.r2_key,
    url:`${ROOT}/audio/${sha}`,
    name:item.name.trim().slice(0,180),
    aliases:"piano instrumental relaxing music Scott Buckley",
    group:"music",
    source:item.source_url,
    duration:item.duration_seconds,
    license:item.license,
    credit:item.attribution.trim().slice(0,500),
    privateMusic:true,
    assetStatus:"PRIVATE_AUDITION_ONLY_NOT_STUDIO_APPROVED",
    studioReady:false,
    publicationApproved:false,
    technicalLufs:Number.isFinite(item.integrated_lufs)?item.integrated_lufs:null,
    technicalTruePeak:Number.isFinite(item.true_peak_dbtp)?item.true_peak_dbtp:null
  });
}

export function selectMusicRows(payload) {
  if (!payload || payload.schema!=="wnc_private_music_studio_bridge_v1" ||
      payload.visibility!=="PRIVATE_R2_ONLY" ||
      payload.audio_origin_exposed!==false ||
      payload.requires_authenticated_gateway!==true ||
      payload.studio_ready!==0 || payload.publication_approved!==0 ||
      !Array.isArray(payload.entries) || payload.entries.length>1000)
    throw new Error("Invalid private Music catalog");
  const seen=new Set(),result=[];
  for (const raw of payload.entries) {
    const row=validateMusicEntry(raw);
    if(!row || seen.has(row.id)) continue;
    seen.add(row.id);
    result.push(row);
  }
  return result;
}

export async function retrievePrivateMusic({
  enabled=false,
  pageOrigin="",
  fetcher=fetch,
  signal=undefined
}={}) {
  if (enabled!==true || pageOrigin!==PAGE_ORIGIN)
    return {status:"DISABLED",rows:[]};
  const res=await fetcher(ROOT+"/catalog",{
    method:"GET",mode:"cors",credentials:"include",cache:"no-store",
    redirect:"error",signal
  });
  if (!res.ok) throw new Error("Private Music gateway login or access required");
  const type=(res.headers?.get?.("content-type")||"").toLowerCase();
  if(!type.includes("application/json"))throw new Error("Unexpected Music gateway content");
  const parsed=await res.json();
  return {status:"CATALOG_FETCHED_PRIVATE",rows:selectMusicRows(parsed)};
}

export function registerMusicRows(rows,{assets,rawAssetIndex,rebuildCatalog,refreshLibraryGroups,renderLibrary,render}){
  if(!Array.isArray(rows) || rows.length>1000 || !Array.isArray(assets) ||
     !(rawAssetIndex instanceof Map)) throw new Error("Invalid Studio registration");
  let added=0;
  for (const item of rows) {
    const verified=validateMusicEntry(item);
    if(!verified || verified.url!==item.url)continue;
    if (rawAssetIndex.has(verified.id)) continue; // never overwrite existing assets
    rawAssetIndex.set(verified.id,assets.length);
    assets.push(verified);
    added++;
  }
  if (added) {
    rebuildCatalog?.();
    refreshLibraryGroups?.();
    renderLibrary?.();
    render?.();
  }
  return added;
}
