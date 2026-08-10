# zh-writing-checker — 中文写作优化器

> 轻量纯 Python 零依赖的中文写作质量优化工具。**检测 → 改写 → 复检** 闭环：先定位 AI 味与质量问题（六维检测），再按场景风格改写，最后复检确认。严谨性（错字/标点/语病/数字）+ 文风（去AI味）+ 活人感。输出结构化 JSON 报告。用于编辑/写作者/审稿人，也能当 CI 检查器。

> **定位**：不是报问题的检测器，是**把稿子改得像人写的优化器**。检测是为了定位，改写是为了解决，复检是为了确认。

[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

## 核心原则

**严谨 ≠ 僵化，只标记不替作者决定；改写不虚构，打磨只在原文已有细节上。**
- **正确性（D2/D3）= fail 必改**，客观无争议（标点规范、语法语病）
- **风格（D1/D4/D5/D6）= warn 建议**，带豁免语境，避免把文字改得千篇一律
- **改写前先判语体与"是否真人文本"**：真人声口不改，学术/公文不误改口语
- 工具只报问题 + 给建议 + 可选改写，最终取舍在作者——保活人感

## 六维检测

| # | 维度 | 级别 | 检测内容 |
|---|------|------|----------|
| **D1** | 错字/错词 | warn | 常见错别字对（寒喧/幅射/决窍…）、异形词规范（《第一批异形词整理表》缘份→缘分/澈底→彻底…）、中英混写 |
| **D2** | 标点规范 | **fail** | 中英标点混用、半角标点、英文引号（GB/T 15834） |
| **D3** | 语法语病 | **fail** | 成分残缺（通过…使）、搭配不当（改善…水平）、句式杂糅（因为…原因）、前后矛盾（大约…左右） |
| **D4** | 数字规范 | warn | 日期格式、范围连接号、中英数字混排（GB/T 15835） |
| **D5** | 文风/去AI味 | warn+fail | 破折号、禁用词（赋能/闭环/底层逻辑…）、元语言、教科书开头、句式指纹、死板动词、空泛工具名 |
| **D6** | 活人感/可读 | warn | 句长均匀（无节奏）、超长段落、连接词密度、结果先行 |

## 用法

```bash
python zh_writing_checker.py 你的文档.md          # 人类可读报告
python zh_writing_checker.py 你的文档.md --json   # 结构化 JSON（适合 CI）
```

示例输出（人类可读）：

```
文件: test_sample.md  v0.1.0
问题 29 项 | fail 12 | warn 14 | 通过 False
  ❌ D3 通过=False 问题=4 (fail 4/warn 0)
  ❌ D5 通过=False 问题=19 (fail 6/warn 10)
  ❌ [D3] 搭配不当·改善…水平 ×1
  ❌ [D5] 禁用词:赋能 ×1
  ⚠️ [D1] 异形词: 缘份（规范:缘分） ×1
```

JSON 报告结构：

```json
{
  "file": "doc.md", "version": "0.1.0",
  "total_issues": 29, "fail_count": 12, "passed": false,
  "dimension_counts": {"D1": 2, "D2": 2, "D3": 4, "D4": 1, "D5": 19, "D6": 1},
  "layers": {"D1": {"passed": true, "issue_count": 2, ...}, ...},
  "issues": [{"layer": "D3", "type": "搭配不当·改善…水平", "severity": "fail", "suggestion": "...", "details": [...]}],
  "stats": {"total_chars": 1227, "total_sentences": 14}
}
```

## 自定义规则

词表集中在文件头部常量（`COMMON_TYPO_PAIRS` / `VARIANT_WORDS` / `DISABLED_WORDS` / `FAULTY_PATTERNS` / `DEAD_VERBS` 等），按需增删，适合接入团队写作规范。

## 与旧版关系

本仓库由 `ai-taste-scanner`（AI 味扫描器）更名重构而来：**AI 味检测保留为 D5 维度**，新增 D1-D4（错字/标点/语病/数字）与 D6（活人感），从"检测 AI 味"扩展为"中文写作质量全维度把关"。

> **版本说明**：当前为 v0.1.0（更名重构后的首个发布），项目未成熟、生态未建，按小版本递增演进，不虚标大版本。

## 来源声明 (Acknowledgements)

**D5 文风/去AI味维度**的检测框架与高频踩雷词表派生自以下开源作品：
- **卡兹克 khazix-writer skill**（数字生命卡兹克 / Khazix）
- 仓库：https://github.com/KKKKhazix/khazix-skills
- 许可：MIT License（Copyright (c) 2026 数字生命卡兹克）

D1-D4、D6 的检测规则与扫描代码为原创。完整声明见 [NOTICE](NOTICE)，MIT 许可全文见 [LICENSE.khazix](LICENSE.khazix)。

## License

[Apache License 2.0](LICENSE)（原创部分）· [MIT License](LICENSE.khazix)（khazix 派生部分，仅 D5 维度，详见 NOTICE）
