#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 data/erjian_tables.json 的第一表與維基文庫《第二次漢字簡化方案（草案）》錄文逐條比對。

用法:
    python3 tools/validate_ws.py [錄文.html]
不給檔案則自維基文庫下載。
"""
import os, urllib.request
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_URL = ('https://zh.wikisource.org/zh-hans/'
        '%E7%AC%AC%E4%BA%8C%E6%AC%A1%E6%B1%89%E5%AD%97%E7%AE%80%E5%8C%96%E6%96%B9%E6%A1%88'
        '%EF%BC%88%E8%8D%89%E6%A1%88%EF%BC%89')
_CACHE = os.path.join(_ROOT, 'data', 'wikisource_erjian.html')

import re, html, json, sys

import sys as _s
if len(_s.argv) > 1:
    _src = _s.argv[1]
else:
    _src = _CACHE
    if not os.path.exists(_src):
        print('下載維基文庫錄文…')
        urllib.request.urlretrieve(_URL, _src)
raw = open(_src, encoding='utf-8').read()
t=re.search(r'<div[^>]*mw-parser-output.*?(?=<div class="printfooter)',raw,re.S).group(0)
t=re.sub(r'<(script|style)[^>]*>.*?</\1>','',t,flags=re.S)
t=re.sub(r'<br[^>]*>','\n',t); t=re.sub(r'<[^>]+>','',t); t=html.unescape(t)
t=re.sub(r'[  ]+',' ',t)
sec=t.split('第一表[编辑]')[1].split('第二表[编辑]')[0]
p1=sec.split('（2）可做简化偏旁用的简化字')
ws={}
# part 1: 原字(可多个)　简作
for line in p1[0].split('\n'):
    line=line.strip()
    m=re.fullmatch(r'([㐀-鿿\U00020000-\U0003ffff]+)[　 ]+([㐀-鿿\U00020000-\U0003ffff�]+)(\[註 \d+\])?',line)
    if m and '原字' not in line:
        src,dst=m.group(1),m.group(2)
        if len(dst)==1 or len(src)==len(dst):   # 多字→单字 或 等长词组
            if len(dst)==1:
                for c in src: ws[c]=dst
            else: ws[src]=dst
# part 2: 原字　简作　类推…
for line in p1[1].split('\n'):
    line=line.strip()
    parts=re.split(r'[　 ]+',line)
    if len(parts)>=2 and re.fullmatch(r'[㐀-鿿\U00020000-\U0003ffff]+',parts[0]) and '原字' not in line:
        for c in parts[0]: ws[c]=parts[1]
        if len(parts)>=3:
            for item in re.findall(r'([㐀-鿿\U00020000-\U0003ffff])—([㐀-鿿\U00020000-\U0003ffff�]*)',parts[2]):
                if item[1]: ws[item[0]]=item[1]
e1=dict(json.load(open(os.path.join(_ROOT,'data','erjian_tables.json'),encoding='utf-8'))['erjian1'])
ws={k:v for k,v in ws.items() if '�' not in v}
print(f"维基文库第一表解析: {len(ws)} 条   honoka erjian1: {len(e1)} 条")
only_ws=[k for k in ws if k not in e1]; only_h=[k for k in e1 if k not in ws]
diff=[(k,ws[k],e1[k]) for k in ws if k in e1 and ws[k]!=e1[k]]
print(f"\n仅维基文库有 ({len(only_ws)}): "+' '.join(f'{k}→{ws[k]}' for k in only_ws))
print(f"\n仅 honoka 有 ({len(only_h)}): "+' '.join(f'{k}→{e1[k]}' for k in only_h))
print(f"\n值不一致 ({len(diff)}): "+'  '.join(f'{k}: ws={a} h={b}' for k,a,b in diff))
