import math

PALETTE = [
    "#2d5741", "#d4a853", "#1a7a8a", "#b84233", "#6b4c8a",
    "#c06030", "#2a6b8a", "#8a6b2a", "#3a7a5a", "#cc8844",
    "#5a3a7a", "#2a8a6b",
]


def _color(i: int) -> str:
    return PALETTE[i % len(PALETTE)]


def _money(v: float) -> str:
    return f"${v:,.0f}" if v == int(v) else f"${v:,.2f}"


def _short_date(d: str) -> str:
    parts = d.split("-")
    if len(parts) == 3:
        return f"{int(parts[1])}/{int(parts[2])}"
    return d


def bar_chart(
    labels: list[str],
    values: list[float],
    title: str = "",
    width: int = 520,
    bar_height: int = 28,
    gap: int = 6,
) -> str:
    if not labels:
        return ""
    left_margin = 120
    right_margin = 80
    top = 10
    plot_w = width - left_margin - right_margin
    chart_h = len(labels) * (bar_height + gap) - gap
    svg_h = top + chart_h + 10
    max_val = max(values) if max(values) > 0 else 1

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {svg_h}"'
        f' style="width:100%;font-family:-apple-system,system-ui,sans-serif;font-size:13px">'
    ]

    for i, (label, val) in enumerate(zip(labels, values)):
        y = top + i * (bar_height + gap)
        bar_w = max((val / max_val) * plot_w, 2)
        parts.append(
            f'<text x="{left_margin - 8}" y="{y + bar_height // 2 + 5}" text-anchor="end" font-size="12">{label}</text>'
            f'<rect x="{left_margin}" y="{y}" width="{bar_w:.1f}" height="{bar_height}" rx="4" fill="{_color(i)}"/>'
            f'<text x="{left_margin + bar_w + 6}" y="{y + bar_height // 2 + 5}" font-size="12">{_money(val)}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def pie_chart(
    labels: list[str],
    values: list[float],
    title: str = "",
    size: int = 240,
) -> str:
    if not labels or sum(values) == 0:
        return ""
    total = sum(values)
    cx, cy = size // 2, size // 2
    outer_r, inner_r = 100, 60
    legend_item_h = 24
    legend_top = size + 16
    legend_h = len(labels) * legend_item_h + 8
    svg_w = size
    svg_h = legend_top + legend_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}"'
        f' style="max-width:280px;margin:0 auto;font-family:-apple-system,system-ui,sans-serif;font-size:12px">'
    ]

    if len(labels) == 1:
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{outer_r}" fill="{_color(0)}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{inner_r}" fill="#fff8ef"/>'
        )
    else:
        angle = -math.pi / 2
        for i, (label, val) in enumerate(zip(labels, values)):
            sweep = (val / total) * 2 * math.pi
            if sweep < 0.01:
                angle += sweep
                continue
            x1 = cx + outer_r * math.cos(angle)
            y1 = cy + outer_r * math.sin(angle)
            x2 = cx + outer_r * math.cos(angle + sweep)
            y2 = cy + outer_r * math.sin(angle + sweep)
            ix1 = cx + inner_r * math.cos(angle + sweep)
            iy1 = cy + inner_r * math.sin(angle + sweep)
            ix2 = cx + inner_r * math.cos(angle)
            iy2 = cy + inner_r * math.sin(angle)
            large = 1 if sweep > math.pi else 0
            parts.append(
                f'<path d="M {x1:.2f} {y1:.2f} A {outer_r} {outer_r} 0 {large} 1 {x2:.2f} {y2:.2f}'
                f' L {ix1:.2f} {iy1:.2f} A {inner_r} {inner_r} 0 {large} 0 {ix2:.2f} {iy2:.2f} Z"'
                f' fill="{_color(i)}"/>'
            )
            angle += sweep

    parts.append(
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="11" fill="#888">Total</text>'
        f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" font-size="18" font-weight="700">{_money(total)}</text>'
    )

    for i, (label, val) in enumerate(zip(labels, values)):
        ly = legend_top + i * legend_item_h
        pct = val / total * 100
        parts.append(
            f'<rect x="0" y="{ly}" width="12" height="12" rx="2" fill="{_color(i)}"/>'
            f'<text x="18" y="{ly + 11}" font-size="12">{label} ({pct:.0f}%)</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def line_chart(
    dates: list[str],
    values: list[float],
    title: str = "",
    width: int = 520,
    height: int = 220,
) -> str:
    if not dates or not values:
        return ""
    left, right, top, bottom = 65, 20, 15, 60
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_val = max(values) if max(values) > 0 else 1
    n = len(dates)

    def px(i: int) -> float:
        return left + (i / max(n - 1, 1)) * plot_w

    def py(v: float) -> float:
        return top + plot_h - (v / max_val) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"'
        f' style="width:100%;font-family:-apple-system,system-ui,sans-serif;font-size:11px">'
    ]

    ticks = 5
    for i in range(ticks + 1):
        yv = max_val * i / ticks
        yp = py(yv)
        parts.append(
            f'<line x1="{left}" y1="{yp:.1f}" x2="{width - right}" y2="{yp:.1f}" stroke="#e0e0e0" stroke-dasharray="4"/>'
            f'<text x="{left - 8}" y="{yp + 4:.1f}" text-anchor="end" fill="#888">{_money(yv)}</text>'
        )

    pts_line = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(values))
    pts_area = f"{px(0):.1f},{top + plot_h:.1f} {pts_line} {px(n - 1):.1f},{top + plot_h:.1f}"
    parts.append(f'<polygon points="{pts_area}" fill="{PALETTE[0]}" opacity="0.18"/>')
    parts.append(f'<polyline points="{pts_line}" fill="none" stroke="{PALETTE[0]}" stroke-width="2.5"/>')

    for i, v in enumerate(values):
        parts.append(f'<circle cx="{px(i):.1f}" cy="{py(v):.1f}" r="3.5" fill="{PALETTE[0]}" stroke="white" stroke-width="1.5"/>')

    step = max(1, n // 7)
    for i in range(0, n, step):
        x = px(i)
        y = top + plot_h + 12
        parts.append(
            f'<text x="{x:.1f}" y="{y}" text-anchor="end" fill="#888" font-size="10"'
            f' transform="rotate(-45 {x:.1f} {y})">{_short_date(dates[i])}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)
