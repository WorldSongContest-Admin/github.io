#!/usr/bin/env python3
"""Recover final and nonqualifier scores from five unusual early Modern Era pages.

Verifies EVERY country/artist/song pair against pre-existing GitHub catalogue.
The published row's rank must equal the catalogue final placement.
No points are inferred for nonnumeric source cells.
"""
import json,re,sys,unicodedata,html
from pathlib import Path
from urllib.request import Request,urlopen
from difflib import SequenceMatcher
sys.path.insert(0,str(Path(__file__).resolve().parent))
from import_published_early_edition import Parser,ranked

ROOT=Path(__file__).resolve().parents[1]
BASE="https://wscgenz.wordpress.com/previous-contests/"
URLS={
 3:BASE+"wsc-genz01-genz10/wsc-gen-z-edition-3/",
 9:BASE+"wsc-genz01-genz10/wsc-gen-z-edition-9/",
 10:BASE+"wsc-genz01-genz10/wsc-gen-z-edition-10/",
 16:BASE+"wsc-genz11-genz20/wsc-genz-edition-16/",
 19:BASE+"wsc-genz11-genz20/wsc-genz-edition-19/",
}
ALIASES={
 "thephilippines":"philippines","phillippines":"philippines",
 "thephillippines":"philippines","thenetherlands":"netherlands",
 "uk":"unitedkingdom","usa":"unitedstates",
 "unitedstatesofamerica":"unitedstates","czechrepublic":"czechia",
 "czechrep":"czechia","turkey":"turkiye","trkiye":"turkiye",
 "fyrofmacedonia":"northmacedonia","fyrmacedonia":"northmacedonia",
 "nmacedonia":"northmacedonia","bosniaandherzegovina":"bosniaherzegovina",
 "bosniaherz":"bosniaherzegovina",
}
def clean(s):
 s=unicodedata.normalize("NFKD",html.unescape(str(s))).encode("ascii","ignore").decode().lower()
 return re.sub(r"[^a-z0-9]","",s)
def key(s):
 c=clean(s)
 return ALIASES.get(c,c)
def score(s):
 m=re.fullmatch(r"\s*(\d+)\s*(?:pts?)?\s*\*?\s*",str(s),re.I)
 return int(m.group(1)) if m else None
def parse_table(table):
 # Header shape 1: ['','Country','Artist','Song','','Player','Points']
 # Header shape 2: ['','Full results:',...]; rows 1-42 use player before points
 # Headerless Edition 3: ['1.','Luxembourg','Artist','Song','214pts','Player']
 hdr=[clean(v) for v in table[0]]
 if "country" in hdr:
  header={v:i for i,v in enumerate(hdr)}
  def col(*labels):
   for a in labels:
    if a in header:return header[a]
   raise ValueError("Missing column "+str(labels))
  ranks=[ranked(row[0]) or (ranked(row[1]) if len(row)>1 else None) for row in table[1:3]]
  rank_col=0 if ranked(table[1][0]) is not None else 1
  country_col=col("country");artist_col=col("artist")
  song_col=col("song","songtitle","title");player_col=col("player")
  score_col=col("points","voted","results","final")
  body=table[1:]
 else:
  country_col,artist_col,song_col=1,2,3
  body=table if ranked(table[0][0]) is not None else table[1:]
  sample=body[0]
  if score(sample[4]) is not None and score(sample[5]) is None:
   score_col,player_col=4,5
  elif score(sample[5]) is not None and score(sample[4]) is None:
   score_col,player_col=5,4
  else:raise ValueError("Ambiguous points and player column placement")
  rank_col=0
 result={}
 for row in body:
  required=max(rank_col,country_col,artist_col,song_col,player_col,score_col)
  if len(row)<=required:continue
  place=ranked(row[rank_col])
  if place is None:continue
  c=row[country_col];k=key(c)
  if not k or k in result:raise ValueError("Duplicate or unknown country: "+c)
  result[k]={
   "country":c,"artist":row[artist_col],"song":row[song_col],
   "player":row[player_col],"rank":place,"points":score(row[score_col]),
   "raw_points":row[score_col],
  }
 return result

def run(n,url):
 path=ROOT/f"archive/data/modern/editions/{n:03d}.json"
 data=json.loads(path.read_text(encoding="utf-8"))
 entries=data["entries"]
 master={key(e["country"]):e for e in entries}
 if len(master)!=len(entries):raise ValueError("Duplicate master country")
 with urlopen(Request(url,headers={"User-Agent":"WSC-Published-Score-Audit/1.0"}),timeout=25) as res:
  text=res.read().decode("utf-8","replace")
 parser=Parser();parser.feed(text)
 if len(parser.tables)!=1:raise ValueError(f"Expected one table, found {len(parser.tables)}")
 published=parse_table(parser.tables[0])
 if set(published)!=set(master):
  raise ValueError(f"Unmatched countries missing={sorted(set(master)-set(published))} extra={sorted(set(published)-set(master))}")
 unresolved=[]
 for k,e in master.items():
  p=published[k]
  ratios=(SequenceMatcher(None,clean(e["artist_credit"]),clean(p["artist"])).ratio(),
          SequenceMatcher(None,clean(e["song_title"]),clean(p["song"])).ratio())
  if min(ratios)<0.58:raise ValueError(f"Artist/song mismatch {e['country']} {ratios}")
  if e["result_status"]=="finalist":
   if p["rank"]!=e["rank"]:raise ValueError(f"Final rank mismatch {e['country']} published={p['rank']} official={e['rank']}")
   if p["points"] is not None:
    if e.get("points") is not None and p["points"]!=e["points"]:
     raise ValueError("Existing score mismatch "+e["country"])
    e["points"]=p["points"]
    e["verification_status"]="published_final_crosschecked"
   else:unresolved.append(e["country"])
  else:
   e["non_qualifier_points"]=p["points"]
   if p["points"] is None:unresolved.append(e["country"])
  e["published_result_order"]=p["rank"]
  e["published_points_source_url"]=url
 if len(unresolved)>4:raise ValueError("Too many nonnumeric scores: "+str(unresolved))
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("VERIFIED",n,"entries",len(entries),"numeric_scores",len(entries)-len(unresolved),"unknown",unresolved)

if __name__=="__main__":
 for number,url in URLS.items():
  try:run(number,url)
  except Exception as exc:print("REVIEW",number,type(exc).__name__,str(exc)[:700])
