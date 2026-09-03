#!/usr/bin/env python3
"""
通用日报网页渲染器 —— 不受邮件客户端 CSS 限制，可做统计 / 筛选 / 响应式。

用法:
    python3 render_web.py data.json out.html [fresh|mint|sky|warm]

主题:
    fresh  默认。只把顶部 banner 换成清新渐变，正文保持中性配色（最安全，适合只想换头图）
    mint   薄荷青整页配色    sky  晴空白蓝    warm  暖阳米白

数据格式见同目录 digest_template.json：
    title / subtitle / byline / date / issue        头部文案
    filters  筛选按钮 [{key,label}]，key 对应条目上的布尔字段
    stats    统计块 [{key,label}]，第一个总是「总数」
    sections [{icon,title,css_class,activities[]}]
    unverified[] / sources{covered,gaps[]}
"""
import json
import sys
import html
from pathlib import Path

esc = lambda s: html.escape(str(s or ""), quote=False)

DEFAULT_FILTERS = [{"key": "urgent", "label": "紧急"},
                   {"key": "star", "label": "重点"},
                   {"key": "online", "label": "可线上"}]
DEFAULT_STATS = [{"key": "urgent", "label": "紧急"},
                 {"key": "star", "label": "重点"},
                 {"key": "online", "label": "可线上"}]

# ---------- 布局骨架（颜色全部走 CSS 变量，默认值 = 中性配色） ----------
BASE = """
*{box-sizing:border-box}
:root{
--bg:#F7F8FA;
--hero:linear-gradient(135deg,#0F172A,#1E3A8A);
--hero-shadow:none;
--card:#FFFFFF;--line:#E5E7EB;--shadow:rgba(37,99,235,.07);
--text:#1F2937;--muted:#6B7280;--muted-strong:#374151;
--accent:#2563EB;--accent-visited:#7C3AED;--soft:#EFF6FF;
--hover-line:#93C5FD;--mt-strong:#DC2626;--hl-strong:#1E3A8A;
--c-red:#991B1B;--c-blue:#1E3A8A;--c-green:#166534;--c-amber:#92400E;
--bu-bg:#FEE2E2;--bu-fg:#991B1B;
--bs-bg:#FEF3C7;--bs-fg:#92400E;
--bo-bg:#DCFCE7;--bo-fg:#166534;
--bh-bg:#FFE4E6;--bh-fg:#9F1239;
}
body{margin:0;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:860px;margin:0 auto;padding:32px 20px 60px}
.hero{background:var(--hero);color:#fff;border-radius:16px;padding:34px 30px;margin-bottom:20px;
  box-shadow:var(--hero-shadow)}
.hero .tag{font-size:11px;letter-spacing:2px;opacity:.65;font-weight:600}
.hero h1{margin:10px 0 8px;font-size:29px;font-weight:700;line-height:1.2}
.hero .sub{font-size:13.5px;opacity:.9}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin-top:20px}
.stat{background:rgba(255,255,255,.13);border-radius:9px;padding:9px 15px;min-width:82px}
.stat .n{font-size:21px;font-weight:700;line-height:1.1}
.stat .l{font-size:11px;opacity:.75;margin-top:3px}

.bar{position:sticky;top:0;z-index:10;background:var(--card);border:1px solid var(--line);
  border-radius:11px;padding:11px 14px;margin-bottom:20px;
  display:flex;flex-wrap:wrap;gap:7px;align-items:center}
.bar .lb{font-size:12px;color:var(--muted);font-weight:600;margin-right:3px}
.f{border:1px solid var(--line);background:var(--card);color:var(--muted-strong);border-radius:20px;
  padding:5px 13px;font-size:12.5px;cursor:pointer;font-family:inherit;transition:.15s}
.f:hover{border-color:var(--accent);color:var(--accent)}
.f.on{background:var(--accent);border-color:var(--accent);color:#fff}
.f .c{opacity:.6;font-size:11px;margin-left:3px}

.sec{margin:30px 0 12px;padding:9px 14px;background:var(--card);border-left:5px solid var(--muted);
  border-radius:7px;font-size:18px;font-weight:700;display:flex;justify-content:space-between;align-items:center}
.sec .n{font-size:12.5px;font-weight:400;color:var(--muted)}
.s-red{color:var(--c-red);border-left-color:var(--c-red)}
.s-blue{color:var(--c-blue);border-left-color:var(--c-blue)}
.s-green{color:var(--c-green);border-left-color:var(--c-green)}
.s-amber{color:var(--c-amber);border-left-color:var(--c-amber)}
.s-gray{color:var(--muted);border-left-color:var(--muted)}

.grid{display:grid;gap:9px;margin-bottom:6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:14px 17px;transition:.15s}
.card:hover{border-color:var(--hover-line);box-shadow:0 2px 10px var(--shadow)}
.card.urgent{border-left:4px solid #DC2626}
.card.hide{display:none}
.ct{font-size:15.5px;font-weight:700;line-height:1.4;margin:0 0 7px}
.ct a{color:var(--accent);text-decoration:none}
.ct a:hover{text-decoration:underline}
.ct a:visited{color:var(--accent-visited)}
.bd{display:inline-block;font-size:10.5px;padding:2px 7px;border-radius:4px;
  font-weight:600;margin-left:5px;vertical-align:2px;white-space:nowrap}
.bu{background:var(--bu-bg);color:var(--bu-fg)}
.bs{background:var(--bs-bg);color:var(--bs-fg)}
.bo{background:var(--bo-bg);color:var(--bo-fg)}
.bh{background:var(--bh-bg);color:var(--bh-fg)}
.mt{font-size:12.5px;color:var(--muted);line-height:1.6}
.mt b{color:var(--mt-strong);font-weight:600}
.hl{margin-top:9px;padding:9px 13px;background:var(--soft);border-left:3px solid var(--accent);
  border-radius:5px;font-size:13px;line-height:1.6;color:var(--muted-strong)}
.hl b{color:var(--hl-strong)}

.box{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:16px 19px;margin-bottom:12px}
.box ul{margin:6px 0 0;padding-left:19px;line-height:1.75;font-size:13.5px}
.box li{margin-bottom:6px;color:var(--muted-strong)}
.foot{margin-top:38px;padding-top:18px;border-top:1px solid var(--line);
  text-align:center;font-size:11.5px;color:#9CA3AF;line-height:1.7}
@media(max-width:600px){.wrap{padding:18px 13px 40px}.hero{padding:24px 20px}.hero h1{font-size:23px}}
"""

THEMES = {
    # 默认：只换 banner，正文不动
    "fresh": """
:root{
--hero:linear-gradient(135deg,#74D4BE 0%,#5FB6E6 100%);
--hero-shadow:0 6px 18px rgba(47,163,150,.25);
}
""",
    "mint": """
:root{
--bg:linear-gradient(180deg,#F2FBF8 0%,#EEF6FC 100%);
--hero:linear-gradient(135deg,#74D4BE 0%,#5FB6E6 100%);
--hero-shadow:rgba(47,163,150,.22);
--card:#FFFFFF;--line:#E3F0EC;--shadow:rgba(16,120,110,.08);
--text:#1E3A38;--muted:#779390;--muted-strong:#3E5C59;
--accent:#0DA592;--accent-visited:#4C8FD0;--soft:#E9F8F4;
--hover-line:#7FD3C4;--mt-strong:#D9605A;--hl-strong:#0DA592;
--c-red:#D9605A;--c-blue:#3D8FD1;--c-green:#1E9878;--c-amber:#CE9331;
--bu-bg:#FDECEB;--bu-fg:#C24B45;--bs-bg:#FFF6E3;--bs-fg:#B5821C;
--bo-bg:#E5F7F0;--bo-fg:#12805F;--bh-bg:#E8F1FC;--bh-fg:#2F6FB5;
}
""",
    "sky": """
:root{
--bg:linear-gradient(180deg,#F6FAFF 0%,#EFF5FC 100%);
--hero:linear-gradient(135deg,#8FC6F5 0%,#A9D8E9 100%);
--hero-shadow:rgba(70,140,200,.20);
--card:#FFFFFF;--line:#E4EDF7;--shadow:rgba(40,90,150,.08);
--text:#22364A;--muted:#7A8FA6;--muted-strong:#40546A;
--accent:#2F86C4;--accent-visited:#7A6FC4;--soft:#EAF4FC;
--hover-line:#8FC6F5;--mt-strong:#D4665F;--hl-strong:#2F86C4;
--c-red:#D4665F;--c-blue:#2F86C4;--c-green:#2E9A7C;--c-amber:#CE9331;
--bu-bg:#FDEDEB;--bu-fg:#C24B45;--bs-bg:#FFF6E3;--bs-fg:#B5821C;
--bo-bg:#E6F7F1;--bo-fg:#12805F;--bh-bg:#E9F1FC;--bh-fg:#2F6FB5;
}
""",
    "warm": """
:root{
--bg:linear-gradient(180deg,#FDF9F3 0%,#FBF3EE 100%);
--hero:linear-gradient(135deg,#F5B98C 0%,#EE9A9A 100%);
--hero-shadow:rgba(210,130,100,.20);
--card:#FFFFFF;--line:#F0E5DA;--shadow:rgba(160,110,80,.09);
--text:#3A2E28;--muted:#96867C;--muted-strong:#5B4B42;
--accent:#D97B4A;--accent-visited:#9A7BC4;--soft:#FDF0E7;
--hover-line:#F0B78E;--mt-strong:#D4655E;--hl-strong:#D97B4A;
--c-red:#D4655E;--c-blue:#3D8FD1;--c-green:#4E9A6E;--c-amber:#C98A2E;
--bu-bg:#FDECEB;--bu-fg:#C24B45;--bs-bg:#FFF4DF;--bs-fg:#B5821C;
--bo-bg:#E9F7EE;--bo-fg:#3F8A5C;--bh-bg:#E8F1FC;--bh-fg:#2F6FB5;
}
""",
}

JS = """
document.querySelectorAll('.f').forEach(function(b){
  b.addEventListener('click',function(){
    document.querySelectorAll('.f').forEach(function(x){x.classList.remove('on')});
    b.classList.add('on');
    var k=b.dataset.k;
    document.querySelectorAll('.card').forEach(function(c){
      c.classList.toggle('hide', k!=='all' && !c.dataset[k]);
    });
    document.querySelectorAll('.sec').forEach(function(s){
      var vis=0, n=s.nextElementSibling;
      if(n&&n.classList.contains('grid')){
        n.querySelectorAll('.card').forEach(function(c){ if(!c.classList.contains('hide')) vis++; });
        var cnt=s.querySelector('.n'); if(cnt) cnt.textContent=vis+' 条';
        s.style.display = vis? '' : 'none';
        n.style.display = vis? '' : 'none';
      }
    });
  });
});
"""

BADGE_CLS = {"urgent": "bu", "star": "bs", "online": "bo"}


def render_card(a: dict, keys: list) -> str:
    badges = ""
    for key in keys:
        if not a.get(key):
            continue
        cls = BADGE_CLS.get(key, "bh")
        label = "紧急 " + (a.get("deadline") or "") if key == "urgent" else {
            "star": "重点", "online": "可线上"}.get(key, key)
        badges += f'<span class="bd {cls}">{esc(label)}</span>'
    if a.get("location"):
        badges += f'<span class="bd bh">{esc(a["location"])}</span>'

    meta = "｜".join(
        x for x in [a.get("time"), a.get("format"), a.get("deadline"), a.get("fee")] if x
    )
    meta_html = f'<div class="mt">{esc(meta)}</div>' if meta else ""
    hl = a.get("highlight")
    hl_html = f'<div class="hl"><b>亮点：</b>{esc(hl)}</div>' if hl else ""
    flags = "".join(f' data-{k}="1"' for k in keys if a.get(k))
    cls = "card urgent" if a.get("urgent") else "card"
    return (f'<div class="{cls}"{flags}>'
            f'<h3 class="ct"><a href="{esc(a["url"])}" target="_blank" rel="noopener">'
            f'{esc(a["title"])}</a>{badges}</h3>{meta_html}{hl_html}</div>')


def render(data: dict, theme: str = "fresh") -> str:
    theme = theme if theme in THEMES else "fresh"
    title = data.get("title", "每日日报")
    subtitle = data.get("subtitle", "每日精选")
    byline = data.get("byline", "")
    date_str = data.get("date", "")
    issue = data.get("issue", "001")
    secs = data["sections"]
    acts = [a for s in secs for a in s["activities"]]
    total = len(acts)

    filters_def = data.get("filters") or DEFAULT_FILTERS
    stats_def = data.get("stats") or DEFAULT_STATS
    keys = [f["key"] for f in filters_def]

    stats = (f'<div class="stat"><div class="n">{total}</div>'
             f'<div class="l">总数</div></div>') + "".join(
        f'<div class="stat"><div class="n">{sum(1 for a in acts if a.get(s["key"]))}</div>'
        f'<div class="l">{esc(s["label"])}</div></div>' for s in stats_def
    )

    filters = (f'<button class="f on" data-k="all">全部'
               f'<span class="c">{total}</span></button>') + "".join(
        f'<button class="f" data-k="{esc(f["key"])}">{esc(f["label"])}'
        f'<span class="c">{sum(1 for a in acts if a.get(f["key"]))}</span></button>'
        for f in filters_def
    )

    body = ""
    for s in secs:
        n = len(s["activities"])
        cards = "".join(render_card(a, keys) for a in s["activities"])
        body += (f'<h2 class="sec {s.get("css_class", "s-gray")}">'
                 f'<span>{s["icon"]} {esc(s["title"])}</span><span class="n">{n} 条</span></h2>'
                 f'<div class="grid">{cards}</div>')

    unver = data.get("unverified") or []
    if unver:
        li = "".join(f"<li>{esc(u)}</li>" for u in unver)
        body += (f'<h2 class="sec s-gray"><span>待核实</span>'
                 f'<span class="n">{len(unver)} 条</span></h2>'
                 f'<div class="box"><ul>{li}</ul></div>')

    src = data.get("sources") or {}
    if src:
        gaps = src.get("gaps") or []
        gl = "".join(f"<li>{esc(g)}</li>" for g in gaps)
        body += (f'<h2 class="sec s-gray"><span>信源说明</span></h2><div class="box">'
                 f'<div><b>已覆盖：</b>{esc(src.get("covered", ""))}</div>'
                 f'<div style="margin-top:8px"><b>未覆盖 / 缺口：</b></div><ul>{gl}</ul></div>')

    tag = f"第 {esc(issue)} 期 · {esc(subtitle)}"
    if byline:
        tag += f" · 由 {esc(byline)} 整理"

    return (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">\n"
        f"<title>{esc(title)} · {esc(date_str)}</title>\n"
        f"<style>{BASE}\n{THEMES[theme]}</style>\n</head>\n<body>\n<div class=\"wrap\">\n"
        f'<div class="hero"><div class="tag">{tag}</div>'
        f'<h1>{esc(title)}</h1>'
        f'<div class="sub">{esc(date_str)} · 共 {total} 条 · 点击标题直达</div>'
        f'<div class="stats">{stats}</div></div>\n'
        f'<div class="bar"><span class="lb">筛选：</span>{filters}</div>\n'
        f"{body}\n"
        f'<div class="foot">{esc(byline)} 自动生成 · 第 {esc(issue)} 期<br>'
        f'订阅渠道为摘要，完整版见此页</div>\n'
        "</div>\n"
        f"<script>{JS}</script>\n</body></html>\n"
    )


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)   # 输出目录不存在时自动建，别让用户在 mkdir 上踩坑
    out.write_text(render(data, sys.argv[3] if len(sys.argv) > 3 else "fresh"), encoding="utf-8")
    size = len(out.read_text(encoding="utf-8").encode("utf-8"))
    n = sum(len(s["activities"]) for s in data["sections"])
    print(f"OK  {out}  {size/1024:.1f} KB  {n} 条")


if __name__ == "__main__":
    main()
