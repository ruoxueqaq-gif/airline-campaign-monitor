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

关注出发地：上海、杭州、北京、广州、深圳、厦门。关注目的地区域：日本、东南亚、澳大利亚、新西兰、欧洲。所有活动都会保存关注度和命中的地区；AirAsia 与 Scoot 对指定中国出发连接市场额外标记为高关注。

## 工作方式

- 每家航司一个独立 adapter；一个来源失败不会阻塞其他航司。
- HTTP 请求配置 User-Agent、连接/读取 timeout，以及针对 429/5xx 的重试退避。
- 解析活动卡片的标题、链接、摘要、购票期、旅行期和关注地区，不使用整页 HTML hash。
- 只接受对应航空公司的官方域名链接。
- 状态保存在 `data/campaigns.json`。内容完全不变时不会重写文件，因此 GitHub Actions 不会产生空提交。
- 某活动连续两次在**成功抓取**的同一航司页面中消失后才标记 `EXPIRED`，降低官网短暂缺块导致的误报。
- 第一次运行只保存 baseline；第二次起有变化才生成 `runtime/change.md` 并创建 GitHub Issue。

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

运行顺序：抓取 → 更新 state → state 有变化才 commit/push → 有 NEW/UPDATED/EXPIRED 才创建 Issue。首次 baseline 会提交 state，但不会创建 Issue。

## 状态与变化判定

活动 ID 使用“航空公司 + 规范化官方 URL”，因此同一页面修改标题、摘要、购票期、旅行期或关注地区时会得到 `UPDATED`，新 URL 是 `NEW`。连续两次缺失后是 `EXPIRED`；抓取失败的航司不会累计缺失次数。

## 已知限制

官网会改版或启用反爬规则。当前实现坚持 requests + HTML，不引入 Selenium/Playwright；当某家页面结构变化导致无法提取卡片时，该航司会被隔离为失败并保留旧状态，需要更新对应 adapter 的选择器。动态脚本内才出现、且服务端 HTML 完全没有的促销暂时无法识别。
