#!/usr/bin/env python3
"""Strict read-only-source enrichment for variable-layout published WSC scoreboards.

Every final country, rank and known score must match the existing catalogue.
Each semi-final table is parsed separately; unknown, duplicate, contradictory,
or ambiguous records cause that entire edition to be skipped.
"""
import json,re,sys
from pathlib import Path
from urllib.request import Request,urlopen
sys.path.insert(0,str(Path(__file__).resolve().parent))
from import_published_early_edition import Parser, norm, points, ranked, key as old_key

ROOT=Path(__file__).resolve().parents[1]
BASE="https://wscgenz.wordpress.com"
URLS={
24:f"{BASE}/previous-contests/wsc-genz21-genz30/wsc-genz-edition-24/",
25:f"{BASE}/previous-contests/wsc-genz21-genz30/wsc-genz-edition-25/",
29:f"{BASE}/previous-contests/wsc-genz21-genz30/wsc-genz-edition-29/",
30:f"{BASE}/previous-contests/wsc-genz21-genz30/wsc-genz-30/",
32:f"{BASE}/wsc-genz-31-40/wsc-edition-32/",
34:f"{BASE}/wsc-genz-31-40/wsc-edition-34/",
35:f"{BASE}/wsc-genz-31-40/wsc-edition-35/",
38:f"{BASE}/wsc-genz-31-40/wsc-edition-38/",
41:f"{BASE}/previous-contests/wsc-genz-41-50/wsc-edition-41/",
42:f"{BASE}/previous-contests/wsc-genz-41-50/wsc-edition-42/",
43:f"{BASE}/previous-contests/wsc-genz-41-50/wsc-edition-43/",
44:f"{BASE}/previous-contests/wsc-genz-41-50/wsc-edition-44/",
45:f"{BASE}/previous-contests/wsc-genz-41-50/wsc-edition-45/",
46:f"{BASE}/previous-contests/wsc-genz-41-50/wsc-edition-46/",
}
ALIASES={
 "trkiye":"turkiye","turkey":"turkiye","kazakshtan":"kazakhstan",
 "unitedstatesofamerica":"unitedstates","thephilippines":"philippines","phillippines":"philippines","thephillippines":"philippines",
 "thenetherlands":"netherlands","fyrofmacedonia":"northmacedonia",
 "fyrmacedonia":"northmacedonia","bosniaherz":"bosniaherzegovina",
 "bosniaandherzegovina":"bosniaherzegovina",
}
def key(name):
 k=old_key(name)
 return ALIASES.get(k,k)

def rows(table):
 if not table:return []
 header={norm(name):i for i,name in enumerate(table[0])}
 if "country" not in header:return []
 score_index=next((header[x] for x in ("points","voted","results") if x in header),None)
 if score_index is None:return []
 # Find position by column name (some tables lead with running order).
 rank_index=next((header[x] for x in ("place","position","rank") if x in header),None)
 parsed=[]
 for item in table[1:]:
  if len(item)<=max(header["country"],score_index):continue
  score=points(item[score_index])
  if score is None:continue
  country=item[header["country"]]
  pos=ranked(item[rank_index]) if rank_index is not None and len(item)>rank_index else None
  parsed.append({"country":country,"key":key(country),"points":score,"rank":pos})
 return parsed

def run(n,url):
 target=ROOT/f"archive/data/modern/editions/{n:03d}.json"
 data=json.loads(target.read_text(encoding="utf-8"))
 entries=data["entries"]
 master={key(e["country"]):e for e in entries}
 if len(master)!=len(entries):raise ValueError("Duplicate master country keys")
 req=Request(url,headers={"User-Agent":"WSC-Published-Results-Audit/1.0"})
 with urlopen(req,timeout=25) as response:
  page=response.read().decode("utf-8","replace")
 parser=Parser();parser.feed(page)
 tables=[r for t in parser.tables if (r:=rows(t))]
 if len(tables)<2:raise ValueError(f"Need final and at least one semifinal table: {len(tables)}")
 finals=tables[0]
 if len({r["key"] for r in finals})!=len(finals):raise ValueError("Duplicate final country")
 official={key(e["country"]):e for e in entries if e["result_status"]=="finalist"}
 found={r["key"]:r for r in finals}
 if set(found)-set(official) or len(set(official)-set(found))>2:
  raise ValueError(f"Final countries missing={sorted(set(official)-set(found))} extra={sorted(set(found)-set(official))}")
 unscored=sorted(set(official)-set(found))
 for k,e in official.items():
  if k not in found:continue
  result=found[k]
  if result["rank"] is not None and result["rank"]!=e["rank"]:
   raise ValueError(f"Final rank mismatch: {e['country']} existing={e['rank']} published={result['rank']}")
  if e.get("points") is not None and e["points"]!=result["points"]:
   raise ValueError(f"Existing score mismatch: {e['country']}")
 semis={}
 for group_idx,group in enumerate(tables[1:],1):
  seen=set()
  for row in group:
   k=row["key"]
   if k in seen:raise ValueError("Duplicate country within semifinal")
   seen.add(k)
   if k not in master:raise ValueError(f"Unknown semifinal country: {row['country']}")
   if k in semis:raise ValueError(f"Duplicate semifinal appearance: {row['country']}")
   semis[k]={"group":group_idx,**row}
 for k,e in master.items():
  if k in found:
   e["points"]=found[k]["points"]
   e["final_points_source_url"]=url
   e["verification_status"]="published_final_crosschecked"
  if k in semis:
   r=semis[k]
   e["semi_final_held"]=True
   e["semi_final"]=r["group"]
   e["semi_final_points"]=r["points"]
   e["semi_final_rank"]=r["rank"]
   e["semi_final_source_url"]=url
  else:
   e["semi_final_points"]=None
   e["semi_final_rank"]=None
   e["semi_final_score_note"]="No numeric semifinal score on the published results page"
 missing=[e["country"] for k,e in master.items() if k not in semis]
 target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("VERIFIED",n,"entries",len(entries),"numeric_final_scores",len(finals),"unknown_final_scores",unscored,"semi_rows",len(semis),"semi_tables",len(tables)-1,"missing_semi",missing)

if __name__=="__main__":
 for n,url in URLS.items():
  try:run(n,url)
  except Exception as exc:print("REVIEW",n,type(exc).__name__,str(exc)[:600])
