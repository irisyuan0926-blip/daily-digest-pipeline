#!/usr/bin/env python3
"""interests.py — 兴趣模型动态更新

标记词汇（用户指定，2026-10-16 定版）：**很感兴趣 / 不感兴趣**。
（早期方案里的「有用/无用」已废弃，不要再写进任何 prompt。）

运转方式：
  1. 用户在 interests.md 的「动态标记」区追加一行（或让 agent 用 mark 子命令代写）：
       - 2026-10-18 | 很感兴趣 | DoraHacks AI 黑客松
       - 2026-10-18 | 不感兴趣 | 校园编程挑战赛
  2. 每周复盘跑 `python3 interests.py update`：把标记与 events_master.json 里的
     历史事件做匹配，重写「动态模型」区（加分/减分关键词 + 命中证据）
  3. 采集时读「动态模型」区：命中加分关键词的排前/加 star，命中减分关键词的降权

用法（在 templates/ 目录下跑）：
  python3 interests.py mark 很感兴趣 <活动名或关键词>
  python3 interests.py mark 不感兴趣 <活动名或关键词>
  python3 interests.py update          # 重算动态模型（周复盘调）
  python3 interests.py show            # 看当前模型
"""
import json, re, sys, os, argparse
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
INTERESTS = os.path.join(os.path.dirname(BASE), "interests.md")
MASTER = os.path.join(BASE, "events_master.json")

MODEL_BEGIN = "<!-- MODEL:BEGIN -->"
MODEL_END = "<!-- MODEL:END -->"
MARKS_HEADER = "## 动态标记"
MODEL_HEADER = "## 动态模型"

VALID_TAGS = ("很感兴趣", "不感兴趣")


def norm(s):
    if not s:
        return ""
    return re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '', s.lower())


def read_interests():
    if not os.path.exists(INTERESTS):
        return ""
    return open(INTERESTS, encoding='utf-8').read()


def write_interests(text):
    with open(INTERESTS, 'w', encoding='utf-8') as f:
        f.write(text)


def parse_marks(text):
    """从「动态标记」区解析 (日期, 标签, 内容)。"""
    marks = []
    in_sec = False
    for line in text.splitlines():
        if line.startswith('## '):
            in_sec = line.strip().startswith(MARKS_HEADER)
            continue
        if not in_sec:
            continue
        m = re.match(r'\s*-\s*(\d{4}-\d{2}-\d{2})?\s*\|?\s*(很感兴趣|不感兴趣)\s*\|\s*(.+)$', line.strip())
        if m:
            marks.append((m.group(1) or '', m.group(2), m.group(3).strip()))
    return marks


def cmd_mark(args):
    if args.tag not in VALID_TAGS:
        print(f"标签只能是 {' / '.join(VALID_TAGS)}"); sys.exit(1)
    text = read_interests()
    if MARKS_HEADER not in text:
        print(f"interests.md 缺少「{MARKS_HEADER}」区，先建文件"); sys.exit(1)
    line = f"- {date.today().isoformat()} | {args.tag} | {' '.join(args.text)}"
    lines = text.splitlines()
    # 找到动态标记区的范围（到下一个 ## 或文件尾），插到该区最后一行之后
    sec_start = None
    for i, l in enumerate(lines):
        if l.strip().startswith(MARKS_HEADER):
            sec_start = i
            break
    if sec_start is None:
        print(f"interests.md 缺少「{MARKS_HEADER}」区"); sys.exit(1)
    sec_end = len(lines)
    for j in range(sec_start + 1, len(lines)):
        if lines[j].startswith('## '):
            sec_end = j
            break
    lines.insert(sec_end, line)
    write_interests('\n'.join(lines) + '\n')
    print(f"已标记: {args.tag} | {' '.join(args.text)}")


def cmd_show(args):
    text = read_interests()
    m = re.search(re.escape(MODEL_BEGIN) + r'(.*?)' + re.escape(MODEL_END), text, re.S)
    print(m.group(1).strip() if m else "（动态模型为空，跑 update 生成）")


def match_events(keyword, events):
    """关键词与事件标题匹配。先试整词；整词 0 命中时拆词回退
    （长关键词如「DoraHacks AI 黑客松」不会原样出现在标题里）。
    返回 (命中标题列表, 生效关键词)。"""
    k = norm(keyword)
    if len(k) < 2:
        return [], k
    hits = [ev.get('title', '') for ev in events.values()
            if (t := norm(ev.get('title', ''))) and (k in t or (len(t) >= 4 and t in k))]
    if hits:
        return hits, k
    # 拆词回退：拉丁词（通常是品牌名）优先；中文词只在不命中的拉丁词时才用，
    # 且「黑客松/大赛/活动」这类泛词禁止当生效词（命中一切 = 没有信息量）
    generic = {'黑客松', '大赛', '活动', '挑战赛', '马拉松', '峰会', '论坛', '训练营', '研讨会'}
    latin = [t for t in re.findall(r'[a-z]{5,}', keyword.lower())
             if t not in ('hackathon', 'showdev', 'opensource')]
    cjk = [t for t in re.findall(r'[\u4e00-\u9fff]{2,}', keyword) if t not in generic]
    best, best_hits = None, []
    for tok in latin + cjk:
        th = [ev.get('title', '') for ev in events.values()
              if tok in norm(ev.get('title', ''))]
        if len(th) > len(best_hits):
            best, best_hits = tok, th
    return best_hits, (best or k)


def cmd_update(args):
    text = read_interests()
    if not text:
        print("interests.md 不存在"); sys.exit(1)
    marks = parse_marks(text)
    events = {}
    if os.path.exists(MASTER):
        events = json.load(open(MASTER, encoding='utf-8')).get('events', {})

    pos_kw, neg_kw = [], []
    pos_lines, neg_lines = [], []
    seen = set()
    for _, tag, content in reversed(marks):  # 同关键词多次标记，以最新一次为准
        if content in seen:
            continue
        seen.add(content)
        hits, eff = match_events(content, events)
        bucket = pos_kw if tag == "很感兴趣" else neg_kw
        lines_b = pos_lines if tag == "很感兴趣" else neg_lines
        bucket.append((eff, len(hits)))
        sample = ' / '.join(h[:30] for h in hits[:3]) if hits else '（历史事件无直接命中，按关键词生效）'
        note = f"，生效词「{eff}」" if eff != norm(content) and hits else ""
        lines_b.append(f"- {'加分' if tag == '很感兴趣' else '减分'}词「{content}」{note}：历史命中 {len(hits)} 个事件（{sample}）")

    def kw_line(bucket):
        if not bucket:
            return "（无）"
        return '、'.join(f"{k}({n})" for k, n in bucket)

    model = f"""{MODEL_BEGIN}
> 由 interests.py update 于 {date.today().isoformat()} 生成，采集时读取；手动改无效，会被覆盖。
> 用法：命中加分词的排前/可加 star；命中减分词的降权或跳过。

**加分关键词**：{kw_line(pos_kw)}
**减分关键词**：{kw_line(neg_kw)}

{chr(10).join(pos_lines + neg_lines) if (pos_lines or neg_lines) else "（暂无标记）"}
{MODEL_END}"""

    if MODEL_BEGIN in text:
        text = re.sub(re.escape(MODEL_BEGIN) + r'.*?' + re.escape(MODEL_END),
                      model, text, flags=re.S)
    else:
        # 没有模型区就插到动态标记区之前
        text = text.replace(MARKS_HEADER, model + "\n\n" + MARKS_HEADER)
    write_interests(text)
    print(f"动态模型已更新：加分 {len(pos_kw)} 词 / 减分 {len(neg_kw)} 词（标记 {len(marks)} 条）")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    mk = sub.add_parser('mark')
    mk.add_argument('tag')
    mk.add_argument('text', nargs='+')
    sub.add_parser('update')
    sub.add_parser('show')
    args = p.parse_args()
    {'mark': cmd_mark, 'update': cmd_update, 'show': cmd_show}[args.cmd](args)


if __name__ == '__main__':
    main()
