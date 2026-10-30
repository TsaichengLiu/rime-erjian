#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查本机已装字体对二简字形的覆盖情况。"""
import os, sys, glob, collections
from fontTools.ttLib import TTFont, TTCollection

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def glyphs():
    s = set()
    for n in ('erjian_b1', 'erjian_b12', 'erjian_xiu'):
        with open(os.path.join(ROOT, 'opencc', n + '.txt'), encoding='utf-8') as f:
            for line in f:
                if '\t' not in line: continue
                for v in line.rstrip('\n').split('\t')[1].split(' '):
                    s.update(v)
    return s

def cmap_of(path):
    try:
        if path.lower().endswith(('.ttc', '.otc')):
            cps = set()
            for f in TTCollection(path, lazy=True).fonts:
                cps |= set(f.getBestCmap())
            return cps
        return set(TTFont(path, lazy=True, fontNumber=0).getBestCmap())
    except Exception:
        return set()

def main():
    want = glyphs()
    need = {c for c in want if ord(c) > 0x2E80}
    dirs = [os.path.expanduser('~/Library/Fonts'), '/Library/Fonts', '/System/Library/Fonts']
    files = []
    for d in dirs:
        for ext in ('ttf','otf','ttc','otc','TTF','OTF','TTC'):
            files += glob.glob(os.path.join(d, '**', '*.'+ext), recursive=True)
    rows, union = [], set()
    SKIP = ('lastresort',)   # Apple 占位字体，每个码位都映射到方框，须排除
    for p in sorted(set(files)):
        if any(k in os.path.basename(p).lower() for k in SKIP):
            continue
        cm = cmap_of(p)
        hit = {c for c in need if ord(c) in cm}
        if hit:
            rows.append((len(hit), os.path.basename(p)))
            union |= hit
    rows.sort(reverse=True)
    print(f'二简字形共 {len(want)} 个（其中需查验 {len(need)} 个）')
    print(f'\n覆盖最好的字体：')
    for n, name in rows[:12]:
        print(f'  {n:4d}/{len(need)}  {name}')
    miss = sorted(need - union, key=ord)
    print(f'\n全系统合计覆盖 {len(union)}/{len(need)}，仍缺 {len(miss)} 个：')
    print('  ' + ''.join(miss))
    if miss:
        blk = collections.Counter()
        for c in miss:
            o = ord(c)
            blk['Ext G (U+30000+)' if o >= 0x30000 else
                'Ext H (U+31350+)' if o >= 0x31350 else
                'Ext B/C/D/E/F' if o >= 0x20000 else 'Ext A/BMP'] += 1
        print('  缺失分布:', dict(blk))

if __name__ == '__main__':
    main()
