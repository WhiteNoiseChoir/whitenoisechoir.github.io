#!/usr/bin/env python3
"""Read-only QA for four private-owner-requested CC0 WNC forest-night R2 assets.
Checks current Studio catalog, public Range bytes and same-origin CORS.
Does not modify production files, upload assets or release any recording.
"""
from __future__ import annotations
import json, pathlib, urllib.request, urllib.error

PUBLIC="https://media.whitenoisechoir.com"
ORIGIN="https://whitenoisechoir.com"
ASSETS={
"campfire":"66c3f391149bdbe5c63b45d4e0bbf50949bdb18344c55e63841129ddb1f4efdc",
"katydid":"950b9ba6337e2d5194e6340ca5f50d7e119c716cd06541999f49179464681022",
"owl":"046abe30b9cc4dae507d133a60d57f074d029be79e9c99741a96aeb8d17d843d",
"frogs":"45fb2c8b270f4a26b2e87401715139c9d8cec187a10e7c0ad7409c3fffdf946c",
}
REPORT=pathlib.Path("audits/night-forest-studio-transport-qa-20261119.json")
def main():
    REPORT.parent.mkdir(exist_ok=True,parents=True)
    out={"schema":"wnc.night-forest.transport-qa.v1","status":"pending",
         "scope":"read-only - R2 HTTP Range + Studio catalog refs + browser-origin CORS",
         "checks":[],"errors":[]}
    try:
        body=pathlib.Path("studio-catalog.js").read_text(encoding="utf8").strip()
        start=body.index("[")
        end=body.rindex("]")
        catalog=json.loads(body[start:end+1])
        for name,sha in ASSETS.items():
            item={"source":name,"assetRef":"r2-"+sha}
            try:
                matched=[x for x in catalog if x.get("sha256")==sha]
                if len(matched)!=1:raise ValueError("CATALOG_MISSING_OR_DUPLICATED")
                if matched[0].get("publicationApproved") is True:raise ValueError("UNEXPECTED_PUBLICATION_APPROVAL")
                item["catalog_registered"]=True
                url=PUBLIC+"/asset-library/raw/sha256/"+sha[:2]+"/"+sha+".mp3"
                request=urllib.request.Request(url,headers={
                  "Origin":ORIGIN,"Range":"bytes=0-1023",
                  "User-Agent":"WhiteNoiseChoir QA/1.0"})
                with urllib.request.urlopen(request,timeout=30) as resp:
                    status=resp.status
                    cors=resp.headers.get("Access-Control-Allow-Origin","")
                    ctype=resp.headers.get("Content-Type","")
                    content_range=resp.headers.get("Content-Range","")
                    sample=resp.read(1025)
                item.update({"http_status":status,"cors":cors,"content_type":ctype,
                             "content_range":content_range,"read_bytes":len(sample)})
                if status!=206:raise ValueError("HTTP_RANGE_NOT_206")
                if len(sample)!=1024:raise ValueError("RANGE_RESPONSE_LENGTH_INVALID")
                if not content_range.lower().startswith("bytes 0-1023/"):
                    raise ValueError("CONTENT_RANGE_NOT_PRESENT")
                if cors not in ("*",ORIGIN):
                    raise ValueError("SITE_BROWSER_ORIGIN_NOT_ALLOWED")
                if not (ctype.startswith("audio/") or ctype=="application/octet-stream"):
                    raise ValueError("NOT_AUDIO_CONTENT_TYPE")
                if not (sample.startswith(b"ID3") or (sample[0]==255 and sample[1] & 0xE0==0xE0)):
                    raise ValueError("MP3_HEADER_NOT_IDENTIFIED")
                item["result"]="PASS"
                print("FOREST_NIGHT_TRANSPORT_PASS "+json.dumps(item),flush=True)
            except Exception as ex:
                item["result"]="FAIL"
                item["error"]=str(ex)[:450]
                out["errors"].append(item)
                print("FOREST_NIGHT_TRANSPORT_FAIL "+json.dumps(item),flush=True)
            out["checks"].append(item)
    except Exception as ex:
        out["errors"].append({"global":str(ex)[:450]})
    out["status"]="PASS" if not out["errors"] else "FAIL"
    REPORT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("FOREST_NIGHT_TRANSPORT_SUMMARY "+json.dumps({"status":out["status"],"checked":len(out["checks"]),"passed":len([x for x in out["checks"] if x["result"]=="PASS"]),"errors":len(out["errors"])}),flush=True)
    if out["errors"]:raise SystemExit(2)
if __name__=="__main__":main()
