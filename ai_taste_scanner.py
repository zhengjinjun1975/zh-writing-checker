"""
AI味指纹扫描脚本
输入 .md 文件路径，输出检查报告（JSON）
"""
import re
import json
import sys
from pathlib import Path


DISABLED_WORDS = [
    "底层逻辑", "前所未有", "毋庸置疑", "赋能", "闭环", "长期主义",
    "关键抓手", "深度链接", "价值沉淀", "认知升级", "图景",
]

META_LANGUAGE = [
    "值得注意的是", "事实上", "换言之", "写在最后", "结语",
    "今天我们来谈", "最后我必须", "回到最初的问题", "总而言之",
]


def scan(filepath: str) -> dict:
    text = Path(filepath).read_text(encoding="utf-8")
    lines = text.split("\n")

    issues = []

    # 1. 破折号
    dashes = len(re.findall(r"——|—", text))
    if dashes:
        issues.append({"type": "破折号", "count": dashes, "severity": "fail"})

    # 2. 禁用词
    for word in DISABLED_WORDS:
        count = text.count(word)
        if count:
            issues.append({"type": f"禁用词: {word}", "count": count, "severity": "fail"})

    # 3. 句式
    for pattern in ["不仅仅是", "不只是"]:
        count = text.count(pattern)
        if count:
            issues.append({"type": f"句式: {pattern}", "count": count, "severity": "warn"})

    # 4. 元语言
    for word in META_LANGUAGE:
        count = text.count(word)
        if count:
            issues.append({"type": f"元语言: {word}", "count": count, "severity": "fail"})

    # 5. 句长统计
    sentences = re.split(r"[。！？\n]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
    lengths = [len(s) for s in sentences]

    uniform_groups = []
    for i in range(len(lengths) - 2):
        if abs(lengths[i] - lengths[i+1]) < 5 and abs(lengths[i+1] - lengths[i+2]) < 5:
            uniform_groups.append((i+1, lengths[i], lengths[i+1], lengths[i+2]))

    if uniform_groups:
        issues.append({
            "type": "句长均匀（连续3句字数差<5）",
            "count": len(uniform_groups),
            "details": [f"第{g[0]}-{g[0]+2}句: {g[1]}/{g[2]}/{g[3]}字" for g in uniform_groups[:5]],
            "severity": "warn",
        })

    # 6. 括号补充
    parens = len(re.findall(r"（[^）]+）", text))
    if parens:
        issues.append({"type": "括号补充", "count": parens, "severity": "warn"})

    # 7. 搜索结果痕迹
    search_trace = "搜索结果显示" in text
    if search_trace:
        issues.append({"type": "搜索结果痕迹", "count": 1, "severity": "fail"})

    # 评分
    fail_count = sum(1 for i in issues if i["severity"] == "fail")
    passed = fail_count == 0

    return {
        "file": filepath,
        "total_issues": len(issues),
        "fail_count": fail_count,
        "passed": passed,
        "issues": issues,
        "stats": {
            "total_sentences": len(sentences),
            "avg_length": round(sum(lengths) / len(lengths), 1) if lengths else 0,
            "min_length": min(lengths) if lengths else 0,
            "max_length": max(lengths) if lengths else 0,
        },
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python ai_taste_scanner.py <filepath>"}))
        sys.exit(1)

    result = scan(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
