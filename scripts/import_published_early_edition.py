#!/usr/bin/env python3
"""Strictly cross-check public single-table edition scores against the WSC catalogue.
Designed for early-era editions. Never infer non-qualifier scores as final points.
"""
import html,json,re,sys
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from pathlib import Path
from difflib import SequenceMatcher

class Parser(HTMLParser):
 def __init__(self):super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None;self.depth=0
 def handle_starttag(self,t,a):
  if t=="table":
   self.depth+=1
   if self.depth==1:self.table=[]
  elif self.depth==1 and t=="tr":self.row=[]
  elif self.depth==1 and t in ("td","th"):self.cell=""
 def handle_data(self,x):
  if self.cell is not None:self.cell+=x
 def handle_endtag(self,t):
  if t in ("td","th") and self.depth==1 and self.cell is not None:
   self.row.append(" ".join(self.cell.split()));self.cell=None
  elif t=="tr" and self.depth==1 and self.row is not None:
   if self.row:self.table.append(self.row)
   self.row=None
  elif t=="table":
   if self.depth==1:self.tables.append(self.table)
   self.depth-=1

ALIASES={"uk":"unitedkingdom","usa":"unitedstates","czechrep":"czechia","czechrepublic":"czechia",
 "nmacedonia":"northmacedonia","bosniaherz":"bosniaherzegovina","thenetherlands":"netherlands","thephilippines":"philippines","phillippines":"philippines","fyrofmacedonia":"northmacedonia","trkiye":"turkiye","turkey":"turkiye","kazakshtan":"kazakhstan","unitedstatesofamerica":"unitedstates"}
def norm(s):return re.sub(r"[^a-z0-9]","",html.unescape(s).casefold())
def key(s):return ALIASES.get(norm(s),norm(s))
def ranked(s):
 m=re.fullmatch(r"\s*(\d+)(?:st|nd|rd|th)?\.?\s*",s,re.I)
 return int(m.group(1)) if m else None
def points(s):
 m=re.fullmatch(r"\s*(\d+)\s*pts?\s*\\*?\s*",s,re.I)
 return int(m.group(1)) if m else None
def catalogue(n):
 text=Path("index.html").read_text(encoding="utf-8")
 m=re.search(r'id="edition-'+str(n)+r'".*?<tbody>(.*?)</tbody>',text,re.S)
 if not m:raise ValueError("Catalogue edition not found")
 rows=[]
 for tr in re.findall(r"<tr>(.*?)</tr>",m.group(1),re.S):
  c=[html.unescape(re.sub(r"<[^>]+>","",x)).strip() for x in re.findall(r"<td>(.*?)</td>",tr,re.S)]
  if len(c)==5:rows.append(c)
 return rows
def parse(url):
 with urlopen(Request(url,headers={"User-Agent":"WSC-Published-Scores-Verification/1.0"}),timeout=25) as r:raw=r.read().decode("utf-8","replace")
 p=Parser();p.feed(raw)
 if len(p.tables)!=1:raise ValueError("Not a single-table page, requires multi-stage parser")
 table=p.tables[0]
 hdr=[norm(z) for z in table[0]]
 if "country" in hdr:
  h={z:i for i,z in enumerate(hdr)}
  def col(*names):
   for name in names:
    if name in h:return h[name]
   raise ValueError("Required header not found: "+str(names))
  rank_col=0 if any(ranked(row[0]) is not None for row in table[1:4] if row) else 1
  idx=(rank_col,col("country"),col("artist"),col("song","title","songtitle"),col("player"),col("points","voted","result","final"))
  rows=table[1:]
 else:
  idx=(0,1,2,3,5,4)
  rows=table
 out={}
 for row in rows:
  if len(row)<=max(idx):continue
  rank=ranked(row[idx[0]]);pt=points(row[idx[5]])
  if rank is None or pt is None:continue
  c,a,s,p=(row[idx[i]] for i in (1,2,3,4))
  k=key(c)
  if k in out:raise ValueError("Duplicate country "+c)
  out[k]={"rank":rank,"points":pt,"artist":a,"song":s,"player":p}
 return out

def run(n,url,write=False):
 rows=catalogue(n);published=parse(url)
 if len(rows)!=len(published):raise ValueError(f"Edition {n}: catalogue {len(rows)} vs published {len(published)}")
 out=[];flags=[]
 for c,a,s,player,result in rows:
  v=published.get(key(c))
  if v is None:raise ValueError("Unmatched country "+c)
  score_sim=SequenceMatcher(None,norm(a),norm(v["artist"])).ratio()
  song_sim=SequenceMatcher(None,norm(s),norm(v["song"])).ratio()
  if min(score_sim,song_sim)<0.57:flags.append((c,score_sim,song_sim))
  rank=1 if result=="Winner" else int(result[7:]) if result.startswith("Final #") else None
  if rank is not None and rank!=v["rank"]:raise ValueError(f"Final rank conflict {c}: {rank} vs {v['rank']}")
  if rank is None and result!="Nonqualifier":raise ValueError("Unrecognised status "+result)
  entry={"entry_id":f"modern:{n}:{key(c)}","edition_key":f"modern:{n}","era":"modern","edition_number":n,
   "rank":rank,"country":c,"artist_credit":a,"song_title":s,"player":player,
   "points":v["points"] if rank is not None else None,
   "non_qualifier_points":v["points"] if rank is None else None,
   "published_result_order":v["rank"],"result_status":"finalist" if rank is not None else "non_qualifier",
   "source_url":url,"verification_status":"published_website_and_catalogue"}
  if norm(player)!=norm(v["player"]):entry["published_player_name"]=v["player"]
  out.append(entry)
 if flags:raise ValueError(f"Artist/song mismatches require review {flags}")
 ranks=sorted(x["rank"] for x in out if x["rank"] is not None)
 if ranks!=list(range(1,len(ranks)+1)):raise ValueError("Final ranks not contiguous")
 print("VERIFIED_EDITION",n,"ENTRIES",len(out),"FINALISTS",len(ranks),"NONQUALIFIERS",len(out)-len(ranks))
 if write:
  path=Path(f"archive/data/modern/editions/{n:03}.json")
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps({"schema_version":1,"era":"modern","edition_key":f"modern:{n}","edition_number":n,"entries":out},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print("EDITION_JSON",json.dumps({"schema_version":1,"era":"modern","edition_key":f"modern:{n}","edition_number":n,"entries":out},ensure_ascii=False,separators=(",",":")))

if __name__=="__main__":
 if len(sys.argv)<3:raise SystemExit("Usage: script EDITION URL [--write]")
 run(int(sys.argv[1]),sys.argv[2],"--write" in sys.argv)
