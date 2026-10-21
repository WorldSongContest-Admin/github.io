#!/usr/bin/env python3
"""Read-only audit for published WSC final and semifinal tables.

Matches all score rows to the existing GitHub master catalogue by country.
Only final-table scores are final points. Semifinal tables are never blended.
"""
import sys
from pathlib import Path
from urllib.request import Request,urlopen
sys.path.insert(0,str(Path(__file__).resolve().parent))
from import_published_early_edition import Parser,catalogue,key as base_key,norm,ranked,points

def key(s):
 k=base_key(s)
 return 'turkiye' if k in ('trkiye','turkiye','turkey') else k

def table_rows(table):
 if not table:return []
 header=[norm(t) for t in table[0]]
 if "country" not in header:return []
 col={v:i for i,v in enumerate(header)}
 if not any(x in col for x in ("points","voted","results")):return []
 result=[]
 for row in table[1:]:
  try:
   country=row[col["country"]]
   country_key=key(country)
   idx=next(col[x] for x in ("points","voted","results") if x in col)
   pt=points(row[idx])
   first=row[0]
   place=ranked(first)
   if pt is None or not country_key:continue
   result.append({"country":country,"key":country_key,"points":pt,"place":place})
  except (ValueError,IndexError):continue
 return result

def audit(edition,url):
 with urlopen(Request(url,headers={"User-Agent":"WSC-Public-Results-Crosscheck/1.0"}),timeout=30) as r:
  html=r.read().decode("utf-8","replace")
 parser=Parser();parser.feed(html)
 catalogue_rows=catalogue(edition)
 expected={key(row[0]):row for row in catalogue_rows}
 if len(expected)!=len(catalogue_rows):raise ValueError("Duplicate master countries")
 score_tables=[table_rows(t) for t in parser.tables]
 score_tables=[t for t in score_tables if t]
 if len(score_tables)<3:raise ValueError(f"Edition {edition}: expected final plus two semifinal tables, got {len(score_tables)}")
 finals=score_tables[0]
 final_by_country={x["key"]:x for x in finals}
 finalists={key(r[0]):r for r in catalogue_rows if r[4]=="Winner" or r[4].startswith("Final #")}
 if len(finals)!=len(final_by_country):raise ValueError("Duplicate final table countries")
 if set(final_by_country)!=set(finalists):
  raise ValueError(f"Edition {edition} final mismatch: missing={sorted(set(finalists)-set(final_by_country))}, extra={sorted(set(final_by_country)-set(finalists))}")
 for country,row in finalists.items():
  actual=final_by_country[country]["place"]
  wanted=1 if row[4]=="Winner" else int(row[4][7:])
  if actual is not None and actual!=wanted:
   raise ValueError(f"Edition {edition} published rank mismatch: {row[0]} catalogue {wanted} vs page {actual}")
 semi_by_country={}
 for i,semi in enumerate(score_tables[1:3],1):
  for row in semi:
   k=row["key"]
   if k not in expected:raise ValueError(f"Unknown semifinal country {row['country']}")
   if k in semi_by_country:raise ValueError(f"Appeared in both semifinal tables {row['country']}")
   semi_by_country[k]={"points":row["points"],"place":row["place"],"semi":i}
 missing=set(expected)-set(semi_by_country)
 print("EDITION",edition,"MASTER",len(expected),"FINAL",len(finals),
       "SEMIS",len(semi_by_country),"UNMATCHED_SEMIS",len(missing),
       "EXTRA_TABLES",len(score_tables)-3)
 print("SEMIFINAL_MISSING_COUNTRIES",sorted(expected[k][0] for k in missing)[:15])
 for k in sorted(list(final_by_country)[:3]):
  print("SAMPLE_FINAL",expected[k][0],final_by_country[k]["points"],"semi",semi_by_country.get(k))
 return not missing

if __name__=="__main__":
 for ed,url in [(20,"https://wscgenz.wordpress.com/previous-contests/wsc-genz11-genz20/wsc-genz-edition-20/"),
                (31,"https://wscgenz.wordpress.com/wsc-genz-31-40/wsc-genz-edition-31/"),
                (40,"https://wscgenz.wordpress.com/wsc-genz-31-40/wsc-edition-40/")]:
  try:audit(ed,url)
  except Exception as exc:
   print("NEEDS_REVIEW",ed,type(exc).__name__,str(exc)[:450])
