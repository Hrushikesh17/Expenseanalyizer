# Back Office Expense Report Analyzer

AI-assisted expense report analysis for back office finance teams. Auditors can upload expense reports and receipts, detect anomalous or suspicious claims, review plain-English explanations, filter the audit queue, and export decision-ready reports.

## Problem Fit

- Uploads CSV, TSV, JSON, Excel, text, PDF, Word, and receipt image files.
- Normalizes employee, vendor, amount, date, category, business purpose, and receipt evidence.
- Flags suspicious claims using duplicate checks, anomaly rules, weekend/round-amount checks, missing evidence checks, and confidence scoring.
- Shows auditor-facing risk score, severity, confidence, policy basis, issue, remediation, and next action.
- Provides interactive filters for decision, severity, employee, and minimum risk score.
- Exports PDF or text reports for finance review.
- Includes a finance assistant for accepted claims, rejected claims, high-risk claims, summaries, policy explanations, and employee response emails.

## Run Demo

```bash
python main.py
```

## Run UI

```bash
streamlit run frontend/streamlit_app.py
```

The UI accepts CSV, TSV, JSON, Excel, text, PDF, and Word files. You can also type manual expense notes in the sidebar, click **Analyze Files**, ask a finance question in the chat field, and download a PDF report.

Reports are written for finance analysts. Each claim gets an **ACCEPTED** or **REJECTED** decision, the company policy used, the issue with the claim, what could make it acceptable, and the next action for the analyst.

The main report is shown as a claim-by-claim table for easier review. The finance assistant can answer follow-up requests such as "show accepted claims", "show rejected claims", "show high risk claims", "summarize decisions", or "generate an employee response email for Asha Rao".

## API Integration Notes

- `api.upload.save_upload()` stores uploaded files under `data/uploads`.
- `ingestion.parser.parse_expense_file()` converts reports and receipts into expense records.
- `api.analyze.analyze_expenses()` returns normalized records, anomaly flags, duplicates, guardrail issues, confidence values, and explainability metadata.
- `api.dashboard.dashboard_metrics()` returns dashboard metrics including total amount, anomaly count, high-risk count, average confidence, and estimated audit time saved.
- Expense management platforms can post exported CSV/JSON rows into the analyzer and consume the returned findings as an audit queue.

## Data And Privacy

Use synthetic or anonymized data for demos and testing. The UI includes a privacy mode that anonymizes employee and receipt identifiers while preserving the existing multiple-file upload workflow, per-file outputs, combined review, extracted-detail table, downloads, and finance assistant.

The analyzer accepts variable-quality finance data:

- Transaction details such as employee, vendor, amount, date, category, and business purpose.
- Receipt evidence from PDFs, images, or file references.
- Employee metadata such as employee ID and department.
- Source-system metadata from ERP, card feeds, accounting platforms, or internal APIs.
- Historical audit outcomes such as previously approved, rejected, duplicate, or under-review status.

Avoid committing real employee financial data, receipts, API keys, or audit outcomes. The prototype stores uploads locally for demonstration; production use should add retention controls, encryption, access logging, and integration-specific privacy reviews.

## Hackathon Fit

The architecture is modular across ingestion, preprocessing, AI, vector DB, guardrails, APIs, exports, and frontend. This keeps the prototype feasible while leaving a scalable path for larger datasets, vector search, richer graph storage, expense platform APIs, OCR pipelines, and production policy controls.
