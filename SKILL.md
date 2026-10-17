---
name: daily-digest-pipeline
description: "把「每天定时采集某个主题的情报 → 渲染成可筛选网页 → 发布到固定在线链接 → 邮件 / IM 只发摘要 + 链接」这条流水线跑通。适合搭建每日日报并自动推送：黑客松与活动、岗位招聘、竞品动态、论文速递、行业资讯、AI 活动、开源项目等。触发词：每日日报、每天推送、定时简报、daily digest、情报简报、做个日报自动化、每天发我一份。"
agent_created: true
---

# 每日情报日报流水线

一套可复用的日报自动化架构：**内容全量放网页，通知只发摘要 + 链接**。

## 为什么是这个架构（核心设计，别改回全量邮件）

把几十上百条内容直接塞进邮件，会同时撞上三堵墙：

| 问题 | 全量进邮件 | 全量上网页 + 通知发摘要 |
|---|---|---|
| 邮件体积 | 55 条约 26KB，必须拆 3 封，拆封还可能被拦截 | 邮件 2.6KB，**永远一封** |
| 送达率 | 163 对 >10KB 多外链 HTML 会静默拦截（发出≠收到） | 小巧纯文本为主，稳定送达 |
| 排版能力 | 邮件客户端只认 inline CSS，无交互 | 网页可筛选、可点击、响应式，手机电脑都能看 |
| 信息完整性 | 为了塞得下往往被迫删减 | **零删减**，全在网页 |

代价只是多一次点击。**原则：减少阅读障碍靠清晰表达和分层，不是缩减信息。**

## 五步流程

### 1. Config —— 首次搭建，先问清这 6 件事
不要边做边猜，一次性问完（用户没答的给合理默认并注明）：
1. **主题与范围**：日报讲什么？什么算「值得收录」？
2. **信源清单**：优先哪些站点/API/社区？先跑一次**网络可达性测试**再定（见第 3 步）
3. **推送时间**：默认每天 19:00
4. **通知通道**：至少选一个（邮箱 / 飞书 / 企业微信 / 仅会话内），记下收件地址或 user_id
5. **是否发布在线链接**：发布后网址固定、每天覆盖更新；不选就只在本地/会话内看
6. **署名与期号**：日报末尾落款

### 2. Collect —— 并行采集
派**多个子代理并行**检索（如国内 / 海外各一个），把「当天日期 + 网络可达性结论」写进每个子代理的 prompt，避免它们各自重复踩墙。
主代理负责：过滤、去重（与上一期比对）、判断是否值得收录、标注不确定项。

### 3. Structure —— 落成 JSON，不要直接写 HTML
数据一律先进 `digest_data_YYYY-MM-DD.json`（格式见 `scripts/digest_template.json`），再由脚本渲染。
好处：改数据不动渲染器；同一份数据可同时产出网页版和邮件版。

**只写新事件**——往期仍有效的不手抄，交给第 3.5 步的事件库。

```json
{
  "date": "2026-09-03", "issue": "001",
  "title": "XX 日报", "subtitle": "每日精选", "byline": "署名",
  "urgent_label": "48 小时内截止",          // 邮件里紧急清单的小标题
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
- `filters` / `stats` 的 `key` 对应 activity 上的布尔字段，缺省回退到 `urgent / star / online`
- 每个条目必须有真实链接；`highlight` 写「为什么值得看」，不要复述标题

### 3.5 Memory —— 事件库：跨期去重 + 「持续开放」段生成
```bash
# 首次：从历史各期建库（之后每期 merge 自动维护，不用再跑）
python3 scripts/events.py backfill

# 每期：agent 先把新事件写成 draft，再合并出正式版
python3 scripts/events.py merge digest_data_YYYY-MM-DD.draft.json --date YYYY-MM-DD
```
- agent 的 draft **只放新事件**；已在库里的重复条目由脚本自动删除（老活动进最后 48 小时的例外：第 1 段或 `urgent=true` 的重复保留原位）
- 「🔁 持续开放」段由脚本从库里生成：往期收录、仍未结束、按截止日期升序，上限 40 个——**这段不许手写**（手抄往期 = 复读机，实测 22 期 62% 内容重复）
- 到期活动自动淘汰，不再反复出现
- merge 打印的「去重删除 N 条」是质量信号，写进日报信源说明段
- 配套子命令：`query <关键词>` 查某活动是否已收录；`status` 看库统计 + 连登榜 + 信源命中（诊断用）

### 3.6 Sources —— 信源效能统计（让「零命中退役」规则真的执行）
写死在 prompt 里的「某信源连续 3 天零命中建议下线」如果没有数据支撑就是死规则。用 `scripts/sources.py` 把命中数落成 json：
```bash
python3 scripts/sources.py backfill                 # 首次：从历史各期重建
python3 scripts/sources.py record <draft.json> --date YYYY-MM-DD   # 每期 merge 后记一笔
python3 scripts/sources.py stats                    # 命中排名 + 退役建议
python3 scripts/sources.py retire <信源名> --reason "..."          # 写入 retired_sources.md
```
- 采集前先读 `retired_sources.md`，列在里面的一律不采（agent 不用改 prompt，改名单文件）
- **停摆保护**：stats 发现最近一个窗口无任何采集记录时，跳过退役判定——暂停期间一切信源都会「假死」
- 退役动作放在**每周复盘**里做（见下），不要每期跑

### 3.7 Interests —— 兴趣模型动态更新
收录排序从静态画像变动态：用户标「很感兴趣 / 不感兴趣」（**词汇只有这两种，不要发明「有用/无用」**），每周复盘把标记匹配进事件库，生成加分/减分关键词。
- `interests.py mark <很感兴趣|不感兴趣> <内容>` 记标记；`interests.py update` 重算模型；采集时读「动态模型」区排前/降权
- 长关键词自动拆「生效词」（品牌拉丁词优先，「黑客松/大赛」这类泛词禁止当生效词——命中一切 = 没有信息量）
- 标记区为空时，周复盘从最近几期挑 ⭐ 和 48h 紧急条目请用户标——**人标一次，机器学一期**

### 4. Render + Publish —— 渲染网页并发布
```bash
# 网页版（默认 fresh 主题：只换顶部 banner 为清新渐变，正文保持中性配色）
python3 scripts/render_web.py digest_data_YYYY-MM-DD.json web/index.html fresh

# 发布 / 更新（同一目录重复发布 = 覆盖内容、网址不变，不要新建目录、不要 unpublish）
#   工具：workbuddy_sites_deploy，参数 language=static，目录指向 web/
# 发布后验证
curl -s -o /tmp/d.html -w "%{http_code}" --noproxy '*' <你的网址>          # 必须 200
grep -o 'class="card' /tmp/d.html | wc -l                                   # 应等于当天条目数
```
网页自带的交互：顶部统计、按标签筛选、段落计数、点击标题直达、移动端自适应。

### 5. Notify —— 三通道推送摘要
```bash
# 邮件：单封 ≈2.6KB 摘要（banner 头 + 统计 + 紧急清单 ≤5 条 + 大按钮 + 网址兜底）
python3 scripts/render_email_digest.py digest_data_YYYY-MM-DD.json out.html "<网页链接>"
```
- **邮件 / IM 末尾必须附网页地址**（按钮可能在某些客户端失效，明文地址是兜底）
- 发完用服务端列表核对「已发出」；但**发出 ≠ 收到**，用户说没收到就直接排查体积，不要争辩
- **推送熔断**：今天的 json 不存在时，先数 push-log 里连续「回退」天数，≥3 天就停发旧数据、改发一次性告警；<3 天照常发但标注「⚠️ 旧数据」
- **发送前校验正文非空**（>800 字节且含链接），空邮件/占位符邮件不许出闸

## 硬规则（写进自动化 prompt 里）

1. **绝不编造**名称、时间、链接。宁可少列 3 条，也不要 1 条假的。链接必须是检索结果里真实出现过的。
2. **抓不到的信源如实标缺口**（如「Reddit / X 域名阻断，本环境无法覆盖」），不许静默略过或编内容填充。
3. **先测网络可达性再定信源**。每个域名最多试 1 次，失败即在日报里标注，不要反复重试烧时间。
4. **与历史去重靠事件库**（第 3.5 步），不要凭记忆手抄往期条目。
5. **内容不许删减**。觉得太长就靠分段、筛选、徽章、导航解决。
6. 信源退役靠数据不靠感觉：`sources.py record` 每期记账，周复盘按窗口命中数退役，停摆期不判退役。
7. **诊断必须落盘**：发现系统性问题（信源失效 / 时区错位 / 结构缺陷）写进 `diagnostics.md` 并给出具体修改建议——只写在日报正文里等于没人执行。这条是拿 8 天停摆换来的。
8. **失败必须告警**：采集产出为空 / 渲染发布失败，走推送通道发独立告警（邮件 + IM），不混进日报正文、不静默结束。
9. **推送要熔断**：连续回退旧数据 ≥3 天就停止推送，改发一次性告警。每日骚扰比断更难受。
10. 兴趣标记词汇只有 **很感兴趣 / 不感兴趣** 两种；标记原文进「动态标记」区，模型由脚本生成，不手改。

## 踩坑清单（血泪版，详见 `references/pitfalls.md`）
- 邮件服务商体积门槛：163 实测 **>10KB 静默拦截**，安全线按 10KB 走
- `queued: true` 只代表服务端受理，**不代表用户收到**
- Agent Mail 的 `to` 必须是**数组** `[{"email": "...", "name": "..."}]`，写成对象/字符串报 schema 错
- 把 >20KB 的 HTML 当工具参数输出会**整段丢失**——这正是要用「摘要 + 链接」的原因之一
- CSS 变量主题：style 里**基础样式在前、主题在后**，反了会被默认值的 `:root` 盖回去

## 目录
- `README.md` — 给人看的安装与 5 分钟上手（对外分享时先看这份）
- `scripts/render_web.py` — 网页渲染器，主题 `fresh`（默认，只换 banner）/`mint`/`sky`/`warm`（整页换色）
- `scripts/render_email_digest.py` — 邮件摘要渲染器
- `scripts/digest_template.json` — 数据格式最小示例（2 条，可直接改）
- `scripts/events.py` — 事件库（跨期去重 / 持续开放段生成 / 到期淘汰），子命令 `backfill` / `merge` / `query` / `status`
- `scripts/sources.py` — 信源效能统计（命中记账 / 退役建议 / 退役名单），子命令 `backfill` / `record` / `stats` / `retire`
- `scripts/interests.py` — 兴趣模型（标记 / 生效词匹配 / 模型重算），子命令 `mark` / `update` / `show`
- `examples/preview-web.html` — **产出长什么样**：55 条真实数据的网页版样例，打开即看
- `examples/preview-email.html` — 对应的 2.5KB 邮件摘要样例
- `references/pitfalls.md` — 完整踩坑与排查路径
- `references/setup.md` — 首次搭建清单、通道选择与降级方案
- `references/example-hackathon.md` — 完整实例：黑客松 & AI 活动日报（含自动化 prompt 骨架）

## 改主题（换主题不是换配色文件）
本 skill 是**流程骨架**，主题无关。换成招聘、竞品、论文、开源项目，改三处即可：
1. `digest_template.json` 里的 `sections`（段落划分）与 `filters` / `stats`（筛选与统计维度）
2. 采集阶段的信源清单（见 `references/setup.md` 的连通性测试）
3. 自动化 prompt 里的用户画像与收录标准

地点类徽章用条目的 `location` 字段（如 `"location": "杭州"`）触发。
