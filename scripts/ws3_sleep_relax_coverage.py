#!/usr/bin/env python3
"""WS3: private, read-only coverage baseline for sleep/relaxation sound identities.
Does NOT download audio, infer acoustic qualities, or publish source inventories.
"""
import collections,datetime,hashlib,json,os,sqlite3,tempfile
from pathlib import Path
import boto3
from botocore.config import Config

BUCKET="whitenoisechoir-media"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
INDEX="internal/ai-metadata-index/v1/current.json"
ROOT="internal/ws3-sleep-relax-discovery/v1/"
# Terms are FTS5 phrases or tokens; candidate counts are lexical, NOT verified recordings.
TYPES={
 "continuous_beds":{"rain":["rain","rainfall","drizzle"],"stream":["stream","creek","brook"],"ocean_waves":["ocean","waves","surf"],"wind":["wind","breeze"],"noise":["white noise","pink noise","brown noise"]},
 "habitats":{"rainforest":["rainforest","jungle"],"woodland":["woodland","forest"],"lake":["lake","lakeside"],"wetland":["swamp","marsh","wetland"],"mountain":["mountain","alpine"],"snow":["snow","blizzard","winter"]},
 "weather_material":{"rain_on_roof":["rain roof","rain rooftop"],"rain_on_leaves":["rain leaves","rain foliage"],"rain_on_tent":["rain tent"],"rain_on_window":["rain window"],"wind_in_pines":["wind pines","pine wind"]},
 "wildlife_events":{"soft_birds":["bird","birds","birdsong"],"owls":["owl","owls"],"frogs":["frog","frogs"],"crickets":["cricket","crickets"],"cicadas":["cicada","cicadas"]},
 "cozy_interiors":{"fireplace":["fireplace","fire crackling"],"cabin":["cabin"],"fan":["fan"],"air_conditioner":["air conditioner"],"night_train":["night train","train"]},
 "gentle_music":{"soft_piano":["piano"],"ambient_pad":["ambient pad","synth pad"],"harp":["harp"],"soft_drone":["drone"],"gentle_strings":["soft strings","string ambient"]}
}
def s3client():
 return boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",
 aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
 config=Config(signature_version="s3v4",retries={"max_attempts":3,"mode":"standard"}))
def getjson(s3,key):
 r=s3.get_object(Bucket=BUCKET,Key=key)
 try:return json.loads(r["Body"].read(131072))
 finally:r["Body"].close()
def qterm(s):
 return " AND ".join('"'+w.replace('"','')+'"' for w in s.split())
def main():
 s3=s3client()
 manifest=getjson(s3,INDEX)
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/"index.sqlite"
  s3.download_file(BUCKET,manifest["index_r2_key"],str(p))
  digest=hashlib.sha256(p.read_bytes()).hexdigest()
  if digest!=manifest["index_sha256"]:raise RuntimeError("R2 index checksum mismatch")
  db=sqlite3.connect("file:"+str(p)+"?mode=ro",uri=True)
  total=db.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
  if total!=manifest["indexed_total"]:raise RuntimeError("Index manifest count mismatch")
  rows=[];stats=collections.Counter()
  for category,types in TYPES.items():
   for sound,terms in types.items():
    ids=set()
    for term in terms:
     try:
      sql="""SELECT a.id,a.has_r2_audio,a.source_class,a.license FROM search
       JOIN assets a ON a.rowid=search.rowid WHERE search MATCH ?"""
      ids.update(db.execute(sql,(qterm(term),)).fetchall())
     except sqlite3.OperationalError as exc:raise RuntimeError("FTS query invalid for "+sound) from exc
    # Group by stable ID, never count multiple synonyms as separate assets.
    byid={x[0]:x[1:] for x in ids}
    audio=sum(1 for a,cls,lic in byid.values() if a==1)
    music=sum(1 for a,cls,lic in byid.values() if cls=="music")
    known=sum(1 for a,cls,lic in byid.values() if lic and lic.lower() not in ("unknown","unspecified","none"))
    status="NO_LEXICAL_MATCH" if not byid else "CANDIDATES_UNVERIFIED"
    rows.append({"category":category,"sound_identity":sound,"lexical_candidates":len(byid),
     "r2_audio_flagged":audio,"music_candidate_only":music,"license_field_present":known,
     "status":status,"acoustic_suitability":"UNKNOWN","license_verified_for_youtube":False,
     "metadata_source":"private_r2_fts5","query_terms":terms})
    stats["types"]+=1
    if not byid:stats["zero_match_types"]+=1
    if audio==0:stats["no_r2_audio_types"]+=1
    if byid:stats["candidate_types"]+=1
  db.close()
  # A stable version means repeated runs on the same index + taxonomy do not create new data.
  taxonomy=hashlib.sha256(json.dumps(TYPES,sort_keys=True).encode()).hexdigest()
  version=hashlib.sha256((digest+taxonomy).encode()).hexdigest()[:20]
  key=ROOT+"versions/"+version+".json"
  previous=None
  try:previous=getjson(s3,ROOT+"current.json")
  except s3.exceptions.NoSuchKey:pass
  except Exception as exc:
   if getattr(exc,"response",{}).get("Error",{}).get("Code") not in ("NoSuchKey","404"):raise
  already=previous is not None and previous.get("version")==version
  report={"schema":"wnc_ws3_coverage_v1","version":version,
   "indexed_total":total,"source_index_sha256":digest,"taxonomy_sha256":taxonomy,
   "coverage":rows,"summary":dict(stats),"source_verified":False,
   "candidate_metadata_only":True,"audio_downloads":0,"new_external_sources":0,
   "dedup_external_sources":0,"provider_queries":0,
   "note":"Lexical FTS candidates are not evidence of usable sound, license, seamless looping, or sleep suitability."}
  if not already:
   body=json.dumps(report,ensure_ascii=False,sort_keys=True).encode()
   s3.put_object(Bucket=BUCKET,Key=key,Body=body,ContentType="application/json",CacheControl="private,no-store")
   if s3.head_object(Bucket=BUCKET,Key=key)["ContentLength"]!=len(body):raise RuntimeError("R2 report verification failed")
   checkpoint={"schema":"wnc_ws3_checkpoint_v1","version":version,"coverage_key":key,
    "indexed_total":total,"summary":dict(stats),"next_stage":"provider_metadata_gap_discovery",
    "created_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
   s3.put_object(Bucket=BUCKET,Key=ROOT+"current.json",Body=json.dumps(checkpoint).encode(),
    ContentType="application/json",CacheControl="private,no-store")
  print("WS3_COVERAGE_SUMMARY "+json.dumps({"version":version,"indexed_total":total,
   "category_count":len(TYPES),"summary":dict(stats),"unchanged":already,
   "new_external_sources":0,"audio_downloads":0,"private_checkpoint":True}))
if __name__=="__main__":main()
