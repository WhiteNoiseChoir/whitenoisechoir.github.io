#!/usr/bin/env python3
"""Build PRIVATE, search-ready SQLite FTS5 index from existing R2 metadata only.
Never downloads source audio; never publishes metadata on GitHub/Pages.
"""
import argparse, collections, datetime, hashlib, json, os, re, sqlite3, tempfile, unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET="whitenoisechoir-media"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
INDEX_ROOT="internal/ai-metadata-index/v1/"
SOURCES={
 "nature":"asset-library/sources/nature-diversity/records/",
 "music":"internal/music-candidates/v1/",
}
REGIONS={"europe","north-america","south-america","africa","oceania","southeast-asia","east-asia","asia","antarctica","middle-east","central-america"}
KIND={
 "Aves":"birds","Strigiformes":"owls","Cuculidae":"cuckoos","Amphibia":"amphibians",
 "Anura":"frogs","Orthoptera":"crickets","Cicadidae":"cicadas","Insecta":"insects",
 "Mammalia":"mammals","Reptilia":"reptiles","Actinopterygii":"fish",
}
VI_EXPAND={
 "rừng":"forest rainforest jungle woodland","mưa":"rain rainfall drizzle","suối":"stream creek brook river",
 "thác":"waterfall cascade","sông":"river stream","biển":"ocean sea coastal surf waves","sóng":"waves ocean surf",
 "gió":"wind breeze rustle","tuyết":"snow winter ice","chim":"bird birds birdsong Aves",
 "ếch":"frog frogs Anura Amphibia","dế":"cricket crickets Orthoptera","ve":"cicada cicadas Cicadidae",
 "cú":"owl owls Strigiformes","sói":"wolf wolves howl","rừng nhiệt đới":"rainforest tropical forest jungle",
 "đêm":"night nocturnal","sáng":"morning dawn","lò sưởi":"fireplace fire crackling",
 "ngủ":"sleep calm relaxation","nước":"water stream","piano":"piano",
}
def s3client():
 return boto3.client("s3",region_name="auto",endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",
  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
  config=Config(signature_version="s3v4",max_pool_connections=20,
   retries={"max_attempts":5,"mode":"standard"},
   request_checksum_calculation="when_required",response_checksum_validation="when_required"))
def list_keys(s3,prefix):
 return sorted(x["Key"] for p in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET,Prefix=prefix)
               for x in p.get("Contents",[]) if x["Key"].endswith(".json"))
def load(s3,key):
 resp=s3.get_object(Bucket=BUCKET,Key=key)
 try: raw=resp["Body"].read(65537)
 finally: resp["Body"].close()
 if len(raw)>65536:raise ValueError("Oversized metadata JSON")
 return json.loads(raw)
def text(v):
 if isinstance(v,str):return v[:6000]
 if isinstance(v,list):return " ".join(map(str,v[:50]))[:5000]
 if isinstance(v,dict):return " ".join(str(x) for x in v.values())[:5000]
 return ""
def clean_query(q):
 q=unicodedata.normalize("NFKC",q.lower())
 terms=re.findall(r"[\w-]+",q,re.UNICODE)
 expanded=list(terms)
 for phrase,more in VI_EXPAND.items():
  if phrase in q:expanded.extend(more.split())
 out=[];seen=set()
 for t in expanded:
  if t not in seen and len(t)>1:
   seen.add(t);out.append(t)
 return out[:32]
def record(kind,src):
 if kind=="nature":
  aid=str(src.get("audio_sha256") or "")
  if not re.fullmatch(r"[0-9a-f]{64}",aid):return None
  rid="nature:"+aid
  name=text(src.get("title") or src.get("original_filename") or src.get("scientific_name") or "Untitled")
  hint=text(src.get("group_hint"))
  region=hint if hint.lower() in REGIONS else ""
  acoustic=KIND.get(hint,hint if not region else text(src.get("iconic_taxon")))
  tags=text(src.get("source_tags") or src.get("classification_labels"))
  habitat=text(src.get("habitat") or src.get("discovery_hint"))
  asset=text(src.get("audio_storage_key"))
  if asset and not asset.startswith("asset-library/"):asset=""
  return (rid,"nature",name,text(src.get("scientific_name")),text(src.get("description")),acoustic,
     habitat,region,text(src.get("source_provider")),text(src.get("source_page")),
     text(src.get("license")),float(src.get("duration_seconds") or 0),
     asset,1 if asset else 0,tags,text(src.get("original_filename")),
     text(src.get("iconic_taxon")),text(src.get("recorded_date")),text(src.get("credit") or src.get("attribution")),
     text(src.get("classification_status") or "pending"))
 cid=str(src.get("candidate_id") or "")
 if not re.fullmatch(r"music-candidate-[a-f0-9]{64}",cid):return None
 cls=src.get("classification") or {}
 return (cid,"music",text(src.get("title") or src.get("file_name")), "",
   text(src.get("source_description") or src.get("description")),
   text(cls.get("instrument_hints")),text(cls.get("ambient_context") or ""), "",
   text(src.get("provider")),text(src.get("source_page")),
   text(src.get("license")),0.0,"",0,
   text(cls.get("instrument_hints"))+" "+text(cls.get("musical_style_hints")),
   text(src.get("file_name")), "", "",text(src.get("attribution")), "candidate_only")
def create_tables(db):
 db.execute("""CREATE TABLE assets(
 id TEXT PRIMARY KEY, source_class TEXT NOT NULL, name TEXT, scientific_name TEXT,
 description TEXT, sound_family TEXT, habitat TEXT, region TEXT, provider TEXT,
 source_page TEXT, license TEXT, duration REAL, r2_key TEXT, has_r2_audio INTEGER,
 tags TEXT, filename TEXT, taxon TEXT, recorded_date TEXT, credit TEXT, qa_status TEXT
 )""")
 db.execute("""CREATE VIRTUAL TABLE search USING fts5(
 name,scientific_name,description,sound_family,habitat,region,tags,filename,taxon,
 content='assets',content_rowid='rowid',tokenize='unicode61 remove_diacritics 2'
 )""")
 db.execute("CREATE INDEX idx_assets_class ON assets(source_class)")
 db.execute("CREATE INDEX idx_assets_has_audio ON assets(has_r2_audio)")
 db.execute("CREATE INDEX idx_assets_sound ON assets(sound_family)")
def finish_tables(db):
 db.execute("INSERT INTO search(search) VALUES('rebuild')")
 db.commit()
def query(db,q,limit=12,source_class=None):
 terms=clean_query(q)
 if not terms:return []
 # FTS5 OR ranking, with prefix matching. The current system is lexical + bilingual taxonomy
 # expansion, NOT an embeddings engine; do not claim semantic inference of acoustic properties.
 safe=" OR ".join('"'+t.replace('"','')+'"*' for t in terms)
 sql="""SELECT a.id,a.source_class,a.name,a.scientific_name,a.sound_family,a.habitat,
 a.region,a.provider,a.source_page,a.license,a.duration,a.has_r2_audio,a.qa_status,
 bm25(search,4,3,2,2,2,1,2,1,2) as score
 FROM search JOIN assets a ON a.rowid=search.rowid WHERE search MATCH ?"""
 args=[safe]
 if source_class:
  sql+=" AND a.source_class=?";args.append(source_class)
 sql+=" ORDER BY score ASC LIMIT ?";args.append(limit)
 return [dict(zip(("id","class","name","species","family","habitat","region","provider","source","license","duration","has_r2_audio","qa_status","score"),x)) for x in db.execute(sql,args)]
def ingest(s3,db,source,keys,workers=12):
 stats=collections.Counter(); seen=0
 with ThreadPoolExecutor(max_workers=workers) as pool:
  futs={pool.submit(load,s3,k):k for k in keys}
  for fut in as_completed(futs):
   try:
    obj=fut.result()
    row=record(source,obj)
    if row is None:
     stats["invalid"]+=1;continue
    db.execute("INSERT OR IGNORE INTO assets VALUES ("+",".join("?" for _ in row)+")",row)
    if db.execute("SELECT changes()").fetchone()[0]:stats["indexed"]+=1
    else:stats["duplicate"]+=1
   except Exception as exc:
    stats["read_or_index_error"]+=1
    if stats["read_or_index_error"]<=4:
     print("METADATA_INDEX_ERROR "+json.dumps({"error":type(exc).__name__,"source":source}),flush=True)
   seen+=1
   if seen%4000==0:print("METADATA_INDEX_PROGRESS "+json.dumps({"source":source,"seen":seen,"total":len(keys),"counts":dict(stats)}),flush=True)
  db.commit()
 return dict(stats)
def build():
 s3=s3client()
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/"ai_metadata.sqlite"
  db=sqlite3.connect(str(path))
  create_tables(db)
  results={}
  for source,prefix in SOURCES.items():
   keys=list_keys(s3,prefix)
   results[source]={"source_json_objects":len(keys),**ingest(s3,db,source,keys)}
  finish_tables(db)
  qa={}
  for q in ["rainforest birds night","forest stream water","winter snow wind","frog crickets night","piano soft ambient"]:
   result=query(db,q,8)
   qa[q]={"count":len(result),"top_matches":[{"name":x["name"][:80],"class":x["class"],"has_r2_audio":bool(x["has_r2_audio"])} for x in result[:3]]}
  total=db.execute("SELECT count(*) FROM assets").fetchone()[0]
  distinct=db.execute("SELECT count(distinct id) FROM assets").fetchone()[0]
  db.close()
  if results["nature"].get("read_or_index_error") or results["music"].get("read_or_index_error"):
   raise RuntimeError("Index incomplete due to R2 read errors; refusing to promote.")
  if total!=distinct or total<15000:raise RuntimeError("Unexpected or truncated metadata population")
  digest=hashlib.sha256(path.read_bytes()).hexdigest()
  size=path.stat().st_size
  ts=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
  obj_key=INDEX_ROOT+"versions/"+ts+"-"+digest[:16]+".sqlite"
  s3.upload_file(str(path),BUCKET,obj_key,ExtraArgs={"ContentType":"application/vnd.sqlite3","CacheControl":"private,no-store","Metadata":{"sha256":digest}})
  head=s3.head_object(Bucket=BUCKET,Key=obj_key)
  if head["ContentLength"]!=size or head.get("Metadata",{}).get("sha256")!=digest:
   raise RuntimeError("R2 index verification failed; not promoting")
  summary={"schema":"wnc_private_ai_metadata_search_index_v1","created_at":ts,"index_r2_key":obj_key,
   "index_sha256":digest,"index_bytes":size,"indexed_total":total,
   "sources":results,"search_qa":qa,"access":"private R2; API/search gateway not yet deployed",
   "retrieval":"SQLite FTS5 lexical with Vietnamese keyword expansion; not vector embeddings",
   "published_to_public_github":False}
  s3.put_object(Bucket=BUCKET,Key=INDEX_ROOT+"current.json",Body=json.dumps(summary,ensure_ascii=False).encode(),
    ContentType="application/json",CacheControl="private,no-store")
  os.makedirs("audits",exist_ok=True)
  Path("audits/ai-metadata-index-build-report.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
  print("AI_METADATA_INDEX_BUILD_FINAL "+json.dumps({k:v for k,v in summary.items() if k not in ("search_qa",)}),flush=True)
  print("AI_METADATA_INDEX_QA "+json.dumps(qa,ensure_ascii=False),flush=True)
def search_r2(q,limit):
 s3=s3client()
 manifest=json.loads(s3.get_object(Bucket=BUCKET,Key=INDEX_ROOT+"current.json")["Body"].read())
 with tempfile.TemporaryDirectory() as td:
  path=str(Path(td)/"i.sqlite")
  s3.download_file(BUCKET,manifest["index_r2_key"],path)
  if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=manifest["index_sha256"]:
   raise RuntimeError("Corrupt R2 index")
  db=sqlite3.connect("file:"+path+"?mode=ro",uri=True)
  rows=query(db,q,limit)
  # For private interactive usage write result into private R2, not public GitHub logs.
  print("AI_METADATA_SEARCH_RESULT_STATS "+json.dumps({"query_terms":len(clean_query(q)),"hits":len(rows),
   "indexed_total":manifest["indexed_total"],"private_results_withheld_from_public_logs":True}),flush=True)
  # Full query results stay local; GitHub public Actions log must not disclose R2 inventory.
  db.close()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--mode",choices=("build","search"),default="build")
 p.add_argument("--query",default="")
 p.add_argument("--limit",type=int,default=12)
 args=p.parse_args()
 if args.mode=="build":build()
 else:search_r2(args.query,min(30,max(1,args.limit)))
if __name__=="__main__":main()
