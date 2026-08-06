# AI Taste Scanner — AI 味指纹扫描器

> 扫描文本中典型的"AI 味"信号，输出结构化 JSON 检查报告。用于编辑/写作者/审稿人把关 AI 生成内容，也能当 CI 检查器。

[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

## 检测项

| 类别 | 检测内容 | 严重级 |
|------|----------|--------|
| 破折号 | `——` / `—` 滥用 | fail |
| 禁用词 | 底层逻辑 / 前所未有 / 毋庸置疑 / 赋能 / 闭环 / 长期主义 / 关键抓手 / 深度链接 / 价值沉淀 / 认知升级 / 图景 | fail |
| 句式 | "不仅仅是" / "不只是" | warn |
| 元语言 | 值得注意的是 / 事实上 / 换言之 / 写在最后 / 结语 / 总而言之 | fail |
| 句长方差 | 连续 3 句字数差 <5（句式过于均匀） | warn |
| 括号补充 | 括号夹注过多 | warn |
| 搜索结果痕迹 | 出现"搜索结果显示" | fail |

评分：`fail_count == 0` 才算通过。禁用词/元语言/破折号是硬伤，句长方差和括号是风格提示。

## 用法

```bash
python ai_taste_scanner.py 你的文档.md
```

输出 JSON 报告：问题清单 + 每项次数/严重级 + 句长统计 + 是否通过。

```json
{
  "file": "doc.md",
  "total_issues": 10,
  "fail_count": 9,
  "passed": false,
  "issues": [
    {"type": "禁用词: 赋能", "count": 1, "severity": "fail"},
    {"type": "破折号", "count": 3, "severity": "fail"}
  ],
  "stats": {"total_sentences": 42, "avg_length": 18.2, "min_length": 4, "max_length": 36}
}
```

## 扩展自定义词表

`DISABLED_WORDS` 和 `META_LANGUAGE` 两个列表在文件头部，按需增删。适合接入团队写作规范。

## 依赖

纯 Python 标准库（`re`/`json`/`sys`/`pathlib`），零第三方依赖。

## License

[Apache License 2.0](LICENSE)
