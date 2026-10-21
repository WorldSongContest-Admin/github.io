#!/usr/bin/env python3
"""Produce a conservative, source-linked Modern Era Edition 6 import.

Reads published WordPress results and the existing WSC catalogue in index.html.
Will refuse to write output if country, artist/song, or final placements conflict.
Non-qualifier website points are kept separately, NEVER mistaken for final points.
"""
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from difflib import SequenceMatcher

PAGE="https://wscgenz.wordpress.com/previous-contests/wsc-genz01-genz10/wsc-gen-z-edition-6/"
ALIASES={"uk":"unitedkingdom","usa":"unitedstates","czechrep":"czechia","nmacedonia":"northmacedonia","bosniaherz":"bosniaherzegovina"}

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.level=0;self.tables=[];self.table=None;self.row=None;self.cell=None
    def handle_starttag(self,t,attrs):
        if t=="table":
            self.level+=1
            if self.level==1:self.table=[]
        elif self.level==1 and t=="tr":self.row=[]
        elif self.level==1 and t in ("th","td"):self.cell=""
    def handle_data(self,data):
        if self.cell is not None:self.cell+=data
    def handle_endtag(self,t):
        if t in ("th","td") and self.level==1 and self.cell is not None:
            self.row.append(" ".join(self.cell.split()));self.cell=None
        elif t=="tr" and self.level==1 and self.row is not None:
            self.table.append(self.row);self.row=None
        elif t=="table":
            if self.level==1:self.tables.append(self.table);self.table=None
            self.level-=1

def norm(s):
    return re.sub(r"[^a-z0-9]","",s.casefold())

def country_key(s):
    return ALIASES.get(norm(s),norm(s))

def read_catalogue(file):
    data=file.read_text(encoding="utf-8")
    found=re.search(r'id="edition-6".*?<tbody>(.*?)</tbody>',data,re.S)
    if not found:raise ValueError("Edition 6 not found in catalogue")
    content=found.group(1)
    rows=[]
    for raw in re.findall(r"<tr>(.*?)</tr>",content,re.S):
        cells=[html.unescape(re.sub(r"<[^>]+>","",t)).strip() for t in re.findall(r"<td>(.*?)</td>",raw,re.S)]
        if len(cells)==5:rows.append(cells)
    return rows

def fetch_public_results():
    with urlopen(Request(PAGE,headers={"User-Agent":"WSC-Archive-Public-Results-Audit/1.0"}),timeout=25) as res:
        p=Tables();p.feed(res.read().decode("utf-8","replace"))
    if len(p.tables)!=1:raise ValueError(f"Expected one WordPress table, got {len(p.tables)}")
    result={}
    for row in p.tables[0]:
        if len(row)<6 or not re.fullmatch(r"\d+\.",row[0]):continue
        rank=int(row[0][:-1]);country,artist,song,pt,player=row[1:6]
        found=re.fullmatch(r"(\d+)\s*pts?",pt.strip(),re.I)
        if not found:raise ValueError("Unrecognised points label for "+country)
        key=country_key(country)
        if key in result:raise ValueError("Duplicate public country "+country)
        result[key]={"published_rank":rank,"country":country,"artist":artist,"song":song,
                     "published_points":int(found.group(1)),"player":player}
    return result

def convert():
    catalogue=read_catalogue(Path("index.html"));scores=fetch_public_results()
    if len(scores)!=46 or len(catalogue)!=46:raise ValueError(f"Expected 46 records; got {len(scores)} public and {len(catalogue)} catalogue")
    entries=[];issues=[]
    for country,artist,song,player,status in catalogue:
        key=country_key(country);src=scores.get(key)
        if src is None:raise ValueError("No published score for "+country)
        finalist=status=="Winner" or status.startswith("Final #")
        final_rank=1 if status=="Winner" else int(status[7:]) if status.startswith("Final #") else None
        if finalist and final_rank!=src["published_rank"]:raise ValueError(f"Final rank mismatch for {country}")
        if not finalist and status!="Nonqualifier":raise ValueError("Unexpected result status "+status)
        ratios={c:SequenceMatcher(None,norm(value),norm(src[k])).ratio() for c,value,k in
                [("artist",artist,"artist"),("song",song,"song"),("player",player,"player")]}
        if min(ratios["artist"],ratios["song"])<0.60:issues.append({"country":country,"similarity":ratios,
                           "catalogue":[artist,song,player],"website":[src["artist"],src["song"],src["player"]]})
        e={"entry_id":"modern:6:"+key,"edition_key":"modern:6","era":"modern","edition_number":6,
           "rank":final_rank,"country":country,"artist_credit":artist,"song_title":song,"player":player,
           "points":src["published_points"] if finalist else None,
           "non_qualifier_points":src["published_points"] if not finalist else None,
           "published_result_order":src["published_rank"],
           "result_status":"finalist" if finalist else "non_qualifier",
           "source_url":PAGE,"verification_status":"crosschecked_website_and_catalogue"}
        if ratios["player"]<0.60:
            if country=="Ukraine" and norm(player)=="vasyl" and norm(src["player"])=="herms":
                e["player_aliases"]=["Vassyl","Vasyl","Hermès"]
                e["player_identity_note"]="Vassyl (also listed as Vasyl) and Hermès are the same player."
            else:
                e["player_source_mismatch"]={"catalogue":player,"published_page":src["player"]}
        entries.append(e)
    if len(entries)!=46 or sum(x["rank"] is not None for x in entries)!=25:raise ValueError("Expected 25 finalists")
    if issues:raise ValueError("Artist/song/player mismatches need manual review: "+json.dumps(issues,ensure_ascii=False))
    output=Path("archive/data/modern/editions/006.json")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({"schema_version":1,"era":"modern","edition_key":"modern:6",
                                  "edition_number":6,"entries":entries},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PASS_EDITION_6: 46 entries, 25 finalists, 21 nonqualifiers; final points isolated from nonqualifier points")

if __name__=="__main__":convert()
