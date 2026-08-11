import csv
from io import StringIO
from typing import Any

from app.services.report_pdf_service import build_report_pdf


def build_report_csv(columns: list[str], rows: list[list]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def build_report_download(
    *,
    report_name: str,
    category: str,
    report_format: str,
    run_result: dict[str, Any],
) -> tuple[bytes, str, str]:
    columns = run_result.get("columns") or []
    rows = run_result.get("rows") or []
    generated_at = run_result.get("generated_at") or ""
    row_count = int(run_result.get("row_count") or len(rows))
    fmt = report_format.strip().upper()
    date_suffix = generated_at[:10] if generated_at else "export"
    safe_name = report_name.lower().replace(" ", "-")[:40]

    if fmt == "PDF":
        content = build_report_pdf(
            report_name=report_name,
            category=category,
            columns=columns,
            rows=rows,
            generated_at=generated_at,
            row_count=row_count,
        )
        filename = f"helixguard-{safe_name}-{date_suffix}.pdf"
        return content, "application/pdf", filename

    csv_text = build_report_csv(columns, rows)
    filename = f"helixguard-{safe_name}-{date_suffix}.csv"
    return csv_text.encode("utf-8"), "text/csv; charset=utf-8", filename
