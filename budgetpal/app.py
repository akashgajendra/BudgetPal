import html
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

from budgetpal import analyzer, categorizer, parser, report, svg_charts

app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
app.secret_key = "budgetpal-local-only"


def _build_response(rows: list[dict], ollama_used: bool = False, ollama_warning: str | None = None) -> dict:
    df = analyzer.to_frame(rows)
    s = analyzer.summary(df)
    cats = analyzer.by_category(df)
    merchants = analyzer.top_merchants(df)
    daily = analyzer.daily_spend(df)

    bar_svg = svg_charts.bar_chart(cats["category"].tolist(), cats["total"].tolist()) if len(cats) else ""
    donut_svg = svg_charts.pie_chart(cats["category"].tolist(), cats["total"].tolist()) if len(cats) else ""
    line_svg = svg_charts.line_chart(
        [str(d) for d in daily.index], daily.values.tolist()
    ) if len(daily) else ""

    merchant_html = _table_html(merchants, {"merchant": "Merchant", "total": "Spent", "count": "Times"})
    txn_df = df.sort_values("date")[["date", "description", "category", "amount"]].copy()
    txn_df["date"] = txn_df["date"].dt.strftime("%Y-%m-%d")
    txn_html = _table_html(txn_df, {"date": "Date", "description": "Description", "category": "Category", "amount": "Amount"})

    display_rows = []
    for _, row in txn_df.iterrows():
        display_rows.append({
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        })

    return {
        "summary": {
            "total_spent": s["total_spent"],
            "largest_purchase": s["largest_purchase"],
            "transaction_count": s["transaction_count"],
            "average_transaction": s["average_transaction"],
        },
        "charts": {"bar": bar_svg, "donut": donut_svg, "line": line_svg},
        "tables": {"merchants": merchant_html, "transactions": txn_html},
        "rows": display_rows,
        "categories": sorted(set(categorizer.load_rules()) | {categorizer.UNCATEGORIZED}),
        "ollama_used": ollama_used,
        "ollama_warning": ollama_warning,
    }


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _table_html(df, columns: dict[str, str]) -> str:
    head = "".join(f"<th>{html.escape(label)}</th>" for label in columns.values())
    rows = []
    for _, row in df.iterrows():
        cells = []
        for key in columns:
            value = row[key]
            if isinstance(value, float):
                value = _money(value)
            cells.append(f"<td>{html.escape(str(value))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file or not file.filename.endswith(".pdf"):
        return jsonify({"error": "Please upload a PDF file."}), 400

    pdf_bytes = file.read()
    try:
        transactions, line_count = parser.parse_statement(pdf_bytes)
    except Exception:
        return jsonify({"error": "Could not read this PDF. The file may be corrupted or password-protected."}), 400

    if not transactions:
        return jsonify({"error": f"No transactions found ({line_count} text lines read). This format may not be supported yet."})

    result = categorizer.categorize(transactions, use_ollama=True)
    session["rows"] = result.rows

    return jsonify(_build_response(result.rows, result.ollama_used, result.ollama_warning))


@app.route("/recalculate", methods=["POST"])
def recalculate():
    data = request.get_json()
    updates = data.get("updates", {})
    rows = session.get("rows", [])

    sorted_rows = sorted(rows, key=lambda r: r["date"])
    for idx_str, category in updates.items():
        i = int(idx_str)
        if 0 <= i < len(sorted_rows):
            sorted_rows[i]["category"] = category

    session["rows"] = sorted_rows
    return jsonify(_build_response(sorted_rows))


@app.route("/download")
def download():
    rows = session.get("rows", [])
    if not rows:
        return "No data", 404
    df = analyzer.to_frame(rows)
    html_report = report.build_html(df)
    return html_report, 200, {
        "Content-Type": "text/html",
        "Content-Disposition": "attachment; filename=budgetpal-report.html",
    }



def run(port: int = 8000):
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    run()
