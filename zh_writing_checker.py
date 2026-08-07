#!/usr/bin/env python3
"""zh_writing_checker.py — 中文写作质量检查器（6 维度）

中文写作质量把关：严谨性（错字/标点/语病/数字）+ 文风（去AI味）+ 活人感。

检测维度：
  D1 错字/错词   (warn)  常见错别字对、异形词规范、中英混写
  D2 标点规范    (fail)  中英标点混用、全半角、顿号/书名号/连接号
  D3 语法语病    (fail)  成分残缺、搭配不当、句式杂糅、前后矛盾
  D4 数字规范    (warn)  数字书写、全半角、日期/范围格式 (GB/T 15835)
  D5 文风/去AI味 (warn)  破折号、禁用词、句式指纹、死板动词、空泛工具名
  D6 活人感/可读 (warn)  句长均匀、超长段落、连接词密度、结果先行、括号夹注

原则：正确性(D2/D3) 必改(fail)，客观无争议；风格(D1/D4/D5/D6) 建议(warn)，
带豁免语境，只标记给建议不替作者决定——严谨 ≠ 僵化，保活人感。

用法:
  python zh_writing_checker.py 你的文档.md [--json]
"""
import re
import sys
import json
import pathlib

VERSION = "3.0"

# ── D1 常见错别字对（近音/近形，上下文不确定，warn） ──
# (疑似错误写法, 应写)  —— 命中即提示作者复核
COMMON_TYPO_PAIRS = [
    ("必需", "必须"), ("做为", "作为"),
    ("帐本", "账本"), ("座落", "坐落"), ("寒喧", "寒暄"),
    ("精萃", "精粹"), ("幅射", "辐射"), ("振撼", "震撼"),
    ("痉孪", "痉挛"), ("决窍", "诀窍"), ("脉博", "脉搏"),
    ("装祯", "装帧"), ("渡假", "度假"), ("按排", "安排"),
    ("既使", "即使"), ("既而", "继而"), ("以经", "已经"),
    ("利害关系", "厉害关系"), ("做为一个", "作为一个"),
]
# 异形词（《第一批异形词整理表》推荐写法）: (非推荐, 推荐)
VARIANT_WORDS = [
    ("交待", "交代"), ("必恭必敬", "毕恭毕敬"), ("当做", "当作"),
    ("缘份", "缘分"), ("澈底", "彻底"), ("谋画", "谋划"),
    ("胡涂", "糊涂"), ("含意", "含义"), ("人材", "人才"),
    ("思惟", "思维"), ("制做", "制作"), ("抹煞", "抹杀"),
    ("想像", "想象"), ("联贯", "连贯"), ("彷佛", "仿佛"),
    ("归根结柢", "归根结底"), ("按排", "安排"), ("装璜", "装潢"),
    ("跌荡", "跌宕"), ("故技重演", "故伎重演"),
]

# ── D2 标点规范（GB/T 15834）──
# 中文句中的英文标点（应改用中文标点）
EN_PUNCT_IN_CN = {
    ",": "，", ".": "。", "?": "？", "!": "！",
    ";": "；", ":": "：", '"': "“”",
}
# 半角标点紧跟中文（应全角）——英文标点夹中文
HALF_PUNCT = re.compile(r"[\u4e00-\u9fff][,.;:!?](?=[\u4e00-\u9fff])")
# 连接号/范围: 中文数字/日期间应全角
MIXED_PUNCT = re.compile(r"[\u4e00-\u9fff][,.;:!?()]")

# ── D3 语法语病（常见病句模式）──
FAULTY_PATTERNS = [
    ("成分残缺·通过…使", r"通过[^。，；]{2,30}(使|让|令)", "“通过…使”双介词，主语残缺，删其一"),
    ("成分残缺·缺主语", r"^(经过|随着|由于)[^。]{5,40}(终于|才|便)", "句首介词短语后缺主语"),
    ("搭配不当·改善…水平", r"改善[^。]{0,8}(水平|程度)", "“改善”搭配“状况/条件”，不用“水平”（用“提高…水平”）"),
    ("搭配不当·提高…质量", r"提高[^。]{0,8}(数量)", "“提高”搭配“质量/水平”，数量用“增加/提升”"),
    ("句式杂糅·是因为…原因", r"是因为[^。]{0,15}的原因", "“是因为…的原因”杂糅，删“的原因”"),
    ("句式杂糅·目的是为了", r"目的是为了", "“目的是为了”杂糅，删“为了”或“目的”"),
    ("句式杂糅·由于…所致", r"由于[^。]{0,20}所致", "“由于…所致”杂糅，删“所致”"),
    ("前后矛盾·大约…左右", r"大约[^。]{0,10}左右", "“大约…左右”语义重复，删一"),
    ("前后矛盾·几乎…都", r"几乎[^。]{0,10}(全部|都)", "“几乎…都”矛盾，二选一"),
    ("句式杂糅·关键在于…在于", r"关键在于[^。]{0,10}在于", "“关键在于…在于”重复"),
    ("成分残缺·对…进行", r"对[^。]{2,30}进行(了)?$", "“对…进行”缺宾语或冗余"),
]

# ── D4 数字规范（GB/T 15835，warn）──
DATE_FMT = re.compile(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}")          # 日期应 2024-08-06
RANGE_TILDE = re.compile(r"\d+~\d+")                             # 范围应用全角连接号 - 或"至"
CN_CN_NUM = re.compile(r"[\u4e00-\u9fff][0-9]+|(?<![0-9])[0-9]+[\u4e00-\u9fff]")  # 中英数字混排

# ── D5 文风/去AI味（保留原 L1-L4，更丰富）──
DISABLED_WORDS = [
    "底层逻辑", "赋能", "闭环", "长期主义", "关键抓手", "价值沉淀", "认知升级",
    "说白了", "本质上", "综上所述", "值得注意的是", "不难发现",
    "无需多言", "归根结底", "众所周知", "显然", "毫无疑问", "某种意义上",
    "抓手", "破局", "降维打击", "第二曲线", "飞轮", "北极星指标",
    "颗粒度", "同理可得", "打个比方", "毫不夸张地说",
]
META_LANGUAGE = ["写在最后", "结语", "让我们讨论", "总而言之", "在深入探讨之前", "接下来", "言归正传"]
TEXTBOOK_OPENERS = ["在当今时代", "随着……发展", "众所周知", "毋庸置疑", "进入新世纪", "随着科技的进步"]
STYLE_PATTERNS = [
    (r"不是[^。，]{1,20}而是", "句式指纹：不是…而是"),
    (r"从[^。，]{1,10}到[^。，]{1,10}", "句式指纹：从…到…"),
    (r"不仅[^。，]{1,20}更是", "句式指纹：不仅…更是"),
    (r"(首先|其次|最后|第一|第二|第三)", "流水账序号，可用转场句"),
    (r"值得注意的是", "踩雷词"),
    (r"AI工具|某个模型|相关技术|一些方法", "空泛工具名，应说具体名字"),
    (r"比如有一次|假设你|想象一下", "假想例子（可能编造场景）"),
    (r"众所周知", "踩雷词"),
]
DEAD_VERBS = ["进行", "实现", "达到", "提升", "降低", "增加", "减少", "拥有", "属于", "涉及", "相关的", "所谓的"]
# 破折号滥用（AI 头号标志，绝对禁用）——只匹配全角破折号，不误伤英文连字符
DASH_PATTERN = re.compile(r"—{1,2}|–{1,2}|\u2014|\u2013")

# ── D6 活人感/可读性 ──
CONNECTIVES = ["然而", "此外", "同时", "因此", "总之", "综上", "进而", "从而", "并且", "而且", "此外", "再者", "换言之"]
LONG_PARAGRAPH = 400    # 字
FLAT_SENTENCE_DELTA = 5  # 连续句长字数差阈值

# ── 工具 ──
def _strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.S)


def _contexts(text: str, needle: str, width: int = 22, max_items: int = 3) -> list:
    out = []
    start = 0
    while True:
        i = text.find(needle, start)
        if i < 0:
            break
        lo = max(0, i - width)
        hi = min(len(text), i + len(needle) + width)
        out.append(text[lo:hi].replace("\n", " "))
        if len(out) >= max_items:
            break
        start = i + len(needle)
    return out


def _split_sentences(text: str) -> list:
    return [s.strip() for s in re.split(r"[。！？!?；]", text) if s.strip()]


def _scan_dimension(text, name, issues, dim, severity="warn", suggestion=""):
    """通用: 对 text 里的每个命中词, 收集为 issue。"""
    if isinstance(text, str):
        for word in [text]:
            pass


# ── 各维度扫描 ──
def scan(filepath: str) -> dict:
    """扫描文件，输出 6 维度报告。"""
    raw = pathlib.Path(filepath).read_text(encoding="utf-8")
    text = _strip_code_blocks(raw)
    issues = []
    stats = {"total_chars": len(raw), "total_sentences": len(_split_sentences(text))}

    # ── D1 错字/错词（warn）──
    d1 = 0
    for wrong, right in VARIANT_WORDS:
        if wrong != right and wrong in text:
            ctx = _contexts(text, wrong, 15, 2)
            issues.append({"layer": "D1", "type": f"异形词: {wrong}（规范:{right}）", "count": text.count(wrong),
                           "severity": "warn", "suggestion": f"建议用规范写法 {right}", "details": ctx})
            d1 += 1
    for wrong, right in COMMON_TYPO_PAIRS:
        if wrong != right and wrong in text and wrong not in [w for w, r in VARIANT_WORDS if r == wrong]:
            ctx = _contexts(text, wrong, 15, 2)
            issues.append({"layer": "D1", "type": f"疑似错字: {wrong}", "count": text.count(wrong),
                           "severity": "warn", "suggestion": f"请复核是否应写 {right}", "details": ctx})
            d1 += 1
    # 中英混写（中文句夹英文，info）
    en_mix = re.findall(r"[\u4e00-\u9fff][A-Za-z]{3,}[\u4e00-\u9fff]", text)
    if en_mix:
        issues.append({"layer": "D1", "type": "中英混写", "count": len(en_mix), "severity": "info",
                       "suggestion": "中文句夹英文，注意空格与术语统一", "details": en_mix[:3]})
        d1 += 1

    # ── D2 标点规范（fail）──
    d2 = 0
    for m in HALF_PUNCT.finditer(text):
        issues.append({"layer": "D2", "type": f"半角标点{text[m.start()+1]}(应全角)", "count": 1,
                       "severity": "fail", "suggestion": f"改用中文标点 {EN_PUNCT_IN_CN.get(text[m.start()+1], text[m.start()+1])}",
                       "details": [text[max(0,m.start()-10):m.start()+12]]})
        d2 += 1
    for m in MIXED_PUNCT.finditer(text):
        c = text[m.start()+1]
        if c in EN_PUNCT_IN_CN:
            issues.append({"layer": "D2", "type": f"中英标点混用:'{c}'", "count": 1,
                           "severity": "fail", "suggestion": f"改用全角 {EN_PUNCT_IN_CN[c]}",
                           "details": [text[max(0,m.start()-10):m.start()+12]]})
            d2 += 1
    # 英文引号夹中文
    for m in re.finditer(r'[\u4e00-\u9fff]"[^"]{1,20}"', text):
        issues.append({"layer": "D2", "type": "英文引号", "count": 1, "severity": "fail",
                       "suggestion": "中文引号用“”", "details": [m.group(0)[:40]]})
        d2 += 1

    # ── D3 语病（fail）──
    d3 = 0
    for name, pat, sug in FAULTY_PATTERNS:
        for m in re.finditer(pat, text):
            issues.append({"layer": "D3", "type": name, "count": 1, "severity": "fail",
                           "suggestion": sug, "details": [m.group(0)[:40]]})
            d3 += 1

    # ── D4 数字规范（warn）──
    d4 = 0
    for m in DATE_FMT.finditer(text):
        issues.append({"layer": "D4", "type": f"日期格式:{m.group(0)}", "count": 1, "severity": "warn",
                       "suggestion": "日期建议用 YYYY-MM-DD 或中文年月日", "details": [m.group(0)]})
        d4 += 1
    for m in RANGE_TILDE.finditer(text):
        issues.append({"layer": "D4", "type": f"范围用~:{m.group(0)}", "count": 1, "severity": "warn",
                       "suggestion": "范围用全角连接号或'至'", "details": [m.group(0)]})
        d4 += 1
    for m in CN_CN_NUM.finditer(text):
        issues.append({"layer": "D4", "type": f"中英数字混排:{m.group(0)}", "count": 1, "severity": "warn",
                       "suggestion": "数字书写统一（全阿拉伯或全汉字）", "details": [m.group(0)]})
        d4 += 1

    # ── D5 文风/去AI味（warn + fail 破折号）──
    d5 = 0
    for w in DISABLED_WORDS:
        if w in text:
            issues.append({"layer": "D5", "type": f"禁用词:{w}", "count": text.count(w), "severity": "fail",
                           "suggestion": "换成具体描述", "details": _contexts(text, w, 18, 2)})
            d5 += 1
    for w in META_LANGUAGE:
        if w in text:
            issues.append({"layer": "D5", "type": f"元语言:{w}", "count": text.count(w), "severity": "warn",
                           "suggestion": "删掉或改自然转场", "details": _contexts(text, w, 18, 2)})
            d5 += 1
    for w in TEXTBOOK_OPENERS:
        if w in text:
            issues.append({"layer": "D5", "type": f"教科书开头:{w}", "count": text.count(w), "severity": "warn",
                           "suggestion": "开头直接给结论", "details": _contexts(text, w, 18, 2)})
            d5 += 1
    for pat, label in STYLE_PATTERNS:
        for m in re.finditer(pat, text):
            issues.append({"layer": "D5", "type": label, "count": 1, "severity": "warn",
                           "suggestion": "换个说法，避免模板腔", "details": [m.group(0)[:40]]})
            d5 += 1
    for v in DEAD_VERBS:
        if v in text:
            issues.append({"layer": "D5", "type": f"死板动词:{v}", "count": text.count(v), "severity": "info",
                           "suggestion": "用有画面感的动词", "details": _contexts(text, v, 15, 1)})
            d5 += 1
    for m in DASH_PATTERN.finditer(text):
        issues.append({"layer": "D5", "type": "破折号", "count": 1, "severity": "fail",
                       "suggestion": "破折号是AI头号标志，改逗号或重写", "details": [text[max(0,m.start()-10):m.start()+12]]})
        d5 += 1

    # ── D6 活人感/可读性（warn + info）──
    d6 = 0
    # 超长段落
    for i, para in enumerate(text.split("\n")):
        if len(para) > LONG_PARAGRAPH:
            issues.append({"layer": "D6", "type": f"超长段落({len(para)}字)", "count": 1, "severity": "warn",
                           "suggestion": "拆段，留呼吸感", "details": [para[:40]]})
            d6 += 1
    # 句长均匀
    sents = _split_sentences(text)
    for i in range(len(sents) - 2):
        lens = [len(sents[i]), len(sents[i+1]), len(sents[i+2])]
        if max(lens) - min(lens) < FLAT_SENTENCE_DELTA and max(lens) > 10:
            issues.append({"layer": "D6", "type": "句长均匀(无节奏)", "count": 1, "severity": "warn",
                           "suggestion": "句长要有变化，长短交错", "details": [" ".join(sents[i:i+3])[:50]]})
            d6 += 1
            break
    # 连接词密度
    conn = sum(text.count(c) for c in CONNECTIVES)
    if stats["total_sentences"] and conn / max(1, stats["total_sentences"]) > 0.3:
        issues.append({"layer": "D6", "type": f"连接词过密({conn}/{stats['total_sentences']}句)", "count": conn,
                       "severity": "warn", "suggestion": "删冗余连接词，用逻辑衔接", "details": []})
        d6 += 1
    # 结果先行（开篇 100 字无数字/结论）
    head = text[:100]
    if stats["total_chars"] > 150 and not re.search(r"\d|结果|结论|是|%|倍|万|亿", head):
        issues.append({"layer": "D6", "type": "开篇未给结论", "count": 1, "severity": "info",
                       "suggestion": "前100字甩出数字/结论，不线性铺陈", "details": [head[:60]]})
        d6 += 1

    # ── 汇总 ──
    dim_counts = {"D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5, "D6": d6}
    layers = {}
    for dim in ["D1", "D2", "D3", "D4", "D5", "D6"]:
        dim_issues = [i for i in issues if i["layer"] == dim]
        has_fail = any(i["severity"] == "fail" for i in dim_issues)
        layers[dim] = {"passed": not has_fail, "issue_count": len(dim_issues),
                       "fail_count": sum(1 for i in dim_issues if i["severity"] == "fail"),
                       "warn_count": sum(1 for i in dim_issues if i["severity"] == "warn")}
    fail_total = sum(1 for i in issues if i["severity"] == "fail")
    return {
        "file": filepath, "version": VERSION,
        "total_issues": len(issues), "fail_count": fail_total,
        "warn_count": sum(1 for i in issues if i["severity"] == "warn"),
        "passed": fail_total == 0,
        "dimension_counts": dim_counts, "layers": layers,
        "issues": issues, "stats": stats,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    report = scan(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"文件: {report['file']}  v{report['version']}")
        print(f"问题 {report['total_issues']} 项 | fail {report['fail_count']} | warn {report['warn_count']} | 通过 {report['passed']}")
        for dim in ["D1", "D2", "D3", "D4", "D5", "D6"]:
            l = report["layers"][dim]
            status = "✅" if l["passed"] else "❌"
            print(f"  {status} {dim} 通过={l['passed']} 问题={l['issue_count']} (fail {l['fail_count']}/warn {l['warn_count']})")
        for i in report["issues"]:
            mark = {"fail": "❌", "warn": "⚠️", "info": "ℹ️"}.get(i["severity"], "·")
            print(f"  {mark} [{i['layer']}] {i['type']} ×{i['count']}")
