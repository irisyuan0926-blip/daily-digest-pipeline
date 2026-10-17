#!/usr/bin/env python3
"""
日报网页版渲染器 —— 不受邮件客户端 CSS 限制，可以做筛选/搜索/统计。

用法:
    python3 render_web.py digest_data_2026-09-03.json output.html
"""
import json
import sys
import html
from pathlib import Path

esc = lambda s: html.escape(str(s or ""), quote=False)

# ---------- 布局骨架（与旧版原型完全一致；颜色走变量，默认值 = 旧版原配色） ----------
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

# ---------- 主题：默认 fresh 只换 banner 色块，正文配色保持旧版原样 ----------
THEMES = {
    # 清新 banner（默认）：淡青绿→天蓝渐变，只动顶部色块，正文一律不改
    "fresh": """
:root{
--hero:linear-gradient(135deg,#74D4BE 0%,#5FB6E6 100%);
--hero-shadow:0 6px 18px rgba(47,163,150,.25);
}
""",

# ---------- 主题：只换颜色变量，不动结构 ----------
    # 薄荷清新：淡青绿 + 天蓝，整页换色
    "mint": """
:root{
--bg:linear-gradient(180deg,#F2FBF8 0%,#EEF6FC 100%);
--hero:linear-gradient(135deg,#74D4BE 0%,#5FB6E6 100%);
--hero-shadow:rgba(47,163,150,.22);
--card:#FFFFFF;--line:#E3F0EC;--shadow:rgba(16,120,110,.08);
--text:#1E3A38;--muted:#779390;--muted-strong:#3E5C59;
--accent:#0DA592;--accent-visited:#4C8FD0;--soft:#E9F8F4;
--c-red:#D9605A;--c-blue:#3D8FD1;--c-green:#1E9878;--c-amber:#CE9331;
--bu-bg:#FDECEB;--bu-fg:#C24B45;
--bs-bg:#FFF6E3;--bs-fg:#B5821C;
--bo-bg:#E5F7F0;--bo-fg:#12805F;
--bh-bg:#E8F1FC;--bh-fg:#2F6FB5;
}
""",
    # 晴空白蓝：更冷、更干净的蓝白
    "sky": """
:root{
--bg:linear-gradient(180deg,#F6FAFF 0%,#EFF5FC 100%);
--hero:linear-gradient(135deg,#8FC6F5 0%,#A9D8E9 100%);
--hero-shadow:rgba(70,140,200,.20);
--card:#FFFFFF;--line:#E4EDF7;--shadow:rgba(40,90,150,.08);
--text:#22364A;--muted:#7A8FA6;--muted-strong:#40546A;
--accent:#2F86C4;--accent-visited:#7A6FC4;--soft:#EAF4FC;
--c-red:#D4665F;--c-blue:#2F86C4;--c-green:#2E9A7C;--c-amber:#CE9331;
--bu-bg:#FDEDEB;--bu-fg:#C24B45;
--bs-bg:#FFF6E3;--bs-fg:#B5821C;
--bo-bg:#E6F7F1;--bo-fg:#12805F;
--bh-bg:#E9F1FC;--bh-fg:#2F6FB5;
}
""",
    # 暖阳米白：奶油底 + 蜜桃橙，柔和暖调
    "warm": """
:root{
--bg:linear-gradient(180deg,#FDF9F3 0%,#FBF3EE 100%);
--hero:linear-gradient(135deg,#F5B98C 0%,#EE9A9A 100%);
--hero-shadow:rgba(210,130,100,.20);
--card:#FFFFFF;--line:#F0E5DA;--shadow:rgba(160,110,80,.09);
--text:#3A2E28;--muted:#96867C;--muted-strong:#5B4B42;
--accent:#D97B4A;--accent-visited:#9A7BC4;--soft:#FDF0E7;
--c-red:#D4655E;--c-blue:#3D8FD1;--c-green:#4E9A6E;--c-amber:#C98A2E;
--bu-bg:#FDECEB;--bu-fg:#C24B45;
--bs-bg:#FFF4DF;--bs-fg:#B5821C;
--bo-bg:#E9F7EE;--bo-fg:#3F8A5C;
--bh-bg:#E8F1FC;--bh-fg:#2F6FB5;
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


def render_card(a: dict) -> str:
    badges = ""
    if a.get("urgent"):
        badges += f'<span class="bd bu">紧急 {esc(a.get("deadline") or "")}</span>'
    if a.get("star"):
        badges += '<span class="bd bs">主线相关</span>'
    if a.get("online"):
        badges += '<span class="bd bo">可线上</span>'
    if "杭州" in (a.get("format") or ""):
        badges += '<span class="bd bh">杭州</span>'

    meta = "｜".join(
        x for x in [a.get("time"), a.get("format"), a.get("deadline"), a.get("fee")] if x
    )
    meta_html = f'<div class="mt">{esc(meta)}</div>' if meta else ""

    hl = a.get("highlight")
    hl_html = f'<div class="hl"><b>亮点：</b>{esc(hl)}</div>' if hl else ""

    flags = ""
    for key, val in [("urgent", a.get("urgent")), ("star", a.get("star")),
                     ("online", a.get("online")), ("hz", "杭州" in (a.get("format") or ""))]:
        if val:
            flags += f' data-{key}="1"'

    cls = "card urgent" if a.get("urgent") else "card"
    return (f'<div class="{cls}"{flags}>'
            f'<h3 class="ct"><a href="{esc(a["url"])}" target="_blank" rel="noopener">'
            f'{esc(a["title"])}</a>{badges}</h3>{meta_html}{hl_html}</div>')


def render(data: dict, theme: str = "fresh") -> str:
    theme = theme if theme in THEMES else "fresh"
    date_str = data.get("date", "")
    issue = data.get("issue", "001")
    secs = data["sections"]
    acts = [a for s in secs for a in s["activities"]]
    total = len(acts)

    n_urgent = sum(1 for a in acts if a.get("urgent"))
    n_star = sum(1 for a in acts if a.get("star"))
    n_online = sum(1 for a in acts if a.get("online"))
    n_hz = sum(1 for a in acts if "杭州" in (a.get("format") or ""))

    stats = "".join(
        f'<div class="stat"><div class="n">{v}</div><div class="l">{l}</div></div>'
        for v, l in [("55" if False else total, "活动总数"), (n_urgent, "紧急"),
                     (n_star, "主线相关"), (n_online, "可线上"), (n_hz, "杭州本地")]
    )

    filters = "".join(
        f'<button class="f{" on" if k == "all" else ""}" data-k="{k}">{l}'
        f'<span class="c">{c}</span></button>'
        for k, l, c in [("all", "全部", total), ("urgent", "紧急", n_urgent),
                        ("star", "主线相关", n_star), ("online", "可线上", n_online),
                        ("hz", "杭州", n_hz)]
    )

    body = ""
    for s in secs:
        n = len(s["activities"])
        cards = "".join(render_card(a) for a in s["activities"])
        body += (f'<h2 class="sec {s.get("css_class", "s-gray")}">'
                 f'<span>{s["icon"]} {esc(s["title"])}</span><span class="n">{n} 条</span></h2>'
                 f'<div class="grid">{cards}</div>')

    unver = data.get("unverified") or []
    if unver:
        li = "".join(f"<li>{esc(u)}</li>" for u in unver)
        body += (f'<h2 class="sec s-gray"><span>待核实（明天跟进）</span>'
                 f'<span class="n">{len(unver)} 条</span></h2>'
                 f'<div class="box"><ul>{li}</ul></div>')

    src = data.get("sources") or {}
    if src:
        gaps = src.get("gaps") or []
        gl = "".join(f"<li>{esc(g)}</li>" for g in gaps)
        body += (f'<h2 class="sec s-gray"><span>信源说明</span></h2><div class="box">'
                 f'<div><b>已覆盖：</b>{esc(src.get("covered", ""))}</div>'
                 f'<div style="margin-top:8px"><b>未覆盖 / 缺口：</b></div><ul>{gl}</ul></div>')

    return (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">\n"
        f"<title>黑客松 &amp; AI 活动日报 · {esc(date_str)}</title>\n"
        f"<style>{BASE}\n{THEMES[theme]}</style>\n</head>\n<body>\n<div class=\"wrap\">\n"
        f'<div class="hero"><div class="tag">第 {esc(issue)} 期 · 每日精选 · 由 哈哈 整理</div>'
        f'<h1>黑客松 &amp; AI 活动日报</h1>'
        f'<div class="sub">{esc(date_str)} · 共 {total} 条 · 点击标题直达报名页</div>'
        f'<div class="stats">{stats}</div></div>\n'
        f'<div class="bar"><span class="lb">筛选：</span>{filters}</div>\n'
        f"{body}\n"
        f'<div class="foot">由 哈哈 每日 19:00 自动生成 · 第 {esc(issue)} 期<br>'
        f'邮件为精简摘要，完整版见此页</div>\n'
        "</div>\n"
        f"<script>{JS}</script>\n</body></html>\n"
    )


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("可选第 4 个参数指定主题: fresh(清新banner,默认,正文不变) / mint(薄荷) / sky(晴空蓝) / warm(暖阳米白)")
        sys.exit(1)
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)   # 输出目录不存在时自动建
    theme = sys.argv[3] if len(sys.argv) > 3 else "fresh"
    out.write_text(render(data, theme), encoding="utf-8")
    size = len(out.read_text(encoding="utf-8").encode("utf-8"))
    n = sum(len(s["activities"]) for s in data["sections"])
    print(f"OK  {out}  {size/1024:.1f} KB  {n} 条活动")


if __name__ == "__main__":
    main()
