#!/usr/bin/env python3
"""test_zh_writing.py — 中文写作质量检查器 6 维度测试（pytest）"""
import os
import sys
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zh_writing_checker as zwc

BAD = pathlib.Path(__file__).parent / "test_sample.md"
GOOD = "今天天气很好。我们去公园散步。湖边的柳树绿了，孩子在水边喂鱼，笑声很轻。\n傍晚回家，家里炖了汤，香气飘满整个屋子。这样的日子平淡，却让人安心。"


def _scan(text, suffix=".md"):
    """对文本字符串直接扫描（复用库内 scan_text，避免重复临时文件逻辑）。"""
    return zwc.scan_text(text)


def test_version():
    assert zwc.VERSION == "0.1.2"


def test_six_dimensions_present():
    r = _scan("赋能 缘份。")
    assert set(r["layers"].keys()) == {"D1", "D2", "D3", "D4", "D5", "D6"}


def test_d1_typo_and_variant():
    r = _scan("他寒喧了几句，说这是缘份。")
    types = {i["type"] for i in r["issues"]}
    assert any("寒喧" in t for t in types)      # 错别字
    assert any("缘份" in t for t in types)      # 异形词


def test_d2_punctuation_fail():
    r = _scan("他来了,然后走了。")
    assert any(i["layer"] == "D2" and i["severity"] == "fail" for i in r["issues"])


def test_d3_grammar_fail():
    r = _scan("由于时间紧张所致，项目延期。")
    assert any(i["layer"] == "D3" and "由于" in i["type"] for i in r["issues"])


def test_d5_ai_flavor():
    r = _scan("我们要赋能业务，形成闭环。")
    types = {i["type"] for i in r["issues"]}
    assert any("赋能" in t for t in types)
    assert any("闭环" in t for t in types)


def test_clean_text_no_false_positive():
    r = _scan(GOOD)
    assert r["fail_count"] == 0


def test_scan_bad_sample_finds_issues():
    r = zwc.scan(str(BAD))
    assert r["total_issues"] >= 5
    assert r["fail_count"] >= 1


def test_three_lines_present():
    """三线汇总字段存在且维度归属正确。"""
    r = _scan("赋能 缘份。")
    assert set(r["lines"].keys()) == {"hard", "style", "human"}
    assert r["lines"]["hard"]["dims"] == ["D1", "D2", "D3", "D4"]
    assert r["lines"]["style"]["dims"] == ["D5"]
    assert r["lines"]["human"]["dims"] == ["D6"]


def test_lines_counts_match_dimensions():
    """三线 issue_count = 所属维度 issue_count 之和。"""
    r = _scan(str(BAD))
    for line in ["hard", "style", "human"]:
        total = sum(r["layers"][d]["issue_count"] for d in r["lines"][line]["dims"])
        assert r["lines"][line]["issue_count"] == total


def test_json_compat_layer_field():
    """JSON 兼容：每个 issue 仍带 layer: D1-D6 字段。"""
    r = _scan(str(BAD))
    assert all(i["layer"] in {"D1", "D2", "D3", "D4", "D5", "D6"} for i in r["issues"])
