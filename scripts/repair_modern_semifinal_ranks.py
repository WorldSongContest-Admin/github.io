#!/usr/bin/env python3
"""Reconcile verified semi-final ranks on already-scored modern entries.

Targets published semi-final tables with varying column order. Edition 47's
semi-final points were never imported and are added where numeric and matched.
No missing rank or score is inferred, and finals are untouched.
"""
import json,re,sys,unicodedata
from pathlib import Path
from urllib.request import Request,urlopen
sys.path.insert(0,str(Path(__file__).resolve().parent))
from import_published_early_edition import Parser,ranked

ROOT=Path(__file__).resolve().parents[1]/"archive"/"data"/"modern"/"editions"
URLS={
22:"https://wscgenz.wordpress.com/previous-contests/wsc-genz21-genz30/wsc-genz-edition-22/",
24:"https://wscgenz.wordpress.com/previous-contests/wsc-genz21-genz30/wsc-genz-edition-24/",
34:"https://wscgenz.wordpress.com/wsc-genz-31-40/wsc-edition-34/",
35:"https://wscgenz.wordpress.com/wsc-genz-31-40/wsc-edition-35/",
41:"https://wscgenz.wordpress.com/previous-contests/wsc-genz-41-50/wsc-edition-41/",
43:"https://wscgenz.wordpress.com/previous-contests/wsc-genz-41-50/wsc-edition-43/",
44:"https://wscgenz.wordpress.com/previous-contests/wsc-genz-41-50/wsc-edition-44/",
47:"https://wscgenz.wordpress.com/previous-contests/wsc-genz-41-50/wsc-edition-47/"
}
def key(s):
 s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
 k=re.sub(r"[^a-z0-9]","",s)
 return {"trkiye":"turkiye","turkey":"turkiye","thephilippines":"philippines","thenetherlands":"netherlands","usa":"unitedstates","unitedstatesofamerica":"unitedstates","czechrepublic":"czechia","kazakshtan":"kazakhstan","fyrofmacedonia":"northmacedonia","bosniaandherzegovina":"bosniaherzegovina"}.get(k,k)
def number(s):
 m=re.fullmatch(r"\s*(\d+)\s*(?:pts?)?\s*\*?\s*",str(s),re.I)
 return int(m.group(1)) if m else None
def parse(table):
 if not table:return []
 h={key(v):i for i,v in enumerate(table[0])}
 if "country" not in h:return []
 ci=h["country"]
 pi=next((h[n] for n in ("points","results","voted","status") if n in h),None)
 ri=next((h[n] for n in ("place","position","rank","result") if n in h),None)
 if ri is None and key(table[0][0]) not in ("ro","ro1","semiFinal"):
  ri=0
 if ri is None:return []
 vals=[]
 for row in table[1:]:
  if max(ci,ri)>=len(row):continue
  p=ranked(row[ri])
  if p is None:continue
  pt=number(row[pi]) if pi is not None and pi<len(row) else None
  vals.append((key(row[ci]),p,pt))
 return vals

def run(n,url):
 path=ROOT/f"{n:03}.json"
 data=json.loads(path.read_text(encoding="utf-8"))
 existing=data["entries"];master={key(x["country"]):x for x in existing}
 if len(master)!=len(existing):raise ValueError("Duplicate country in edition "+str(n))
 with urlopen(Request(url,headers={"User-Agent":"WSC-Results-Historical-Semifinal-Crosscheck/1.0"}),timeout=25) as res:
  raw=res.read().decode("utf-8","replace")
 parser=Parser();parser.feed(raw)
 semi_tables=parser.tables[1:]
 if len(semi_tables)<2:raise ValueError("Fewer than two semifinal tables")
 changes=0;score_changes=0;unknown=[]
 seen=set()
 for stage,table in enumerate(semi_tables,1):
  vals=parse(table)
  for k,rank,pts in vals:
   if k not in master:raise ValueError(f"Edition {n}: unknown country {k}")
   if k in seen:raise ValueError(f"Edition {n}: duplicate semi country {k}")
   seen.add(k)
   row=master[k]
   if row.get("semi_final_rank") is not None and row["semi_final_rank"]!=rank:
    raise ValueError(f"Edition {n}: existing semi rank differs {row['country']}")
   if row.get("semi_final_points") is not None and pts is not None and row["semi_final_points"]!=pts:
    raise ValueError(f"Edition {n}: existing semi points differ {row['country']}")
   if row.get("semi_final_rank") is None:
    row["semi_final_rank"]=rank;changes+=1
   if pts is not None and row.get("semi_final_points") is None:
    row["semi_final_points"]=pts;score_changes+=1
   row["semi_final_held"]=True
   row["semi_final_source_url"]=url
  print("STAGE",n,stage,"ranked_rows",len(vals))
 for k,v in master.items():
  if k not in seen:unknown.append(v["country"])
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("PASS_EDITION",n,"new_ranks",changes,"new_points",score_changes,"not_in_ranked_tables",unknown)

if __name__=="__main__":
 for n,url in URLS.items():
  try:run(n,url)
  except Exception as exc:print("REVIEW",n,type(exc).__name__,str(exc)[:400])
