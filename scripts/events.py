#!/usr/bin/env python3
"""events.py — 日报事件库（记忆层）

解决三个问题：
1. 跨期去重——不跟「上一期」比，跟全部历史比
2. 「持续开放」段由脚本从事件库生成，agent 不再手抄往期条目
3. 到期自动淘汰——结束的活动不再反复出现

用法：
  python3 events.py backfill                     # 从历史 digest_data_*.json 建库
  python3 events.py merge <draft.json> --date 2026-10-17 [--out final.json]
  python3 events.py query <关键词>               # 查某个活动是否已收录
  python3 events.py status                       # 库整体统计（诊断用）

merge 的行为：
  - draft 里的条目先与库比对：已在库里的 = 重复
  - 重复条目默认从各段删除（进「持续开放」段或直接淘汰）；
    例外：位于第 1 段（48h 内截止）或 urgent=true 的重复条目保留在原位
    （老活动进入最后 48 小时是正经新闻，不该被去重干掉）
  - 「持续开放」段 = 库中 last_seen 早于今天且仍未结束的活动，按截止日期升序，上限 40 个
  - 输出 final json（draft 的段 + 持续开放段），并打印统计
"""
import json, re, sys, os, glob, argparse
from datetime import date, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, "events_master.json")
ONGOING_CAP = 40
URGENT_SECTION_INDEX = 0  # 第 1 段视为紧急段


# ---------- 工具 ----------

def norm_url(u):
    if not u:
        return ""
    u = u.strip().lower()
    u = re.sub(r'^https?://', '', u)
    u = re.sub(r'^www\.', '', u)
    u = u.split('#')[0].split('?')[0].rstrip('/')
    return u

def norm_title(t):
    if not t:
        return ""
    return re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '', t.lower())

def event_key(a):
    """URL 为主键（最稳），无 URL 退回标题归一化。"""
    u = norm_url(a.get('url', ''))
    if u and len(u) > 12:
        return 'u:' + u
    return 't:' + norm_title(a.get('title', ''))[:60]

def parse_dates(text, today):
    """从自由文本里榨出日期列表。返回 date 对象列表（可能为空）。"""
    if not text:
        return []
    text = str(text)
    out = []
    cur_y = today.year
    # 完整日期 2026-10-30 / 2026/10/30
    for m in re.finditer(r'(20\d{2})[-/](\d{1,2})[-/](\d{1,2})', text):
        try:
            out.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            pass
    # 缺年份 10-30 / 10/30 / 10.30
    for m in re.finditer(r'(?<!\d)(\d{1,2})[-/.](\d{1,2})(?!\d)', text):
        mo, d = int(m.group(1)), int(m.group(2))
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            continue
        # 选让日期落在 today-60 天 ~ today+400 天区间的年份
        for y in (cur_y, cur_y + 1, cur_y - 1):
            try:
                cand = date(y, mo, d)
            except ValueError:
                continue
            if -60 <= (cand - today).days <= 400:
                out.append(cand)
                break
    return out

def latest_date(a, today):
    """条目的「最后相关日期」：deadline 优先，其次 time。"""
    cands = parse_dates(a.get('deadline', ''), today)
    if not cands:
        cands = parse_dates(a.get('time', ''), today)
    return max(cands) if cands else None

def is_closed(a, today):
    d = latest_date(a, today)
    return d is not None and d < today

def load_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def sections_of(d):
    return d.get('sections', [])

def activities_of(d):
    out = []
    for s in sections_of(d):
        for a in s.get('activities', []):
            out.append((s, a))
    return out


# ---------- 子命令 ----------

def cmd_backfill(args):
    files = sorted(glob.glob(os.path.join(BASE, 'digest_data_*.json')))
    files = [f for f in files if '.draft.' not in f]
    master = {'version': 1, 'events': {}}
    for f in files:
        day = re.search(r'digest_data_(\d{4}-\d{2}-\d{2})', os.path.basename(f))
        if not day:
            continue
        day = day.group(1)
        d = load_json(f)
        for _, a in activities_of(d):
            k = event_key(a)
            ev = master['events'].get(k)
            if ev is None:
                master['events'][k] = {
                    'title': a.get('title', ''), 'url': a.get('url', ''),
                    'first_seen': day, 'last_seen': day,
                    'deadline': a.get('deadline', ''), 'time': a.get('time', ''),
                    'format': a.get('format', ''), 'source': a.get('source', ''),
                    'highlight': a.get('highlight', ''), 'star': a.get('star', False),
                    'online': a.get('online', False), 'hz': a.get('hz', False),
                    'status': 'unknown',
                }
            else:
                ev['last_seen'] = max(ev['last_seen'], day)
                ev['first_seen'] = min(ev['first_seen'], day)
                # 字段刷新为最新一期看到的样子
                for fld in ('deadline', 'time', 'format', 'highlight', 'title', 'url'):
                    if a.get(fld):
                        ev[fld] = a[fld]
    # 结算 status
    today = date.today()
    for ev in master['events'].values():
        d = parse_dates(ev.get('deadline', ''), today) or parse_dates(ev.get('time', ''), today)
        if not d:
            ev['status'] = 'unknown'
        else:
            ev['status'] = 'closed' if max(d) < today else 'open'
    master['updated'] = today.isoformat()
    with open(MASTER, 'w', encoding='utf-8') as f:
        json.dump(master, f, ensure_ascii=False, indent=1)
    op = sum(1 for e in master['events'].values() if e['status'] == 'open')
    cl = sum(1 for e in master['events'].values() if e['status'] == 'closed')
    un = len(master['events']) - op - cl
    print(f"backfill: {len(files)} 期 → 库内 {len(master['events'])} 个事件")
    print(f"  open {op} / closed {cl} / unknown {un}")
    print(f"  master: {MASTER}")


def cmd_merge(args):
    today = date.fromisoformat(args.date)
    draft = load_json(args.draft)
    master = load_json(MASTER) if os.path.exists(MASTER) else {'version': 1, 'events': {}}
    if not master.get('events'):
        print("!! events_master.json 为空——先跑 backfill，否则第一期会把历史全当新的", file=sys.stderr)

    kept, dropped = [], []
    for si, s in enumerate(sections_of(draft)):
        kept_acts = []
        for a in s.get('activities', []):
            k = event_key(a)
            is_urgent_slot = (si == URGENT_SECTION_INDEX) or bool(a.get('urgent'))
            if k in master['events'] and not is_urgent_slot:
                dropped.append(a.get('title', '?'))
                continue
            kept_acts.append(a)
        s['activities'] = kept_acts
        kept.append(s)

    # 更新库
    for s in kept:
        for a in s['activities']:
            k = event_key(a)
            ev = master['events'].get(k)
            rec = {
                'title': a.get('title', ''), 'url': a.get('url', ''),
                'first_seen': args.date, 'last_seen': args.date,
                'deadline': a.get('deadline', ''), 'time': a.get('time', ''),
                'format': a.get('format', ''), 'source': a.get('source', ''),
                'highlight': a.get('highlight', ''), 'star': a.get('star', False),
                'online': a.get('online', False), 'hz': a.get('hz', False),
                'status': 'unknown',
            }
            if ev is None:
                master['events'][k] = rec
            else:
                ev['last_seen'] = args.date
                for fld in ('deadline', 'time', 'format', 'highlight', 'title', 'url', 'star', 'online', 'hz'):
                    if a.get(fld):
                        ev[fld] = a[fld]

    # 重算 status + 生成持续开放段
    # 可见键 = 去重后仍留在各段里的条目（这些不用再进持续开放，避免重复展示）
    visible_keys = set()
    for s in kept:
        for a in s['activities']:
            visible_keys.add(event_key(a))

    ongoing = []
    for k, ev in master['events'].items():
        if k in visible_keys:
            continue
        d = parse_dates(ev.get('deadline', ''), today) or parse_dates(ev.get('time', ''), today)
        if d and max(d) < today:
            ev['status'] = 'closed'
            continue
        ev['status'] = 'open' if d else 'unknown'
        # 只带仍有明确截止或高相关的进持续开放；unknown 状态且 star 的也保留
        if d or ev.get('star'):
            ongoing.append((k, ev))
    ongoing.sort(key=lambda kv: (
        kv[1]['status'] != 'open',                      # open 优先
        not kv[1].get('star'),                          # 主线相关优先
        min(parse_dates(kv[1].get('deadline', ''), today) or [date(2099, 1, 1)]),
    ))
    ongoing = ongoing[:ONGOING_CAP]

    if ongoing:
        acts = []
        for k, ev in ongoing:
            acts.append({
                'group': '持续开放', 'title': ev.get('title', ''), 'url': ev.get('url', ''),
                'time': ev.get('time', ''), 'format': ev.get('format', ''),
                'deadline': ev.get('deadline', ''), 'fee': '见原页',
                'source': ev.get('source', ''),
                'highlight': ev.get('highlight', ''),
                'note': f"{ev['first_seen']} 起收录，仍有效",
                'star': ev.get('star', False), 'online': ev.get('online', False),
                'hz': ev.get('hz', False),
            })
        total_open = sum(1 for k2, e in master['events'].items()
                         if e['status'] in ('open', 'unknown') and k2 not in visible_keys)
        title = f"🔁 持续开放 · 往期仍可参与（{len(acts)}/{total_open}，按截止排序）"
        kept.append({'icon': '🔁', 'title': title, 'css_class': 's-gray', 'activities': acts})

    master['updated'] = args.date
    with open(MASTER, 'w', encoding='utf-8') as f:
        json.dump(master, f, ensure_ascii=False, indent=1)

    final = dict(draft)
    final['sections'] = kept
    out = args.out or args.draft.replace('.draft.json', '.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=1)

    n_new = sum(len(s['activities']) for s in kept[:-1]) if ongoing else sum(len(s['activities']) for s in kept)
    print(f"merge {args.date}:")
    print(f"  新增/保留 {n_new} 条 | 去重删除 {len(dropped)} 条 | 持续开放 {len(ongoing)} 条")
    if dropped:
        print(f"  被去重的前 10 条: {dropped[:10]}")
    print(f"  库内事件总数 {len(master['events'])}")
    print(f"  输出: {out}")


def cmd_query(args):
    if not os.path.exists(MASTER):
        print("库不存在，先 backfill"); return
    master = load_json(MASTER)
    kw = args.keyword.lower()
    hits = [(k, e) for k, e in master['events'].items()
            if kw in e.get('title', '').lower() or kw in e.get('url', '').lower()]
    print(f"命中 {len(hits)} 条：")
    for k, e in hits[:20]:
        print(f"  [{e['status']:>7}] {e['first_seen']}~{e['last_seen']} | {e['title'][:50]}")


def cmd_status(args):
    if not os.path.exists(MASTER):
        print("库不存在，先 backfill"); return
    master = load_json(MASTER)
    evs = master['events'].values()
    from collections import Counter
    c = Counter(e['status'] for e in evs)
    print(f"库内 {len(master['events'])} 事件: {dict(c)}")
    today = date.today()
    # 复读榜：last_seen - first_seen 跨度最大的
    span = []
    for e in evs:
        try:
            fs = date.fromisoformat(e['first_seen']); ls = date.fromisoformat(e['last_seen'])
            span.append(((ls - fs).days, e))
        except Exception:
            pass
    span.sort(reverse=True, key=lambda x: x[0])
    print("连登榜 top 8（跨度天数）：")
    for days, e in span[:8]:
        print(f"  {days:>3} 天 | {e['first_seen']}~{e['last_seen']} | {e['title'][:45]}")
    # 信源命中
    src = Counter(e.get('source', '?') for e in evs if e.get('last_seen', '') >= (today.replace(day=1).isoformat()))
    print("本月信源命中 top 10:")
    for s, n in src.most_common(10):
        print(f"  {n:>4} | {s}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    sub.add_parser('backfill')
    mg = sub.add_parser('merge')
    mg.add_argument('draft')
    mg.add_argument('--date', required=True)
    mg.add_argument('--out')
    q = sub.add_parser('query')
    q.add_argument('keyword')
    sub.add_parser('status')
    args = p.parse_args()
    {'backfill': cmd_backfill, 'merge': cmd_merge, 'query': cmd_query, 'status': cmd_status}[args.cmd](args)


if __name__ == '__main__':
    main()
