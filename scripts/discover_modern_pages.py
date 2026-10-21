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
 path=urlparse(url).path.lower().rstrip("/")
 name=path.rsplit("/",1)[-1]
 if len(re.findall(r"\d+",name))!=1:return None
 m=re.search(r"(?:edition|wsc|genz)[-_]?(\d+)(?:[-_]final)?$",name)
 return int(m.group(1)) if m else None

def main():
    from html.parser import HTMLParser
    from urllib.parse import urljoin
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            if tag=="a":
                href=dict(attrs).get("href")
                if href:self.links.append(href)
    discovered={}
    roots=[
      "https://wscgenz.wordpress.com/previous-contests/",
      "https://wscgenz.wordpress.com/wp-sitemap-posts-page-1.xml",
      "https://wscgenz.wordpress.com/sitemap.xml",
    ]
    for base in roots:
        try:
            with urlopen(Request(base,headers={"User-Agent":"Mozilla/5.0 (WSC public archive preservation)"}),timeout=18) as r:
                page=r.read().decode("utf-8","replace")
            links=Links();links.feed(page)
            urls=[urljoin(base,u) for u in links.links]
            urls+=re.findall(r'<loc>(.*?)</loc>',page,re.I|re.S)
            print("SITE_ROOT",base,"BYTES",len(page),"LINKS",len(urls))
            for url in urls:
                ed=edition_from_url(url)
                if ed and ed<=47 and "the-early-years" not in url and "the-rebirth" not in url:
                    if ed not in discovered or "final" in url and "final" not in discovered[ed]:discovered[ed]=url
                elif "wsc-genz" in url or "previous-contests" in url:
                    print("POTENTIAL_CATEGORY_LINK",url[:150])
        except Exception as exc:
            print("ROOT_UNAVAILABLE",base,type(exc).__name__)
    print("EDITION_URL_COUNT",len(discovered))
    for n,url in sorted(discovered.items()):print("EDITION_URL",n,url)
    print("EDITION_URL_MISSING",*[i for i in range(1,48) if i not in discovered])

if __name__=="__main__":main()
