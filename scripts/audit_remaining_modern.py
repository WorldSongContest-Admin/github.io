#!/usr/bin/env python3
"""Read-only audit of seven public Modern Era scoreboard exceptions."""
import sys
from pathlib import Path
from urllib.request import urlopen,Request
sys.path.insert(0,str(Path(__file__).resolve().parent))
from import_published_early_edition import Parser,catalogue,ranked,points
B="https://wscgenz.wordpress.com"
pages={
 3:f"{B}/previous-contests/wsc-genz01-genz10/wsc-gen-z-edition-3/",
 9:f"{B}/previous-contests/wsc-genz01-genz10/wsc-gen-z-edition-9/",
 10:f"{B}/previous-contests/wsc-genz01-genz10/wsc-gen-z-edition-10/",
 16:f"{B}/previous-contests/wsc-genz11-genz20/wsc-genz-edition-16/",
 19:f"{B}/previous-contests/wsc-genz11-genz20/wsc-genz-edition-19/",
 35:f"{B}/wsc-genz-31-40/wsc-edition-35/",
 45:f"{B}/previous-contests/wsc-genz-41-50/wsc-edition-45/",
}
for n,url in pages.items():
 try:
  with urlopen(Request(url,headers={"User-Agent":"WSC-Historical-Public-Results-Audit/1.0"}),timeout=25) as response:
   body=response.read().decode("utf-8","replace")
  p=Parser();p.feed(body)
  print("EXCEPTION_EDITION",n,"CATALOGUE_ROWS",len(catalogue(n)),"TABLES",len(p.tables))
  for i,t in enumerate(p.tables[:5]):
   print("EXCEPTION_TABLE",n,i,"ROWS",len(t),"HEADER",t[0] if t else [],"FIRST",t[1:3],"LAST",t[-2:])
 except Exception as exc:print("EXCEPTION_ERROR",n,type(exc).__name__,str(exc)[:220])
