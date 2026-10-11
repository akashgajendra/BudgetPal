import math

PALETTE = [
    "#059669", "#f97316", "#0ea5e9", "#e11d48", "#eab308",
    "#8b5cf6", "#14b8a6", "#f43f5e", "#6366f1", "#84cc16",
    "#d946ef", "#0891b2",
]


def _color(i: int) -> str:
    return PALETTE[i % len(PALETTE)]


def _money(v: float) -> str:
    return f"${v:,.0f}" if v == int(v) else f"${v:,.2f}"


def bar_chart(
    labels: list[str],
    values: list[float],
    title: str = "",
    width: int = 620,
    bar_height: int = 28,
    gap: int = 6,
) -> str:
    if not labels:
        return ""
    left_margin = 130
    right_margin = 80
    top = 40 if title else 10
    plot_w = width - left_margin - right_margin
    chart_h = len(labels) * (bar_height + gap) - gap
    svg_h = top + chart_h + 10
    max_val = max(values) if max(values) > 0 else 1

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {svg_h}"'
        f' style="max-width:100%;font-family:-apple-system,system-ui,sans-serif;font-size:13px">'
    ]
    if title:
        parts.append(f'<text x="{width // 2}" y="22" text-anchor="middle" font-size="15" font-weight="600">{title}</text>')

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
    size: int = 380,
) -> str:
    if not labels or sum(values) == 0:
        return ""
    total = sum(values)
    cx, cy = size // 2, size // 2
    outer_r, inner_r = 130, 78
    legend_x = size + 20
    svg_w = size + 220

    legend_h = len(labels) * 22 + 10
    svg_h = max(size, legend_h) + (30 if title else 0)
    top_offset = 30 if title else 0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}"'
        f' style="max-width:100%;font-family:-apple-system,system-ui,sans-serif;font-size:12px">'
    ]
    if title:
        parts.append(f'<text x="{svg_w // 2}" y="20" text-anchor="middle" font-size="15" font-weight="600">{title}</text>')

    if len(labels) == 1:
        parts.append(
            f'<circle cx="{cx}" cy="{cy + top_offset}" r="{outer_r}" fill="{_color(0)}"/>'
            f'<circle cx="{cx}" cy="{cy + top_offset}" r="{inner_r}" fill="white"/>'
        )
    else:
        angle = -math.pi / 2
        for i, (label, val) in enumerate(zip(labels, values)):
            sweep = (val / total) * 2 * math.pi
            if sweep < 0.01:
                angle += sweep
                continue
            x1 = cx + outer_r * math.cos(angle)
            y1 = cy + top_offset + outer_r * math.sin(angle)
            x2 = cx + outer_r * math.cos(angle + sweep)
            y2 = cy + top_offset + outer_r * math.sin(angle + sweep)
            ix1 = cx + inner_r * math.cos(angle + sweep)
            iy1 = cy + top_offset + inner_r * math.sin(angle + sweep)
            ix2 = cx + inner_r * math.cos(angle)
            iy2 = cy + top_offset + inner_r * math.sin(angle)
            large = 1 if sweep > math.pi else 0
            parts.append(
                f'<path d="M {x1:.2f} {y1:.2f} A {outer_r} {outer_r} 0 {large} 1 {x2:.2f} {y2:.2f}'
                f' L {ix1:.2f} {iy1:.2f} A {inner_r} {inner_r} 0 {large} 0 {ix2:.2f} {iy2:.2f} Z"'
                f' fill="{_color(i)}"/>'
            )
            angle += sweep

    # total in center
    parts.append(
        f'<text x="{cx}" y="{cy + top_offset - 4}" text-anchor="middle" font-size="11" fill="#666">Total</text>'
        f'<text x="{cx}" y="{cy + top_offset + 16}" text-anchor="middle" font-size="18" font-weight="700">{_money(total)}</text>'
    )

    # legend
    for i, (label, val) in enumerate(zip(labels, values)):
        ly = top_offset + 10 + i * 22
        pct = val / total * 100
        parts.append(
            f'<rect x="{legend_x}" y="{ly}" width="12" height="12" rx="2" fill="{_color(i)}"/>'
            f'<text x="{legend_x + 18}" y="{ly + 11}" font-size="12">{label} ({pct:.0f}%)</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def line_chart(
    dates: list[str],
    values: list[float],
    title: str = "",
    width: int = 620,
    height: int = 260,
) -> str:
    if not dates or not values:
        return ""
    left, right, top, bottom = 65, 20, 40 if title else 15, 50
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
        f' style="max-width:100%;font-family:-apple-system,system-ui,sans-serif;font-size:11px">'
    ]
    if title:
        parts.append(f'<text x="{width // 2}" y="22" text-anchor="middle" font-size="15" font-weight="600">{title}</text>')

    # y-axis grid
    ticks = 5
    for i in range(ticks + 1):
        yv = max_val * i / ticks
        yp = py(yv)
        parts.append(
            f'<line x1="{left}" y1="{yp:.1f}" x2="{width - right}" y2="{yp:.1f}" stroke="#e0e0e0" stroke-dasharray="4"/>'
            f'<text x="{left - 8}" y="{yp + 4:.1f}" text-anchor="end" fill="#888">{_money(yv)}</text>'
        )

    # area fill
    pts_line = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(values))
    pts_area = f"{px(0):.1f},{top + plot_h:.1f} {pts_line} {px(n - 1):.1f},{top + plot_h:.1f}"
    parts.append(f'<polygon points="{pts_area}" fill="{PALETTE[0]}" opacity="0.12"/>')
    parts.append(f'<polyline points="{pts_line}" fill="none" stroke="{PALETTE[0]}" stroke-width="2.5"/>')

    # dots
    for i, v in enumerate(values):
        parts.append(f'<circle cx="{px(i):.1f}" cy="{py(v):.1f}" r="3.5" fill="{PALETTE[0]}" stroke="white" stroke-width="1.5"/>')

    # x-axis labels
    step = max(1, n // 8)
    for i in range(0, n, step):
        parts.append(
            f'<text x="{px(i):.1f}" y="{height - 8}" text-anchor="middle" fill="#888" font-size="10">'
            f'{dates[i]}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)
