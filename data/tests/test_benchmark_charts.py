"""The documentation's benchmark charts are drawn from the benchmark's own report."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import importlib.util
import json
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "documentation" / "assets" / "proxy-benchmark.json"
SVG = "{http://www.w3.org/2000/svg}"


def _renderer():
    spec = importlib.util.spec_from_file_location("render_benchmark_charts", ROOT / "tools" / "render_benchmark_charts.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _texts(path: Path) -> list[str]:
    return [node.text or "" for node in ElementTree.parse(path).iter(f"{SVG}text")]


def test_three_charts_are_drawn_from_the_report(tmp_path):
    written = _renderer().render(json.loads(REPORT.read_text()), tmp_path)
    assert sorted(p.name for p in written) == [
        "proxy-benchmark-call.svg", "proxy-benchmark-p95.svg", "proxy-benchmark-rps.svg",
    ]


def test_the_call_chart_has_one_bar_per_path_with_its_measured_value(tmp_path):
    report = json.loads(REPORT.read_text())
    _renderer().render(report, tmp_path)
    chart = tmp_path / "proxy-benchmark-call.svg"
    assert len(list(ElementTree.parse(chart).iter(f"{SVG}rect"))) == 5
    assert f"{report['per_call']['proxy_call']['mean_us']:,.1f} us" in _texts(chart)


def test_the_line_charts_name_both_series(tmp_path):
    _renderer().render(json.loads(REPORT.read_text()), tmp_path)
    for name in ("proxy-benchmark-rps.svg", "proxy-benchmark-p95.svg"):
        labels = " ".join(_texts(tmp_path / name))
        assert "After: proxy" in labels and "Before: HTTP" in labels


def test_the_published_charts_match_the_published_report(tmp_path):
    _renderer().render(json.loads(REPORT.read_text()), tmp_path)
    for name in ("proxy-benchmark-call.svg", "proxy-benchmark-rps.svg", "proxy-benchmark-p95.svg"):
        assert (tmp_path / name).read_bytes() == (REPORT.parent / name).read_bytes(), name
