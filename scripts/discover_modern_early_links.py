#!/usr/bin/env python3
"""Find links for publicly published Modern Era Editions 1–10, read only."""
from html.parser import HTMLParser
from urllib.request import urlopen,Request
from urllib.parse import urljoin
BASE="https://wscgenz.wordpress.com/previous-contests/wsc-genz01-genz10/"
class Links(HTMLParser):
 def __init__(self):super().__init__();self.a=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a":
   url=dict(attrs).get("href")
   if url:self.a.append(url)
with urlopen(Request(BASE,headers={"User-Agent":"Mozilla/5.0"}),timeout=30) as r:
 html=r.read().decode("utf-8","replace")
links=Links();links.feed(html)
for u in sorted(set(urljoin(BASE,x) for x in links.a)):
 if "edition" in u.lower() or "wsc-gen" in u.lower() and u.startswith(BASE):
  print("EARLY_LINK",u)
