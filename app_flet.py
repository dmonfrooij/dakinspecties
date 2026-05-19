import json
import os
import re
from datetime import date

import flet as ft
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BASE_DIR = os.path.dirname(__file__)
COUNTER_FILE = os.path.join(BASE_DIR, "project_counter.json")


def next_rapportnummer() -> str:
    jaar = date.today().year
    last = 0
    try:
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if int(data.get("year", 0)) == jaar:
                last = int(data.get("last", 0))
    except Exception:
        last = 0
    return f"{jaar}-{last + 1:03d}"


def mark_used_rapportnummer(value: str) -> None:
    m = re.match(r"^(\d{4})-(\d{1,6})$", (value or "").strip())
    if not m:
        return
    year = int(m.group(1))
    number = int(m.group(2))
    if number <= 0:
        return

    current = {"year": year, "last": number}
    try:
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                old = json.load(f)
            old_year = int(old.get("year", 0))
            old_last = int(old.get("last", 0))
            if old_year > year or (old_year == year and old_last > number):
                current = {"year": old_year, "last": old_last}
    except Exception:
        pass

    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=True, indent=2)
    except Exception:
        pass


class CrossPlatformApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Dakinspecties - Cross-platform"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.padding = 12
        self.page.window.width = 1200
        self.page.window.height = 860

        self._active_pick_target = None
        self._pending_project_data = None
        self._active_tab = 0

        self.file_picker = ft.FilePicker()
        self.save_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)
        self.page.services.append(self.save_picker)

        self.build_ui()

    def notify(self, msg: str):
        snack = ft.SnackBar(ft.Text(msg), open=True)
        self.page.overlay.append(snack)
        self.page.update()

    def _switch_tab(self, idx: int):
        self._active_tab = idx
        for i, btn in enumerate(self._tab_buttons):
            btn.bgcolor = ft.Colors.PRIMARY if i == idx else None
            btn.color = ft.Colors.ON_PRIMARY if i == idx else None
        self._tab_content_area.content = self._tab_contents[idx]
        self.page.update()

    def build_ui(self):
        self.rapportnummer = ft.TextField(label="Rapportnummer", value=next_rapportnummer(), width=240)
        self.datum = ft.TextField(label="Datum inspectie", value=date.today().strftime("%d %B %Y"), width=240)
        self.operator = ft.TextField(label="Operator", width=240)

        self.opdrachtgever = ft.TextField(label="Opdrachtgever")
        self.adres = ft.TextField(label="Adres")
        self.postcode = ft.TextField(label="Postcode / Plaats")
        self.telefoon = ft.TextField(label="Telefoonnummer")
        self.type_object = ft.TextField(label="Type object")
        self.dakbedekking = ft.TextField(label="Dakbedekking")
        self.bouwjaar = ft.TextField(label="Bouwjaar")
        self.oppervlakte = ft.TextField(label="Oppervlakte (m2)")

        self.status_algemeen = ft.Dropdown(
            label="Algehele status",
            value="MATIG / AANDACHTSPUNT",
            options=[
                ft.dropdown.Option("UITSTEKEND"),
                ft.dropdown.Option("GOED"),
                ft.dropdown.Option("MATIG / AANDACHTSPUNT"),
                ft.dropdown.Option("SLECHT"),
                ft.dropdown.Option("KRITIEK"),
            ],
            width=320,
        )
        self.samenvatting = ft.TextField(label="Samenvatting", multiline=True, min_lines=4, max_lines=8)

        self.score_controls = [
            ("Dakbedekking & Oppervlakte", ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="2", width=120)),
            ("Naden en Lasverbindingen", ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="2", width=120)),
            ("Randafwerking & Trimmen", ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="3", width=120)),
            ("Hemelwaterafvoer (HWA) & Goot", ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="4", width=120)),
            ("Dakdoorvoeren & Aansluitingen", ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="2", width=120)),
        ]

        self.result_titles = [
            "4.1 Dakbedekking & Oppervlakte",
            "4.2 Naden en Lasverbindingen",
            "4.3 Randafwerking & Trimmen",
            "4.4 Hemelwaterafvoer (HWA) & Goot",
            "4.5 Dakdoorvoeren & Aansluitingen",
        ]
        self.result_controls = []
        for title in self.result_titles:
            oms = ft.TextField(label="Omschrijving", multiline=True, min_lines=3, max_lines=6)
            stat = ft.Dropdown(
                label="Status",
                value="Akkoord",
                options=[
                    ft.dropdown.Option("Akkoord"),
                    ft.dropdown.Option("Akkoord (lichte vervuiling)"),
                    ft.dropdown.Option("Aandachtspunt"),
                    ft.dropdown.Option("Directe actie vereist"),
                    ft.dropdown.Option("Kritiek"),
                ],
                width=300,
            )
            foto = ft.TextField(label="Foto pad", read_only=True, expand=True)
            self.result_controls.append((title, oms, stat, foto))

        self.foto1 = ft.TextField(label="Foto 1 pad", read_only=True, expand=True)
        self.foto2 = ft.TextField(label="Foto 2 pad", read_only=True, expand=True)
        self.caption1 = ft.TextField(label="Bijschrift foto 1", value="Totaaloverzicht van het geinspecteerde dakvlak.")
        self.caption2 = ft.TextField(label="Bijschrift foto 2", value="Detailopname van de verstopte hemelwaterafvoer.")

        self.advies_kort = ft.TextField(label="Korte termijn", multiline=True, min_lines=2, max_lines=5)
        self.advies_middel = ft.TextField(label="Middellange termijn", multiline=True, min_lines=2, max_lines=5)
        self.advies_periodiek = ft.TextField(label="Periodiek onderhoud", multiline=True, min_lines=2, max_lines=5)

        tab_labels = ["Algemeen", "Inspectieresultaten", "Foto's", "Samenvatting", "Conclusie"]
        self._tab_contents = [
            self.tab_algemeen(),
            self.tab_resultaten(),
            self.tab_fotos(),
            self.tab_samenvatting(),
            self.tab_conclusie(),
        ]

        self._tab_buttons = []
        for i, label in enumerate(tab_labels):
            idx = i

            def make_switch(i=i):
                def handler(e):
                    self._switch_tab(i)
                return handler

            btn = ft.Button(
                content=label,
                bgcolor=ft.Colors.PRIMARY if i == 0 else None,
                color=ft.Colors.ON_PRIMARY if i == 0 else None,
                on_click=make_switch(i),
            )
            self._tab_buttons.append(btn)

        tab_bar = ft.Row(self._tab_buttons, spacing=4, wrap=True)

        self._tab_content_area = ft.Container(
            content=self._tab_contents[0],
            expand=True,
        )

        header = ft.Row(
            [
                ft.Text("Dakinspecties - Cross-platform", size=24, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.Button("Nieuw", on_click=self.new_project),
                        ft.Button("Open project", on_click=self.open_project),
                        ft.Button("Opslaan project", on_click=self.save_project),
                        ft.Button("Genereer PDF", on_click=self.genereer_pdf, bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY),
                    ],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.page.add(
            header,
            ft.Divider(height=4),
            tab_bar,
            ft.Divider(height=2),
            self._tab_content_area,
        )

    def tab_algemeen(self):
        return ft.Container(
            padding=12,
            content=ft.Column(
                [
                    ft.Row([self.rapportnummer, self.datum, self.operator], wrap=True),
                    self.opdrachtgever,
                    self.adres,
                    ft.Row([self.postcode, self.telefoon], wrap=True),
                    ft.Row([self.type_object, self.dakbedekking], wrap=True),
                    ft.Row([self.bouwjaar, self.oppervlakte], wrap=True),
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    def _make_pick_handler(self, target: ft.TextField):
        async def handler(e):
            files = await self.file_picker.pick_files(allow_multiple=False)
            if files:
                target.value = files[0].path
                self.page.update()
        return handler

    def tab_resultaten(self):
        sections = []
        for idx, (title, oms, stat, foto) in enumerate(self.result_controls):
            sections.append(
                ft.Container(
                    padding=10,
                    border=ft.Border(
                        left=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                        right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                        top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                        bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                    ),
                    border_radius=8,
                    content=ft.Column(
                        [
                            ft.Text(title, weight=ft.FontWeight.BOLD),
                            oms,
                            stat,
                            ft.Row(
                                [
                                    foto,
                                    ft.Button(
                                        "Kies foto",
                                        on_click=self._make_pick_handler(foto),
                                    ),
                                ]
                            ),
                        ],
                        spacing=8,
                    ),
                )
            )
        return ft.Container(padding=12, content=ft.Column(sections, spacing=10, scroll=ft.ScrollMode.AUTO))

    def tab_fotos(self):
        return ft.Container(
            padding=12,
            content=ft.Column(
                [
                    ft.Row([self.foto1, ft.Button("Kies foto 1", on_click=self._make_pick_handler(self.foto1))]),
                    self.caption1,
                    ft.Row([self.foto2, ft.Button("Kies foto 2", on_click=self._make_pick_handler(self.foto2))]),
                    self.caption2,
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    def tab_samenvatting(self):
        score_rows = []
        for name, ctrl in self.score_controls:
            score_rows.append(ft.Row([ft.Text(name, expand=True), ctrl]))
        return ft.Container(
            padding=12,
            content=ft.Column(
                [self.status_algemeen, self.samenvatting, ft.Divider(), *score_rows],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    def tab_conclusie(self):
        return ft.Container(
            padding=12,
            content=ft.Column(
                [self.advies_kort, self.advies_middel, self.advies_periodiek],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    async def pick_image_for(self, target: ft.TextField):
        files = await self.file_picker.pick_files(allow_multiple=False)
        if not files:
            return
        target.value = files[0].path
        self.page.update()

    def _collect(self) -> dict:
        return {
            "rapportnummer": self.rapportnummer.value,
            "datum": self.datum.value,
            "operator": self.operator.value,
            "opdrachtgever": self.opdrachtgever.value,
            "adres": self.adres.value,
            "postcode": self.postcode.value,
            "telefoon": self.telefoon.value,
            "type_object": self.type_object.value,
            "dakbedekking": self.dakbedekking.value,
            "bouwjaar": self.bouwjaar.value,
            "oppervlakte": self.oppervlakte.value,
            "status_algemeen": self.status_algemeen.value,
            "samenvatting": self.samenvatting.value,
            "scores": [ctrl.value for _, ctrl in self.score_controls],
            "resultaten": [
                {
                    "title": title,
                    "omschrijving": oms.value,
                    "status": stat.value,
                    "foto": foto.value,
                }
                for title, oms, stat, foto in self.result_controls
            ],
            "foto1": self.foto1.value,
            "foto2": self.foto2.value,
            "caption1": self.caption1.value,
            "caption2": self.caption2.value,
            "advies_kort": self.advies_kort.value,
            "advies_middel": self.advies_middel.value,
            "advies_periodiek": self.advies_periodiek.value,
        }

    def _apply(self, data: dict):
        self.rapportnummer.value = data.get("rapportnummer", self.rapportnummer.value)
        self.datum.value = data.get("datum", self.datum.value)
        self.operator.value = data.get("operator", self.operator.value)
        self.opdrachtgever.value = data.get("opdrachtgever", "")
        self.adres.value = data.get("adres", "")
        self.postcode.value = data.get("postcode", "")
        self.telefoon.value = data.get("telefoon", "")
        self.type_object.value = data.get("type_object", "")
        self.dakbedekking.value = data.get("dakbedekking", "")
        self.bouwjaar.value = data.get("bouwjaar", "")
        self.oppervlakte.value = data.get("oppervlakte", "")
        self.status_algemeen.value = data.get("status_algemeen", self.status_algemeen.value)
        self.samenvatting.value = data.get("samenvatting", "")

        scores = data.get("scores", [])
        for i, (_, ctrl) in enumerate(self.score_controls):
            if i < len(scores):
                ctrl.value = str(scores[i])

        rows = data.get("resultaten", [])
        for i, (_, oms, stat, foto) in enumerate(self.result_controls):
            if i < len(rows):
                oms.value = rows[i].get("omschrijving", "")
                stat.value = rows[i].get("status", stat.value)
                foto.value = rows[i].get("foto", "")

        self.foto1.value = data.get("foto1", "")
        self.foto2.value = data.get("foto2", "")
        self.caption1.value = data.get("caption1", self.caption1.value)
        self.caption2.value = data.get("caption2", self.caption2.value)

        self.advies_kort.value = data.get("advies_kort", "")
        self.advies_middel.value = data.get("advies_middel", "")
        self.advies_periodiek.value = data.get("advies_periodiek", "")
        self.page.update()

    async def save_project(self, e=None):
        self._pending_project_data = self._collect()
        path = await self.save_picker.save_file(file_name=f"Project_{self.rapportnummer.value}.json")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._pending_project_data or {}, f, ensure_ascii=False, indent=2)
            mark_used_rapportnummer(self.rapportnummer.value)
            self.notify("Project opgeslagen")
        except Exception as exc:
            self.notify(f"Opslaan mislukt: {exc}")

    async def open_project(self, e=None):
        files = await self.file_picker.pick_files(allow_multiple=False, allowed_extensions=["json"])
        if not files:
            return
        try:
            with open(files[0].path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._apply(data)
            self.notify("Project geladen")
        except Exception as exc:
            self.notify(f"Project openen mislukt: {exc}")

    def new_project(self, e=None):
        self.rapportnummer.value = next_rapportnummer()
        self.datum.value = date.today().strftime("%d %B %Y")
        self.operator.value = ""
        self.opdrachtgever.value = ""
        self.adres.value = ""
        self.postcode.value = ""
        self.telefoon.value = ""
        self.type_object.value = ""
        self.dakbedekking.value = ""
        self.bouwjaar.value = ""
        self.oppervlakte.value = ""
        self.status_algemeen.value = "MATIG / AANDACHTSPUNT"
        self.samenvatting.value = ""
        for _, c in self.score_controls:
            c.value = "3"
        for _, oms, stat, foto in self.result_controls:
            oms.value = ""
            stat.value = "Akkoord"
            foto.value = ""
        self.foto1.value = ""
        self.foto2.value = ""
        self.caption1.value = ""
        self.caption2.value = ""
        self.advies_kort.value = ""
        self.advies_middel.value = ""
        self.advies_periodiek.value = ""
        self.page.update()

    async def genereer_pdf(self, e=None):
        path = await self.save_picker.save_file(file_name=f"Inspectierapport_{self.rapportnummer.value}.pdf")
        if not path:
            return
        self._build_pdf(path)

    def _build_pdf(self, filepath: str):
        W_PAGE, _ = A4
        margin = 2 * cm
        usable_w = W_PAGE - 2 * margin
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin)

        def S(name, **kw):
            return ParagraphStyle(name, **kw)

        h2 = S("H2", fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#1f2d3d"), spaceBefore=8, spaceAfter=2)
        n = S("N", fontSize=9, fontName="Helvetica", leading=13)

        story = []

        logo_path = os.path.join(BASE_DIR, "inspectie.png")
        left = Image(logo_path, width=9 * cm, height=2.0 * cm, kind="proportional") if os.path.exists(logo_path) else Paragraph("<b>DAKINSPECTIES</b>", n)
        hdr = Table(
            [
                [left, Paragraph(f"<b>Rapportnummer:</b> {self.rapportnummer.value}", n)],
                [Paragraph("Drone Inspectierapport", n), Paragraph(f"<b>Datum:</b> {self.datum.value}", n)],
                ["", Paragraph(f"<b>Operator:</b> {self.operator.value}", n)],
            ],
            colWidths=[10 * cm, usable_w - 10 * cm],
        )
        hdr.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1f2d3d")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#f1f4f7")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.extend([hdr, Spacer(1, 0.35 * cm)])

        story.append(Paragraph("1. Project- en klantgegevens", h2))
        story.append(HRFlowable(width=usable_w, thickness=1, color=colors.HexColor("#32465a")))
        kv_rows = [
            ["Opdrachtgever", self.opdrachtgever.value, "Type object", self.type_object.value],
            ["Adres", self.adres.value, "Dakbedekking", self.dakbedekking.value],
            ["Postcode/Plaats", self.postcode.value, "Bouwjaar", self.bouwjaar.value],
            ["Telefoon", self.telefoon.value, "Oppervlakte", f"{self.oppervlakte.value} m2"],
        ]
        kv = Table(kv_rows, colWidths=[3.2 * cm, 5.0 * cm, 3.2 * cm, usable_w - 11.4 * cm])
        kv.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c6d0da")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#dbe3ec")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#dbe3ec")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([kv, Spacer(1, 0.3 * cm)])

        story.append(Paragraph("2. Samenvatting", h2))
        story.append(HRFlowable(width=usable_w, thickness=1, color=colors.HexColor("#32465a")))
        story.append(Paragraph(f"<b>Status:</b> {self.status_algemeen.value}", n))
        story.append(Paragraph(self.samenvatting.value or "-", n))
        story.append(Spacer(1, 0.2 * cm))

        score_rows = [["Onderdeel", "Score"]] + [[name, ctrl.value] for name, ctrl in self.score_controls]
        st = Table(score_rows, colWidths=[usable_w - 3 * cm, 3 * cm])
        st.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c6d0da")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#32465a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([st, Spacer(1, 0.3 * cm)])

        story.append(Paragraph("3. Inspectieresultaten", h2))
        story.append(HRFlowable(width=usable_w, thickness=1, color=colors.HexColor("#32465a")))
        for title, oms, stat, foto in self.result_controls:
            story.append(Paragraph(f"<b>{title}</b>", n))
            story.append(Paragraph(oms.value or "-", n))
            story.append(Paragraph(f"Status: {stat.value}", n))
            if foto.value and os.path.exists(foto.value):
                try:
                    story.append(Image(foto.value, width=9 * cm, height=6 * cm, kind="proportional"))
                except Exception:
                    pass
            story.append(Spacer(1, 0.15 * cm))

        story.append(Paragraph("4. Foto bijlage", h2))
        story.append(HRFlowable(width=usable_w, thickness=1, color=colors.HexColor("#32465a")))
        for fpath, cap in [(self.foto1.value, self.caption1.value), (self.foto2.value, self.caption2.value)]:
            if fpath and os.path.exists(fpath):
                try:
                    story.append(Image(fpath, width=8.5 * cm, height=5.5 * cm, kind="proportional"))
                except Exception:
                    pass
            story.append(Paragraph(cap or "-", n))
            story.append(Spacer(1, 0.15 * cm))

        story.append(Paragraph("5. Conclusie en advies", h2))
        story.append(HRFlowable(width=usable_w, thickness=1, color=colors.HexColor("#32465a")))
        story.append(Paragraph(f"<b>Korte termijn:</b> {self.advies_kort.value or '-'}", n))
        story.append(Paragraph(f"<b>Middellange termijn:</b> {self.advies_middel.value or '-'}", n))
        story.append(Paragraph(f"<b>Periodiek:</b> {self.advies_periodiek.value or '-'}", n))

        doc.build(story)
        mark_used_rapportnummer(self.rapportnummer.value)
        self.notify(f"PDF opgeslagen: {filepath}")


def main(page: ft.Page):
    CrossPlatformApp(page)


if __name__ == "__main__":
    ft.run(main)

