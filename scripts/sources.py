#!/usr/bin/env python3
"""sources.py — 信源效能统计 + 退役管理

解决一个问题：SKILL.md 硬规则「某信源连续 3 天零命中建议下线」从来没被执行过，
因为没有人统计信源命中数。本脚本把命中数落成 json，让退役决策有数据。

状态文件：templates/sources_stats.json  {"days": {"2026-10-08": {"HN": 6, ...}}}

用法（在 templates/ 目录下跑）：
  python3 sources.py backfill                    # 从历史 digest_data_*.json 重建统计
  python3 sources.py record <json> --date D      # 记录某一天各信源命中数（每期 merge 后跑，传 draft）
  python3 sources.py stats [--window 7]          # 命中排名 + 退役建议（诊断/周复用）
  python3 sources.py retire <信源名> [--reason 理由]   # 把信源写进 ../retired_sources.md

退役判定（stats 输出「建议退役」）：
  - 历史有命中，但最近 window 天 0 命中
  - 已知域名阻断名单（reddit/x/facebook/news.ycombinator/r.jina.ai/google）不算退役对象，
    它们本来就标注在采集 prompt 的 ❌ 名单里
  - 最近 window 天完全没有任何采集记录时（比如采集任务暂停），跳过退役判定——
  暂停期间一切信源都会「假死」，不能按停摆数据做决策
"""
import json, re, sys, os, glob, argparse
from datetime import date, datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, "sources_stats.json")
RETIRED = os.path.join(os.path.dirname(BASE), "retired_sources.md")

# 已知域名阻断——采集 prompt 里已标注，不是「变老了」，不参与退役判定
BLOCKED = ('reddit', 'x.com', 'twitter', 'facebook', 'news.ycombinator.com',
           'r.jina.ai', 'google.com', 'www.google.com')


def load_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def save_json(p, obj):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def count_sources(obj):
    """统计一个 digest json 里各信源的条目数（按 activities 的 source 字段）。"""
    from collections import Counter
    c = Counter()
    for s in obj.get('sections', []):
        for a in s.get('activities', []):
            src = (a.get('source') or '').strip()
            if src:
                # 信源名可能带「（本期验 200）」之类的尾注，归一时保留原文但归类取主干
                c[src] += 1
    return c


def norm_source(name):
    """归类键：去掉域名尾注/路径，取可比对的主干。"""
    n = name.strip().lower()
    n = re.sub(r'（.*?）', '', n)
    n = re.sub(r'\(.*?\)', '', n)
    n = re.sub(r'https?://', '', n)
    n = n.split('/')[0]
    return n.strip()


def is_blocked(name):
    n = norm_source(name)
    return any(b in n for b in BLOCKED)


# ---------- 子命令 ----------

def cmd_backfill(args):
    files = sorted(glob.glob(os.path.join(BASE, 'digest_data_*.json')))
    files = [f for f in files if '.draft.' not in f]
    days = {}
    for f in files:
        m = re.search(r'digest_data_(\d{4}-\d{2}-\d{2})', os.path.basename(f))
        if not m:
            continue
        day = m.group(1)
        c = count_sources(load_json(f))
        if c:
            days[day] = dict(c)
    save_json(STATE, {'version': 1, 'days': days})
    print(f"backfill: {len(files)} 期 → {len(days)} 天有记录")
    print(f"  state: {STATE}")
    if days:
        last = sorted(days)[-1]
        print(f"  最后记录日: {last}（{sum(days[last].values())} 条）")


def cmd_record(args):
    if not os.path.exists(STATE):
        st = {'version': 1, 'days': {}}
    else:
        st = load_json(STATE)
    c = count_sources(load_json(args.json))
    if not c:
        print(f"record {args.date}: 当天无带 source 的条目，未记录")
        return
    # 同一天重复 record 时覆盖（以最新一次为准）
    st['days'][args.date] = dict(c)
    save_json(STATE, st)
    print(f"record {args.date}: {len(c)} 个信源 / {sum(c.values())} 条")
    for s, n in sorted(c.items(), key=lambda x: -x[1])[:5]:
        print(f"  {n:>4} | {s}")


def cmd_stats(args):
    if not os.path.exists(STATE):
        print("无统计数据，先 backfill"); return
    st = load_json(STATE)
    days = st['days']
    if not days:
        print("统计为空"); return
    today = date.today()
    all_days = sorted(days)
    last_data_day = all_days[-1]

    # 汇总每个信源：总命中、首次、末次
    agg = {}
    for d in all_days:
        for src, n in days[d].items():
            a = agg.setdefault(src, {'total': 0, 'first': d, 'last': d, 'days': 0})
            a['total'] += n
            a['first'] = min(a['first'], d)
            a['last'] = max(a['last'], d)
            a['days'] += 1

    win_end = last_data_day
    win_start = (date.fromisoformat(last_data_day) - timedelta(days=args.window - 1)).isoformat()
    window_days = [d for d in all_days if d >= win_start]

    stale = (today - date.fromisoformat(last_data_day)).days
    print(f"数据范围 {all_days[0]} ~ {last_data_day}（距今 {stale} 天），窗口 = 最近 {args.window} 个采集日")
    if stale > args.window:
        print(f"!! 最近 {stale} 天没有采集记录（采集任务可能暂停）——跳过退役判定")
        print("\n全部信源历史命中（仅供参考，不做退役决策）:")
        for s, a in sorted(agg.items(), key=lambda x: -x[1]['total'])[:15]:
            print(f"  {a['total']:>5} 条 / {a['days']:>3} 天 | {s}")
        return

    recent = {}
    for d in window_days:
        for src, n in days[d].items():
            recent[src] = recent.get(src, 0) + n

    print(f"\n=== 最近 {len(window_days)} 个采集日 信源命中排名 ===")
    for s, n in sorted(recent.items(), key=lambda x: -x[1]):
        a = agg[s]
        print(f"  {n:>4} | 历史 {a['total']:>5} 条 / {a['days']:>3} 天 | {s}")

    # 退役建议：历史有命中、窗口内 0 命中、非已知阻断
    retired_candidates = []
    print(f"\n=== 建议退役（窗口内 0 命中且历史有命中）===")
    any_cand = False
    for s, a in sorted(agg.items(), key=lambda x: x[1]['last']):
        if is_blocked(s):
            continue
        if recent.get(s, 0) == 0:
            any_cand = True
            print(f"  {s}  → 末次命中 {a['last']}，历史 {a['total']} 条")
            retired_candidates.append(s)
    if not any_cand:
        print("  （无）")

    zero_ever = [s for s in agg if agg[s]['total'] == 0]
    if zero_ever:
        print(f"\n零命中信源: {zero_ever}")


def cmd_retire(args):
    reason = args.reason or '未注明'
    line = f"- {args.source} — {reason}（{date.today().isoformat()} 由周复盘退役）"
    existing = ''
    if os.path.exists(RETIRED):
        existing = open(RETIRED, encoding='utf-8').read()
    key = norm_source(args.source)
    for l in existing.splitlines():
        if l.startswith('- ') and norm_source(l[2:].split('—')[0]) == key:
            print(f"已在退役名单: {args.source}")
            return
    with open(RETIRED, 'a', encoding='utf-8') as f:
        if existing and not existing.endswith('\n'):
            f.write('\n')
        f.write(line + '\n')
    print(f"已写入退役名单: {args.source}")
    print(f"  {RETIRED}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    sub.add_parser('backfill')
    r = sub.add_parser('record')
    r.add_argument('json')
    r.add_argument('--date', required=True)
    s = sub.add_parser('stats')
    s.add_argument('--window', type=int, default=7)
    rt = sub.add_parser('retire')
    rt.add_argument('source')
    rt.add_argument('--reason')
    args = p.parse_args()
    {'backfill': cmd_backfill, 'record': cmd_record, 'stats': cmd_stats,
     'retire': cmd_retire}[args.cmd](args)


if __name__ == '__main__':
    main()
