# Changelog

所有显著变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)（小版本递增，未成熟不逼近 1.0）。

## [0.1.2] - 2026-08-11

### 新增（优化器能力，吸收 qu-ai-wei 方法论）
- 人味门检 human_gate：改写前判真人文本，真人停手不改声口
- 语体识别 register_of：8 种语体，避免学术/公文误改口语
- refine() 闭环：人味门检 → 三线检测 → 复检，输出 improvement 对比
- 定位升级：检测器 → 优化器（检测→改写→复检）

### 变更（方法论语体系重构，能力不变）
- 语言体系：D1-D6 编号 → 三线（硬规则/文风/人味）叙述，保留 `layer: D1-D6` 兼容
- 术语重构：门检→人味门检(human_gate)、语体识别→register_of、optimize→refine、六维→三线检测
- JSON 新增 `lines` 三线汇总字段（纯增量，不破坏既有字段与 CI 解析）
- 代码极简重构：删死代码 `_scan_dimension`、抽统一收集 `_collect`、修语体数注释 9→8、CONNECTIVES 去重
- 圈复杂度重构（CodeAgent 审查发现）：`scan()` 拆为 6 个维度扫描函数 + `_summarize` 汇总，圈复杂度 39→0；D5 抽 `_scan_wordlist` 通用词表扫描
- 合规补声明：NOTICE + LICENSE.quaiwei + README 致谢，补 qu-ai-wei 派生来源（此前遗漏）

## [0.1.0] - 2026-08-11

### 变更
- 从 `ai-taste-scanner` 更名重构为 `zh-writing-checker`，版本降为 0.1.0（诚实定位：未成熟、无生态，不虚标大版本）
- 六维检测框架定型：D1 错字 / D2 标点(fail) / D3 语病(fail) / D4 数字 / D5 去AI味 / D6 活人感
- 保留 AI 味检测为 D5 维度（从 AI 味扫描器继承）

### 新增
- D1 错字/异形词：19 组常见错别字 + 20 组异形词（《第一批异形词整理表》）
- D2 标点规范：半角标点 / 中英混用 / 英文引号夹中文（GB/T 15834）
- D3 语法语病：11 种病句模式（成分残缺/搭配不当/句式杂糅/前后矛盾）
- D4 数字规范：日期格式 / 范围连接号 / 中英数字混排（GB/T 15835）
- D5 去AI味：27 禁用词 / 元语言 / 教科书开头 / 句式指纹 / 死板动词 / 破折号
- D6 活人感：句长均匀 / 超长段落 / 连接词密度 / 结果先行
- `--json` 结构化输出（可被 CI 消费）

### 技术
- 纯 Python 标准库，零第三方依赖
- 上下文抓取 `_contexts()`、代码块跳过 `_strip_code_blocks()`、severity 三级（fail/warn/info）
- GitHub Actions 测试工作流（main + PR 触发）

## [旧版] ai-taste-scanner（前身）

> 更名前的独立仓库，历史版本不在此记录。

### 2.0 (2026-08)
- 四层检测框架（L1 硬性 / L2 风格 / L3 内容 / L4 活人感）

### 1.0 (init)
- AI 味指纹扫描器（Apache-2.0）
