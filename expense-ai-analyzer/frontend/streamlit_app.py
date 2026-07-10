"""Streamlit frontend for expense-ai-analyzer."""

from __future__ import annotations

import sys
from html import escape
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.analyze import analyze_expenses
from api.dashboard import dashboard_metrics
from api.upload import save_upload
from exporters.pdf import build_audit_pdf_bytes
from ingestion.parser import parse_expense_file, parse_expense_text


SUPPORTED_HINT = "CSV, TSV, JSON, Excel, text, PDF, Word, receipt images, and text-readable unknown files"


def demo_records() -> list[dict[str, Any]]:
    return [
        {
            "employee_id": "E-1021",
            "employee": "Asha Rao",
            "department": "Consulting",
            "vendor": "City Hotel",
            "amount": "12500",
            "date": "2026-07-04",
            "category": "Travel",
            "business_purpose": "Client implementation travel",
            "receipt": "",
            "source_system": "Synthetic ERP export",
            "historical_outcome": "Rejected - missing receipt",
            "description": "Late manual hotel claim missing receipt",
        },
        {
            "employee_id": "E-1021",
            "employee": "Asha Rao",
            "department": "Consulting",
            "vendor": "City Hotel",
            "amount": "12500",
            "date": "2026-07-04",
            "category": "Travel",
            "business_purpose": "Client implementation travel",
            "receipt": "",
            "source_system": "Synthetic card feed",
            "historical_outcome": "Duplicate under review",
            "description": "Duplicate hotel reimbursement request",
        },
        {
            "employee_id": "E-2217",
            "employee": "Ravi Menon",
            "department": "Finance",
            "vendor": "OfficeKart",
            "amount": "899",
            "date": "2026-07-02",
            "category": "Supplies",
            "business_purpose": "Replacement keyboard for finance workstation",
            "receipt": "receipt-7781.pdf",
            "source_system": "Synthetic accounting platform",
            "historical_outcome": "Previously approved",
            "description": "Keyboard replacement with receipt",
        },
    ]


def anonymized_value(value: Any, prefix: str) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"unknown", "manual input"}:
        return text or "unknown"
    digest = sha256(text.lower().encode("utf-8")).hexdigest()[:8].upper()
    return f"{prefix}-{digest}"


def anonymize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anonymized: list[dict[str, Any]] = []
    for record in records:
        item = dict(record)
        item["employee"] = anonymized_value(item.get("employee"), "EMP")
        item["employee_id"] = anonymized_value(item.get("employee_id") or item.get("employee"), "EID")
        if item.get("receipt"):
            item["receipt"] = anonymized_value(item.get("receipt"), "RECEIPT")
        anonymized.append(item)
    return anonymized


def display_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        row = {
            "Claim ID": record.get("id", ""),
            "Employee": record.get("employee", ""),
            "Vendor": record.get("vendor", ""),
            "Category": record.get("category", ""),
            "Employee ID": record.get("employee_id", ""),
            "Department": record.get("department", ""),
            "Amount": record.get("amount", 0.0),
            "Date": record.get("date", ""),
            "Purpose": record.get("business_purpose", ""),
            "Receipt": record.get("receipt", ""),
            "Source System": record.get("source_system", ""),
            "Historical Outcome": record.get("historical_outcome", ""),
            "Description": record.get("description", ""),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def data_quality_summary(records: list[dict[str, Any]], anonymized: bool) -> str:
    total = len(records)
    if not total:
        return "No records found."

    required = ("employee", "vendor", "amount", "date", "category", "business_purpose")
    missing_counts = {
        field: sum(1 for record in records if not str(record.get(field, "")).strip())
        for field in required
    }
    receipt_count = sum(1 for record in records if str(record.get("receipt", "")).strip())
    metadata_count = sum(
        1
        for record in records
        if str(record.get("employee_id", "")).strip()
        or str(record.get("department", "")).strip()
        or str(record.get("historical_outcome", "")).strip()
        or str(record.get("source_system", "")).strip()
    )

    lines = [
        "Data Quality And Privacy Check",
        f"- Records reviewed: {total}",
        f"- Records with receipt or document reference: {receipt_count}",
        f"- Records with employee metadata, source system, or historical audit outcome: {metadata_count}",
        f"- Anonymization applied: {'Yes' if anonymized else 'No'}",
        "- Privacy note: use synthetic or anonymized records for demos; do not upload real sensitive finance data unless approved by your organization.",
        "- Missing required fields:",
    ]
    lines.extend(f"  - {field.replace('_', ' ').title()}: {count}" for field, count in missing_counts.items())
    return "\n".join(lines)


def safe_download_name(name: str, suffix: str) -> str:
    stem = Path(name).stem or "expense_audit"
    safe_stem = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in stem)
    return f"{safe_stem}{suffix}"


def rows_to_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")


def _fit_text(value: Any, width: int) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    if len(text) > width:
        text = text[: max(width - 3, 1)] + "..."
    return text.ljust(width)


def rows_to_text_table(rows: list[dict[str, Any]], limit: int = 999) -> str:
    if not rows:
        return "No matching claims found."

    columns = [
        ("Decision", 9),
        ("Claim ID", 12),
        ("Employee", 16),
        ("Vendor", 16),
        ("Amount", 12),
        ("Date", 12),
        ("Risk Score", 5),
        ("Severity", 8),
        ("Confidence", 10),
        ("Policy", 12),
        ("Next Action", 34),
    ]
    header = " | ".join(_fit_text(name, width) for name, width in columns)
    divider = "-+-".join("-" * width for _, width in columns)
    lines = [header, divider]
    for row in rows[:limit]:
        lines.append(" | ".join(_fit_text(row.get(name, ""), width) for name, width in columns))
    if len(rows) > limit:
        lines.append(f"Showing {limit} of {len(rows)} matching claims.")
    return "\n".join(lines)


def rows_to_action_table(rows: list[dict[str, Any]], limit: int = 999) -> str:
    columns = [
        ("Claim ID", 12),
        ("Decision", 9),
        ("Issue", 48),
        ("What Can Make It Acceptable", 46),
        ("Next Action", 46),
    ]
    header = " | ".join(_fit_text(name, width) for name, width in columns)
    divider = "-+-".join("-" * width for _, width in columns)
    lines = [header, divider]
    for row in rows[:limit]:
        lines.append(" | ".join(_fit_text(row.get(name, ""), width) for name, width in columns))
    if len(rows) > limit:
        lines.append(f"Showing {limit} of {len(rows)} matching claims.")
    return "\n".join(lines)


def report_summary_lines(metrics: dict[str, Any], summary: dict[str, int], final_decision: str) -> list[str]:
    return [
        f"Overall decision: {final_decision}",
        f"Claims reviewed: {metrics['record_count']}",
        f"Total claimed amount: {metrics['total_amount']:,.2f}",
        f"Accepted claims: {summary['accepted']}",
        f"Rejected claims: {summary['rejected']}",
    ]


def fallback_file_record(filename: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"file-{Path(filename).stem or 'upload'}",
            "employee": "unknown",
            "vendor": Path(filename).name,
            "category": "unparsed file",
            "amount": "0",
            "date": "",
            "receipt": Path(filename).name,
            "description": "File was uploaded, but no structured expense rows were found.",
        }
    ]


def build_input_batches(
    uploaded_files: list[Any],
    manual_text: str,
    use_demo: bool,
    anonymize: bool,
) -> list[dict[str, Any]]:
    batches: list[dict[str, Any]] = []
    for uploaded in uploaded_files:
        temp_path = save_upload(uploaded.name, uploaded.getvalue())
        try:
            parsed_records = parse_expense_file(temp_path)
            records = parsed_records or fallback_file_record(uploaded.name)
        except Exception as exc:
            st.warning(f"{uploaded.name} could not be parsed directly, so it was added for guardrail review. Details: {exc}")
            records = fallback_file_record(uploaded.name)
        if anonymize:
            records = anonymize_records(records)
        batches.append({"label": uploaded.name, "records": records, "anonymized": anonymize})

    if manual_text.strip():
        manual_records = parse_expense_text(manual_text)
        if manual_records:
            records = anonymize_records(manual_records) if anonymize else manual_records
            batches.append({"label": "manual input", "records": records, "anonymized": anonymize})

    if not batches and use_demo:
        records = demo_records()
        if anonymize:
            records = anonymize_records(records)
        batches.append({"label": "synthetic demo data", "records": records, "anonymized": anonymize})

    return batches


COMPANY_POLICIES = {
    "P-001": "Every claim must include employee, vendor, amount, date, category, business purpose, and required receipt evidence.",
    "P-002": "Duplicate claims for the same employee, vendor, amount, and date must be rejected.",
    "P-003": "Claims with missing or invalid date, zero amount, or unreadable supporting file must be rejected until corrected.",
    "P-004": "Weekend, round-amount, late, manual, or missing-receipt claims require supporting evidence before payment.",
    "P-005": "Claims may be accepted only when the finance analyst can verify business purpose and supporting evidence.",
}


GUARDRAIL_DETAILS = {
    "Completeness check": "Employee, vendor, amount, date, category, and business purpose must be present.",
    "Amount check": "Amount must be greater than zero and should match the submitted invoice or receipt.",
    "Date check": "Date must be valid, readable, and aligned with the claimed business activity.",
    "Duplicate check": "Same employee, vendor, amount, and date is treated as a duplicate risk and rejected until clarified.",
    "Evidence check": "Missing receipt, manual entry, weekend claim, or round amount requires additional proof before payment.",
    "Verifiability check": "Unreadable files or unstructured claims are rejected until finance can verify the claim details.",
}


def policy_rules_text() -> str:
    lines = [
        "Policy And Guardrail Details",
        "",
        "What must be present to ACCEPT a claim:",
        "- Employee name must be available.",
        "- Vendor or merchant name must be available.",
        "- Claim amount must be valid and greater than zero.",
        "- Claim date must be readable and valid.",
        "- Expense category and business purpose must be clear.",
        "- Receipt, invoice, or supporting proof must be available when the claim is manual, round amount, weekend-dated, or otherwise unusual.",
        "- The claim must not duplicate another submitted claim.",
        "- Finance must be able to verify the claim from the submitted file or manual details.",
        "",
        "What causes a claim to be REJECTED:",
        "- Missing employee, vendor, amount, date, category, or business purpose.",
        "- Zero, negative, unreadable, or invalid amount.",
        "- Missing, invalid, or unreadable date.",
        "- Possible duplicate claim for the same employee, vendor, amount, and date.",
        "- Missing receipt or supporting proof where evidence is required.",
        "- Manual claim without enough explanation or supporting document.",
        "- Weekend claim without business justification.",
        "- Round amount without receipt or invoice validation.",
        "- Uploaded file cannot be read or converted into claim details.",
        "",
        "Guardrails used before giving a decision:",
    ]
    lines.extend(f"- {name}: {detail}" for name, detail in GUARDRAIL_DETAILS.items())
    lines.extend(["", "Company policies mapped to decisions:"])
    lines.extend(f"- {policy_id}: {policy}" for policy_id, policy in COMPANY_POLICIES.items())
    return "\n".join(lines)


ISSUE_LABELS = {
    "amount is statistically unusual": "Claim amount is unusually high or low compared with the other submitted claims.",
    "expense was submitted for a weekend date": "Claim date falls on a weekend and needs business justification.",
    "round amount may need receipt validation": "Round amount should be supported by a receipt or invoice.",
    "manual claim needs extra verification": "Manual claim needs extra verification before payment.",
    "receipt or supporting proof is missing": "Receipt or supporting proof is missing.",
    "missing employee": "Employee name is missing.",
    "missing vendor": "Vendor name is missing.",
    "missing business purpose": "Business purpose is missing.",
    "amount must be positive": "Claim amount is missing, zero, or invalid.",
    "date could not be parsed": "Claim date is missing or invalid.",
    "receipt evidence is missing": "Receipt evidence is missing.",
}


def finance_issue_text(issue: str) -> str:
    return ISSUE_LABELS.get(issue, issue[:1].upper() + issue[1:])


def _duplicate_ids(findings: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for duplicate in findings.get("duplicates", []):
        ids.update(duplicate.get("ids", []))
    return ids


def _guardrail_map(findings: dict[str, Any]) -> dict[str, list[str]]:
    return {
        issue.get("id", "unknown"): issue.get("issues", [])
        for issue in findings.get("guardrails", {}).get("issues", [])
    }


def _anomaly_map(findings: dict[str, Any]) -> dict[str, list[str]]:
    return {
        item.get("id", "unknown"): item.get("reasons", [])
        for item in findings.get("anomalies", [])
    }


def _anomaly_detail_map(findings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item.get("id", "unknown"): item
        for item in findings.get("anomalies", [])
    }


def claim_decision(record: dict[str, Any], findings: dict[str, Any]) -> dict[str, Any]:
    claim_id = record.get("id", "unknown")
    duplicate_ids = _duplicate_ids(findings)
    guardrails = _guardrail_map(findings).get(claim_id, [])
    anomalies = _anomaly_map(findings).get(claim_id, [])
    anomaly_detail = _anomaly_detail_map(findings).get(claim_id, {})
    description = str(record.get("description", "")).lower()

    issues: list[str] = []
    policies: list[str] = []

    if claim_id in duplicate_ids:
        issues.append("Possible duplicate claim found for the same employee, vendor, amount, and date.")
        policies.append("P-002")
    if guardrails:
        issues.extend(guardrails)
        policies.append("P-003")
    if "missing receipt" in description or "no receipt" in description:
        issues.append("Receipt or supporting proof appears to be missing.")
        policies.append("P-004")
    if "manual" in description:
        issues.append("Manual claim needs stronger verification before payment.")
        policies.append("P-004")
    if anomalies:
        issues.extend(anomalies)
        policies.append("P-004")

    unique_issues = [finance_issue_text(issue) for issue in dict.fromkeys(issues)]
    unique_policies = list(dict.fromkeys(policies or ["P-001", "P-005"]))
    rejected = bool(unique_issues)
    severity = anomaly_detail.get("severity", "low" if not rejected else "medium")
    anomaly_confidence = anomaly_detail.get("confidence", record.get("confidence", 0.0))
    risk_score = min(
        100,
        (35 if rejected else 10)
        + (25 if severity == "high" else 12 if severity == "medium" else 0)
        + (15 if claim_id in duplicate_ids else 0)
        + (10 if guardrails else 0),
    )

    return {
        "decision": "REJECTED" if rejected else "ACCEPTED",
        "severity": severity.upper(),
        "confidence": round(float(anomaly_confidence or 0.0), 2),
        "risk_score": risk_score,
        "issues": unique_issues or ["No blocking policy issue found in the submitted data."],
        "policies": unique_policies,
        "next_action": (
            "Ask the employee to correct the claim and resubmit with missing evidence."
            if rejected
            else "Approve for payment after routine finance sign-off."
        ),
        "acceptable_if": (
            "The employee provides a valid receipt, business purpose, corrected date/amount, and proof this is not a duplicate."
            if rejected
            else "No further action is needed unless the approver requires extra business context."
        ),
    }


def claim_report_rows(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    findings = analysis["findings"]
    for record in analysis["records"]:
        decision = claim_decision(record, findings)
        amount = record.get("amount", 0.0)
        rows.append(
            {
                "Decision": decision["decision"],
                "Claim ID": record.get("id", "unknown"),
                "Employee": record.get("employee", "unknown"),
                "Vendor": record.get("vendor", "unknown"),
                "Amount": f"{amount:,.2f}",
                "Date": record.get("date", "") or "Not provided",
                "Risk Score": decision["risk_score"],
                "Severity": decision["severity"],
                "Confidence": f"{decision['confidence']:.0%}",
                "Policy": ", ".join(decision["policies"]),
                "Issue": "\n".join(decision["issues"]),
                "Finance Explanation": (
                    "This claim can be paid because the submitted details satisfy the required checks."
                    if decision["decision"] == "ACCEPTED"
                    else "This claim should not be paid yet because one or more company policy requirements are not satisfied."
                ),
                "What Can Make It Acceptable": decision["acceptable_if"],
                "Next Action": decision["next_action"],
            }
        )
    return rows


def filter_claim_rows(rows: list[dict[str, Any]], key_prefix: str) -> list[dict[str, Any]]:
    if not rows:
        return rows

    frame = pd.DataFrame(rows)
    filter_cols = st.columns([1, 1, 1, 1])
    decision = filter_cols[0].selectbox(
        "Decision",
        ["All", "ACCEPTED", "REJECTED"],
        key=f"{key_prefix}-decision-filter",
    )
    severity = filter_cols[1].selectbox(
        "Severity",
        ["All", "HIGH", "MEDIUM", "LOW"],
        key=f"{key_prefix}-severity-filter",
    )
    employee_options = ["All"] + sorted(value for value in frame["Employee"].dropna().unique() if value)
    employee = filter_cols[2].selectbox("Employee", employee_options, key=f"{key_prefix}-employee-filter")
    min_risk = filter_cols[3].slider("Min Risk", 0, 100, 0, 5, key=f"{key_prefix}-risk-filter")

    filtered = frame.copy()
    if decision != "All":
        filtered = filtered[filtered["Decision"] == decision]
    if severity != "All":
        filtered = filtered[filtered["Severity"] == severity]
    if employee != "All":
        filtered = filtered[filtered["Employee"] == employee]
    filtered = filtered[filtered["Risk Score"].astype(int) >= min_risk]
    return filtered.to_dict(orient="records")


def decision_summary(analysis: dict[str, Any]) -> dict[str, int]:
    decisions = [claim_decision(record, analysis["findings"])["decision"] for record in analysis["records"]]
    return {
        "accepted": decisions.count("ACCEPTED"),
        "rejected": decisions.count("REJECTED"),
    }


def make_text_report(analysis: dict[str, Any], metrics: dict[str, Any], user_question: str = "") -> str:
    summary = decision_summary(analysis)
    final_decision = "REJECTED" if summary["rejected"] else "ACCEPTED"
    rows = claim_report_rows(analysis)

    lines = [
        "Expense Claim Analysis Report",
        "",
        "Summary",
        *report_summary_lines(metrics, summary, final_decision),
        "",
        "Claim Decision Table",
        rows_to_text_table(rows, limit=999),
        "",
        "Analysis And Required Action",
        rows_to_action_table(rows, limit=999),
    ]

    if user_question:
        lines.extend(
            [
                "",
                "Answer To Analyst Question",
                f"You asked: {user_question}",
                "Use the claim decisions above as the source of truth. Rejected claims should not be paid until the listed policy issues are resolved.",
            ]
        )

    return "\n".join(lines)


def make_ui_action_report(analysis: dict[str, Any], metrics: dict[str, Any]) -> str:
    summary = decision_summary(analysis)
    final_decision = "REJECTED" if summary["rejected"] else "ACCEPTED"
    lines = [
        "Expense Claim Analysis",
        "",
        f"Overall decision: {final_decision}",
        f"Claims reviewed: {metrics['record_count']}",
        f"Accepted: {summary['accepted']}",
        f"Rejected: {summary['rejected']}",
        "",
        "Claim Details And Actions",
    ]

    for index, row in enumerate(claim_report_rows(analysis), start=1):
        lines.extend(
            [
                "",
                f"Claim {index}: {row['Claim ID']}",
                f"- Decision: {row['Decision']}",
                f"- Employee: {row['Employee']}",
                f"- Vendor: {row['Vendor']}",
                f"- Amount: {row['Amount']}",
                f"- Date: {row['Date']}",
                f"- Risk: {row['Severity']} | Score {row['Risk Score']} | Confidence {row['Confidence']}",
                "- Analysis:",
            ]
        )
        lines.extend(f"  - {issue}" for issue in str(row["Issue"]).split("\n") if issue.strip())
        lines.extend(
            [
                "- What can make it acceptable:",
                f"  - {row['What Can Make It Acceptable']}",
                "- Next action:",
                f"  - {row['Next Action']}",
            ]
        )
    return "\n".join(lines)


def rows_to_markdown(rows: list[dict[str, Any]], limit: int = 12) -> str:
    if not rows:
        return "No matching claims found."

    headers = ["Decision", "Claim ID", "Employee", "Vendor", "Amount", "Risk Score", "Severity", "Confidence", "Policy", "Next Action"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows[:limit]:
        values = [str(row.get(header, "")).replace("\n", " ") for header in headers]
        lines.append("| " + " | ".join(values) + " |")
    if len(rows) > limit:
        lines.append(f"\nShowing {limit} of {len(rows)} matching claims.")
    return "\n".join(lines)


def employee_response(rows: list[dict[str, Any]], employee_name: str = "") -> str:
    selected = [
        row for row in rows
        if not employee_name or employee_name.lower() in str(row.get("Employee", "")).lower()
    ]
    if not selected:
        return "I could not find matching claims for that employee."

    employee = employee_name or str(selected[0].get("Employee", "Employee"))
    claim_lines = []
    for row in selected:
        claim_lines.append(
            "\n".join(
                [
                    f"- Claim ID: {row['Claim ID']}",
                    f"  Decision: {row['Decision']}",
                    f"  Amount: {row['Amount']}",
                    f"  Vendor: {row['Vendor']}",
                    f"  Policy: {row['Policy']}",
                    f"  Issue: {row['Issue']}",
                    f"  Required action: {row['What Can Make It Acceptable']}",
                ]
            )
        )

    return "\n".join(
        [
            f"Subject: Expense claim review update for {employee}",
            "",
            f"Dear {employee},",
            "",
            "We reviewed your submitted expense claim(s). Please find the decision and required action below.",
            "",
            *claim_lines,
            "",
            "Please resubmit any rejected claim after resolving the listed policy issue. Accepted claims will proceed for normal finance approval.",
            "",
            "Regards,",
            "Finance Team",
        ]
    )


def guess_employee_name(prompt: str, rows: list[dict[str, Any]]) -> str:
    prompt_lower = prompt.lower()
    for row in rows:
        employee = str(row.get("Employee", ""))
        if employee and employee.lower() in prompt_lower:
            return employee
    markers = ["for ", "to ", "employee "]
    for marker in markers:
        if marker in prompt_lower:
            possible = prompt_lower.split(marker, 1)[1].strip(" .")
            return possible.title()
    return ""


def handle_chat_task(prompt: str, rows: list[dict[str, Any]]) -> str:
    prompt_lower = prompt.lower()

    if any(word in prompt_lower for word in ("accepted", "approved", "payable")):
        accepted = [row for row in rows if row["Decision"] == "ACCEPTED"]
        return f"Accepted claims: {len(accepted)}\n\n" + rows_to_markdown(accepted, limit=8)

    if any(word in prompt_lower for word in ("rejected", "reject", "not payable", "blocked")):
        rejected = [row for row in rows if row["Decision"] == "REJECTED"]
        return f"Rejected claims: {len(rejected)}\n\n" + rows_to_markdown(rejected, limit=8)

    if any(word in prompt_lower for word in ("high risk", "suspicious", "anomaly", "anomalies", "fraud")):
        suspicious = [row for row in rows if row["Decision"] == "REJECTED" or row["Severity"] in {"HIGH", "MEDIUM"}]
        suspicious.sort(key=lambda row: int(row.get("Risk Score", 0)), reverse=True)
        return f"Suspicious claims: {len(suspicious)}\n\n" + rows_to_markdown(suspicious, limit=8)

    if any(word in prompt_lower for word in ("employee response", "send", "mail", "email", "message", "letter")):
        employee = guess_employee_name(prompt, rows)
        return employee_response(rows, employee)

    if any(word in prompt_lower for word in ("policy", "policies", "guardrail", "guardrails", "accept", "reject", "rules")):
        return policy_rules_text()

    if any(word in prompt_lower for word in ("summary", "summarize", "overview")):
        accepted = sum(1 for row in rows if row["Decision"] == "ACCEPTED")
        rejected = sum(1 for row in rows if row["Decision"] == "REJECTED")
        return (
            f"Reviewed {len(rows)} claim(s): {accepted} accepted, {rejected} rejected. "
            "Priority: fix rejected claims with missing receipts, missing fields, or duplicate clarification."
        )

    employee = guess_employee_name(prompt, rows)
    if employee:
        matching = [row for row in rows if employee.lower() in str(row.get("Employee", "")).lower()]
        return f"Claims for {employee}: {len(matching)}\n\n" + rows_to_markdown(matching, limit=8)

    return (
        "Ask me for: accepted claims, rejected claims, high-risk claims, summary, policies, or an employee email."
    )


st.set_page_config(page_title="Expense AI Analyzer", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; max-width: 1180px;}
    div[data-testid="stMetric"] {background: #f8fafc; border: 1px solid #e5e7eb; padding: 14px; border-radius: 8px;}
    .report-box {background: #ffffff; border: 1px solid #d6dde8; border-radius: 8px; padding: 22px; line-height: 1.62; white-space: pre-wrap;}
    .report-box pre {white-space: pre-wrap; font-family: inherit; margin: 0;}
    .ready-box {background: #f8fafc; border: 1px solid #dbe3ef; border-radius: 8px; padding: 14px;}
    div[data-testid="stMetricValue"] {font-size: 1.35rem;}
    div[data-testid="stMetricLabel"] {font-size: 0.85rem;}
    .chat-panel {max-height: 360px; overflow-y: auto; background: #f8fafc; border: 1px solid #dbe3ef; border-radius: 8px; padding: 14px;}
    .chat-user {background: #e0f2fe; border: 1px solid #bae6fd; border-radius: 8px; padding: 10px; margin-bottom: 10px;}
    .chat-assistant {background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; margin-bottom: 14px; white-space: pre-wrap;}
    div[data-testid="stHorizontalBlock"] {align-items: stretch;}
    .stDataFrame {border: 1px solid #e5e7eb; border-radius: 8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Back Office Expense Report Analyzer with AI-Powered Anomaly Detection")
st.caption("Upload reports or receipts, review anomaly flags, filter suspicious claims, and export auditor-ready decisions.")

with st.sidebar:
    st.header("Input")
    uploaded_files = st.file_uploader("Upload expense files", accept_multiple_files=True)
    manual_text = st.text_area(
        "Manual expense input",
        placeholder="Example: Asha Rao, City Hotel, Travel, INR 12500, 2026-07-04, missing receipt",
        height=140,
    )
    st.caption(f"Supports {SUPPORTED_HINT}. Select multiple files to get separate outputs for each file.")
    anonymize_input = st.toggle("Anonymize employee and receipt identifiers", value=True)
    analyze_clicked = st.button("Analyze Files", type="primary", use_container_width=True)

if "analysis_batches" not in st.session_state:
    st.session_state.analysis_batches = []
if "last_question" not in st.session_state:
    st.session_state.last_question = ""
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

st.markdown("### Ready To Analyze")
uploaded_count = len(uploaded_files)
manual_ready = bool(manual_text.strip())
st.markdown(
    f"""
    <div class="ready-box">
    Files selected: <b>{uploaded_count}</b><br/>
    Manual input: <b>{'Yes' if manual_ready else 'No'}</b><br/>
    Privacy mode: <b>{'Anonymized' if anonymize_input else 'Original identifiers'}</b>
    </div>
    """,
    unsafe_allow_html=True,
)

if analyze_clicked:
    input_batches = build_input_batches(uploaded_files, manual_text, False, anonymize_input)
    if input_batches:
        st.session_state.analysis_batches = input_batches
        st.success(f"Analysis ready for {len(input_batches)} input source(s).")
    else:
        st.session_state.analysis_batches = []
        st.warning("Please upload files or enter manual expense text before analyzing.")

if not st.session_state.analysis_batches:
    st.info("Add files or manual text, then click Analyze Files.")
    st.stop()

st.subheader("Audit Outputs")

all_records: list[dict[str, Any]] = []
all_claim_rows: list[dict[str, Any]] = []
for index, batch in enumerate(st.session_state.analysis_batches, start=1):
    source_label = batch["label"]
    records = batch["records"]
    anonymized = bool(batch.get("anonymized"))
    all_records.extend(records)
    analysis = analyze_expenses(records)
    metrics = dashboard_metrics(analysis)
    decisions = decision_summary(analysis)
    claim_rows = claim_report_rows(analysis)
    all_claim_rows.extend(claim_rows)
    report_text = make_text_report(analysis, metrics, st.session_state.last_question)
    ui_action_report = make_ui_action_report(analysis, metrics)
    overall_decision = "REJECTED" if decisions["rejected"] else "ACCEPTED"

    with st.container(border=True):
        st.markdown(f"### {index}. {source_label}")
        metric_columns = st.columns([0.8, 1.8, 0.8, 0.8, 0.8, 1.1], gap="small")
        metric_columns[0].metric("Records", metrics["record_count"])
        metric_columns[1].metric("Total Claim Amount", f"{metrics['total_amount']:,.2f}")
        metric_columns[2].metric("Accepted", decisions["accepted"])
        metric_columns[3].metric("Rejected", decisions["rejected"])
        metric_columns[4].metric("High Risk", metrics["high_risk_count"])
        metric_columns[5].metric("Avg Confidence", f"{metrics['average_confidence']:.0%}")

        left, right = st.columns([3, 1], gap="large")
        with left:
            st.markdown("#### Claim Decision Table")
            filtered_rows = filter_claim_rows(claim_rows, f"batch-{index}")
            st.dataframe(pd.DataFrame(filtered_rows), use_container_width=True, hide_index=True)
            with st.expander("Analysis report and actions", expanded=False):
                st.markdown(f"<div class='report-box'><pre>{escape(ui_action_report)}</pre></div>", unsafe_allow_html=True)
        with right:
            st.markdown("#### Actions")
            st.download_button(
                "Download Report PDF",
                data=build_audit_pdf_bytes(
                    "Expense Claim Analysis Report",
                    report_summary_lines(metrics, decisions, overall_decision),
                    claim_rows,
                ),
                file_name=safe_download_name(source_label, "_audit_report.pdf"),
                mime="application/pdf",
                use_container_width=True,
                key=f"pdf-{index}-{source_label}",
            )
            st.download_button(
                "Download Report Text",
                data=report_text,
                file_name=safe_download_name(source_label, "_audit_report.txt"),
                mime="text/plain",
                use_container_width=True,
                key=f"text-{index}-{source_label}",
            )
            st.download_button(
                "Download Table CSV",
                data=rows_to_csv_bytes(claim_rows),
                file_name=safe_download_name(source_label, "_claim_table.csv"),
                mime="text/csv",
                use_container_width=True,
                key=f"csv-{index}-{source_label}",
            )

if len(st.session_state.analysis_batches) > 1:
    combined_analysis = analyze_expenses(all_records)
    combined_metrics = dashboard_metrics(combined_analysis)
    combined_decisions = decision_summary(combined_analysis)
    combined_rows = claim_report_rows(combined_analysis)
    combined_report = make_text_report(combined_analysis, combined_metrics, st.session_state.last_question)
    combined_ui_action_report = make_ui_action_report(combined_analysis, combined_metrics)
    combined_overall = "REJECTED" if combined_decisions["rejected"] else "ACCEPTED"

    st.subheader("Combined Finance Review")
    combined_metric_columns = st.columns([0.8, 1.8, 0.8, 0.8, 0.8, 1.1], gap="small")
    combined_metric_columns[0].metric("Records", combined_metrics["record_count"])
    combined_metric_columns[1].metric("Total Claim Amount", f"{combined_metrics['total_amount']:,.2f}")
    combined_metric_columns[2].metric("Accepted", combined_decisions["accepted"])
    combined_metric_columns[3].metric("Rejected", combined_decisions["rejected"])
    combined_metric_columns[4].metric("High Risk", combined_metrics["high_risk_count"])
    combined_metric_columns[5].metric("Avg Confidence", f"{combined_metrics['average_confidence']:.0%}")
    combined_filtered_rows = filter_claim_rows(combined_rows, "combined")
    st.dataframe(pd.DataFrame(combined_filtered_rows), use_container_width=True, hide_index=True)
    with st.expander("Combined analysis report and actions", expanded=False):
        st.markdown(f"<div class='report-box'><pre>{escape(combined_ui_action_report)}</pre></div>", unsafe_allow_html=True)
    st.download_button(
        "Download Combined Report PDF",
        data=build_audit_pdf_bytes(
            "Combined Expense Claim Analysis Report",
            report_summary_lines(combined_metrics, combined_decisions, combined_overall),
            combined_rows,
        ),
        file_name="combined_expense_audit_report.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="combined-pdf",
    )
    st.download_button(
        "Download Combined Table CSV",
        data=rows_to_csv_bytes(combined_rows),
        file_name="combined_expense_claim_table.csv",
        mime="text/csv",
        use_container_width=True,
        key="combined-csv",
    )

st.subheader("Finance Assistant")
st.caption("Ask for actions such as accepted claims, rejected claims, a summary, policies, or an employee response email.")

question = st.chat_input("Ask the assistant to filter claims or draft a finance response")
if question:
    st.session_state.last_question = question
    st.session_state.chat_messages.append({"role": "user", "content": question})
    st.session_state.chat_messages.append({"role": "assistant", "content": handle_chat_task(question, all_claim_rows)})

if st.session_state.chat_messages:
    chat_html = ["<div class='chat-panel'>"]
    for message in st.session_state.chat_messages:
        css_class = "chat-user" if message["role"] == "user" else "chat-assistant"
        speaker = "You" if message["role"] == "user" else "Assistant"
        chat_html.append(
            f"<div class='{css_class}'><b>{speaker}</b><br/><pre>{escape(message['content'])}</pre></div>"
        )
    chat_html.append("</div>")
    st.markdown("".join(chat_html), unsafe_allow_html=True)
else:
    st.info("After analysis, ask: 'show accepted claims', 'show rejected claims', or 'generate an employee response email for Asha Rao'.")
