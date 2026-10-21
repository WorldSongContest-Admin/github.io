#!/usr/bin/env python3
"""Inspect PUBLIC WSC WordPress edition pages to locate final and semifinal scores.

Read-only reconnaissance. No data is written to the live website or archive.
"""
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from collections import Counter
import re

URL = "https://wscgenz.wordpress.com/previous-contests/wsc-genz01-genz10/wsc-gen-z-edition-6/"
class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.level = 0
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.tags = Counter()
    def handle_starttag(self, tag, attrs):
        self.tags[tag] += 1
        if tag == 'table':
            self.level += 1
            if self.level == 1:
                self.table = []
        if self.level == 1 and tag == 'tr':
            self.row = []
        if self.level == 1 and tag in ('th', 'td'):
            self.cell = ''
    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data
    def handle_endtag(self, tag):
        if self.level == 1 and tag in ('th','td') and self.cell is not None:
            self.row.append(' '.join(self.cell.split()))
            self.cell = None
        if self.level == 1 and tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None
        if tag == 'table':
            if self.level == 1:
                self.tables.append(self.table)
                self.table = None
            self.level -= 1

def main():
    req=Request(URL, headers={'User-Agent': 'WSC-Archive-Verification/1.0 (public edition audit)'})
    with urlopen(req, timeout=25) as response:
        raw=response.read()
        status=response.status
    html=raw.decode('utf-8', errors='replace')
    print('HTTP_STATUS',status,'HTML_BYTES',len(raw))
    p=Tables()
    p.feed(html)
    print('TABLE_COUNT',len(p.tables))
    for i,table in enumerate(p.tables[:30]):
        header=table[0] if table else []
        print('TABLE',i,'ROWS',len(table),'HEADER',repr(header[:12]))
        if table and len(table)>1:
            print('FIRST_ROW',repr(table[1][:12])); print('LAST_ROWS',repr(table[-6:]))
    from pathlib import Path
    local=Path('index.html').read_text(encoding='utf-8')
    m=re.search(r'id="edition-6".*?<tbody>(.*?)</tbody>',local,re.S)
    if m:
        static_rows=[re.sub(r'<[^>]+>', '', n) for n in re.findall(r'<td>(.*?)</td>',m.group(1),re.S)]
        reference=[static_rows[i:i+5] for i in range(0,len(static_rows),5)]
        source=p.tables[0]
        norm=lambda x:re.sub(r'[^a-z0-9]','',x.lower())
        p_countries=[norm(row[1]) for row in source if len(row)>=5 and row[0].strip().rstrip('.').isdigit()]
        h_countries=[norm(row[0]) for row in reference]
        print('WORDPRESS_RANKED_ROWS',len(p_countries),'GITHUB_ENTRIES',len(h_countries))
        print('COUNTRY_ONLY_WP',sorted(set(p_countries)-set(h_countries)))
        print('COUNTRY_ONLY_GITHUB',sorted(set(h_countries)-set(p_countries)))
        print('STATUS_5_TO_8',[(x[0],x[4]) for x in reference[4:8]])
        print('STATUS_23_TO_29',[(x[0],x[4]) for x in reference[22:29]])
    print('TABLES_WITH_POINTS',sum(any(re.search(r'point|pts|score',str(h),re.I) for h in (t[0] if t else [])) for t in p.tables))

if __name__ == '__main__':
    main()
