# zh-writing-checker

> 轻量、纯 Python、零依赖的中文写作优化器：**先判人味，再查三线，改完复检**（Gate → Detect → Rewrite → Recheck）。把"AI 腔、机械文"拉回"像人写的"，同时不误伤真人声口。输出结构化 JSON，供写作者、编辑、审稿人使用，也能当 CI 检查器。

## 一句话方法论

**先判人味，再查三线，改完复检。**

改写前先问三个递进的问题：

1. **这是人写的吗？** —— 真人文本停手，只清格式，不动声口（human_gate）
2. **哪里不像人写的？** —— 按三条线检测定位（scan，三线检测）
3. **怎么改得像人？** —— 生成改写建议并复检，确认问题减少（refine）

## 三线检测

六维不是六个并列编号，是三条线。**记住三线，比记住六个编号容易：硬规则 / 文风 / 人味。**
| 线 | 级别 | 维度 | 检测内容 |
|----|------|------|----------|
| **硬规则线** | fail 必改 | 字词 D1 | 常见错别字、异形词（《第一批异形词整理表》）、中英混写 |
| | | 标点 D2 | 中英标点混用、半角标点、英文引号（GB/T 15834） |
| | | 语法 D3 | 成分残缺、搭配不当、句式杂糅、前后矛盾 |
| | | 数字 D4 | 日期格式、范围连接号、中英数字混排（GB/T 15835） |
| **文风线** | warn+fail | 去AI味 D5 | 破折号、禁用词、元语言、教科书开头、句式指纹、死板动词、空泛工具名 |
| **人味线** | warn | 活人感 D6 | 句长均匀（无节奏）、超长段落、连接词密度、结果先行 |

**三线各司其职：**
- **硬规则线**（D1-D4）= 客观对错，无争议，fail 必改。错字、标点、语法、数字，错了就是错了。
- **文风线**（D5）= 风格判断，留余地。去 AI 味是重头，但语言是活的，带豁免语境。
- **人味线**（D6）= 最主观，只给建议。可读性是品味问题，不替作者决定。

> 原则：**严谨 ≠ 僵化**。正确性必改，风格给建议，改写不虚构（只在原文已有细节上打磨），真人文本停手——最终取舍在作者。

## 用法

```bash
python zh_writing_checker.py 你的文档.md          # 人类可读报告（含三线概览）
python zh_writing_checker.py 你的文档.md --json   # 结构化 JSON（适合 CI）
```

人类可读报告示例（三线概览 + 六维明细）：
```
文件: test_sample.md  v0.1.2
问题 29 项 | fail 12 | warn 14 | 通过 False
  ❌ 硬规则线 D1,D2,D3,D4 问题=9 (fail 6)
  ❌ 文风线 D5 问题=19 (fail 6)
  ✅ 人味线 D6 问题=1 (fail 0)
  ❌ [D3] 搭配不当·改善…水平 ×1
  ❌ [D5] 禁用词:赋能 ×1
  ⚠️ [D1] 异形词: 缘份（规范:缘分） ×1
```

JSON 报告结构（`layer: D1-D6` 保持不变，新增 `lines` 三线汇总）：

```json
{
  "file": "doc.md", "version": "0.1.2",
  "total_issues": 29, "fail_count": 12, "passed": false,
  "dimension_counts": {"D1": 2, "D2": 2, "D3": 4, "D4": 1, "D5": 19, "D6": 1},
  "layers": {"D1": {"passed": true, "issue_count": 2, ...}, ...},
  "lines": {"hard": {"dims": ["D1","D2","D3","D4"], "issue_count": 9, "fail_count": 6}, ...},
  "issues": [{"layer": "D3", "type": "搭配不当·改善…水平", "severity": "fail", "suggestion": "...", "details": [...]}],
  "stats": {"total_chars": 1227, "total_sentences": 14}
}
```

## 自定义规则

词表集中在文件头部常量（`COMMON_TYPO_PAIRS` / `VARIANT_WORDS` / `DISABLED_WORDS` / `FAULTY_PATTERNS` / `DEAD_VERBS` 等），按需增删，适合接入团队写作规范。维度归属线在 `_LINE_OF_DIM` 定义，可调整。

## 三种用法

1. **命令行**：对本机文档跑一遍，人类可读或 JSON 报告。
2. **CI 检查器**：在持续集成里加一步，对提交的中文内容自动扫描，fail 问题让流水线失败。
3. **智能体技能**：把工具封装进 agent 工作流，让 agent 改稿前先人味门检、先识别语体，避免把真人稿改得千篇一律。

## 与旧版关系

本仓库由 `ai-taste-scanner`（AI 味扫描器）更名重构而来：AI 味检测保留为 D5 维度，新增 D1-D4 与 D6。当前 v0.1.2（含优化器三步流程 + 三线语言体系）。项目尚未成熟，按小版本递增演进。

## 致谢（Acknowledgements）

本项目在方法框架上借鉴了以下开源作品，声明与许可全文见 [NOTICE](NOTICE)：

- **khazix-writer** skill（数字生命卡兹克，MIT）：D5 文风/去 AI 味维度的检测框架与高频踩雷词表。仓库：https://github.com/KKKKhazix/khazix-skills
- **qu-ai-wei**（@LifelongLazyLearner，MIT）：human_gate 人味门检 与 register_of 语体识别的方法框架。仓库：https://github.com/LifelongLazyLearner/qu-ai-wei

具体规则与扫描代码为原创，仅采用其方法框架。

## License

Apache License 2.0（原创部分）· MIT License（khazix 与 qu-ai-wei 派生部分，详见 NOTICE）。
