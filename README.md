# AI Taste Scanner — AI 味指纹扫描器

> 扫描文本中典型的"AI 味"信号，输出**四层结构化**检查报告（JSON）。用于编辑/写作者/审稿人把关 AI 生成内容，也能当 CI 检查器。

[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

## 检测框架（四层）

### L1 硬性规则（fail，必改）
| 检测 | 内容 |
|------|------|
| 破折号 | `——` / `—` 滥用（AI 头号标志，绝对禁用） |
| 禁用词 | 底层逻辑 / 前所未有 / 赋能 / 闭环 / 长期主义 / 关键抓手 / 价值沉淀 / 认知升级 / 说白了 / 本质上 / 综上所述 / 值得注意的是 / 不难发现 / 不仅仅是... 等 ~31 个黑话+踩雷词 |
| 元语言 | 写在最后 / 结语 / 让我们讨论 / 总而言之 / 在深入探讨之前... |
| 教科书开头 | 在当今时代 / 随着...发展 / 众所周知 / 毋庸置疑... |
| 搜索结果痕迹 | "搜索结果显示" |

### L2 风格一致性（warn）
| 检测 | 内容 |
|------|------|
| 句式指纹 | 不是X而是Y / 从X到Y / 不仅...更是 / 首先其次最后 / 值得注意 |
| 死板动词 | 进行 / 实现 / 达到 / 提升...（主张用有画面感的动词） |
| 空泛工具名 | AI工具 / 某个模型 / 相关技术（应说具体名字） |
| 假想例子 | "比如有一次" / "假设你..."（编造场景） |
| markdown 小标题 | 用口语转场句分段，禁小标题 |
| 句长均匀 | 连续 3 句字数差 <5（匀速句长是 AI 味） |
| 超长段落 | >500 字的段落（缺呼吸感） |
| 连接词密度 | 然而 / 此外 / 同时 / 因此... |
| 括号补充 | 括号夹注过多（内容应揉入正文） |

### L3 内容质量（warn）
| 检测 | 内容 |
|------|------|
| 金句收束密度 | 每段都用短句收金句，过度仪式化 |

### L4 活人感 / 风格指纹（warn + info）
| 检测 | 内容 |
|------|------|
| 结果先行 | 开篇 100 字内应甩出数字/结论，不线性铺陈 |
| 汉字数字 | 用"一万七千多行""八成三"，避免 159,000 书面格式 |
| 结尾短句收束 | 结尾用一句能立住的话，不总结不升华 |
| 自问自答 | 长文关键数据处用自问自答制造对话节奏 |

## 评分

- 每层独立 `passed`（该层无 fail 即通过）
- 严重级：`fail`（必改）/ `warn`（建议）/ `info`（提示）
- 每项带 `suggestion`（修复建议）+ `details`（命中上下文片段）

## 用法

```bash
python ai_taste_scanner.py 你的文档.md
```

输出 JSON 报告：四层问题清单 + 分层评分 + 句长统计。

```json
{
  "file": "doc.md",
  "version": "2.0",
  "total_issues": 11,
  "fail_count": 9,
  "warn_count": 2,
  "passed": false,
  "layers": {"L1": {"passed": false, "issue_count": 9}, ...},
  "issues": [
    {"layer": "L1", "type": "禁用词: 赋能", "count": 1, "severity": "fail", "suggestion": "...", "details": [...]}
  ],
  "stats": {"total_chars": 312, "total_sentences": 8, ...}
}
```

## 自定义规则

词表集中在文件头部 `DISABLED_WORDS` / `META_LANGUAGE` / `TEXTBOOK_OPENERS` / `DEAD_VERBS` / `CONNECTIVES` 等常量，按需增删，适合接入团队写作规范。

## 依赖

纯 Python 标准库（`re`/`json`/`sys`/`pathlib`），零第三方依赖。

## 来源声明 (Acknowledgements)

本工具的 **L1-L4 四层自检体系** 与 **高频踩雷词表** 派生自以下开源作品：

- **卡兹克 khazix-writer skill**（数字生命卡兹克 / Khazix）
- 仓库：https://github.com/KKKKhazix/khazix-skills
- 许可：MIT License（Copyright (c) 2026 数字生命卡兹克）

扫描/分析代码本身为原创，但四层框架与踩雷词表为 khazix-writer 的移植。完整声明见 [NOTICE](NOTICE)，MIT 许可全文见 [LICENSE.khazix](LICENSE.khazix)。

## License

[Apache License 2.0](LICENSE)（原创部分）· [MIT License](LICENSE.khazix)（khazix 派生部分，详见 NOTICE）
