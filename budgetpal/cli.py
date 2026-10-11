import webbrowser
from pathlib import Path

import click

from budgetpal import analyzer, categorizer, parser, report


@click.group()
@click.version_option(package_name="budgetpal")
def cli():
    """BudgetPal — local bank statement analyzer."""


@cli.command()
@click.argument("statement", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", default="budgetpal-report.html", help="Path for the HTML report.")
@click.option("--no-ollama", is_flag=True, help="Skip AI categorization, use keyword rules only.")
@click.option("--no-report", is_flag=True, help="Print summary only, skip HTML report generation.")
def report_cmd(statement: Path, output: str, no_ollama: bool, no_report: bool):
    """Parse a bank statement PDF and generate a spending report."""
    pdf_bytes = statement.read_bytes()
    transactions, line_count = parser.parse_statement(pdf_bytes)

    if not transactions:
        click.echo(f"No transactions found in {statement.name} ({line_count} text lines read).")
        raise SystemExit(1)

    click.echo(f"Parsed {len(transactions)} transactions from {statement.name}")

    result = categorizer.categorize(transactions, use_ollama=not no_ollama)
    if result.ollama_warning:
        click.secho(f"  ! {result.ollama_warning}", fg="yellow")
    elif result.ollama_used:
        click.echo("  AI categorization complete")

    df = analyzer.to_frame(result.rows)
    s = analyzer.summary(df)
    cats = analyzer.by_category(df)
    merchants = analyzer.top_merchants(df, n=5)

    click.echo()
    if s["start"] is not None:
        click.echo(f"  Period:       {s['start']:%b %d, %Y} - {s['end']:%b %d, %Y}")
    click.echo(f"  Total spent:  ${s['total_spent']:,.2f}")
    click.echo(f"  Money in:     ${s['total_income']:,.2f}")
    click.echo(f"  Transactions: {s['transaction_count']}")
    click.echo(f"  Avg purchase: ${s['average_transaction']:,.2f}")

    click.echo()
    click.echo("  Top categories:")
    for _, row in cats.head(5).iterrows():
        click.echo(f"    {row['category']:20s} ${row['total']:>10,.2f}  ({row['share']:.0%})")

    click.echo()
    click.echo("  Top merchants:")
    for _, row in merchants.iterrows():
        click.echo(f"    {row['merchant']:20s} ${row['total']:>10,.2f}  ({row['count']}x)")

    if not no_report:
        html = report.build_html(df)
        Path(output).write_text(html)
        click.echo()
        click.secho(f"  Report saved to {output}", fg="green")


@cli.command()
@click.option("--port", default=8000, help="Port for the web server.")
def dashboard(port: int):
    """Launch the BudgetPal dashboard in your browser."""
    from budgetpal.app import run

    click.echo(f"BudgetPal running at http://localhost:{port}")
    webbrowser.open(f"http://localhost:{port}")
    run(port=port)


cli.add_command(report_cmd, name="report")
