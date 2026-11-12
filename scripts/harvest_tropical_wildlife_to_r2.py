#!/usr/bin/env python3
"""Targeted Southeast Asian rainforest wildlife intake (CC0 + one verified PD)."""
from __future__ import annotations
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json, os, time
from pathlib import Path
from urllib.parse import urlsplit
import requests

import harvest_commons_cc0_to_r2 as commons
from harvest_inaturalist_cc0_to_r2 import API, HOSTS, api_results, ingest as ingest_inat
from harvest_nature_diversity_to_r2 import Intake, emit, now, put_json, commons_media_downloader
from harvest_nature_diversity_to_r2 import probe as probe_original, file_digest

# Taxon selection is bounded to SE Asia; recordings are not mixed with American fauna.
# Each group is sampled independently to prioritize sound identity over asset count.
GROUPS = {
 "gibbons": ("Hylobatidae", 4),
 "monkeys": ("Cercopithecidae", 3),
 "hornbills": ("Bucerotidae", 4),
 "cuckoos": ("Cuculidae", 3),
 "barbets": ("Megalaimidae", 3),
 "bulbuls": ("Pycnonotidae", 3),
 "pittas": ("Pittidae", 2),
 "cicadas": ("Cicadidae", 4),
 "katydids": ("Tettigoniidae", 3),
 "crickets": ("Gryllidae", 3),
 "tree_frogs": ("Rhacophoridae", 4),
 "other_frogs": ("Microhylidae", 3),
 "geckos": ("Gekkonidae", 3),
}
BOUNDS = dict(swlat=-11, swlng=92, nelat=24, nelng=145)
# Commons source page manually verified as Public Domain (not CC-BY-SA).
TOKAY = "File:Mating call of a male Tokay gecko (Gekko gecko).ogg"

def gather_inat(report):
    found, seen_sounds = [], set()
    with requests.Session() as session:
        session.headers.update({"User-Agent":commons.USER_AGENT})
        for group, (taxon_name, limit) in GROUPS.items():
            try:
                taxa=api_results(session,{"q":taxon_name,"per_page":30},
                    endpoint="https://api.inaturalist.org/v1/taxa")
                taxon=next((t for t in taxa if t.get("name")==taxon_name),None)
                if taxon is None: raise ValueError("Taxon not resolved: "+taxon_name)
                time.sleep(.6)
                rows=api_results(session,{
                    "taxon_id":taxon["id"],"sounds":"true","sound_license":"cc0",
                    "order_by":"id","order":"desc","per_page":160,"page":1,**BOUNDS
                })
                chosen=0; species=Counter()
                for row in rows:
                    organism=row.get("taxon") or {}
                    species_id=organism.get("min_species_taxon_id") or organism.get("id")
                    if not species_id or species[species_id]>=2: continue
                    for sound in row.get("sounds") or []:
                        sid=sound.get("id");url=sound.get("file_url") or ""
                        parsed=urlsplit(url)
                        if (not sid or sid in seen_sounds or sound.get("license_code")!="cc0"
                            or sound.get("hidden") or sound.get("secret_token")
                            or parsed.scheme!="https" or parsed.hostname not in HOSTS
                            or not parsed.path.startswith("/sounds/")
                            or Path(parsed.path).suffix.lower() not in commons.EXT):
                            continue
                        seen_sounds.add(sid);species[species_id]+=1;chosen+=1
                        meta={
                            "source_provider":"iNaturalist",
                            "source_page":f"https://www.inaturalist.org/observations/{row['id']}",
                            "license_evidence_url":f"https://www.inaturalist.org/sounds/{sid}",
                            "source_sound_id":sid,"source_observation_id":row["id"],
                            "original_filename":Path(parsed.path).name,
                            "title":organism.get("preferred_common_name") or organism.get("name") or taxon_name,
                            "scientific_name":organism.get("name"),"species_taxon_id":species_id,
                            "iconic_taxon":organism.get("iconic_taxon_name"),
                            "credit":sound.get("attribution"),"group_hint":"tropical-"+group,
                            "recorded_date":row.get("observed_on"),"download_url":url,
                            "license":"CC0-1.0","origin_region":"southeast-asia",
                            "classification_status":"pending","rights_evidence":"cc0 sound-level metadata"
                        }
                        found.append((url,meta));break
                    if chosen>=limit: break
                report["discovery"][group]=chosen
                emit("TROPICAL_DISCOVERY",{"group":group,"selected":chosen})
            except Exception as exc:
                report["errors"].append({"group":group,"error":str(exc)[:300]})
    return found

def ingest_commons_pd(intake):
    response=commons.get_json({
        "titles":TOKAY,"prop":"imageinfo","iiprop":"url|mime|size|sha1|extmetadata|user"
    })
    pages=response.get("query",{}).get("pages",[])
    if len(pages)!=1 or pages[0].get("title")!=TOKAY:
        raise RuntimeError("PD file metadata not resolved exactly")
    info=pages[0]["imageinfo"][0]
    meta=info.get("extmetadata") or {}
    short=commons.val(meta,"LicenseShortName").strip().lower()
    url=info.get("url") or ""
    if short not in {"public domain","pd-self","pd","publicdomain"}:
        raise RuntimeError("Tokay file no longer declares Public Domain: "+short)
    if not url.startswith("https://upload.wikimedia.org/") or int(info.get("size") or 0)>25000000:
        raise RuntimeError("Unsafe or oversized Tokay source")
    row={"direct_file_url":url,"extension":".ogg","size":int(info["size"])}
    identity=url+"\n"+(info.get("sha1") or str(info["size"]))
    if intake.cached(identity):
        return {"state":"cached","group":"tropical-geckos","source_page":"https://commons.wikimedia.org/wiki/"+TOKAY.replace(" ","_")}
    path,size,digest,dur,audio=commons_media_downloader()(row)
    try:
        record={
            "source_provider":"Wikimedia Commons",
            "source_page":"https://commons.wikimedia.org/wiki/"+TOKAY.replace(" ","_"),
            "license_evidence_url":"https://commons.wikimedia.org/wiki/"+TOKAY.replace(" ","_"),
            "download_url":url,"original_filename":TOKAY.removeprefix("File:"),
            "title":"Tokay gecko mating call — northern Laos",
            "scientific_name":"Gekko gecko","creator":"Richard Ling",
            "license":"Public Domain","license_url":"https://creativecommons.org/publicdomain/mark/1.0/",
            "group_hint":"tropical-geckos","origin_region":"southeast-asia",
            "country":"Laos","recording_type":"ONE_SHOT","classification_status":"pending",
        }
        return intake.save(path,identity,record,audio,dur,digest) | {"source_page":record["source_page"]}
    finally:
        path.unlink(missing_ok=True)

def main():
    intake=Intake()
    report={"started_at":now(),"scene":"Southeast Asian tropical rainforest",
            "license_policy":"CC0 sound metadata or verified Commons Public Domain",
            "discovery":{},"errors":[],"assets":[]}
    # Include a verified public-domain animal call even if iNaturalist is rate-limited.
    try:
        entry=ingest_commons_pd(intake)
        report["assets"].append(entry)
        emit("TROPICAL_ASSET",entry)
    except Exception as exc:
        report["errors"].append({"group":"tokay-commons","error":str(exc)[:400]})
    selected=gather_inat(report)
    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks={executor.submit(ingest_inat,intake,url,meta):meta for url,meta in selected}
        for future in as_completed(tasks):
            try:
                entry=future.result()
                report["assets"].append(entry)
                emit("TROPICAL_ASSET",{**entry,"species":tasks[future]["scientific_name"],
                     "source_page":tasks[future]["source_page"],
                     "group":tasks[future]["group_hint"]})
            except Exception as exc:
                report["errors"].append({"source_sound_id":tasks[future]["source_sound_id"],
                    "error":str(exc)[:350]})
    counts=Counter(r["state"] for r in report["assets"])
    report.update(finished_at=now(),counts=dict(counts),
                  selected=len(selected)+1,
                  new_assets=sum(r["state"]=="new" for r in report["assets"]),
                  stored_bytes=sum(r.get("bytes",0) for r in report["assets"]),
                  qa_status="technical_only_listening_pending")
    key=("asset-library/sources/tropical-wildlife/runs/"+
         os.environ.get("GITHUB_RUN_ID","local")+"-"+
         os.environ.get("GITHUB_RUN_ATTEMPT","1")+".json")
    put_json(intake.s3,key,report)
    Path("tropical-wildlife-intake-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    emit("TROPICAL_FINAL",{"counts":report["counts"],"candidates":len(selected)+1,
        "new_assets":report["new_assets"],"errors":len(report["errors"]),
        "report_key":key,"groups":report["discovery"]})
    if not report["assets"]: raise SystemExit("No recorded source was imported or reused")

if __name__=="__main__": main()
