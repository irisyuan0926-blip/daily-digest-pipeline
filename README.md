# daily-digest-pipeline · 每日情报日报流水线

把「每天定时采集某个主题的情报 → 渲染成可筛选网页 → 发布到固定在线链接 → 邮件 / IM 只发摘要 + 链接」这条链路跑通。

**核心架构：内容全量放网页，通知只发摘要 + 链接。**

主题无关——黑客松与活动、岗位招聘、竞品动态、论文速递、行业资讯、开源项目周报，换信源和字段就能跑。

---

## 为什么不能把内容全塞进邮件

| 问题 | 全量进邮件 | 全量上网页 + 通知发摘要 |
|---|---|---|
| 邮件体积 | 55 条约 26KB，必须拆 3 封 | 邮件 2.6KB，**永远一封** |
| 送达率 | 163 对 >10KB 多外链 HTML 会**静默拦截**（发出≠收到） | 小巧纯文本为主，稳定送达 |
| 排版能力 | 邮件客户端只认 inline CSS，无交互 | 网页可筛选、可点击、响应式 |
| 信息完整性 | 为了塞得下往往被迫删减 | **零删减**，全在网页 |

代价只是多一次点击。**减少阅读障碍靠清晰表达和分层，不是缩减信息。**

---

## 5 分钟上手

### 0. 安装

仓库：<https://github.com/irisyuan0926-blip/daily-digest-pipeline>

把整个目录放进你的 skills 目录即可，无需 pip 安装、无第三方依赖（只用 Python 标准库）。

```bash
# WorkBuddy 用户级（所有项目可用）—— 二选一
git clone https://github.com/irisyuan0926-blip/daily-digest-pipeline.git ~/.workbuddy/skills/daily-digest-pipeline
# 或下载后手动拷：cp -r daily-digest-pipeline ~/.workbuddy/skills/
```

要求：**Python 3.7+**，无其他依赖。

### 1. 抄一份数据模板，改成你自己的内容

```bash
cd daily-digest-pipeline
cp scripts/digest_template.json my_data.json
```

模板里只有 2 条示例数据，字段含义一眼能看明白：

```jsonc
{
  "date": "2026-09-03", "issue": "001",
  "title": "XX 日报", "subtitle": "每日精选", "byline": "署名",
  "urgent_label": "48 小时内截止",        // 邮件里紧急清单的小标题
  "filters": [{"key": "urgent", "label": "紧急"}, {"key": "online", "label": "可线上"}],
  "stats":   [{"key": "urgent", "label": "紧急"}, {"key": "online", "label": "可线上"}],
  "sections": [{"icon": "⏰", "title": "48 小时内截止", "css_class": "s-red",
                "activities": [{"title": "...", "url": "...", "time": "...", "format": "...",
                                "deadline": "...", "fee": "...", "highlight": "...",
                                "urgent": true, "online": false}]}],
  "unverified": ["待核实项"],
  "sources": {"covered": "已覆盖信源", "gaps": ["缺口 / 阻断说明"]}
}
```

- `css_class` 取 `s-red` / `s-blue` / `s-green` / `s-amber` / `s-gray`，控制段落标题色
- `filters` / `stats` 的 `key` 对应条目上的布尔字段（`urgent` / `star` / `online` / 自定义）
- 地点徽章用条目的 `location` 字段触发，如 `"location": "杭州"`
- 每个条目必须有真实链接；`highlight` 写「为什么值得看」，不要复述标题

### 2. 渲染网页版，浏览器打开看效果

```bash
python3 scripts/render_web.py my_data.json web/index.html fresh
open web/index.html
```

第 4 个参数是主题，省略默认 `fresh`：

| 主题 | 效果 |
|---|---|
| `fresh` | **默认**。只把顶部 banner 换成清新渐变，正文保持中性配色 |
| `mint` / `sky` / `warm` | 整页换色：薄荷青 / 晴空白蓝 / 暖阳米白 |

网页自带：顶部统计块、按标签筛选、段落计数、点击标题直达、移动端自适应。

### 3. 渲染邮件摘要

```bash
python3 scripts/render_email_digest.py my_data.json out.html "https://<你的网页链接>"
```

产出约 2.6KB：渐变 banner 头 + 统计块 + 紧急清单（默认 ≤5 条，第 4 个参数可改上限）+ 大按钮跳完整版 + 明文地址兜底。

**末尾必须保留明文网址**——按钮在部分邮件客户端会失效。

---

## 想让它每天自动跑？

三步：发布网页 → 配推送通道 → 建定时任务。

**发布在线链接**：用 `workbuddy_sites_deploy`（`language: static`，目录指向 `web/`）。同一目录重复发布 = 覆盖内容、**网址不变**，不要新建目录、不要 unpublish。发布后验证：

```bash
curl -s -o /tmp/d.html -w "%{http_code}" --noproxy '*' <你的网址>   # 必须是 200
grep -o 'class="card' /tmp/d.html | wc -l                          # 应等于当天条目数
```

**推送通道**：邮箱 / 飞书 / 企业微信 / 仅会话内，至少一个即可，没有哪个就降级，不影响其余链路。详见 `references/setup.md`。

**建定时任务**：新建一个每日自动化（如每天 19:00），把「采集 → 过滤 → 写 JSON → 渲染 → 发布 → 推送」写进 prompt。可直接改的 prompt 骨架在 `references/example-hackathon.md`。

---

## 目录

| 路径 | 说明 |
|---|---|
| `SKILL.md` | 五步流程 + 6 条硬规则（AI 读这份） |
| `README.md` | 本文件（人读这份） |
| `scripts/render_web.py` | 网页渲染器 |
| `scripts/render_email_digest.py` | 邮件摘要渲染器 |
| `scripts/digest_template.json` | 数据格式最小示例 |
| `examples/preview-web.html` | **产出长什么样**：55 条真实数据的网页版样例 |
| `examples/preview-email.html` | 对应的 2.5KB 邮件摘要样例 |
| `references/pitfalls.md` | 完整踩坑与排查路径 |
| `references/setup.md` | 首次搭建清单、通道选择与降级方案 |
| `references/example-hackathon.md` | 完整实例 + 可直接复用的自动化 prompt 骨架 |

---

## 换成别的主题要改什么

本 skill 是**流程骨架**，主题无关。改三处：

1. `digest_template.json` 里的 `sections`（段落划分）与 `filters` / `stats`（筛选与统计维度）
2. 采集阶段的信源清单（先做连通性测试，见 `references/setup.md`）
3. 自动化 prompt 里的用户画像与收录标准

---

## 三条不能破的规矩

1. **绝不编造**名称、时间、链接。宁可少列 3 条，也不要 1 条假的。
2. **抓不到的信源如实标缺口**，不许静默略过或编内容填充。
3. **内容不许删减**。觉得太长就靠分段、筛选、徽章、导航解决。

---

## 已知坑（速查，完整版见 `references/pitfalls.md`）

- 邮件服务商体积门槛：163 实测 **>10KB 静默拦截**，安全线按 10KB 走
- `queued: true` 只代表服务端受理，**不代表用户收到**
- Agent Mail 的 `to` 必须是**数组** `[{"email": "...", "name": "..."}]`，写成对象/字符串报 schema 错
- 把 >20KB 的 HTML 当工具参数输出会**整段丢失**——这正是要用「摘要 + 链接」的原因之一
- CSS 变量主题：style 里**基础样式在前、主题在后**，反了会被默认值盖回去

---

## 分享

整个目录压缩或推 GitHub 即可，对方丢进自己的 `~/.workbuddy/skills/` 就能用。

脚本只做本地 HTML 渲染：不联网、不删文件、不执行外部命令。
