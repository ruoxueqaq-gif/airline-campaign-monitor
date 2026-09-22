# airline-campaign-monitor

监控航空公司**官方网页**上的机票促销。首次运行只建立 baseline，不推送当前已有活动；后续以 GitHub Issue 通知 `NEW`、`UPDATED`、`EXPIRED`。

## 监控范围

| 航空公司 | 官方入口 | 重点 |
| --- | --- | --- |
| ANA | <https://www.ana.co.jp/zh/cn/> | 中国大陆出发、日本及远程航线 |
| JAL | <https://www.jal.co.jp/ja-jp/campaign/inter.html> | 国际线活动和特别运价 |
| Vietnam Airlines | <https://www.vietnamairlines.com/zh-cn/> | 中国大陆经越南前往东南亚、澳新、欧洲 |
| AirAsia | <https://newsroom.airasia.com/news> | 中国大陆往返东南亚促销 |
| Scoot | <https://www.flyscoot.com/en/promotions> | 中国大陆经新加坡前往东南亚、澳大利亚 |
| Singapore Airlines | <https://www.singaporeair.com/en_UK/cn/plan-travel/local-promotions/local-promotion-in-china/> | 中国大陆出发的本地促销 |
| Air China | <https://www.airchina.com.cn/cn/> | 中国大陆出发的国际线促销 |

出发地优先级：核心机场为杭州 HGH、上海浦东 PVG、上海虹桥 SHA；次级机场为南京 NKG、宁波 NGB。关注目的地区域为澳大利亚、新西兰、日本、欧洲和东南亚，但**目的地区域单独命中不会提升相关度**。

每条活动保存 `relevance`（`HIGH / MEDIUM / LOW`）、`deal_strength`（`GREAT / GOOD / NORMAL`）、`origin_match`、`destination_match`、是否有明确价格、是否通知和简短判断原因。核心机场出发权重最高，明确价格/促销和核心机场新开、复航、加密航线会加权；境外机场之间的航线新闻、单纯运力扩张和旺季 PR 会降权。

## 工作方式

- 每家航司一个独立 adapter；一个来源失败不会阻塞其他航司。
- HTTP 请求配置 User-Agent、连接/读取 timeout，以及针对 429/5xx 的重试退避。
- 解析活动卡片的标题、链接、摘要、购票期、旅行期和关注地区，不使用整页 HTML hash。
- 只接受对应航空公司的官方域名链接。
- 当前有效活动保存在 `data/campaigns.json`；方便人工查看的中文表格集中在 `data/csv/`。
- `data/csv/my_campaigns.csv` 列出全部有效活动；`data/csv/my_best_deals.csv` 只列 `GREAT` 且属于机票的活动，并按力度排序。`my_` 前缀表示建议优先查看。
- CSV 使用带 BOM 的 UTF-8 编码，可直接用 Excel 打开中文内容；包含航司、标题、出发地、目的地、相关度、优惠力度、是否有明确价格、是否通知、判断原因、购票期、旅行期、链接和摘要。
- JSON 和 CSV 内容完全不变时都不会重写，因此 GitHub Actions 不会产生空提交。
- 某活动连续两次在**成功抓取**的同一航司页面中消失后才标记 `EXPIRED`，降低官网短暂缺块导致的误报。
- 第一次运行只保存 baseline。第二次起所有变化都会进入状态/CSV，但只有 `HIGH`，或带明确价格/促销/核心机场航线变化的 `MEDIUM` 才生成 `runtime/change.md` 并创建 GitHub Issue。
- 抓取超时、403、429、5xx、空响应、配额限制或解析失败只写 Actions 日志；失败航司不累计“消失”次数，也不会触发 Issue。

## 本地运行

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
python -m pip install -e .
python -m airline_campaign_monitor.monitor
```

运行测试：

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

## GitHub Actions

`.github/workflows/monitor.yml` 支持手动 `workflow_dispatch`，并按中国标准时间每天约 `01:20`、`09:20`、`17:20` 运行。工作流需要仓库允许 GitHub Actions 对 contents 和 issues 写入；权限已在 workflow 中声明。

运行顺序：抓取 → 剔除明确过期活动 → 评估相关度和优惠力度 → 更新 JSON、完整 CSV 与精选优惠 CSV → 数据文件有变化才 commit/push → 只有满足通知规则的真实状态变化才创建 Issue。Issue 标题使用 `[ALERT] 航司促销活动更新 - YYYY-MM-DD`，自动添加 `alert` label 并指派给 `ruoxueqaq-gif`。

## 状态与变化判定

活动 ID 使用“航空公司 + 规范化官方 URL”，因此同一页面修改标题、摘要、购票期或旅行期时会得到 `UPDATED`，新 URL 是 `NEW`。评分规则本身的升级只会静默更新派生字段，不会制造内容变化 Issue。连续两次缺失后是 `EXPIRED`；抓取失败的航司不会累计缺失次数。同一条未再次发生内容变化的新闻不会重复通知。

## 已知限制

官网会改版或启用反爬规则。当前实现坚持 requests + HTML，不引入 Selenium/Playwright；当某家页面结构变化导致无法提取卡片时，该航司会被隔离为失败并保留旧状态，需要更新对应 adapter 的选择器。动态脚本内才出现、且服务端 HTML 完全没有的促销暂时无法识别。
