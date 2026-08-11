from datetime import datetime
from io import BytesIO
from typing import Any

from fpdf import FPDF


def _truncate(value: Any, max_len: int = 48) -> str:
    text = str(value) if value is not None else ""
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3]}..."


class HelixReportPDF(FPDF):
    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self._title = title
        self._subtitle = subtitle

    def header(self) -> None:
        self.set_fill_color(15, 23, 42)
        self.rect(0, 0, 297, 22, style="F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.set_xy(10, 6)
        self.cell(0, 8, "PySetu AI", ln=False)
        self.set_font("Helvetica", "", 10)
        self.set_xy(10, 14)
        self.cell(0, 6, self._title, ln=True)
        self.set_text_color(30, 41, 59)
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, f"{self._subtitle}  ·  Page {self.page_no()}", align="C")


def build_report_pdf(
    *,
    report_name: str,
    category: str,
    columns: list[str],
    rows: list[list],
    generated_at: str,
    row_count: int,
    max_rows: int = 400,
) -> bytes:
    subtitle = f"{category} · Generated {generated_at[:10] if generated_at else datetime.utcnow().date().isoformat()}"
    pdf = HelixReportPDF(title=report_name, subtitle=subtitle)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # Executive summary strip for governance reports
    if category.lower() in {"executive", "compliance"}:
        pdf.set_fill_color(239, 246, 255)
        pdf.set_draw_color(191, 219, 254)
        pdf.rect(10, 28, 277, 18, style="FD")
        pdf.set_xy(14, 32)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 64, 175)
        pdf.cell(0, 6, "Governance Executive Summary", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(51, 65, 85)
        pdf.set_x(14)
        pdf.cell(
            0,
            6,
            f"Total records: {row_count:,}  ·  Exported rows: {min(len(rows), max_rows):,}",
            ln=True,
        )
        pdf.ln(6)
    else:
        pdf.set_y(30)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(0, 6, f"Records: {row_count:,}  ·  Showing up to {max_rows:,} rows", ln=True)
        pdf.ln(4)

    display_rows = rows[:max_rows]
    truncated = len(rows) > max_rows
    col_count = max(len(columns), 1)
    usable_width = 277
    col_width = usable_width / col_count

    # Table header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_text_color(15, 23, 42)
    for col in columns:
        pdf.cell(col_width, 7, _truncate(col, 24), border=1, fill=True)
    pdf.ln()

    # Table body
    pdf.set_font("Helvetica", "", 7)
    fill = False
    for row in display_rows:
        pdf.set_fill_color(248, 250, 252 if fill else 255)
        for i, col in enumerate(columns):
            value = row[i] if i < len(row) else ""
            pdf.cell(col_width, 6, _truncate(value, 32), border=1, fill=True)
        pdf.ln()
        fill = not fill

    if truncated:
        pdf.ln(4)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(180, 83, 9)
        pdf.cell(
            0,
            6,
            f"Note: {len(rows) - max_rows:,} additional rows omitted from PDF. Download CSV for full data.",
            ln=True,
        )

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
