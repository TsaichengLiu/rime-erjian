#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""二简字转换表自测 + 歧义体检。

OpenCC 的 mmseg 分词是「从左起取最长匹配键」，这里照此模拟，
用来在部署到 Rime 之前验证表的行为。
"""
import os, sys, json, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    tab = {}
    with open(os.path.join(ROOT, 'opencc', name + '.txt'), encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            k, v = line.rstrip('\n').split('\t')
            tab[k] = v.split(' ')
    return tab


def conv(text, tab, alt=0):
    """模拟 OpenCC：从左起最长匹配。alt 选第几个候选。"""
    maxk = max(len(k) for k in tab)
    out, i = [], 0
    while i < len(text):
        for L in range(min(maxk, len(text) - i), 0, -1):
            seg = text[i:i + L]
            if seg in tab:
                vs = tab[seg]
                out.append(vs[alt] if alt < len(vs) else vs[0])
                i += L
                break
        else:
            out.append(text[i]); i += 1
    return ''.join(out)


GOLDEN = [
    # (表, 输入, 期望)
    ('erjian_b1',  '停止营业',       '仃止营业'),
    ('erjian_b1',  '鸡蛋',           '鸡旦'),
    ('erjian_b1',  '餐厅',           '歺厅'),
    ('erjian_b1',  '知道',           '知辺'),
    ('erjian_b1',  '跳舞',           '跳午'),
    ('erjian_b1',  '嘴巴',           '咀巴'),
    ('erjian_b1',  '咀嚼',           '咀嚼'),      # 咀 本音 jǔ，不受影响
    ('erjian_b1',  '伶仃',           '伶仃'),      # 仃 本音 dīng，不受影响
    ('erjian_b1',  '元旦',           '元旦'),      # 旦 本字，不受影响
    ('erjian_b1',  '副食',           '付食'),
    ('erjian_b1',  '彩色',           '采色'),
    ('erjian_b1',  '蝌蚪',           '科斗'),      # 词级规则
    ('erjian_b1',  '朦胧',           '𰰡龙'),      # 词级规则
    ('erjian_b1',  '蒙眬',           '𰰡龙'),
    ('erjian_b1',  '信息',           '伩息'),
    ('erjian_b1',  '稀少',           '希少'),
    ('erjian_b12', '辩论',           '弁论'),
    ('erjian_b12', '蜻蜓',           '𰀈𨑳'),
    ('erjian_b12', '叮咛',           '丁宁'),
    ('erjian_b12', '柠檬',           '宁𰰡'),
    ('erjian_b12', '雕刻',           '刁刻'),      # 註7 雕刻之雕作刁
    ('erjian_b12', '座山雕',         '坐山𩾗'),    # 註7 鸟名作𩾗；且座→坐须一并合成
    ('erjian_b12', '雕属',           '𩾗𰍱'),      # 合成：属→𰍱
    ('erjian_b12', '真雕',           '𰅴𩾗'),      # 合成：真→𰅴
    ('erjian_b12', '鹦鹉',           '𰋷武'),
    ('erjian_xiu', '餐厅',           '歺厅'),
    # 校订层必须分表作用：雕→刁 属第二表，第一表不简化「雕」，
    # 故鸟名词组不得漏进第一表；但「座→坐」是第一表的字级规则，仍应生效。
    ('erjian_b1',  '座山雕',         '坐山雕'),
    ('erjian_b12', '座山雕',         '坐山𩾗'),
    ('erjian_xiu', '座山雕',         '座山雕'),
    # IDS 推导所得：褴 = ⿰衤监 → ⿰礻监 = 𱵥（第二表 衤→礻 类推）
    ('erjian_b12', '褴褛',           '𱵥褛'),
    ('erjian_b1',  '褴褛',           '褴褛'),
    # 据 1981 年《征求意见表》原件补入修订表的四条（原件一之11、二之7/18/19）
    ('erjian_xiu', '矗立',           '𰅹立'),
    ('erjian_xiu', '具体',           '𰋙体'),
    ('erjian_xiu', '真实',           '𰅴实'),
    ('erjian_xiu', '直接',           '𰅰接'),
    # 这四字 1977 一表本就有，补入修订表不应改变一表／一二表的行为
    ('erjian_b1',  '矗立',           '𰅹立'),
    ('erjian_b12', '直接',           '𰅰接'),
    # 原件一之13：巅癫并作颠，颠之真旁再按 真→𰅴 类推，合成得 𱂪
    ('erjian_xiu', '巅峰',           '𱂪峰'),
    ('erjian_xiu', '癫痫',           '𱂪痫'),
    ('erjian_b12', '巅峰',           '𱂪夆'),
]


def golden():
    bad = 0
    cache = {}
    for t, src, want in GOLDEN:
        tab = cache.setdefault(t, load(t))
        got = conv(src, tab)
        if got != want:
            print(f'  FAIL [{t}] {src}: 期望 {want} 实得 {got}')
            bad += 1
    print(f'黄金用例 {len(GOLDEN)} 条，失败 {bad} 条。')
    return bad


def corpus_report(tabname, limit=None):
    """用朙月拼音词库做语料，统计二简造成的同形合并。"""
    import re
    src = '/Library/Input Methods/Squirrel.app/Contents/SharedSupport/luna_pinyin.dict.yaml'
    if not os.path.exists(src):
        print('（未找到朙月拼音词库，跳过歧义体检）'); return
    try:
        import opencc as _o
        t2s = _o.OpenCC('t2s')
        to_simp = t2s.convert
    except Exception:
        print('（无 opencc t2s，跳过歧义体检）'); return

    words, seen = [], set()
    with open(src, encoding='utf-8') as f:
        body = False
        for line in f:
            if line.startswith('...'):
                body = True; continue
            if not body or line.startswith('#') or not line.strip():
                continue
            w = line.split('\t')[0].strip()
            if 2 <= len(w) <= 4 and re.fullmatch(r'[㐀-鿿]+', w):
                s = to_simp(w)
                if s not in seen:
                    seen.add(s); words.append(s)
            if limit and len(words) >= limit:
                break

    tab = load(tabname)
    buckets = collections.defaultdict(list)
    for w in words:
        buckets[conv(w, tab)].append(w)
    merged = {k: v for k, v in buckets.items() if len(v) > 1}
    print(f'\n[{tabname}] 歧义体检：语料 {len(words)} 词，'
          f'转换后 {len(buckets)} 个不同字形，{len(merged)} 组发生同形合并。')
    rank = sorted(merged.items(), key=lambda kv: -len(kv[1]))
    print('  合并最多的 20 组：')
    for k, v in rank[:20]:
        print(f'    {k}  ←  {" ".join(v)}')
    return merged


if __name__ == '__main__':
    bad = golden()
    corpus_report('erjian_b1')
    corpus_report('erjian_b12')
    sys.exit(1 if bad else 0)
