#!/usr/bin/env python3
"""Export PRIVATE R2 SQLite metadata index to D1-compatible SQL import batches.
No audio is downloaded. SQL files remain private on R2 and never enter Actions artifacts.
D1 deploy/import is a separate explicit, authenticated operation.
"""
import datetime,hashlib,json,os,sqlite3,tempfile
from pathlib import Path
import boto3
from botocore.config import Config

BUCKET="whitenoisechoir-media"
ROOT="internal/ai-metadata-index/v1/"
ACCOUNT="7483501ad8365fe26b0448b96b54fb9f"
FIELDS=("id","source_class","name","scientific_name","description","sound_family","habitat",
 "region","provider","source_page","license","duration","r2_key","has_r2_audio",
 "tags","filename","taxon","recorded_date","credit","qa_status")
def q(v):
 if v is None:return "NULL"
 if isinstance(v,(float,int)):return str(v)
 return "'"+str(v).replace("'","''")+"'"
def s3client():
 return boto3.client("s3",region_name="auto",
  endpoint_url="https://"+ACCOUNT+".r2.cloudflarestorage.com",
  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
  aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
  config=Config(signature_version="s3v4",max_pool_connections=8))
def main():
 s3=s3client()
 manifest=json.loads(s3.get_object(Bucket=BUCKET,Key=ROOT+"current.json")["Body"].read())
 with tempfile.TemporaryDirectory() as td:
  source=Path(td)/"source.sqlite"
  s3.download_file(BUCKET,manifest["index_r2_key"],str(source))
  if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest["index_sha256"]:
   raise RuntimeError("Index checksum mismatch")
  db=sqlite3.connect("file:"+str(source)+"?mode=ro",uri=True)
  cols=[r[1] for r in db.execute("PRAGMA table_info(assets)")]
  if cols!=list(FIELDS):raise RuntimeError("Unexpected source index schema")
  total=db.execute("SELECT count(*) FROM assets").fetchone()[0]
  if total!=manifest["indexed_total"]:raise RuntimeError("Manifest count mismatch")
  stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
  prefix=ROOT+"d1-staging/"+stamp+"/"
  create=(
   "CREATE TABLE IF NOT EXISTS assets("+
   "id TEXT PRIMARY KEY,source_class TEXT NOT NULL,name TEXT,scientific_name TEXT,"+
   "description TEXT,sound_family TEXT,habitat TEXT,region TEXT,provider TEXT,"+
   "source_page TEXT,license TEXT,duration REAL,r2_key TEXT,has_r2_audio INTEGER,"+
   "tags TEXT,filename TEXT,taxon TEXT,recorded_date TEXT,credit TEXT,qa_status TEXT);\n"+
   "CREATE INDEX IF NOT EXISTS idx_assets_class ON assets(source_class);\n"+
   "CREATE INDEX IF NOT EXISTS idx_assets_has_audio ON assets(has_r2_audio);\n"+
   "CREATE INDEX IF NOT EXISTS idx_assets_sound ON assets(sound_family);\n"+
   "CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5("+
   "name,scientific_name,description,sound_family,habitat,region,tags,filename,taxon,"+
   "content='assets',content_rowid='rowid',tokenize='unicode61 remove_diacritics 2');\n"
  )
  objects=[]
  def upload(name,data):
   key=prefix+name
   s3.put_object(Bucket=BUCKET,Key=key,Body=data.encode("utf-8"),
    ContentType="application/sql",CacheControl="private,no-store")
   objects.append({"key":key,"bytes":len(data.encode("utf-8"))})
  upload("0000-schema.sql",create)
  count=0;part=1;buf=[];bytes_used=0
  for row in db.execute("SELECT "+",".join(FIELDS)+" FROM assets ORDER BY id"):
   stmt="INSERT OR IGNORE INTO assets VALUES("+",".join(map(q,row))+");\n"
   n=len(stmt.encode("utf-8"))
   if n>95000:raise RuntimeError("Row too large for D1 safe batch")
   if buf and (len(buf)>=40 or bytes_used+n>95000):
    upload(f"{part:05d}-rows.sql","BEGIN TRANSACTION;\n"+"".join(buf)+"COMMIT;\n")
    part+=1;buf=[];bytes_used=0
   buf.append(stmt);bytes_used+=n;count+=1
  if buf:upload(f"{part:05d}-rows.sql","BEGIN TRANSACTION;\n"+"".join(buf)+"COMMIT;\n")
  upload(f"{part+1:05d}-fts.sql","INSERT INTO search(search) VALUES('rebuild');\n")
  if count!=total:raise RuntimeError("Export count mismatch")
  report={"schema":"wnc_d1_private_import_v1","created_at":stamp,"source_index_sha256":manifest["index_sha256"],
   "source_indexed_total":total,"private_sql_prefix":prefix,"sql_files":len(objects),
   "sql_bytes":sum(x["bytes"] for x in objects),
   "deployment_status":"NOT_DEPLOYED","note":"Import to D1 in order: schema, numbered row batches, FTS rebuild. Do not publish SQL or include in public artifacts."}
  s3.put_object(Bucket=BUCKET,Key=prefix+"manifest.json",Body=json.dumps(report).encode(),
   ContentType="application/json",CacheControl="private,no-store")
  print("AI_METADATA_D1_EXPORT_FINAL "+json.dumps(report),flush=True)
if __name__=="__main__":main()
