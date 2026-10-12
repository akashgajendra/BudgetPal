import html
import math
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from budgetpal import analyzer, categorizer, parser, report, svg_charts

app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))

_store: dict[str, list[dict]] = {"rows": []}


def _safe(v: float) -> float:
    if math.isnan(v) or math.isinf(v):
        return 0.0
    return v


def _build_response(rows: list[dict], ollama_used: bool = False, ollama_warning: str | None = None) -> dict:
    df = analyzer.to_frame(rows)
    s = analyzer.summary(df)
    cats = analyzer.by_category(df)
    merchants = analyzer.top_merchants(df, n=5)
    daily = analyzer.daily_spend(df)

    bar_svg = svg_charts.bar_chart(cats["category"].tolist(), cats["total"].tolist()) if len(cats) else ""
    donut_svg = svg_charts.pie_chart(cats["category"].tolist(), cats["total"].tolist()) if len(cats) else ""
    line_svg = svg_charts.line_chart(
        [str(d) for d in daily.index], daily.values.tolist()
    ) if len(daily) else ""

    merchant_html = _table_html(merchants, {"merchant": "Merchant", "total": "Spent", "count": "Times"})
    txn_df = df[["date", "description", "category", "amount"]].copy()
    if not txn_df.empty:
        txn_df["date"] = txn_df["date"].dt.strftime("%b %d")

    has_source = any("source" in r for r in rows)
    display_rows = []
    for i, (_, row) in enumerate(txn_df.iterrows()):
        d = {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": _safe(float(row["amount"])),
        }
        if has_source and i < len(rows):
            d["source"] = rows[i].get("source", "")
        display_rows.append(d)

    return {
        "summary": {
            "total_spent": _safe(s["total_spent"]),
            "largest_purchase": _safe(s["largest_purchase"]),
            "transaction_count": s["transaction_count"],
            "average_transaction": _safe(s["average_transaction"]),
            "start": s["start"].strftime("%b %d") if s.get("start") is not None else None,
            "end": s["end"].strftime("%b %d") if s.get("end") is not None else None,
        },
        "charts": {"bar": bar_svg, "donut": donut_svg, "line": line_svg},
        "tables": {"merchants": merchant_html},
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


@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    if not files:
        file = request.files.get("file")
        if file:
            files = [file]
    files = [f for f in files if f.filename and f.filename.endswith(".pdf")]
    if not files:
        return jsonify({"error": "Please upload at least one PDF file."}), 400

    all_rows = []
    ollama_used = False
    ollama_warning = None
    errors = []

    for file in files:
        pdf_bytes = file.read()
        source = file.filename.rsplit(".", 1)[0]
        try:
            transactions, line_count = parser.parse_statement(pdf_bytes)
        except Exception:
            errors.append(f"{file.filename}: could not read (corrupted or password-protected)")
            continue

        if not transactions:
            errors.append(f"{file.filename}: no transactions found ({line_count} lines read)")
            continue

        result = categorizer.categorize(transactions, use_ollama=True)
        for r in result.rows:
            if not isinstance(r["date"], str):
                r["date"] = r["date"].strftime("%Y-%m-%d")
            r["source"] = source
        all_rows.extend(result.rows)
        if result.ollama_used:
            ollama_used = True
        if result.ollama_warning:
            ollama_warning = result.ollama_warning

    if not all_rows:
        msg = "No transactions found in any file."
        if errors:
            msg += " " + "; ".join(errors)
        return jsonify({"error": msg}), 400

    all_rows.sort(key=lambda r: r["date"])
    _store["rows"] = all_rows

    resp = _build_response(all_rows, ollama_used, ollama_warning)
    if errors:
        resp["partial_errors"] = errors
    return jsonify(resp)


@app.route("/recalculate", methods=["POST"])
def recalculate():
    data = request.get_json()
    updates = data.get("updates", {})
    rows = list(_store["rows"])

    for idx_str, category in updates.items():
        i = int(idx_str)
        if 0 <= i < len(rows):
            rows[i]["category"] = category

    _store["rows"] = rows
    return jsonify(_build_response(rows))


@app.route("/remove", methods=["POST"])
def remove():
    data = request.get_json()
    idx = data.get("index")
    rows = list(_store["rows"])
    if isinstance(idx, int) and 0 <= idx < len(rows):
        rows.pop(idx)
    _store["rows"] = rows
    return jsonify(_build_response(rows))


@app.route("/download")
def download():
    rows = _store["rows"]
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
