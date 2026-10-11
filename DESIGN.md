# BudgetPal Design Document

## Overview
BudgetPal is a local-first bank statement analyzer. Upload a PDF, get AI-categorized
transactions, interactive charts, and a downloadable HTML report. No data leaves your machine.

## Architecture

### Frontend: Flask + custom HTML/CSS/JS
Streamlit was dropped — it controls the markup, forces its own widget styles, and every
visual fix is a CSS hack targeting unstable internal class names. Flask serves a single
HTML template with full design control.

One route serves the page and handles the upload. The backend modules (parser, categorizer,
analyzer, report, svg_charts) are unchanged.

### Backend modules
- parser.py — pdfplumber extracts text, regex pulls date/description/amount rows
- categorizer.py — keyword rules first, Ollama (gemma3:4b) fallback for unmatched
- analyzer.py — pandas: summaries, category grouping, top merchants, daily spend
- svg_charts.py — pure-Python inline SVG chart generators (bar, donut, line)
- report.py — assembles self-contained HTML report with inline SVG
- ollama_client.py — HTTP client for local Ollama instance

## Visual Design

### Color system
Base: warm neutral, not pure white or pure black.
- Background: #f7f7f5 (warm off-white)
- Surface/cards: #ffffff
- Text primary: #1a1a1a
- Text secondary: #6b7280
- Border: #e5e5e3
- Accent: #2563eb (blue — used sparingly for CTAs and active states)

Chart palette (must be distinguishable, accessible, print-friendly):
- #2563eb (blue), #dc2626 (red), #16a34a (green), #f59e0b (amber),
  #7c3aed (violet), #ec4899 (pink), #0891b2 (cyan), #ea580c (orange),
  #4b5563 (gray), #84cc16 (lime), #6366f1 (indigo), #14b8a6 (teal)

### Typography
System font stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif.
- Page title: 28px, weight 800, tracking -0.5px
- Section headers: 18px, weight 600
- Body/tables: 14px, weight 400
- Labels/captions: 12px, weight 500, uppercase, letter-spacing 0.5px

### Layout
Single-column centered layout, max-width 960px. Sections separated by generous whitespace
(48px between major sections), not horizontal rules.

Upload area: large drop zone with dashed border, centered icon and text, hover state
darkens border. Full width.

KPI cards: 4-up row, equal width, subtle border, no heavy background. Numbers are large
and bold, labels are small uppercase.

Charts: bar chart and donut side by side (60/40 split). Line chart full width below.
All charts are inline SVG, responsive.

Tables: minimal — no zebra stripes, just bottom borders on rows. Header row has a light
background. Hover highlights row.

Download button: full-width at the bottom, dark background (#1a1a1a), white text,
rounded corners, prominent.

### Responsive
The page works at phone width (~400px). Charts stack vertically, KPI cards wrap to 2x2,
tables scroll horizontally if needed.

## Technical Challenges

### PDF parsing
Every bank formats statements differently. The regex approach handles common layouts
(date at line start, amount at line end) but will fail on:
- Multi-line transaction descriptions
- Tables with column headers that look like transactions
- PDFs that use spacing instead of text structure (fixed-width columns)
- Statements that list debits and credits in separate columns

Mitigation: the parser returns a line count so the UI can warn when few/no transactions
are found. Future improvement: use pdfplumber's table extraction as a second pass.

### PII in transaction data
Bank statements contain account holder names, account numbers, addresses, and sometimes
partial SSNs in headers/footers. These must NOT be sent to Ollama.

Approach: parser strips lines that match PII patterns (account numbers, names in
header position, SSN fragments) before returning transactions. Only the transaction
description field goes to the LLM — never raw page text.

### Ollama reliability
- Model may not be pulled (gemma3:4b)
- Ollama may not be running
- Response format may vary (model doesn't always follow the numbered format)
- Inference can be slow without GPU

Mitigations: 3-second health check, 30-second timeout per batch, 1 retry, lenient
response parsing, graceful fallback to "other" with a user-visible warning.

### SVG chart edge cases
- Pie chart with one 100% slice: draw a full circle, not a degenerate arc
- Very small slices (<1%): skip rendering to avoid invisible slivers
- Line chart with one data point: render as a single dot, no line
- Long category names: truncate in bar chart labels
- Many categories: bar chart height scales, donut legend can overflow

### Self-contained HTML report
The report must open in any browser with no network access. This means:
- All charts are inline SVG (no external JS libraries)
- All styles are in a <style> tag (no CDN fonts)
- No images (SVG is markup, not a resource)
- Print-friendly: @media print resets margins, avoids page-break inside cards
