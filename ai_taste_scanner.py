# -*- coding: utf-8 -*-
"""
AI味指纹扫描器 v2.0
输入 .md 文件路径，输出四层检查报告（JSON）

v2.0 升级（2026-08-06）：
- 规则层对齐写作规范词表（词汇黑名单 + 高频踩雷词）
- 新增句式指纹：不是X而是Y高密度 / 从X到Y / 不仅...更 / 首先其次最后
- 新增结构检测：教科书开头 / markdown 小标题滥用 / 段落呼吸感 / 金句收束密度
- 新增活人感检测：死板动词 / 假想例子 / 空泛工具名 / 自问自答缺失
- 新增风格指纹检查：结果先行 / 汉字数字 / 活物动词 / 结尾短句收束
- 输出四层报告 L1-L4，每项带修复建议
"""
import re
import json
import sys
from pathlib import Path

# ============ 规则配置 ============

# L1 禁用词（对齐写作规范词表）
DISABLED_WORDS = [
    # 黑话/空话
    "底层逻辑", "前所未有", "毋庸置疑", "赋能", "闭环", "长期主义",
    "关键抓手", "深度链接", "价值沉淀", "认知升级", "图景", "静默的",
    "系统性", "链路", "总而言之", "一场", "绝非是",
    "说白了", "本质上", "换句话说", "不可否认", "综上所述", "总的来说",
    "值得注意的是", "不难发现", "让我们来看看", "接下来让我们",
    "不仅仅是", "不只是", "意味着什么", "这意味着",
]

# L1 元语言（结构废话）
META_LANGUAGE = [
    "写在最后", "结语", "今天我们来谈", "最后我必须", "回到最初的问题",
    "总而言之", "我们来谈谈", "让我们讨论", "在深入探讨之前",
]

# L1 教科书开头模式
TEXTBOOK_OPENERS = [
    r"在当今.{0,10}(时代|背景下)",
    r"随着.{0,15}(发展|进步|到来)",
    r"近年来.{0,10}(发展|兴起|崛起)",
    r"在这个.{0,10}(时代|年代)",
    r"众所周知，",
    r"毋庸置疑，",
]

# L2 句式指纹
PATTERN_NOT_X_BUT_Y = r"不是[^。，]{1,20}，?而是"      # 不是X而是Y
PATTERN_FROM_X_TO_Y = r"从[^。，]{1,15}到[^。，]{1,15}"  # 从X到Y（需人工判断是否虚假范围）
PATTERN_NOT_ONLY = r"不仅[^。，]{1,10}(更是|也是|还是)"  # 不仅是...更是
PATTERN_FIRST_SECOND = r"首先.{0,20}(其次|再次|最后)"   # 首先其次最后
PATTERN_TAKEAWAY = r"(值得.{0,4}(注意|关注|一提)|需要指出|值得注意的是)"  # 值得注意

# L2 死板动词（AI 默认用词，主张用有画面感的动词）
DEAD_VERBS = ["进行", "实现", "达到", "提升", "降低", "增加", "减少", "拥有",
              "存在", "产生", "表示", "体现", "展示", "确保", "提供", "获得"]

# L2 空泛工具名
VAGUE_TOOLS = ["AI工具", "某个模型", "相关技术", "各种工具", "一些模型", "某家"]

# L2 假想例子
FAKE_EXAMPLES = [r"比如有一次", r"举个例子，?有一次", r"假设.{0,10}(遇到|面临|你)",
                 r"如果.{0,10}(你|我们).{0,10}(会|能)发现"]

# L2 markdown 小标题（禁 markdown 小标题）
MD_HEADING = r"^#{1,6}\s+\S"

# L3 内容质量
CONNECTIVES = ["然而", "此外", "同时", "因此", "总之", "综上", "进而", "从而",
               "也就是说", "换言之", "值得注意的是", "事实上"]

# 风格指纹
FINGERPRINTS = {
    "结果先行": {
        "desc": "开篇100字内应甩出最震撼的数字/结论",
        "check": lambda text: _check_result_first(text),
    },
    "汉字数字": {
        "desc": "数字用汉字+口语量词（一万七千、八成三），避免 159,000 书面格式",
        "check": lambda text: _check_arabic_digits(text),
    },
    "结尾短句收束": {
        "desc": "结尾用一句能立住的话收束，不总结不升华",
        "check": lambda text: _check_ending(text),
    },
}


def _strip_code_blocks(text: str) -> str:
    """去掉代码块内容（``` 包裹的），代码块内数字/格式不参与检查"""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def _check_result_first(text: str) -> list:
    """指纹一：结果先行。开篇 100 字内有无具体数字/结论"""
    head = text[:200]
    has_number = re.search(r"\d|十|百|千|万|亿", head)
    if not has_number:
        return [{"issue": "开篇 200 字内没有具体数字或结论，可能从背景线性铺陈",
                 "suggestion": "开篇直接甩出最震撼的数字或结论，再回头讲过程"}]
    return []


def _check_arabic_digits(text: str) -> list:
    """指纹三：汉字数字。检测书面格式的阿拉伯数字（千分位分隔符），排除代码块"""
    body = _strip_code_blocks(text)
    issues = []
    # 千分位格式如 159,000 / 3,695
    for m in re.finditer(r"\d{1,3}(,\d{3})+", body):
        issues.append({"issue": f"书面格式阿拉伯数字: {m.group()}",
                       "suggestion": "用汉字+口语量词（'一万七千多行''八成三'），替代书面数字"})
    # 美元/百分比书面格式
    for m in re.finditer(r"\$\d+(\.\d+)?/|\d+%", body):
        issues.append({"issue": f"书面数字格式: {m.group()}",
                       "suggestion": "用口语化表达（'四毛钱''不到四成'）"})
    return issues[:5]


def _check_ending(text: str) -> list:
    """指纹七：结尾短句独立收束，不总结"""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return []
    last = lines[-1]
    ending_bad = ["总而言之", "综上所述", "总之", "未来已来", "让我们一起",
                  "相信", "期待", "希望我们", "我们有理由相信"]
    for w in ending_bad:
        if w in last:
            return [{"issue": f"结尾疑似总结/升华: 含'{w}'",
                     "suggestion": "结尾用一句能立住的话，是洞察不是总结"}]
    if len(last) > 30:
        return [{"issue": f"结尾句偏长({len(last)}字)，且非独立短句",
                 "suggestion": "最后一句用短句独立收束，制造重量感"}]
    return []


def scan(filepath: str) -> dict:
    text = Path(filepath).read_text(encoding="utf-8")
    lines = text.split("\n")
    total_chars = len(text)

    issues = []  # 每项: {layer, type, count, severity, suggestion, details}

    # ========== L1 硬性规则 ==========

    # 1. 破折号
    dashes = len(re.findall(r"——|—", text))
    if dashes:
        issues.append({"layer": "L1", "type": "破折号", "count": dashes,
                       "severity": "fail",
                       "suggestion": "破折号是AI写作头号标志，绝对禁用。用逗号、句号或自然语言处理",
                       "details": []})

    # 2. 禁用词
    for word in DISABLED_WORDS:
        count = text.count(word)
        if count:
            issues.append({"layer": "L1", "type": f"禁用词: {word}", "count": count,
                           "severity": "fail",
                           "suggestion": _suggestion_for(word),
                           "details": _contexts(text, word)})

    # 3. 元语言
    for word in META_LANGUAGE:
        count = text.count(word)
        if count:
            issues.append({"layer": "L1", "type": f"元语言: {word}", "count": count,
                           "severity": "fail",
                           "suggestion": "结构废话，删掉直接说",
                           "details": _contexts(text, word)})

    # 4. 教科书开头
    for pat in TEXTBOOK_OPENERS:
        for m in re.finditer(pat, text):
            issues.append({"layer": "L1", "type": f"教科书开头: {m.group()}",
                           "count": 1, "severity": "warn",
                           "suggestion": "永远从一个具体的、当下的事件/场景切入，拒绝宏大叙事开头",
                           "details": []})

    # 5. 搜索痕迹
    if "搜索结果显示" in text:
        issues.append({"layer": "L1", "type": "搜索结果痕迹", "count": 1,
                       "severity": "fail",
                       "suggestion": "绝对不出现，删除",
                       "details": []})

    # ========== L2 风格一致性 ==========

    # 6. 句式指纹
    not_x_but_y = len(re.findall(PATTERN_NOT_X_BUT_Y, text))
    if not_x_but_y >= 3:
        issues.append({"layer": "L2", "type": "不是X而是Y句式高密度", "count": not_x_but_y,
                       "severity": "warn",
                       "suggestion": "认知翻转句式只能少量使用，且X必须是读者真实持有的认知。超过3次就是AI味",
                       "details": [m.group(0)[:40] for m in re.finditer(PATTERN_NOT_X_BUT_Y, text)][:5]})
    elif not_x_but_y > 0:
        issues.append({"layer": "L2", "type": "不是X而是Y句式", "count": not_x_but_y,
                       "severity": "info",
                       "suggestion": "少量使用可接受，注意X必须是真实存在的认知",
                       "details": []})

    from_x_to_y = len(re.findall(PATTERN_FROM_X_TO_Y, text))
    if from_x_to_y >= 3:
        issues.append({"layer": "L2", "type": "从X到Y句式", "count": from_x_to_y,
                       "severity": "warn",
                       "suggestion": "检查是否虚假范围（X和Y无本质关联时禁用）",
                       "details": [m.group(0)[:40] for m in re.finditer(PATTERN_FROM_X_TO_Y, text)][:5]})

    not_only = len(re.findall(PATTERN_NOT_ONLY, text))
    if not_only:
        issues.append({"layer": "L2", "type": "不仅...更是句式", "count": not_only,
                       "severity": "fail",
                       "suggestion": "AI最明显的语言指纹之一。直接说是什么就可以了",
                       "details": [m.group(0)[:40] for m in re.finditer(PATTERN_NOT_ONLY, text)][:5]})

    first_second = len(re.findall(PATTERN_FIRST_SECOND, text))
    if first_second:
        issues.append({"layer": "L2", "type": "首先...其次...最后结构", "count": first_second,
                       "severity": "warn",
                       "suggestion": "结构化套话，用自然转场词替代",
                       "details": []})

    takeaway = len(re.findall(PATTERN_TAKEAWAY, text))
    if takeaway:
        issues.append({"layer": "L2", "type": "值得注意句式", "count": takeaway,
                       "severity": "warn",
                       "suggestion": "删掉，直接说",
                       "details": []})

    # 7. 死板动词
    dead_verb_hits = []
    for v in DEAD_VERBS:
        c = text.count(v)
        if c:
            dead_verb_hits.append((v, c))
    total_dead = sum(c for _, c in dead_verb_hits)
    if total_dead >= 10:
        issues.append({"layer": "L2", "type": "死板动词密度高", "count": total_dead,
                       "severity": "warn",
                       "suggestion": "AI默认用'达到/进行/实现'这类死词。用有画面感的动词，每个动词要能在脑子里成像",
                       "details": [f"{v}×{c}" for v, c in dead_verb_hits]})

    # 8. 空泛工具名
    for t in VAGUE_TOOLS:
        c = text.count(t)
        if c:
            issues.append({"layer": "L2", "type": f"空泛工具名: {t}", "count": c,
                           "severity": "warn",
                           "suggestion": "说具体名字（具体的工具/模型），不说'AI工具''某个模型'",
                           "details": _contexts(text, t)})

    # 9. 假想例子
    for pat in FAKE_EXAMPLES:
        for m in re.finditer(pat, text):
            issues.append({"layer": "L2", "type": f"假想例子: {m.group()}",
                           "count": 1, "severity": "warn",
                           "suggestion": "'比如有一次'编造场景是大忌。用'就像我今天正在搞的xxx'真实细节，没有就明说没试过",
                           "details": []})

    # 10. markdown 小标题（排除 H1 主标题和 frontmatter，只检查 ## 及以上正文标题）
    body_lines = _strip_code_blocks(text).split("\n")
    # 去掉 frontmatter（--- 包裹）
    if body_lines and body_lines[0].strip() == "---":
        try:
            end = body_lines.index("---", 1)
            body_lines = body_lines[end+1:]
        except ValueError:
            pass
    md_heads = [l for l in body_lines if re.match(r"^#{2,6}\s+\S", l)]
    if md_heads:
        issues.append({"layer": "L2", "type": "markdown小标题", "count": len(md_heads),
                       "severity": "warn",
                       "suggestion": "禁markdown小标题，用口语转场句分段",
                       "details": md_heads[:8]})

    # 11. 句长均匀
    sentences = re.split(r"[。！？\n]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
    lengths = [len(s) for s in sentences]

    uniform_groups = []
    for i in range(len(lengths) - 2):
        if abs(lengths[i] - lengths[i+1]) < 5 and abs(lengths[i+1] - lengths[i+2]) < 5:
            uniform_groups.append((i+1, lengths[i], lengths[i+1], lengths[i+2]))

    if len(uniform_groups) >= 3:
        issues.append({"layer": "L2", "type": "句长均匀（连续3句字数差<5）",
                       "count": len(uniform_groups), "severity": "warn",
                       "suggestion": "匀速句长本身就是AI味。短句3-8字、中句15-25字、长句30字+交替",
                       "details": [f"第{g[0]}-{g[0]+2}句: {g[1]}/{g[2]}/{g[3]}字" for g in uniform_groups[:5]]})

    # 12. 段落呼吸感：平均段落是否过长
    paras = [p for p in text.split("\n\n") if p.strip()]
    long_paras = [p for p in paras if len(p) > 500]
    if long_paras:
        issues.append({"layer": "L2", "type": "超长段落（>500字）", "count": len(long_paras),
                       "severity": "warn",
                       "suggestion": "段落要短，重要观点前后留白让它呼吸。长段落拆开",
                       "details": [f"{len(p)}字: {p[:30]}..." for p in long_paras[:3]]})

    # 13. 连接词密度
    connective_count = sum(text.count(c) for c in CONNECTIVES)
    if total_chars > 1000 and connective_count >= 8:
        issues.append({"layer": "L2", "type": "连接词密度高", "count": connective_count,
                       "severity": "warn",
                       "suggestion": "连接词越少文字越干净。大部分删掉文意更顺",
                       "details": []})

    # 14. 括号补充
    parens = len(re.findall(r"（[^）]+）", text))
    if parens:
        issues.append({"layer": "L2", "type": "括号补充", "count": parens,
                       "severity": "warn",
                       "suggestion": "严禁用括号作补充说明，内容直接揉入正文",
                       "details": []})

    # ========== L3 内容质量 ==========

    # 15. 金句收束密度（每段末句都很短且有感叹号/句号收束）
    short_enders = 0
    for p in paras:
        ends = [s for s in re.split(r"[。！？]", p) if s.strip()]
        if ends and len(ends[-1]) <= 10:
            short_enders += 1
    if len(paras) >= 6 and short_enders >= len(paras) * 0.7:
        issues.append({"layer": "L3", "type": "金句收束密度高", "count": short_enders,
                       "severity": "warn",
                       "suggestion": "不要每段都收束金句，只让最重要的一两句话有爆发力",
                       "details": []})

    # ========== L4 活人感 / 风格指纹 ==========

    for name, fp in FINGERPRINTS.items():
        for hit in fp["check"](text):
            issues.append({"layer": "L4", "type": f"指纹: {name}", "count": 1,
                           "severity": "warn", "suggestion": hit["suggestion"],
                           "details": [hit["issue"]]})

    # 自问自答检查
    questions = len(re.findall(r"？", text))
    if total_chars > 1500 and questions < 2:
        issues.append({"layer": "L4", "type": "自问自答缺失", "count": 0,
                       "severity": "info",
                       "suggestion": "关键数据处用自问自答，制造对话节奏",
                       "details": []})

    # 评分
    fail_count = sum(1 for i in issues if i["severity"] == "fail")
    warn_count = sum(1 for i in issues if i["severity"] == "warn")
    passed = fail_count == 0

    layers = {}
    for layer in ["L1", "L2", "L3", "L4"]:
        layer_issues = [i for i in issues if i["layer"] == layer]
        fails = sum(1 for i in layer_issues if i["severity"] == "fail")
        warns = sum(1 for i in layer_issues if i["severity"] == "warn")
        layers[layer] = {
            "passed": fails == 0,
            "fail_count": fails,
            "warn_count": warns,
            "issue_count": len(layer_issues),
        }

    return {
        "file": filepath,
        "version": "2.0",
        "total_issues": len(issues),
        "fail_count": fail_count,
        "warn_count": warn_count,
        "passed": passed,
        "layers": layers,
        "issues": issues,
        "stats": {
            "total_chars": total_chars,
            "total_sentences": len(sentences),
            "avg_length": round(sum(lengths) / len(lengths), 1) if lengths else 0,
            "min_length": min(lengths) if lengths else 0,
            "max_length": max(lengths) if lengths else 0,
        },
    }


def _contexts(text: str, word: str, width: int = 25, max_items: int = 3) -> list:
    """返回命中词的上下文片段"""
    out = []
    for m in re.finditer(re.escape(word), text):
        start = max(0, m.start() - width)
        end = min(len(text), m.end() + width)
        ctx = text[start:end].replace("\n", " ")
        out.append(f"...{ctx}...")
        if len(out) >= max_items:
            break
    return out


def _suggestion_for(word: str) -> str:
    """禁用词修复建议"""
    mapping = {
        "说白了": "换成'坦率的讲'、'其实就是'",
        "本质上": "换成'说到底'、'其实'",
        "换句话说": "换成'你想想看'、'也就是说'",
        "不可否认": "删掉，直接正面陈述",
        "综上所述": "换成具体的回扣句",
        "总的来说": "换成具体的回扣句",
        "值得注意的是": "删掉，直接说",
        "不难发现": "删掉，直接说",
        "让我们来看看": "直接展示内容",
        "接下来让我们": "直接进入内容",
        "不仅仅是": "直接说Y，去掉前半截",
        "不只是": "直接说Y，去掉前半截",
        "底层逻辑": "换成'根本原因'、'实质'",
        "前所未有": "删掉，用具体事实替代",
        "赋能": "换成具体动作",
        "闭环": "换成'走通流程'",
        "长期主义": "换成'坚持'、'持续投入'",
        "认知升级": "删掉",
        "意味着什么": "换成'那结果会怎样呢'、'所以呢'",
        "这意味着": "换成'也就是说'",
    }
    return mapping.get(word, "删掉或换成具体表达")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python ai_taste_scanner.py <filepath>"}))
        sys.exit(1)

    result = scan(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
