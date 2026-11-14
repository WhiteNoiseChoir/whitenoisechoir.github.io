#!/usr/bin/env python3
"""WS4 offline benchmark. Input: JSON mapping case ID to list of actual search results.
Never infer audio quality from titles. Exit nonzero if evidence is absent/invalid.
"""
import argparse, json, pathlib, sys

def pick(x,*names):
    for n in names:
        if x.get(n) not in (None,""): return x[n]
    return None

def evaluate(cases,results):
    metrics=[]; failures=[]
    for c in cases:
        hits=results.get(c["id"],[])
        if not isinstance(hits,list):
            failures.append({"case":c["id"],"reason":"invalid_results_type"}); continue
        hits=hits[:5]
        if not hits:
            failures.append({"case":c["id"],"reason":"no_search_results"})
        matches=[]; audio=[]; rights=[]; duplicate=[]; seen=set(); unknown_audio=0
        for h in hits:
            family=str(pick(h,"sound_family","family") or "").lower()
            role=str(pick(h,"composition_role","role") or "").upper()
            habitat=str(pick(h,"habitat") or "").lower()
            # Metadata-only relevance proxy; not a human judgement.
            good=(c["expected_family"] in family and c["expected_role"]==role)
            matches.append(good)
            r2=pick(h,"r2_key","audio_r2_key")
            status=str(pick(h,"audio_status","r2_status") or "").lower()
            verified=bool(r2) and status in ("verified","ready","qa_pass")
            audio.append(verified)
            unknown_audio+=int(bool(r2) and not verified)
            lic=str(pick(h,"license","license_spdx") or "").lower()
            rights.append(bool(lic) and lic not in ("unknown","none","unverified"))
            ident=pick(h,"sha256","source_id","canonical_url","id")
            if ident is not None:
                duplicate.append(ident in seen);seen.add(ident)
            if habitat and c["expected_habitat"] not in habitat:
                failures.append({"case":c["id"],"reason":"habitat_mismatch","id":str(ident)})
        metrics.append({"id":c["id"],"top5_relevant_proxy":sum(matches),"retrieved":len(hits),
          "has_verified_r2_audio":any(audio),"known_license_count":sum(rights),
          "duplicate_count":sum(duplicate),"unverified_r2_count":unknown_audio})
    n=len(cases); total=sum(m["retrieved"] for m in metrics)
    return {"schema":"wnc_ws4_results_v1","cases_total":n,"cases_evaluated":len(metrics),
      "top5_relevance_proxy":round(sum(m["top5_relevant_proxy"] for m in metrics)/total,4) if total else None,
      "prompts_with_verified_r2_audio_pct":round(100*sum(m["has_verified_r2_audio"] for m in metrics)/n,2) if n else None,
      "known_license_pct":round(100*sum(m["known_license_count"] for m in metrics)/total,2) if total else None,
      "duplicate_hits":sum(m["duplicate_count"] for m in metrics),"failures":failures,
      "per_case":metrics,"notes":["Proxy relevance is taxonomy match, not graded human relevance@5.",
      "Known license does not imply commercial use clearance.",
      "R2 verified flag depends on upstream audit; no decode or acoustic QA performed."]}
def main():
    p=argparse.ArgumentParser();p.add_argument("--cases",default="qa/ws4/benchmark_30.json")
    p.add_argument("--results",required=True,help="Private JSON object case_id -> top-N actual search result objects")
    p.add_argument("--output",required=True);a=p.parse_args()
    cases=json.loads(pathlib.Path(a.cases).read_text())["cases"]
    assert len(cases)>=30 and len({c["id"] for c in cases})==len(cases)
    results=json.loads(pathlib.Path(a.results).read_text())
    report=evaluate(cases,results)
    pathlib.Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    pathlib.Path(a.output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("per_case","failures")}))
    return 0 if report["cases_evaluated"]==len(cases) and all(results.get(c["id"]) for c in cases) else 2
if __name__=="__main__":sys.exit(main())
