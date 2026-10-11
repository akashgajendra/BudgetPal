# BudgetPal

A local-first bank statement analyzer. Upload a PDF, get categorized transactions, interactive charts, and a downloadable spending report. Everything runs on your machine — no data leaves your computer.

## What it does

1. **Parses** bank statement PDFs using pdfplumber (regex-based row extraction)
2. **Categorizes** transactions — keyword rules first, then a local AI model (Ollama + gemma3:4b) for anything the rules don't catch
3. **Shows** an interactive dashboard with spending breakdowns, top merchants, and daily trends
4. **Exports** a self-contained HTML report with inline SVG charts you can open anywhere or print to PDF

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/yourusername/BudgetPal.git
cd BudgetPal
uv sync
```

### AI categorization (optional)

Install [Ollama](https://ollama.com) and pull the model:

```bash
ollama pull gemma3:4b
ollama serve   # if not already running
```

BudgetPal works without Ollama — transactions that don't match keyword rules will be labeled "other" instead of AI-categorized. The app warns you when Ollama isn't available.

## Web app (Streamlit dashboard)

```bash
uv run budgetpal dashboard
```

This opens the dashboard at `http://localhost:8501`. From there:

- **Drag and drop** a bank statement PDF
- **Toggle AI categorization** on or off
- **Review and fix** categories inline — edits update charts and the report instantly
- **Download** the HTML report with the button at the bottom

You can also launch it directly:

```bash
uv run streamlit run budgetpal/app.py
```

## CLI

### Generate a report

```bash
uv run budgetpal report statement.pdf
```

This parses the PDF, categorizes transactions (with Ollama if available), prints a summary to the terminal, and saves `budgetpal-report.html` in the current directory.

Options:

| Flag | Description |
|------|-------------|
| `-o`, `--output PATH` | Save the HTML report to a specific path (default: `budgetpal-report.html`) |
| `--no-ollama` | Skip AI categorization, use keyword rules only |
| `--no-report` | Print the summary to the terminal without generating an HTML file |

Examples:

```bash
# Save report to a specific file
uv run budgetpal report statement.pdf -o ~/Desktop/october-report.html

# Quick terminal summary, no file
uv run budgetpal report statement.pdf --no-report

# Keywords only, no AI
uv run budgetpal report statement.pdf --no-ollama
```

### Launch the dashboard

```bash
uv run budgetpal dashboard
uv run budgetpal dashboard --port 9000   # custom port
```

## How categorization works

BudgetPal uses a two-pass approach:

1. **Keyword matching** — `categories.yaml` maps keywords to categories (e.g., "starbucks" → dining, "safeway" → groceries). This is instant and handles most common merchants.

2. **AI fallback** — transactions that don't match any keyword get batched (20 at a time) and sent to a local Ollama model. The model sees only the transaction description and picks from the predefined category list. Temperature is set to 0 for consistent results.

You can edit `categories.yaml` to add your own rules. Any merchant you add there will be matched by keywords and skip the AI entirely.

### Categories

housing, utilities, groceries, transportation, insurance, health, dining, shopping, entertainment, subscriptions, travel, personal_care, income, transfer, fees, debt, other

## Privacy

- All processing happens locally — PDF parsing, categorization, chart generation
- Ollama runs on your machine at `localhost:11434`
- No network requests except to your local Ollama instance
- No telemetry, no accounts, no cloud
