#!/usr/bin/env python3
"""Discover already-published WSC edition page URLs. No results or votes are modified."""
import json,re
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from html import unescape

API="https://public-api.wordpress.com/rest/v1.1/sites/wscgenz.wordpress.com/pages/?number=100&page={}"
WP="https://wscgenz.wordpress.com/wp-json/wp/v2/pages?per_page=100&page={}"
def get(url):
 with urlopen(Request(url,headers={"User-Agent":"WSC-Public-Results-Indexer/1.0","Accept":"application/json"}),timeout=25) as r:return json.load(r)
def edition_from_url(url):
 path=urlparse(url).path.lower()
 found=re.search(r"(?:gen-?z[-_ ]*)?edition[-_ ]*(\d+)(?:/|$)",path)
 return int(found.group(1)) if found else None

def main():
 discovered={}
 for source in ("wordpress-v2","wordpress-public-api"):
  for page in range(1,5):
   try:
    obj=get((WP if source=="wordpress-v2" else API).format(page))
   except Exception as exc:
    print("ENDPOINT_STOP",source,page,type(exc).__name__)
    break
   items=obj.get("pages",[]) if isinstance(obj,dict) else obj
   if not items:break
   for item in items:
    url=item.get("link") or item.get("URL") or ""
    ed=edition_from_url(url)
    if ed and ed<=47:discovered[ed]=url
 print("EDITION_URL_COUNT",len(discovered))
 for n,url in sorted(discovered.items()):print("EDITION_URL",n,url)
 print("EDITION_URL_MISSING",*[i for i in range(1,48) if i not in discovered])

if __name__=="__main__":main()
