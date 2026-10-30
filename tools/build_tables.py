#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由《第二次汉字简化方案（草案）》字表生成 Rime/OpenCC 转换词典。

输入: data/erjian_tables.json   (erjian1 / erjian2 / erjianXiu / yijian，保序键值对)
      tools/curated.json        (人工校订: 覆盖、增补、多候选)
输出: opencc/erjian_b1.{txt,json}   第一表
      opencc/erjian_b12.{txt,json}  第一表 + 第二表
      opencc/erjian_xiu.{txt,json}  1981 修订草案
"""
import json, os, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'erjian_tables.json')
CURATED = os.path.join(ROOT, 'tools', 'curated.json')
OUT = os.path.join(ROOT, 'opencc')

TABLES = {
    'erjian_b1':  {'title': '二简字·第一表（试行表）',        'src': ['erjian1']},
    'erjian_b12': {'title': '二简字·第一表＋第二表',          'src': ['erjian1', 'erjian2']},
    'erjian_xiu': {'title': '二简字·1981 年修订草案',         'src': ['erjianXiu']},
}


def load():
    pairs = json.load(open(DATA, encoding='utf-8'))
    cur = json.load(open(CURATED, encoding='utf-8'))
    return pairs, cur


def build(pairs, cur, srcs):
    """合并来源表。e1/e2 已验证互不冲突、无级联，故取并集。"""
    tab = {}
    for s in srcs:
        for k, v in pairs[s]:
            tab.setdefault(k, [])
            if v not in tab[k]:
                tab[k].append(v)
    return tab


def apply_curated(name, tab, cur):
    """套用人工校订层。

    override 只改已存在的条目，因而自动只作用于收了该字的表；
    override_by_table / add / remove 必须按表指定——第一表与第二表所简化的字
    并不相同，不分表就会把第二表的规则（如 雕→刁 的鸟名词组）漏进第一表。
    """
    n = 0
    for k, v in cur.get('override', {}).items():
        if k in tab:
            tab[k] = v if isinstance(v, list) else [v]; n += 1
    for k, v in cur.get('override_by_table', {}).get(name, {}).items():
        if k in tab:
            tab[k] = v if isinstance(v, list) else [v]; n += 1
    for k, v in cur.get('add', {}).get(name, {}).items():
        if k not in tab:
            tab[k] = v if isinstance(v, list) else [v]; n += 1
    for k in cur.get('remove', {}).get(name, []):
        if tab.pop(k, None) is not None:
            n += 1
    return n


def compose(tab):
    """把词级规则的输出再过一遍字级规则，直到不动点。

    OpenCC 是单遍最长匹配，不会像逐条正则替换那样反复套用。
    例如「座山雕→座山𩾗」若不合成，座→坐 就会漏掉，
    正确结果应为「坐山𩾗」。
    """
    chartab = {k: v[0] for k, v in tab.items() if len(k) == 1}
    def step(s):
        return ''.join(chartab.get(c, c) for c in s)
    changed = 0
    for k, vs in tab.items():
        for i, v in enumerate(vs):
            seen = {v}
            nv = step(v)
            guard = 0
            while nv != v:
                if nv in seen or guard > 8:
                    raise SystemExit(f'合成不收敛: {k} -> {v}')
                seen.add(nv); v = nv; nv = step(v); guard += 1
            if vs[i] != v:
                changed += 1
                vs[i] = v
    return changed


def sanity(name, tab):
    errs = []
    for k, vs in tab.items():
        if not k or not vs:
            errs.append(f'{name}: 空条目 {k!r}')
        for ch in k:
            if ch.isspace() or ch == '\t':
                errs.append(f'{name}: 键含空白 {k!r}')
        for v in vs:
            if ' ' in v or '\t' in v:
                errs.append(f'{name}: 值含空白 {k!r}->{v!r}')
        if len(vs) == 1 and vs[0] == k:
            errs.append(f'{name}: 自映射 {k}')
    # 级联：输出是否会再次被本表命中（OpenCC 单遍替换，不应依赖级联）
    for k, vs in tab.items():
        for ch in vs[0]:
            if ch in tab and tab[ch][0] != ch:
                errs.append(f'{name}: 级联 {k}->{vs[0]} 中的 {ch} 另有映射 {tab[ch][0]}')
    return errs


def write(name, title, tab):
    txt = os.path.join(OUT, name + '.txt')
    # OpenCC 的 text 词典不支持注释行，且要求按键排序；
    # 任何多余内容都会让 OpenCC 解析失败，而 librime 只会笼统地报
    # 「opencc config not found」，极难排查。故此处只写纯条目。
    with open(txt, 'w', encoding='utf-8', newline='\n') as f:
        for k in sorted(tab):
            f.write(k + '\t' + ' '.join(tab[k]) + '\n')
    cfg = {
        'name': title,
        'segmentation': {'type': 'mmseg', 'dict': {'type': 'text', 'file': name + '.txt'}},
        # 用 group 包一层：与 rime-emoji 等公认可用的配置保持一致
        'conversion_chain': [{'dict': {'type': 'group',
                                       'dicts': [{'type': 'text', 'file': name + '.txt'}]}}],
    }
    with open(os.path.join(OUT, name + '.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return txt


def main():
    pairs, cur = load()
    os.makedirs(OUT, exist_ok=True)
    allerr = []
    for name, meta in TABLES.items():
        tab = build(pairs, cur, meta['src'])
        ncur = apply_curated(name, tab, cur)
        nfix = compose(tab)
        errs = sanity(name, tab)
        allerr += errs
        write(name, meta['title'], tab)
        nchar = sum(1 for k in tab if len(k) == 1)
        nmulti = sum(1 for v in tab.values() if len(v) > 1)
        glyphs = {c for vs in tab.values() for v in vs for c in v}
        nonbmp = sum(1 for c in glyphs if ord(c) > 0xFFFF)
        print(f'{name:12s} {len(tab):4d} 条 ({nchar} 字级 / {len(tab)-nchar} 词级), '
              f'{nmulti} 条多候选, 字形 {len(glyphs)} 个 (BMP 外 {nonbmp}), 校订 {ncur} 条, 合成修正 {nfix} 条')
    if allerr:
        print('\n!! 校验问题:')
        for e in allerr:
            print('  ', e)
        return 1
    print('\n校验通过。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
