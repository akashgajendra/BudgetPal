import html

import pandas as pd

from budgetpal import analyzer, svg_charts


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _table(df: pd.DataFrame, columns: dict[str, str]) -> str:
    head = "".join(f"<th>{html.escape(label)}</th>" for label in columns.values())
    rows = []
    for _, row in df.iterrows():
        cells = []
        for key in columns:
            value = row[key]
            if isinstance(value, float):
                value = _money(value) if key != "share" else f"{value:.1%}"
            cells.append(f"<td>{html.escape(str(value))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def build_html(df: pd.DataFrame, title: str = "BudgetPal Spending Report") -> str:
    s = analyzer.summary(df)
    cats = analyzer.by_category(df)
    merchants = analyzer.top_merchants(df)
    daily = analyzer.daily_spend(df)

    period = "No transactions"
    if s["start"] is not None:
        period = f"{s['start']:%b %d, %Y} &ndash; {s['end']:%b %d, %Y}"

    bar_svg = svg_charts.bar_chart(
        cats["category"].tolist(), cats["total"].tolist(), title="Spending by Category"
    ) if len(cats) else ""

    donut_svg = svg_charts.pie_chart(
        cats["category"].tolist(), cats["total"].tolist(), title="Spending Breakdown"
    ) if len(cats) else ""

    line_svg = svg_charts.line_chart(
        [str(d) for d in daily.index], daily.values.tolist(), title="Daily Spending"
    ) if len(daily) else ""

    cat_table = _table(cats, {"category": "Category", "total": "Total", "count": "Transactions", "share": "Share"})
    merchant_table = _table(merchants, {"merchant": "Merchant", "total": "Total", "count": "Transactions"})

    txn_df = df.sort_values("date")[["date", "description", "category", "amount"]].copy()
    txn_df["date"] = txn_df["date"].dt.strftime("%Y-%m-%d")
    txn_table = _table(txn_df, {"date": "Date", "description": "Description", "category": "Category", "amount": "Amount"})

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color: #1c1917; max-width: 920px; margin: 40px auto; padding: 0 20px; line-height: 1.5; background: #f5f3ef; }}
h1 {{ margin-bottom: 4px; font-weight: 800; letter-spacing: -0.5px; }}
h2 {{ font-size: 18px; font-weight: 600; color: #1c1917; margin-top: 40px; margin-bottom: 16px; }}
.muted {{ color: #78716c; margin-bottom: 24px; font-size: 14px; }}
.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 28px 0; }}
.kpi {{ background: #fff; border: 1px solid #e7e5e4; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }}
.kpi span {{ display: block; font-size: 11px; font-weight: 600; color: #78716c; text-transform: uppercase; letter-spacing: 0.8px; }}
.kpi b {{ display: block; font-size: 26px; margin-top: 6px; color: #1c1917; }}
.charts {{ display: grid; grid-template-columns: 3fr 2fr; gap: 32px; margin: 32px 0; align-items: start; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0 32px; font-size: 13px; }}
th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e7e5e4; }}
th {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #78716c; background: #f5f3ef; }}
tr:hover td {{ background: #faf9f7; }}
svg {{ display: block; }}
@media print {{ body {{ margin: 0; }} .kpi {{ break-inside: avoid; }} }}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="muted">{period}</div>

<div class="kpis">
  <div class="kpi"><span>Total Spent</span><b>{_money(s['total_spent'])}</b></div>
  <div class="kpi"><span>Largest Purchase</span><b>{_money(s['largest_purchase'])}</b></div>
  <div class="kpi"><span>Transactions</span><b>{s['transaction_count']}</b></div>
  <div class="kpi"><span>Avg. Purchase</span><b>{_money(s['average_transaction'])}</b></div>
</div>

<div class="charts">
  <div>{bar_svg}</div>
  <div>{donut_svg}</div>
</div>

<h2>Spending Over Time</h2>
{line_svg}

<h2>Category Breakdown</h2>
{cat_table}

<h2>Top Merchants</h2>
{merchant_table}

<h2>All Transactions</h2>
{txn_table}

</body></html>"""
