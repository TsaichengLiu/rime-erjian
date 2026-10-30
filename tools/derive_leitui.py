#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 IDS（表意文字描述序列）推导《二简》第二表「简化偏旁」的类推字。

原理： 谏 = ⿰讠柬，二简把偏旁 柬 简作 𫠣，故二简形 = ⿰讠𫠣 → 反查得 𫍝。

用法: python3 tools/derive_leitui.py <CHISE IDS 目录>
IDS 数据: https://github.com/chise/ids (IDS-UCS-*.txt)
"""
import os, re, sys, json, html, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDC = set('⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻⿼⿽⿾⿿')

# 部首变体归一：CHISE 对同一形体有时记作独体字、有时记作偏旁形。
# 两边都归一到同一代表字，才能对上。
VARIANT = {
    '礻': '示', '衤': '衣', '犭': '犬', '讠': '言', '钅': '金', '釒': '金',
    '饣': '食', '纟': '糸', '忄': '心', '㣺': '心', '扌': '手', '氵': '水',
    '艹': '艸', '艸': '艸', '辶': '辵', '⻌': '辵', '⻍': '辵', '辵': '辵',
    '丬': '爿', '灬': '火', '飠': '食', '糹': '糸', '訁': '言', '釦': '釦',
    '⺮': '竹', '罒': '网', '⺈': '刀', '刂': '刀', '⻖': '阜', '阝': '阜',
    '疒': '疒', '尣': '尢', '龹': '龹', '彳': '彳',
}
norm = lambda s: ''.join(VARIANT.get(c, c) for c in s)


def load_ids(d):
    ids = collections.defaultdict(list)
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith('IDS-UCS-') and fn.endswith('.txt')):
            continue
        for line in open(os.path.join(d, fn), encoding='utf-8'):
            if line.startswith(';;') or '\t' not in line:
                continue
            col = line.rstrip('\n').split('\t')
            if len(col) < 3:
                continue
            ch = col[1]
            if len(ch) != 1:
                continue
            for s in col[2:]:
                if s.startswith('@apparent='):
                    s = s[len('@apparent='):]
                elif s.startswith('@'):
                    continue
                if '&' in s:          # &CDP-xxxx; 之类实体，无法比对，跳过
                    continue
                if s and s not in ids[ch]:
                    ids[ch].append(s)
    return ids


def expand(s, ids, depth=5):
    """递归展开 IDS 到叶子构件。"""
    if depth == 0:
        return s
    out = []
    for c in s:
        if c in IDC or c not in ids:
            out.append(c); continue
        sub = ids[c][0]
        out.append(expand(sub, ids, depth - 1) if sub != c else c)
    return ''.join(out)


def build_index(ids):
    """三层索引：
       exact — 未归一的展开式，证据最强（偏旁变体也要一致）
       loose — 归一后的展开式，容忍 纟/糸、礻/示 之类记法差异
       bag   — 叶子构件多重集，不管版式。二简常把 ⿱ 改成 ⿰
               （杰 ⿱木灬 → 𣎶 ⿰木一），只能靠这层，但证据弱，需人工核。
    """
    exact, loose, bag = (collections.defaultdict(list) for _ in range(3))
    for ch, forms in ids.items():
        for f in forms:
            if f == ch:
                continue
            e = expand(f, ids)
            exact[e].append(ch)
            loose[norm(e)].append(ch)
            bag[bagkey(norm(e))].append(ch)
    rank = lambda c: (ord(c) > 0x9FFF, ord(c))
    for d in (exact, loose, bag):
        for k in d:
            d[k] = sorted(set(d[k]), key=rank)
    return exact, loose, bag


def bagkey(s):
    return ''.join(sorted(c for c in s if c not in IDC))


def wikisource_groups():
    """从草案录文抓 (偏旁, 简作, [类推字])，只取简作有码位者。"""
    raw = open(os.path.join(ROOT, 'data', 'wikisource_erjian.html'), encoding='utf-8').read()
    t = re.search(r'<div[^>]*mw-parser-output.*?(?=<div class="printfooter)', raw, re.S).group(0)
    t = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', t, flags=re.S)
    t = re.sub(r'<br[^>]*>', '\n', t); t = re.sub(r'<[^>]+>', '', t); t = html.unescape(t)
    t = re.sub(r'[  ]+', ' ', t)
    CJK = r'[㐀-鿿\U00020000-\U0003ffff]'
    sec = t.split('8．简化偏旁')[1].split('↑')[0]
    out = []
    for line in sec.split('\n'):
        p = re.split(r'[　 ]+', line.strip())
        if len(p) >= 3 and re.fullmatch(CJK + '+', p[0]) and '原字' not in line:
            if not re.fullmatch(CJK, p[1]):      # 简作无码位，整组无解
                continue
            d = [c for c in ''.join(p[2:]) if re.fullmatch(CJK, c)]
            if d:
                out.append((p[0], p[1], d))
    return out


def derive(src_parts, dst, ch, ids, index):
    """把 ch 的 IDS 里的 src 构件换成 dst，分三层强度反查码位。"""
    exact, loose, bag = index
    fallback = None
    for form in ids.get(ch, []):
        if form == ch:
            continue
        for depth in range(0, 5):
            e = expand(form, ids, depth) if depth else form
            for src in src_parts:
                if src not in e:
                    continue
                want = expand(e.replace(src, dst), ids)
                for cand in exact.get(want, []):
                    if cand != ch:
                        return cand, 'exact'
                for cand in loose.get(norm(want), []):
                    if cand != ch:
                        return cand, 'loose'
                if fallback is None:
                    for cand in bag.get(bagkey(norm(want)), []):
                        if cand != ch:
                            fallback = cand; break
    return (fallback, 'bag') if fallback else (None, None)


def main():
    d = sys.argv[1]
    ids = load_ids(d)
    print(f'IDS 条目 {len(ids)} 字')
    index = build_index(ids)
    print(f'反查索引 exact={len(index[0])} loose={len(index[1])} bag={len(index[2])}\n')

    P = json.load(open(os.path.join(ROOT, 'data', 'erjian_tables.json'), encoding='utf-8'))
    known = dict(P['erjian2'])

    groups = wikisource_groups()
    hit = miss = 0
    verified = wrong = 0
    tiers = {}
    cands = []
    unresolved = collections.defaultdict(list)
    new = {}
    print(f'{"偏旁":<4} {"简作":<4} {"原字":<4} {"推导":<4}  状态')
    for src, dst, derived in groups:
        for ch in derived:
            cand, tier = derive(list(src), dst, ch, ids, index)
            if ch in known:                       # 留出验证：表里已有，看推导对不对
                if cand == known[ch]:
                    verified += 1
                    tiers[tier] = tiers.get(tier, 0) + 1
                elif cand:
                    wrong += 1
                    print(f'{src:<4} {dst:<4} {ch:<4} {cand:<4}  ✗ 表作 {known[ch]} (层 {tier})')
                else:
                    print(f'{src:<4} {dst:<4} {ch:<4} {"-":<4}  ? 表作 {known[ch]}，推导不出')
            elif cand and tier != 'bag':
                hit += 1; new[ch] = cand
                print(f'{src:<4} {dst:<4} {ch:<4} {cand:<4}  ＋采纳  [{tier}]')
            elif cand:
                # bag 层只比对构件多重集、不管版式，实测全是误配
                # （慨→㤅 实为 ⿱旡心「愛」的古字），故仅列出供人工判断，不采纳。
                cands.append((src, dst, ch, cand))
                miss += 1
            else:
                miss += 1
                unresolved[f'{src}→{dst}'].append(ch)
    print(f'\n留出验证: 命中 {verified}（{tiers}），推错 {wrong}')
    print(f'采纳: {hit}   推不出: {miss}')
    if cands:
        print(f'\nbag 层候选（构件相同但版式不符，未采纳，供人工核）:')
        for a, b, c, d in cands:
            print(f'  {c} ({a}→{b}) → {d}?')
    print(f'\n各组仍无解:')
    for k, v in sorted(unresolved.items(), key=lambda kv: -len(kv[1])):
        print(f'  {k:<8} {len(v):>3}  {"".join(v)}')
    json.dump(new, open(os.path.join(ROOT, 'data', 'derived_leitui.json'), 'w',
                        encoding='utf-8'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
