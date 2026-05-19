import os
import re
import sys
from typing import Any


def _sanitize_import_path() -> None:
    blocked = f"{os.sep}build{os.sep}site-packages{os.sep}"
    sys.path[:] = [p for p in sys.path if blocked not in (p or "")]


_sanitize_import_path()

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _normalize_result_title(index: int, raw_title: Any) -> str:
    # Force consistent numbering under chapter 2, even for legacy titles like 4.1/4.2.
    base = str(raw_title or "").strip()
    base = re.sub(r"^\d+\.\d+\s*", "", base)
    if not base:
        base = f"Onderdeel {index}"
    return f"2.{index} {base}"


def build_pdf_report(filepath: str, data: dict[str, Any]) -> None:
    page_w, _ = A4
    margin = 2 * cm
    usable_w = page_w - (2 * margin)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    def style(name: str, **kwargs: Any) -> ParagraphStyle:
        return ParagraphStyle(name, **kwargs)

    h2 = style("H2", fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#1f2d3d"), spaceBefore=8, spaceAfter=2)
    n = style("N", fontSize=9, fontName="Helvetica", leading=13, wordWrap="CJK", textColor=colors.HexColor("#1f2d3d"))
    n_b = style("NB", parent=n, fontName="Helvetica-Bold")

    grid = colors.HexColor("#c6d0da")
    label_bg = colors.HexColor("#e9eef3")
    row_bg = colors.HexColor("#f7f9fb")
    footer_bg = colors.HexColor("#eef2f6")

    def p(value: Any, st: ParagraphStyle | None = None) -> Paragraph:
        text = str(value if value not in (None, "") else "-")
        return Paragraph(text, st or n)

    report_type = data.get("rapport_type", "Inspectierapport")
    is_oplever = report_type == "Opleverrapport"
    date_label = "Datum oplevering" if is_oplever else "Datum inspectie"
    operator_label = "Uitvoerder" if is_oplever else "Operator"
    title = "Dak Opleverrapport" if is_oplever else "Drone Inspectierapport"

    story = []

    def draw_footer(canvas, doc):
        canvas.saveState()
        page_no = canvas.getPageNumber()
        left = f"{company_name}  |  Rapport {data.get('rapportnummer', '-')}"
        right = f"Pagina {page_no}"
        y = 1.2 * cm
        canvas.setFillColor(footer_bg)
        canvas.rect(margin, y - 0.35 * cm, usable_w, 0.55 * cm, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#34495e"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(margin + 0.2 * cm, y - 0.1 * cm, left)
        canvas.drawRightString(margin + usable_w - 0.2 * cm, y - 0.1 * cm, right)
        canvas.restoreState()

    logo_path = data.get("logo_path", "") or ""
    company_name = data.get("company_name", "Dakinspecties") or "Dakinspecties"
    left_cell = Image(logo_path, width=8.0 * cm, height=1.9 * cm, kind="proportional") if logo_path and os.path.exists(logo_path) else p(company_name, n_b)
    header = Table(
        [
            [left_cell, p(f"<b>Rapportnummer:</b> {data.get('rapportnummer', '-')}")],
            [p(f"<b>{title}</b>", n_b), p(f"<b>{date_label}:</b> {data.get('datum', '-')}")],
            [p(""), p(f"<b>{operator_label}:</b> {data.get('operator', '-')}")],
        ],
        colWidths=[8.8 * cm, usable_w - 8.8 * cm],
    )
    header.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, grid),
                ("BACKGROUND", (0, 0), (0, -1), row_bg),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("PADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([header, Spacer(1, 0.3 * cm)])

    story.append(p("1. Project- en klantgegevens", h2))
    story.append(HRFlowable(width=usable_w, thickness=1, color=grid))
    project_rows = [
        [p("Opdrachtgever", n_b), p(data.get("opdrachtgever")), p("Type object", n_b), p(data.get("type_object"))],
        [p("Adres", n_b), p(data.get("adres")), p("Dakbedekking", n_b), p(data.get("dakbedekking"))],
        [p("Postcode / Plaats", n_b), p(data.get("postcode")), p("Bouwjaar", n_b), p(data.get("bouwjaar"))],
        [p("Telefoon", n_b), p(data.get("telefoon")), p("Oppervlakte", n_b), p(f"{data.get('oppervlakte') or '-'} m2")],
    ]
    project_tbl = Table(project_rows, colWidths=[3.5 * cm, 5.3 * cm, 3.3 * cm, usable_w - 12.1 * cm])
    project_tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, grid),
                ("BACKGROUND", (0, 0), (0, -1), label_bg),
                ("BACKGROUND", (2, 0), (2, -1), label_bg),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("BACKGROUND", (3, 0), (3, -1), colors.white),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([project_tbl, Spacer(1, 0.3 * cm)])

    story.append(p("2. Inspectieresultaten" if not is_oplever else "2. Opleverpunten", h2))
    story.append(HRFlowable(width=usable_w, thickness=1, color=grid))
    result_rows = [[p("Onderdeel", n_b), p("Status", n_b), p("Omschrijving", n_b)]]
    for idx, row in enumerate(data.get("resultaten", []), start=1):
        result_rows.append([
            p(_normalize_result_title(idx, row.get("title"))),
            p(row.get("status")),
            p(row.get("omschrijving")),
        ])
    result_tbl = Table(result_rows, colWidths=[5.9 * cm, 3.2 * cm, usable_w - 9.1 * cm], repeatRows=1)
    result_tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, grid),
                ("BACKGROUND", (0, 0), (-1, 0), label_bg),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([result_tbl, Spacer(1, 0.25 * cm)])

    story.append(p("3. Samenvatting", h2))
    story.append(HRFlowable(width=usable_w, thickness=1, color=grid))
    story.append(p(f"<b>Algemene status:</b> {data.get('status_algemeen', '-')}", n))
    story.append(p(data.get("samenvatting"), n))
    story.append(Spacer(1, 0.15 * cm))

    score_rows = [[p("Onderdeel", n_b), p("Score", n_b)]]
    for label, score in data.get("scores", []):
        score_rows.append([p(label), p(score)])
    score_tbl = Table(score_rows, colWidths=[usable_w - 3.2 * cm, 3.2 * cm], repeatRows=1)
    score_tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, grid),
                ("BACKGROUND", (0, 0), (-1, 0), label_bg),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.extend([score_tbl, Spacer(1, 0.3 * cm)])

    story.append(p("4. Fotobijlage", h2))
    story.append(HRFlowable(width=usable_w, thickness=1, color=grid))
    for i, photo in enumerate(data.get("foto_items", []), start=1):
        img_path = photo.get("path", "")
        story.append(p(f"<b>Foto {i}</b>", n_b))
        if img_path and os.path.exists(img_path):
            try:
                story.append(Image(img_path, width=9.8 * cm, height=6.4 * cm, kind="proportional"))
            except Exception:
                story.append(p("[ Foto kon niet worden geladen ]"))
        else:
            story.append(p("[ Geen foto gekoppeld ]"))
        story.append(p(photo.get("caption")))
        story.append(Spacer(1, 0.12 * cm))

    story.append(p("5. Conclusie en advies", h2))
    story.append(HRFlowable(width=usable_w, thickness=1, color=grid))
    story.append(p(f"<b>Korte termijn:</b> {data.get('advies_kort', '-')}", n))
    story.append(p(f"<b>Middellange termijn:</b> {data.get('advies_middel', '-')}", n))
    story.append(p(f"<b>Periodiek onderhoud:</b> {data.get('advies_periodiek', '-')}", n))

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)

