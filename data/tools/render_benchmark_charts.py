"""Render the internal proxy benchmark report as SVG charts for the documentation.

Reads the JSON that `tests/benchmark_internal_proxy.py --json` writes and draws
three self-contained SVG files into `documentation/assets/`:

- `proxy-benchmark-call.svg` - mean cost of one call, five paths, log scale;
- `proxy-benchmark-rps.svg`  - requests per second by concurrent clients;
- `proxy-benchmark-p95.svg`  - p95 latency by concurrent clients, log scale.

The charts follow the reader's light or dark preference. The two series
colours were checked for colour-blind separation in both themes.

    python tools/render_benchmark_charts.py documentation/assets/proxy-benchmark.json
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "documentation" / "assets"
SVG_NS = "http://www.w3.org/2000/svg"

THEME = """
svg { --ink: #0e1726; --ink-2: #48546a; --grid: #e3e8ef; --rule: #c9d1dc;
      --after: #2a78d6; --before: #eb6834; --neutral: #8a94a6; }
@media (prefers-color-scheme: dark) {
  svg { --ink: #f3f5f9; --ink-2: #b8c1d1; --grid: #2a3442; --rule: #3a4556;
        --after: #3987e5; --before: #d95926; --neutral: #7d879a; }
}
text { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; fill: var(--ink-2); }
.title { font-size: 14px; font-weight: 700; fill: var(--ink); }
.value { fill: var(--ink); font-weight: 600; }
.grid { stroke: var(--grid); stroke-width: 1; }
.base { stroke: var(--rule); stroke-width: 1; }
"""

#: Colour role per per-call path and per end-to-end route.
GROUP = {
    "direct_method_call": "neutral",
    "proxy_call": "after",
    "proxy_dispatch": "after",
    "http_over_tcp_keepalive": "before",
    "kernel_in_process_asgi": "before",
}
PATH_LABEL = {
    "direct_method_call": "Direct method call",
    "proxy_dispatch": "Proxy.dispatch",
    "proxy_call": "Proxy.call",
    "http_over_tcp_keepalive": "HTTP over TCP",
    "kernel_in_process_asgi": "Kernel in process",
}
ROUTE_LABEL = {"proxy": "After: proxy", "loopback": "Before: HTTP"}
ROUTE_GROUP = {"proxy": "after", "loopback": "before"}


def _node(parent: ElementTree.Element, tag: str, text: str = "", **attrs: object) -> ElementTree.Element:
    node = ElementTree.SubElement(parent, tag, {k.replace("_", "-"): str(v) for k, v in attrs.items()})
    if text:
        node.text = text
    return node


def _canvas(width: int, height: int, title: str) -> ElementTree.Element:
    svg = ElementTree.Element("svg", {"xmlns": SVG_NS, "viewBox": f"0 0 {width} {height}", "role": "img"})
    _node(svg, "title", title)
    _node(svg, "style", THEME)
    _node(svg, "text", title, x=16, y=24, **{"class": "title"})
    return svg


def _log_scale(low: float, high: float, start: float, end: float) -> Callable[[float], float]:
    span = math.log10(high) - math.log10(low)
    return lambda value: start + (math.log10(value) - math.log10(low)) / span * (end - start)


def call_chart(per_call: dict) -> ElementTree.Element:
    """Horizontal bars: mean cost of one call per path, log scale."""
    order = ["direct_method_call", "proxy_dispatch", "proxy_call", "http_over_tcp_keepalive", "kernel_in_process_asgi"]
    width, left, right, top, row = 760, 170, 90, 48, 40
    height = top + row * len(order) + 36
    svg = _canvas(width, height, "Mean cost of one call between modules (log scale)")
    x = _log_scale(1, 3000, left, width - right)
    for tick, label in ((1, "1 us"), (10, "10 us"), (100, "100 us"), (1000, "1 ms")):
        _node(svg, "line", x1=x(tick), x2=x(tick), y1=top - 6, y2=height - 30, **{"class": "grid"})
        _node(svg, "text", label, x=x(tick), y=height - 12, text_anchor="middle")
    for index, key in enumerate(order):
        mean = per_call[key]["mean_us"]
        y = top + index * row
        _node(svg, "text", PATH_LABEL[key], x=left - 10, y=y + 15, text_anchor="end")
        _node(svg, "rect", x=x(1), y=y + 2, width=max(4, x(mean) - x(1)), height=18, rx=4, fill=f"var(--{GROUP[key]})")
        _node(svg, "text", f"{mean:,.1f} us", x=x(mean) + 8, y=y + 15, **{"class": "value"})
    return svg


def _line_chart(rows: list[dict], field: str, title: str, y: Callable[[float], float],
                ticks: list[tuple[float, str]], end_label: Callable[[float], str]) -> ElementTree.Element:
    width, left, right, top, bottom = 780, 70, 200, 48, 300
    svg = _canvas(width, bottom + 40, title)
    levels = sorted({row["clients"] for row in rows})
    step = (width - left - right) / (len(levels) - 1)
    for tick, label in ticks:
        _node(svg, "line", x1=left, x2=width - right, y1=y(tick), y2=y(tick), **{"class": "grid"})
        _node(svg, "text", label, x=left - 8, y=y(tick) + 4, text_anchor="end")
    for index, clients in enumerate(levels):
        _node(svg, "text", str(clients), x=left + index * step, y=bottom + 20, text_anchor="middle")
    _node(svg, "text", "concurrent clients", x=(left + width - right) / 2, y=bottom + 36, text_anchor="middle")
    for route in ("loopback", "proxy"):
        series = sorted((r for r in rows if r["route"] == route), key=lambda r: r["clients"])
        points = [(left + levels.index(r["clients"]) * step, y(r[field])) for r in series]
        color = f"var(--{ROUTE_GROUP[route]})"
        _node(svg, "polyline", points=" ".join(f"{px:.1f},{py:.1f}" for px, py in points),
              fill="none", stroke=color, stroke_width=2, stroke_linejoin="round")
        for px, py in points:
            _node(svg, "circle", cx=f"{px:.1f}", cy=f"{py:.1f}", r=5, fill=color)
        last_x, last_y = points[-1]
        _node(svg, "text", f"{ROUTE_LABEL[route]} {end_label(series[-1][field])}",
              x=last_x + 12, y=last_y + 4, **{"class": "value"})
    return svg


def rps_chart(rows: list[dict]) -> ElementTree.Element:
    """Requests per second by concurrent clients, linear scale from zero."""
    top, bottom, high = 48, 300, 1600
    return _line_chart(
        rows, "per_second", "Requests per second, module A calling module B",
        lambda v: bottom - v / high * (bottom - top),
        [(v, f"{v:,}") for v in (0, 400, 800, 1200, 1600)],
        lambda v: f"{v:,.0f} req/s",
    )


def p95_chart(rows: list[dict]) -> ElementTree.Element:
    """p95 latency by concurrent clients, log scale (milliseconds)."""
    return _line_chart(
        [{**r, "p95_ms": r["p95_us"] / 1000} for r in rows], "p95_ms",
        "p95 latency, module A calling module B (log scale)",
        _log_scale(0.5, 20000, 300, 48),
        [(1, "1 ms"), (10, "10 ms"), (100, "100 ms"), (1000, "1 s"), (10000, "10 s")],
        lambda v: f"{v / 1000:,.1f} s" if v >= 1000 else f"{v:,.0f} ms",
    )


def render(report: dict, output: Path = ASSETS) -> list[Path]:
    """Write the three charts and return their paths."""
    ElementTree.register_namespace("", SVG_NS)
    charts = {
        "proxy-benchmark-call.svg": call_chart(report["per_call"]),
        "proxy-benchmark-rps.svg": rps_chart(report["end_to_end"]),
        "proxy-benchmark-p95.svg": p95_chart(report["end_to_end"]),
    }
    written = []
    for name, svg in charts.items():
        path = output / name
        ElementTree.ElementTree(svg).write(path, encoding="utf-8", xml_declaration=True)
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", help="JSON written by tests/benchmark_internal_proxy.py --json")
    parser.add_argument("--output", default=str(ASSETS), help="directory to write the SVG files into")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    for path in render(report, Path(args.output)):
        print(path)


if __name__ == "__main__":
    main()
