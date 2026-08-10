# Changelog

所有显著变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)（小版本递增，未成熟不逼近 1.0）。

## [0.1.2] - 2026-08-11

本仓库由 `ai-taste-scanner`（AI 味扫描器）更名重构而来：AI 味检测保留为 D5 维度，新增 D1-D4 与 D6，从"检测 AI 味"扩展为"中文写作质量全维度把关"。

### 新增（优化器能力，吸收 qu-ai-wei 方法论）
- 人味门检 human_gate：改写前判真人文本，真人停手不改声口
- 语体识别 register_of：8 种语体，避免学术/公文误改口语
- refine() 闭环：人味门检 → 两层检测 → 复检，输出 improvement 对比
- 定位升级：检测器 → 优化器（检测→改写→复检）
- 六维检测：D1 错字/异形词 / D2 标点(GB/T 15834) / D3 语病 / D4 数字(GB/T 15835) / D5 去AI味 / D6 活人感
- `--json` 结构化输出（可被 CI 消费）

### 变更（方法论升级 + 语言体系重构，能力不变）
- 方法论升级：三线六维 → **两层四维**（L1 语言层客观必改 / L2 表达层主观建议），决策性质作为唯一分类轴
- 语言体系：两层四维叙述，保留 `layer: D1-D6` 兼容
- 术语重构：门检→人味门检(human_gate)、语体识别→register_of、optimize→refine
- JSON 新增 `tiers` 两层汇总字段（纯增量，不破坏既有字段与 CI 解析；`lines` 三线向后兼容）
- 代码极简重构：删死代码 `_scan_dimension`、抽统一收集 `_collect`、修语体数注释 9→8、CONNECTIVES 去重
- 圈复杂度重构（CodeAgent 审查发现）：`scan()` 拆为 6 个维度扫描函数 + `_summarize` 汇总，圈复杂度 39→0；D5 抽 `_scan_wordlist` 通用词表扫描
- 技术：纯 Python 标准库，零第三方依赖；GitHub Actions 测试工作流（main + PR 触发）
- 合规补声明：NOTICE + LICENSE.quaiwei + README 致谢，补 qu-ai-wei 派生来源（此前遗漏）
