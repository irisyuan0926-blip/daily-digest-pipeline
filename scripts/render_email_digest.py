#!/usr/bin/env python3
"""
日报邮件「摘要 + 网页链接」渲染器 —— 单封 < 2KB，永不拆封、稳定送达 163。

用法:
    python3 render_email_digest.py data.json out.html "https://<网页链接>" [紧急条数上限]

产出：渐变 banner 头 + 统计块 + 紧急清单（默认 ≤12 条）+ 大按钮跳完整版 + 明文地址兜底。
完整条目不进邮件，全部放在网页版（核心架构：内容全量上网页，通知只发摘要）。

紧急判定双通道（缺一不可，否则紧急清单会空）：
    ① 条目自带 urgent=True；
    ② 归在标题含「48」的板块（如「⏰ 48小时内截止 / 48h 紧急」）——采集阶段通常不写
       urgent 字段，靠板块归属表达紧急，故必须回退识别。
统计块可配：data["stats"] = [{"key":..., "label":...}, ...]（key 对应条目布尔字段）。
"""
import json
import sys
import html
from pathlib import Path

esc = lambda s: html.escape(str(s or ""), quote=False)

DEFAULT_STATS = [{"key": "urgent", "label": "紧急"},
                 {"key": "star", "label": "重点"},
                 {"key": "online", "label": "可线上"}]


def render(data: dict, link: str, max_urgent: int = 5) -> str:
    title = data.get("title", "每日日报")
    byline = data.get("byline", "")
    date_str = data.get("date", "")
    issue = data.get("issue", "001")
    urgent_label = data.get("urgent_label", "紧急项")
    stats_def = data.get("stats") or DEFAULT_STATS

    secs = data.get("sections", [])
    # 紧急回退：板块标题含「48」→ 其下条目一律视为紧急（采集不写 urgent 字段时的兜底）。
    for s in secs:
        if "48" in (s.get("title") or ""):
            for a in s.get("activities", []):
                a["urgent"] = True
    acts = [a for s in secs for a in s["activities"]]
    total = len(acts)

    stats = (f'<td class="s"><b>{total}</b><br>总数</td>' + "".join(
        f'<td class="s"><b>{sum(1 for a in acts if a.get(s["key"]))}</b><br>{esc(s["label"])}</td>'
        for s in stats_def[:3]
    ))

    # 摘要邮件至少展示 12 条紧急（48h 段常接近此量），故取 max(max_urgent, 12)。
    urgent = [a for a in acts if a.get("urgent")][:max(max_urgent, 12)]
    if urgent:
        li = "".join(
            f'<li><a href="{esc(a["url"])}">{esc(a["title"])}</a>'
            f'<span class="d">{esc(a.get("deadline") or a.get("time") or "")}</span></li>'
            for a in urgent
        )
        more = (f'<div class="more">另有 {total - len(urgent)} 条 · 完整清单见网页版</div>'
                if total > len(urgent) else "")
        body_html = f'<div class="hd">{esc(urgent_label)}</div><ul>{li}</ul>{more}'
    else:
        body_html = f'<div class="hd">今日无{esc(urgent_label)}</div>'

    foot_by = f"—— {esc(byline)} · 自动生成" if byline else "自动生成"

    return f"""<div class="w">
<div class="h"><div class="t">第 {esc(issue)} 期 · {esc(date_str)}</div>
<div class="n">{esc(title)}</div>
<div class="dt">共 {total} 条</div></div>
<table class="st"><tr>{stats}</tr></table>
{body_html}
<a class="b" href="{esc(link)}">查看完整 {total} 条（可筛选 · 点标题直达）</a>
<div class="f">网页版地址（建议收藏，每天自动更新）：<br><a href="{esc(link)}">{esc(link)}</a><br>
{foot_by}</div>
</div>
<style>
.w{{max-width:600px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;color:#1F2937;background:#fff}}
.h{{background:linear-gradient(135deg,#74D4BE 0%,#5FB6E6 100%);color:#fff;border-radius:14px;padding:22px 20px}}
.h .t{{font-size:11px;letter-spacing:1px;opacity:.85}}
.h .n{{font-size:22px;font-weight:700;margin:8px 0 4px}}
.h .dt{{font-size:12.5px;opacity:.92}}
.st{{width:100%;border-collapse:separate;border-spacing:6px;margin:14px 0 4px}}
.st .s{{background:#F4F7FA;border-radius:9px;padding:9px 4px;text-align:center;font-size:11px;color:#6B7280}}
.st .s b{{display:block;font-size:19px;color:#1F2937;line-height:1.2}}
.hd{{margin:16px 0 8px;font-size:14.5px;font-weight:700;color:#991B1B}}
.w ul{{margin:0;padding-left:18px}}
.w li{{font-size:13.5px;line-height:1.7;margin-bottom:7px}}
.w li a{{color:#2563EB;text-decoration:none;font-weight:600}}
.w li .d{{color:#991B1B;font-size:11.5px;margin-left:5px}}
.more{{font-size:12px;color:#6B7280;margin-top:4px}}
.b{{display:block;margin:18px 0 14px;background:#2563EB;color:#fff;text-align:center;
text-decoration:none;font-size:15px;font-weight:700;padding:13px;border-radius:9px}}
.f{{font-size:11.5px;color:#9CA3AF;line-height:1.7;text-align:center;border-top:1px solid #E5E7EB;padding-top:12px}}
.f a{{color:#6B7280}}
</style>"""


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)   # 输出目录不存在时自动建
    cap = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    out.write_text(render(data, sys.argv[3], cap), encoding="utf-8")
    size = len(out.read_text(encoding="utf-8").encode("utf-8"))
    n = sum(len(s["activities"]) for s in data["sections"])
    print(f"OK  {out}  {size/1024:.2f} KB  {n} 条（清单在网页版）")


if __name__ == "__main__":
    main()
