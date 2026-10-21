#!/usr/bin/env python3
"""Enrich existing Modern Era records with independently verified published scores.

Conservative: requires exact country coverage for the Grand Final and exact
official finalist ranks; leaves absent semi-final scores null. Never imports
Edition 48, invents points or replaces identities from the GitHub catalogue.
"""
import json,sys
from pathlib import Path
from urllib.request import Request,urlopen
sys.path.insert(0,str(Path(__file__).resolve().parent))
from import_published_early_edition import Parser, norm, ranked, points, key as old_key

ROOT=Path(__file__).resolve().parents[1]
URLS={n:f"https://wscgenz.wordpress.com/previous-contests/wsc-genz21-genz30/wsc-genz-edition-{n}/"
      for n in range(21,31)}

def key(s):
 k=old_key(s)
 return "turkiye" if k in ("trkiye","turkiye","turkey") else k

def parse_rows(table):
 if not table:return []
 h={norm(v):i for i,v in enumerate(table[0])}
 if "country" not in h:return []
 score_col=next((h[x] for x in ("points","voted","results") if x in h),None)
 if score_col is None:return []
 result=[]
 for row in table[1:]:
  if len(row)<=max(score_col,h["country"]):continue
  c=row[h["country"]];p=points(row[score_col]);place=ranked(row[0])
  if not c or p is None:continue
  result.append({"key":key(c),"country":c,"points":p,"rank":place})
 return result

def run(n,url):
 file=ROOT/f"archive/data/modern/editions/{n:03d}.json"
 doc=json.loads(file.read_text(encoding="utf-8"))
 entries=doc["entries"]
 known={key(x["country"]):x for x in entries}
 if len(known)!=len(entries):raise ValueError("Duplicate country in catalogue")
 with urlopen(Request(url,headers={"User-Agent":"WSC-Published-Results-Verification/1.0"}),timeout=30) as r:
  html=r.read().decode("utf-8","replace")
 parser=Parser();parser.feed(html)
 tables=[r for t in parser.tables if (r:=parse_rows(t))]
 if len(tables)!=3:raise ValueError(f"Edition {n}: expected 3 scoring tables, found {len(tables)}")
 final=tables[0];finals={x["key"]:x for x in final}
 expected={k:v for k,v in known.items() if v["result_status"]=="finalist"}
 if len(final)!=len(finals) or set(finals)!=set(expected):
  raise ValueError(f"Finalist countries differ for Edition {n}")
 for k,e in expected.items():
  row=finals[k]
  if row["rank"] is None or row["rank"]!=e["rank"]:
   raise ValueError(f"Final position differs {n} {e['country']}")
  if e.get("points") is not None and e["points"]!=row["points"]:
   raise ValueError(f"Score already present differs {n} {e['country']}")
 semi={}
 for i,group in enumerate(tables[1:],1):
  for row in group:
   k=row["key"]
   if k not in known:raise ValueError(f"Unknown semi country {row['country']}")
   if k in semi:raise ValueError(f"Duplicate semi country {row['country']}")
   semi[k]=(i,row)
 for k,e in known.items():
  if k in finals:
   e["points"]=finals[k]["points"]
   e["final_points_source_url"]=url
   e["verification_status"]="published_final_crosschecked"
  elif e["result_status"]=="non_qualifier":
   e["points"]=None
  if k in semi:
   i,row=semi[k]
   e["semi_final"]=i
   e["semi_final_points"]=row["points"]
   e["semi_final_rank"]=row["rank"]
   e["semi_final_source_url"]=url
  else:
   e["semi_final"]=None
   e["semi_final_points"]=None
   e["semi_final_rank"]=None
   e["semi_final_score_note"]="No numeric score in the published semifinal table"
 missing=sorted(e["country"] for k,e in known.items() if k not in semi)
 file.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"VERIFIED_EDITION {n} entries={len(entries)} finalists={len(final)} semifinal_scores={len(semi)} missing={missing}")

if __name__=="__main__":
 for n,url in URLS.items():
  try:run(n,url)
  except Exception as exc:print("NEEDS_REVIEW",n,type(exc).__name__,str(exc)[:500])
