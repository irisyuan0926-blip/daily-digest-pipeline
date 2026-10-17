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

## 事件库（2026-10-16 加，记忆层）

前 22 期的教训：只跟上一期去重 = 复读机。10-08 期 278 条里 177 条（64%）是「上期已收录·简写带过」；22 期累计 62% 内容重复；最毒的活动连登 20 期；501 个已过截止日的事件还在被反复收录。

现在的流程（agent 只写新事件，记忆交给脚本）：
1. 首次 `python3 scripts/events.py backfill` 从历史各期建库（本实例：927 个事件）
2. agent 把新事件写进 `digest_data_YYYY-MM-DD.draft.json`，**不手写持续开放段**
3. `python3 scripts/events.py merge <draft> --date <日期>` → 正式版 json：
   - 库内已有的重复条目自动删除（第 1 段 48h 紧急位或 urgent 的例外保留）
   - 「🔁 持续开放」段自动生成：往期收录 + 仍未结束 + 按截止升序，上限 40
   - 到期事件自动淘汰
4. merge 打印的统计写进日报信源说明段，作为质量信号

配套：`query <关键词>` 查收录历史；`status` 看连登榜 + 信源命中（诊断用）。

这条改造的经验已提炼进 SKILL.md 第 3.5 步和硬规则第 4/7 条——换任何主题都别跳过记忆层。

## 信源效能统计 + 每周复盘（2026-10-16 加，第二层记忆）

事件库管「内容不重复」，信源统计管「渠道不死不烂」：
1. 每期 merge 后 `python3 scripts/sources.py record <draft> --date <日期>`（draft 每条必须带 source 字段）
2. 每周日 20:00 复盘自动化跑 `sources.py stats`：输出 7 日命中排名 + 退役建议
3. 退役 = `sources.py retire <名>` 写进 `retired_sources.md`；采集任务第 0 步读它，名单里的不采——**改名单文件，不改长 prompt**
4. 停摆保护：stats 发现窗口内无采集记录就跳过退役判定（暂停期一切信源假死）

配套实例文件（都在 hackathon-digest/ 根目录）：`interests.md`（兴趣模型，静态画像 + 动态标记 + 脚本生成的动态模型）、`retired_sources.md`（退役名单）、`weekly-review.md`（周报）。

## 兴趣模型（2026-10-16 加）

标记词汇只有 **很感兴趣 / 不感兴趣**（用户 2026-10-16 拍板，替代早期的「有用/无用」）。用户在对话里表态 → agent 跑 `interests.py mark` 记账；周日复盘跑 `interests.py update` 把标记匹配进事件库、重写「动态模型」区；采集时读模型排前/降权。生效词逻辑：品牌拉丁词优先，泛词（黑客松/大赛/活动）禁止当生效词。

## 失败告警 + 推送熔断（2026-10-16 加）

- 采集失败（无 draft / 子代理全败 / 0 条 / 渲染发布失败）→ 邮件 + 飞书独立告警，不混进日报正文
- 推送连续回退旧数据 ≥3 天 → 熔断：停发旧数据，改发一次性告警 + 恢复方法，push-log 记「熔断」
- 邮件发送前校验：渲染产物 >800 字节且含 http 链接，否则中止（10-05 空邮件事故的防线）
