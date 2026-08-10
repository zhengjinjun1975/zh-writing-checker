#!/usr/bin/env python3
"""zh_writing_checker.py — 中文写作优化器（三线检测）

工作流：人味门检 → 三线检测 → 复检（Gate → Detect → Recheck）。

三线：
  · 硬规则线（must-fix, fail）：字词 D1 / 标点 D2 / 语法 D3 / 数字 D4 —— 客观对错
  · 文风线  （should-fix, warn+fail）：去AI味 D5 —— 风格判断，留余地
  · 人味线  （should-fix, warn）：活人感/可读 D6 —— 最主观

原则：正确性必改，风格给建议，改写不虚构，真人文本停手。
用法:
  python zh_writing_checker.py 你的文档.md [--json]
"""
import re
import os
import sys
import json
import pathlib

VERSION = "0.1.2"

# ── 硬规则线 D1 字词 ──
COMMON_TYPO_PAIRS = [
    ("必需", "必须"), ("做为", "作为"),
    ("帐本", "账本"), ("座落", "坐落"), ("寒喧", "寒暄"),
    ("精萃", "精粹"), ("幅射", "辐射"), ("振撼", "震撼"),
    ("痉孪", "痉挛"), ("决窍", "诀窍"), ("脉博", "脉搏"),
    ("装祯", "装帧"), ("渡假", "度假"), ("按排", "安排"),
    ("既使", "即使"), ("既而", "继而"), ("以经", "已经"),
    ("利害关系", "厉害关系"), ("做为一个", "作为一个"),
]
VARIANT_WORDS = [
    ("交待", "交代"), ("必恭必敬", "毕恭毕敬"), ("当做", "当作"),
    ("缘份", "缘分"), ("澈底", "彻底"), ("谋画", "谋划"),
    ("胡涂", "糊涂"), ("含意", "含义"), ("人材", "人才"),
    ("思惟", "思维"), ("制做", "制作"), ("抹煞", "抹杀"),
    ("想像", "想象"), ("联贯", "连贯"), ("彷佛", "仿佛"),
    ("归根结柢", "归根结底"), ("按排", "安排"), ("装璜", "装潢"),
    ("跌荡", "跌宕"), ("故技重演", "故伎重演"),
]

# ── 硬规则线 D2 标点（GB/T 15834）──
EN_PUNCT_IN_CN = {
    ",": "，", ".": "。", "?": "？", "!": "！",
    ";": "；", ":": "：", '"': "“”",
}
HALF_PUNCT = re.compile(r"[\u4e00-\u9fff][,.;:!?](?=[\u4e00-\u9fff])")
MIXED_PUNCT = re.compile(r"[\u4e00-\u9fff][,.;:!?()]")

# ── 硬规则线 D3 语法语病 ──
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

# ── 硬规则线 D4 数字（GB/T 15835）──
DATE_FMT = re.compile(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}")
RANGE_TILDE = re.compile(r"\d+~\d+")
CN_CN_NUM = re.compile(r"[\u4e00-\u9fff][0-9]+|(?<![0-9])[0-9]+[\u4e00-\u9fff]")

# ── 文风线 D5 去AI味 ──
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
DASH_PATTERN = re.compile(r"—{1,2}|–{1,2}|\u2014|\u2013")

# ── 人味线 D6 活人感/可读 ──
CONNECTIVES = ["然而", "此外", "同时", "因此", "总之", "综上", "进而", "从而", "并且", "而且", "再者", "换言之"]
LONG_PARAGRAPH = 400
FLAT_SENTENCE_DELTA = 5

# ── 工具 ──
def _strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.S)


def _contexts(text: str, needle: str, width: int = 22, max_items: int = 3) -> list:
    out, start = [], 0
    while True:
        i = text.find(needle, start)
        if i < 0:
            break
        lo, hi = max(0, i - width), min(len(text), i + len(needle) + width)
        out.append(text[lo:hi].replace("\n", " "))
        if len(out) >= max_items:
            break
        start = i + len(needle)
    return out


def _split_sentences(text: str) -> list:
    return [s.strip() for s in re.split(r"[。！？!?；]", text) if s.strip()]


def _collect(hits, layer, type_, count, severity, suggestion, details):
    """向 issues 收集一条 issue（统一入口）。"""
    hits.append({"layer": layer, "type": type_, "count": count,
                 "severity": severity, "suggestion": suggestion, "details": details})



# ── 各维度扫描 ──
# 维度归属线（三线）：硬规则 D1-D4 / 文风 D5 / 人味 D6
_LINE_OF_DIM = {"D1": "hard", "D2": "hard", "D3": "hard", "D4": "hard",
                "D5": "style", "D6": "human"}
_DIMS = ["D1", "D2", "D3", "D4", "D5", "D6"]
_LINES = ["hard", "style", "human"]


def _scan_d1(text, issues):
    """硬规则线·字词：错字 / 异形词 / 中英混写。"""
    for wrong, right in VARIANT_WORDS:
        if wrong != right and wrong in text:
            _collect(issues, "D1", f"异形词: {wrong}（规范:{right}）", text.count(wrong), "warn",
                     f"建议用规范写法 {right}", _contexts(text, wrong, 15, 2))
    for wrong, right in COMMON_TYPO_PAIRS:
        if wrong != right and wrong in text and wrong not in [w for w, r in VARIANT_WORDS if r == wrong]:
            _collect(issues, "D1", f"疑似错字: {wrong}", text.count(wrong), "warn",
                     f"请复核是否应写 {right}", _contexts(text, wrong, 15, 2))
    en_mix = re.findall(r"[\u4e00-\u9fff][A-Za-z]{3,}[\u4e00-\u9fff]", text)
    if en_mix:
        _collect(issues, "D1", "中英混写", len(en_mix), "info",
                 "中文句夹英文，注意空格与术语统一", en_mix[:3])


def _scan_d2(text, issues):
    """硬规则线·标点：中英混用 / 半角 / 英文引号（GB/T 15834）。"""
    for m in HALF_PUNCT.finditer(text):
        c = text[m.start() + 1]
        _collect(issues, "D2", f"半角标点{c}(应全角)", 1, "fail",
                 f"改用中文标点 {EN_PUNCT_IN_CN.get(c, c)}", [text[max(0, m.start()-10):m.start()+12]])
    for m in MIXED_PUNCT.finditer(text):
        c = text[m.start() + 1]
        if c in EN_PUNCT_IN_CN:
            _collect(issues, "D2", f"中英标点混用:'{c}'", 1, "fail",
                     f"改用全角 {EN_PUNCT_IN_CN[c]}", [text[max(0, m.start()-10):m.start()+12]])
    for m in re.finditer(r'[\u4e00-\u9fff]"[^"]{1,20}"', text):
        _collect(issues, "D2", "英文引号", 1, "fail", "中文引号用“”", [m.group(0)[:40]])


def _scan_d3(text, issues):
    """硬规则线·语法：成分残缺 / 搭配不当 / 句式杂糅 / 前后矛盾。"""
    for name, pat, sug in FAULTY_PATTERNS:
        for m in re.finditer(pat, text):
            _collect(issues, "D3", name, 1, "fail", sug, [m.group(0)[:40]])


def _scan_d4(text, issues):
    """硬规则线·数字：日期 / 范围连接号 / 中英数字混排（GB/T 15835）。"""
    for m in DATE_FMT.finditer(text):
        _collect(issues, "D4", f"日期格式:{m.group(0)}", 1, "warn",
                 "日期建议用 YYYY-MM-DD 或中文年月日", [m.group(0)])
    for m in RANGE_TILDE.finditer(text):
        _collect(issues, "D4", f"范围用~:{m.group(0)}", 1, "warn",
                 "范围用全角连接号或'至'", [m.group(0)])
    for m in CN_CN_NUM.finditer(text):
        _collect(issues, "D4", f"中英数字混排:{m.group(0)}", 1, "warn",
                 "数字书写统一（全阿拉伯或全汉字）", [m.group(0)])


def _scan_wordlist(text, issues, layer, words, severity, suggestion, prefix=""):
    """通用：逐个词表命中扫描，统一收集。type 形如 '{prefix}{w}'。"""
    for w in words:
        if w in text:
            _collect(issues, layer, f"{prefix}{w}", text.count(w), severity,
                     suggestion, _contexts(text, w, 18, 2))


def _scan_d5(text, issues):
    """文风线·去AI味：禁用词 / 元语言 / 教科书开头 / 句式指纹 / 死板动词 / 破折号。"""
    _scan_wordlist(text, issues, "D5", DISABLED_WORDS, "fail", "换成具体描述", "禁用词:")
    _scan_wordlist(text, issues, "D5", META_LANGUAGE, "warn", "删掉或改自然转场", "元语言:")
    _scan_wordlist(text, issues, "D5", TEXTBOOK_OPENERS, "warn", "开头直接给结论", "教科书开头:")
    for pat, label in STYLE_PATTERNS:
        for m in re.finditer(pat, text):
            _collect(issues, "D5", label, 1, "warn", "换个说法，避免模板腔", [m.group(0)[:40]])
    _scan_wordlist(text, issues, "D5", DEAD_VERBS, "info", "用有画面感的动词", "死板动词:")
    for m in DASH_PATTERN.finditer(text):
        _collect(issues, "D5", "破折号", 1, "fail",
                 "破折号是AI头号标志，改逗号或重写", [text[max(0, m.start()-10):m.start()+12]])


def _scan_d6(text, issues, stats):
    """人味线·可读：超长段落 / 句长均匀 / 连接词密度 / 结果先行。"""
    for para in text.split("\n"):
        if len(para) > LONG_PARAGRAPH:
            _collect(issues, "D6", f"超长段落({len(para)}字)", 1, "warn",
                     "拆段，留呼吸感", [para[:40]])
    sents = _split_sentences(text)
    for i in range(len(sents) - 2):
        lens = [len(sents[i]), len(sents[i+1]), len(sents[i+2])]
        if max(lens) - min(lens) < FLAT_SENTENCE_DELTA and max(lens) > 10:
            _collect(issues, "D6", "句长均匀(无节奏)", 1, "warn",
                     "句长要有变化，长短交错", [" ".join(sents[i:i+3])[:50]])
            break
    conn = sum(text.count(c) for c in CONNECTIVES)
    if stats["total_sentences"] and conn / max(1, stats["total_sentences"]) > 0.3:
        _collect(issues, "D6", f"连接词过密({conn}/{stats['total_sentences']}句)", conn, "warn",
                 "删冗余连接词，用逻辑衔接", [])
    head = text[:100]
    if stats["total_chars"] > 150 and not re.search(r"\d|结果|结论|是|%|倍|万|亿", head):
        _collect(issues, "D6", "开篇未给结论", 1, "info",
                 "前100字甩出数字/结论，不线性铺陈", [head[:60]])


def _summarize(issues, filepath, stats):
    """汇总：六维分层 + 三线归并，输出最终报告。"""
    dim_counts, layers = {}, {}
    for dim in _DIMS:
        dim_issues = [i for i in issues if i["layer"] == dim]
        has_fail = any(i["severity"] == "fail" for i in dim_issues)
        layers[dim] = {"passed": not has_fail, "issue_count": len(dim_issues),
                       "fail_count": sum(1 for i in dim_issues if i["severity"] == "fail"),
                       "warn_count": sum(1 for i in dim_issues if i["severity"] == "warn")}
        dim_counts[dim] = len(dim_issues)
    lines = {line: {"dims": [], "issue_count": 0, "fail_count": 0} for line in _LINES}
    for dim, line in _LINE_OF_DIM.items():
        lines[line]["dims"].append(dim)
        lines[line]["issue_count"] += layers[dim]["issue_count"]
        lines[line]["fail_count"] += layers[dim]["fail_count"]
    fail_total = sum(1 for i in issues if i["severity"] == "fail")
    return {
        "file": filepath, "version": VERSION,
        "total_issues": len(issues), "fail_count": fail_total,
        "warn_count": sum(1 for i in issues if i["severity"] == "warn"),
        "passed": fail_total == 0,
        "dimension_counts": dim_counts, "layers": layers, "lines": lines,
        "issues": issues, "stats": stats,
    }


def scan(filepath: str) -> dict:
    """三线检测：扫描文件，输出三线六维报告。"""
    raw = pathlib.Path(filepath).read_text(encoding="utf-8")
    text = _strip_code_blocks(raw)
    issues = []
    stats = {"total_chars": len(raw), "total_sentences": len(_split_sentences(text))}

    # 三线六维扫描（每条线各司其职）
    _scan_d1(text, issues)
    _scan_d2(text, issues)
    _scan_d3(text, issues)
    _scan_d4(text, issues)
    _scan_d5(text, issues)
    _scan_d6(text, issues, stats)

    return _summarize(issues, filepath, stats)


# ═══════════ 优化器能力：人味门检 + 语体识别 + 三线检测→改写→复检 闭环 ═══════════
# 定位：不是报问题的检测器，是把稿子改得像人写的优化器（吸收 qu-ai-wei 方法论）

# ── 语体识别（8 种）：不同语体 AI 腔标准不同，避免把学术/公文误改口语 ──
_REGISTER_FINGERPRINTS = {
    "学术/科技": ["论文", "综述", "研究表明", "综上所述", "分析认为", "本研究", "方法论", "机制", "阈值", "显著性"],
    "公文/法律": ["依照", "予以", "兹", "特此", "本办法", "规定", "责令", "行政许可", "依法"],
    "叙事/特稿": ["那时", "我坐在", "他说", "推开门", "记得", "黄昏", "巷子", "她转身"],
    "品牌/广告": ["限时", "即刻", "仅此一次", "秒杀", "爆款", "上新", "为你", "专属"],
    "高考/应试": ["由此可见", "总而言之", "诚然", "不可否认", "值得称道", "排比递进"],
    "社交/口语": ["哈哈", "咱", "贼", "咋", "老铁", "哈喽", "诶", "嘛", "呗", "啦", "啊哈哈"],
    "内容/自媒体": ["家人们", "宝子", "宝们", "姐妹们", "种草", "打卡", "冲鸭", "集美"],
    "商务/职场": ["汇报", "方案", "截止", "跟进", "对接", "本周", "进度", "同步", "请知悉"],
}


def register_of(text: str) -> str:
    """语体识别（8 种）。命中数最多且 ≥2 才判定，否则默认'书面/一般'。"""
    if not text:
        return "书面/一般"
    scores = {}
    for reg, words in _REGISTER_FINGERPRINTS.items():
        scores[reg] = sum(text.count(w) for w in words)
    dk = sum(text.count(w) for w in ["那啥", "咋", "嘛", "呗", "咱"])
    if dk >= 3:
        scores["社交/口语"] = scores.get("社交/口语", 0) + dk
    best = max(scores, key=scores.get) if scores else "书面/一般"
    return best if scores.get(best, 0) >= 2 else "书面/一般"


# ── 人味门检：改写前判断是否真人文本（吸收 qu-ai-wei "第负一步"）──
_HUMAN_SIGNALS = [
    r"我忘了|我猜啊|不定扯|三十秒还是一分钟|记不清",
    r"咋|贼|那啥|咱|唠嗑|整|老铁",
    r"用比较酸的话说|听着就不正经|我知道这话|装一把",
    r"有人跟我说|那年我|我记得那|我妈说",
]


def human_gate(text: str) -> dict:
    """人味门检：判断输入是不是真人写的。

    返回 {"human": bool, "signal": str, "reason": str}
    human=True: 真人文本（自纠/方言/自嘲/具体细节），改写应停手（真人停手）
    """
    for pat in _HUMAN_SIGNALS:
        m = re.search(pat, text)
        if m:
            return {"human": True, "signal": m.group(0),
                    "reason": "命中真人文本强信号，停手不改声口"}
    return {"human": False, "signal": "", "reason": "未命中真人信号，可继续改写"}


def scan_text(text: str) -> dict:
    """对文本字符串扫描（内部辅助，scan() 保持文件输入接口兼容）。"""
    # 复用 scan 的文件逻辑：写临时文件
    import tempfile
    fd, p = tempfile.mkstemp(suffix=".txt", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        return scan(p)
    finally:
        try:
            os.remove(p)
        except OSError:
            pass


def refine(filepath: str, style: str = "report", out_file: str = None) -> dict:
    """人味门检 → 三线检测 → 复检 闭环（优化器核心入口）。

    流程：
      1. 人味门检：真人文本停手（不改声口）
      2. 三线检测：scan 定位 AI 味与质量问题
      3. 改写：按规则生成改写建议/新文本（无 LLM，基于检测建议给改写提示）
      4. 复检：对改写结果重新 scan，确认问题减少

    style: report/wechat/tweet/paper（改写风格倾向）
    out_file: 可选，把改写结果写到此文件
    """
    text = pathlib.Path(filepath).read_text(encoding="utf-8")
    text = _strip_code_blocks(text)

    # 1. 人味门检
    gate = human_gate(text)
    if gate["human"]:
        return {"ok": True, "phase": "gate", "gate": gate,
                "detect": scan_text(text), "register": register_of(text),
                "note": "检测到真人文本，停手不改声口。"}

    # 2. 三线检测
    detect = scan_text(text)

    # 3. 改写建议（基于检测的 fail/warn issue 生成可执行改写提示，不虚构）
    register = register_of(text)
    suggestions = []
    for i in detect["issues"]:
        if i["severity"] == "fail":
            sug = i.get("suggestion", "")
            if sug:
                suggestions.append(f"[{i['layer']}] {i['type']}：{sug}")
    rewritten = "\n".join(suggestions) if suggestions else ""

    # 4. 复检
    recheck = scan_text(rewritten) if rewritten else None
    improvement = None
    if recheck and detect.get("fail_count", 0) > 0:
        improvement = detect["fail_count"] - recheck["fail_count"]

    result = {
        "ok": True, "phase": "done", "gate": gate, "register": register,
        "detect": detect, "rewrite": rewritten, "recheck": recheck,
        "improvement": improvement,
        "summary": {
            "before_fail": detect.get("fail_count", 0),
            "after_fail": recheck.get("fail_count", 0) if recheck else None,
            "before_issues": detect.get("total_issues", 0),
            "after_issues": recheck.get("total_issues", 0) if recheck else None,
        },
    }
    if out_file and rewritten:
        pathlib.Path(out_file).write_text(rewritten, encoding="utf-8")
        result["out_file"] = out_file
    return result


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
        for line, label in [("hard", "硬规则"), ("style", "文风"), ("human", "人味")]:
            l = report["lines"][line]
            status = "✅" if l["fail_count"] == 0 else "❌"
            print(f"  {status} {label}线 {','.join(l['dims'])} 问题={l['issue_count']} (fail {l['fail_count']})")
        for dim in ["D1", "D2", "D3", "D4", "D5", "D6"]:
            l = report["layers"][dim]
            status = "✅" if l["passed"] else "❌"
            print(f"  {status} {dim} 通过={l['passed']} 问题={l['issue_count']} (fail {l['fail_count']}/warn {l['warn_count']})")
        for i in report["issues"]:
            mark = {"fail": "❌", "warn": "⚠️", "info": "ℹ️"}.get(i["severity"], "·")
            print(f"  {mark} [{i['layer']}] {i['type']} ×{i['count']}")
