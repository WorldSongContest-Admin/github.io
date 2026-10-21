#!/usr/bin/env python3
"""Populate unimported Modern Era WSC entries from the existing root index.html.

The root HTML catalogue is the primary identity/official-placement source.
Previously imported editions and any verified points are NEVER overwritten.
New catalogue-only entries retain unknown points as null, not zero.
"""
import json,re,unicodedata
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"archive"/"data"/"modern"
class ResultRows(HTMLParser):
 def __init__(self):
  super().__init__();self.depth=0;self.inbody=False;self.row=None;self.cell=None;self.rows=[]
 def handle_starttag(self,tag,attrs):
  if tag=="tbody":self.inbody=True
  if tag=="tr" and self.inbody:self.row=[]
  if tag=="td" and self.inbody and self.row is not None:self.cell=""
 def handle_data(self,data):
  if self.cell is not None:self.cell+=data
 def handle_endtag(self,tag):
  if tag=="td" and self.cell is not None and self.row is not None:self.row.append(" ".join(self.cell.split()));self.cell=None
  if tag=="tr" and self.row is not None:self.rows.append(self.row);self.row=None
  if tag=="tbody":self.inbody=False
def slug(s):
 s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
 return re.sub(r"[^a-z0-9]","",s)
def main():
 source=(ROOT/"index.html").read_text(encoding="utf-8")
 spans={}
 for n in range(1,48):
  match=re.search(r'<div class="history-entry edition-entry" id="edition-'+str(n)+r'">',source)
  if not match:raise ValueError(f"Missing catalogue edition {n}")
  next_start=re.search(r'<div class="history-entry edition-entry" id="edition-\\d+">',source[match.end():])
  section=source[match.end():match.end()+next_start.start()] if next_start else source[match.end():]
  table=re.search(r"<table[^>]*>.*?</table>",section,re.S)
  if not table:raise ValueError(f"Edition {n}: no entries table")
  parser=ResultRows();parser.feed(table.group())
  spans[n]=parser.rows
 manifest_path=ARCHIVE/"manifest.json"
 manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
 old={item["edition_number"] for item in manifest["editions"]}
 created=0
 for n,rows in sorted(spans.items()):
  if n in old:
   stored=json.loads((ARCHIVE/f"editions/{n:03d}.json").read_text(encoding="utf-8"))
   if len(stored["entries"])!=len(rows):
    raise ValueError(f"Existing edition {n} count changed: {len(stored['entries'])} vs {len(rows)}")
   print("PRESERVED",n,len(rows))
   continue
  entries=[];used=set()
  for row in rows:
   if len(row)!=5:raise ValueError(f"Edition {n} malformed row {row}")
   country,artist,song,player,status=row
   key=slug(country)
   if not key or key in used:raise ValueError(f"Edition {n} duplicate/blank country {country}")
   used.add(key)
   if status=="Winner":rank=1
   elif status.startswith("Final #"):rank=int(status.partition("#")[2])
   elif status=="Nonqualifier":rank=None
   else:raise ValueError(f"Edition {n} unknown placing {status}")
   entries.append({
    "entry_id":f"modern:{n}:{key}","edition_key":f"modern:{n}","era":"modern",
    "edition_number":n,"rank":rank,"country":country,"artist_credit":artist,
    "song_title":song,"player":player,"points":None,
    "result_status":"finalist" if rank is not None else "non_qualifier",
    "source_url":"https://github.com/WorldSongContest-Admin/github.io/blob/main/index.html#edition-"+str(n),
    "verification_status":"catalogue_verified_scores_pending"
   })
  rankset=sorted(x["rank"] for x in entries if x["rank"] is not None)
  if rankset!=list(range(1,len(rankset)+1)):
   raise ValueError(f"Edition {n} final ranks not consecutive")
  path=ARCHIVE/f"editions/{n:03}.json"
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps({"schema_version":1,"era":"modern","edition_key":f"modern:{n}",
   "edition_number":n,"entries":entries},ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
  manifest["editions"].append({"edition_key":f"modern:{n}","edition_number":n,
   "entries":len(entries),"path":f"editions/{n:03}.json"})
  created+=1
  print("CREATED",n,len(entries),"finalists",len(rankset))
 manifest["editions"].sort(key=lambda x:x["edition_number"])
 manifest["edition_count"]=len(manifest["editions"])
 manifest["entry_count"]=sum(x["entries"] for x in manifest["editions"])
 manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
 print("SUMMARY",created,"new editions,",manifest["edition_count"],"modern editions,",manifest["entry_count"],"modern entries; existing scores preserved")
if __name__=="__main__":main()
