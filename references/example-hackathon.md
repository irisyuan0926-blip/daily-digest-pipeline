# 参考实例：黑客松 & AI 活动日报（已跑通）

主题：每天扫国内外黑客松、AI 大会、vibe coding、coffee chat / meetup，产出 55 条，三通道推送。
用途：照抄它的数据结构和自动化 prompt 骨架，换成你自己的主题和信源即可。

## 实例产物
- 在线链接：发布后拿到一个固定网址（发布目录 `web/`，网址固定、每天覆盖）
- 日报归档：`你的目录/YYYY-MM-DD.md`
- 数据：`digest_data_YYYY-MM-DD.json`（55 条，7 个 section）
- 网页渲染 30.4KB，邮件摘要 2.6KB

## 日报结构（7 段，按「紧迫度 + 地理」分，不按信源分）
1. ⏰ 48 小时内截止（最紧急，放最前，css_class `s-red`）
2. 🇨🇳 国内赛事与大会（`s-blue`）
3. 🎤 国内讲座论坛（`s-amber`）
4. 🌍 海外·线上可参与（`s-green`）
5. 🫖 Meetup / Coffee chat（`s-gray`）
6. ✈️ 海外·线下（`s-gray`）
7. ❓ 待核实 + 📌 信源说明

## 条目字段
`title | url | time | format | deadline | fee | highlight | urgent | star | online`
徽章：紧急（带截止时间）/ 主线相关 / 可线上 / 地点。

## 采集架构
- 派**两个子代理并行**：A 扫国内/华语圈，B 扫海外/国际。主代理负责过滤去重与排版。
- 子代理 prompt 里必须带上当天日期 + 网络可达性结论。

### 高命中信源
- 国内：OpenBuild 周报、校园VC《中国黑客松赛事日历》、CompeteHub、HackathonRadar、IT Knowledge Zone、`site:mp.weixin.qq.com 黑客松 2026 报名`、Lu.ma（杭州/上海/深圳）、活动行、互动吧、知乎、天池、各云厂商开发者社区
- 海外：**lablab.ai（线上赛最全）**、mlh.com/events、devpost.com/hackathons、kaggle、DoraHacks、Lu.ma 周报聚合站、Eventbrite、Meetup、forum.cursor.com
- 社区 API：`hn.algolia.com/api/v1/search_by_date?query=<kw>&tags=story&hitsPerPage=30&numericFilters=created_at_i><今日0点UTC时间戳>`；`dev.to/api/articles?tag=<tag>&per_page=30&top=7`
- 已知抓不到：Devpost / Lu.ma 前端渲染（走 `site:` 快照）；小红书正文需登录（只做标题反查）；Reddit / X / Facebook 域名阻断（如实标注）

## 自动化 prompt 骨架（可直接改主题复用）
```
为<用户>生成并推送当天的《<日报名>》。落款署名：<署名>。

## 用户画像（用于精选和标注）
...

## 网络可达性实测结论（亲测，严格遵守，别浪费轮次）
❌ 不可达：...（最多各试 1 次即放弃，并在日报里如实标注）
✅ 可达：...

## 第一步：采集（并行派子代理，不要自己硬扛）
子代理 A —— 国内：信源清单 1..7
子代理 B —— 海外：信源清单 1..5
（把当天日期和可达性结论写进子代理 prompt）

## 第二步：过滤（严格执行）
- 只要当天之后仍可参与的；优先未来 60 天
- 不确定的标「待确认」，不要丢弃
- 每条必须有可点击链接
- 绝对不许编造名称/时间/链接，宁可少列 3 条也不要 1 条假的
- 与上一期去重

## 第三步：产出 + 渲染 + 发布
1. 写 markdown 到 <目录>/YYYY-MM-DD.md（7 段结构）
2. 写 JSON 到 templates/digest_data_YYYY-MM-DD.json
3. 渲染网页：render_web.py <json> web/index.html fresh
4. 校验：取 CSS 中最后一个 --hero: 定义，确认是主题色
5. 发布/更新：workbuddy_sites_deploy（同目录重复发布 = 覆盖，网址不变）
6. 验证：curl 返回 200 且卡片数 == 当天条目数

## 第四步：推送
1. 飞书：精简版写一屏半以内，末尾加完整版链接
2. 邮件：render_email_digest.py 出 2.6KB 摘要，一封搞定；发完核对已发送列表
3. 会话内：present_files 呈现网页版 + md

## 交付要求
3-5 句话说明：新增了哪几条、哪几条紧急、哪几条与主线最相关、各渠道命中与阻断、链接已更新、邮件已发。
```

## 这个实例踩过的坑（具体数值）
- 全量邮件 26KB → 拆成 16.2KB + 13.9KB，**16.2KB 那封用户没收到**（163 拦截）→ 再拆 10.0KB + 9.6KB 才送达
- 最终解法：改「网页全量 + 邮件 2.6KB 摘要」，拆封问题消失
- banner 换色时 CSS 变量顺序写反，主题不生效 → 用「取最后一个 `--hero:`」的正则校验才发现
