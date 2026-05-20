import json
import os
import re
import inspect
import tempfile
import traceback
from datetime import date

import flet as ft

from branding_settings import BrandingSettings, load_branding_settings, save_branding_settings
from pdf_report_common import build_pdf_report


BASE_DIR = os.path.dirname(__file__)
COUNTER_FILE = os.path.join(BASE_DIR, "project_counter.json")
IMAGE_FIT_CONTAIN = getattr(getattr(ft, "ImageFit", None), "CONTAIN", "contain")


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
        self.page.title = "Dakinspecties"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.scroll = ft.ScrollMode.HIDDEN
        self.page.padding = 8
        self.page.bgcolor = ft.Colors.BLUE_GREY_50
        self.page.theme = ft.Theme(
            use_material3=True,
            color_scheme_seed=ft.Colors.BLUE,
            visual_density=ft.VisualDensity.COMPACT,
            scaffold_bgcolor=ft.Colors.BLUE_GREY_50,
            divider_color=ft.Colors.BLUE_GREY_100,
        )
        self._panel_bg = ft.Colors.WHITE
        self._panel_alt_bg = ft.Colors.BLUE_GREY_50
        self._panel_border = ft.Colors.BLUE_GREY_100
        self._accent_bg = ft.Colors.BLUE_50
        self._accent_text = ft.Colors.BLUE_700
        self._muted_text = ft.Colors.BLUE_GREY_600
        self._success_text = ft.Colors.GREEN_700
        self._error_text = ft.Colors.RED_700
        self._page_title_size = 20
        self._section_title_size = 16
        self._compact_spacing = 6
        self._compact_padding = 8
        self._field_width = 220
        self._dropdown_width = 190
        self._logo_field_width = 520
        self._status_width = 280
        self._configure_window()

        self._active_tab = 0
        self._mobile_breakpoint = 900
        self._tab_labels = ["Algemeen", "Inspectieresultaten", "Foto's", "Samenvatting", "Conclusie", "Instellingen"]
        self._branding = load_branding_settings(BASE_DIR)

        self.file_picker = ft.FilePicker()
        self.save_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)
        self.page.services.append(self.save_picker)
        self.page.on_resized = self._on_page_resized

        self.build_ui()

    def _brand_name(self) -> str:
        value = (self.company_name.value or "").strip()
        return value or "Dakinspecties"

    def _brand_logo_path(self) -> str:
        logo_path = (self.company_logo.value or "").strip()
        if logo_path and os.path.exists(logo_path):
            return logo_path
        return ""

    def _save_branding(self, completed: bool = True):
        self._branding = BrandingSettings(
            company_name=self._brand_name(),
            logo_path=(self.company_logo.value or "").strip(),
            setup_completed=completed,
        )
        save_branding_settings(BASE_DIR, self._branding)

    def _new_image(self, width: int, height: int, visible: bool = False):
        # Flet API differs between versions; always pass src to avoid constructor errors.
        try:
            return ft.Image(src="", width=width, height=height, fit=IMAGE_FIT_CONTAIN, visible=visible)
        except TypeError:
            return ft.Image("", width=width, height=height, fit=IMAGE_FIT_CONTAIN, visible=visible)

    def _apply_branding_ui(self):
        company = self._brand_name()
        logo_path = self._brand_logo_path()
        self.page.title = "Dakinspecties"
        self.branding_title.value = f"{company} - Dakinspecties"
        self.branding_logo.src = logo_path
        self.branding_logo.visible = bool(logo_path)
        if hasattr(self, "branding_logo_preview"):
            self.branding_logo_preview.src = logo_path
            self.branding_logo_preview.visible = bool(logo_path)
        if hasattr(self, "branding_name_preview"):
            self.branding_name_preview.value = company
        if hasattr(self, "logo_path_status"):
            raw = (self.company_logo.value or "").strip()
            if not raw:
                self.logo_path_status.value = "Geen logo ingesteld"
                self.logo_path_status.color = self._muted_text
            elif logo_path:
                self.logo_path_status.value = "Logo gevonden"
                self.logo_path_status.color = self._success_text
            else:
                self.logo_path_status.value = "Logo pad bestaat niet"
                self.logo_path_status.color = self._error_text

    async def _pick_company_logo(self, e=None):
        files = await self._resolve_picker_result(
            self.file_picker.pick_files(allow_multiple=False, allowed_extensions=["png", "jpg", "jpeg", "bmp", "gif"])
        )
        if files:
            self.company_logo.value = files[0].path
            self._apply_branding_ui()
            self.page.update()

    def _save_branding_action(self, e=None):
        self._save_branding(completed=True)
        self._apply_branding_ui()
        self.notify("Bedrijfsprofiel opgeslagen")

    def _reset_branding_action(self, e=None):
        defaults = BrandingSettings()
        self.company_name.value = defaults.company_name
        self.company_logo.value = defaults.logo_path
        self._save_branding(completed=True)
        self._apply_branding_ui()
        self.page.update()
        self.notify("Bedrijfsprofiel hersteld")

    def _on_company_name_change(self, e):
        self._apply_branding_ui()
        self.page.update()

    def _on_company_logo_change(self, e):
        self._apply_branding_ui()
        self.page.update()

    def notify(self, msg: str):
        snack = ft.SnackBar(ft.Text(msg), open=True)
        self.page.overlay.append(snack)
        self.page.update()

    async def _resolve_picker_result(self, value):
        if inspect.isawaitable(value):
            return await value
        return value

    def _is_phone(self) -> bool:
        platform_str = str(getattr(self.page, "platform", "")).lower()
        return "android" in platform_str or "ios" in platform_str

    def _configure_window(self):
        # Mobile targets do not always expose desktop window sizing APIs.
        if self._is_phone():
            return
        try:
            if getattr(self.page, "window", None):
                    self.page.window.width = 1120
                    self.page.window.height = 760
        except Exception:
            pass

    def _fallback_dir(self) -> str:
        fallback = os.path.join(BASE_DIR, "exports")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _write_fallback_bytes(self, filename: str, payload: bytes) -> str:
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
        target = os.path.join(self._fallback_dir(), safe_name)
        with open(target, "wb") as f:
            f.write(payload)
        return target

    def _write_fallback_json(self, filename: str, data: dict) -> str:
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        return self._write_fallback_bytes(filename, payload)

    def _switch_tab(self, idx: int):
        self._active_tab = idx
        for i, btn in enumerate(self._tab_buttons):
            btn.bgcolor = self._accent_bg if i == idx else ft.Colors.WHITE
            btn.color = self._accent_text if i == idx else self._muted_text
            btn.style = self._tab_button_style(selected=i == idx)
        self._tab_content_area.content = self._tab_contents[idx]
        if self._tab_selector.value != self._tab_labels[idx]:
            self._tab_selector.value = self._tab_labels[idx]
        self.page.update()

    def _is_mobile(self) -> bool:
        width = self.page.width or 0
        if width <= 0:
            try:
                if getattr(self.page, "window", None):
                    width = self.page.window.width or 0
            except Exception:
                width = 0
        return width > 0 and width <= self._mobile_breakpoint

    def _apply_responsive_layout(self):
        mobile = self._is_mobile()
        self._tab_bar.visible = not mobile
        self._tab_selector.visible = mobile
        self.page.update()

    def _on_page_resized(self, e):
        self._apply_responsive_layout()

    def _on_tab_selector_change(self, e):
        try:
            idx = self._tab_labels.index(self._tab_selector.value)
        except ValueError:
            idx = 0
        self._switch_tab(idx)

    def _on_rapport_type_change(self, e):
        self._apply_rapport_type_labels()
        label = self.rapport_type.value or "Inspectierapport"
        self.notify(f"Rapporttype ingesteld op: {label}")

    def _apply_rapport_type_labels(self):
        is_oplever = self.rapport_type.value == "Opleverrapport"
        self.datum.label = "Datum oplevering" if is_oplever else "Datum inspectie"
        self.operator.label = "Uitvoerder" if is_oplever else "Operator"
        self._tab_labels[1] = "Opleverpunten" if is_oplever else "Inspectieresultaten"
        for i, btn in enumerate(self._tab_buttons):
            btn.content = self._tab_labels[i]
        self._tab_selector.options = [ft.dropdown.Option(l) for l in self._tab_labels]
        self._tab_selector.value = self._tab_labels[self._active_tab]

    def _tab_shell(self, controls):
        return ft.Container(
            expand=True,
            padding=self._compact_padding,
            bgcolor=self._panel_bg,
            border_radius=12,
            border=ft.Border(
                left=ft.BorderSide(1, self._panel_border),
                right=ft.BorderSide(1, self._panel_border),
                top=ft.BorderSide(1, self._panel_border),
                bottom=ft.BorderSide(1, self._panel_border),
            ),
            content=ft.ListView(controls=controls, spacing=self._compact_spacing, expand=True),
        )

    def _tab_button_style(self, selected: bool = False):
        return ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=18),
            padding=ft.Padding(left=14, top=9, right=14, bottom=9),
            side=ft.BorderSide(1, self._accent_bg if selected else self._panel_border),
        )

    def _secondary_button(self, text: str, on_click, icon=None):
        return ft.OutlinedButton(
            text,
            icon=icon,
            on_click=on_click,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=14),
                padding=ft.Padding(left=12, top=10, right=12, bottom=10),
                side=ft.BorderSide(1, self._panel_border),
            ),
        )

    def _primary_button(self, text: str, on_click, icon=None):
        return ft.FilledButton(
            text,
            icon=icon,
            on_click=on_click,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=14),
                padding=ft.Padding(left=14, top=10, right=14, bottom=10),
            ),
        )

    def build_ui(self):
        self.company_name = ft.TextField(
            label="Bedrijfsnaam",
            value=self._branding.company_name,
            width=280,
            on_change=self._on_company_name_change,
        )
        self.company_logo = ft.TextField(
            label="Logo pad",
            value=self._branding.logo_path,
            read_only=False,
            expand=False,
            width=self._logo_field_width,
            hint_text="Bijv. C:\\Afbeeldingen\\bedrijfslogo.png",
            on_change=self._on_company_logo_change,
        )

        self.rapportnummer = ft.TextField(label="Rapportnummer", value=next_rapportnummer(), width=200)
        self.datum = ft.TextField(label="Datum inspectie", value=date.today().strftime("%d %B %Y"), width=200)
        self.operator = ft.TextField(label="Operator", width=200)
        self.rapport_type = ft.Dropdown(
            label="Rapporttype",
            value="Inspectierapport",
            options=[
                ft.dropdown.Option("Inspectierapport"),
                ft.dropdown.Option("Opleverrapport"),
            ],
            width=self._dropdown_width,
            on_select=self._on_rapport_type_change,
        )

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
            width=self._status_width,
        )
        self.samenvatting = ft.TextField(label="Samenvatting", multiline=True, min_lines=3, max_lines=6)

        self.score_controls = [
            ("Dakbedekking & Oppervlakte", ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="2", width=92)),
            ("Naden en Lasverbindingen", ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="2", width=92)),
            ("Randafwerking & Trimmen", ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="3", width=92)),
            ("Hemelwaterafvoer (HWA) & Goot", ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="4", width=92)),
            ("Dakdoorvoeren & Aansluitingen", ft.Dropdown(options=[ft.dropdown.Option(str(i)) for i in range(1, 6)], value="2", width=92)),
        ]

        self.result_titles = [
            "2.1 Dakbedekking & Oppervlakte",
            "2.2 Naden en Lasverbindingen",
            "2.3 Randafwerking & Trimmen",
            "2.4 Hemelwaterafvoer (HWA) & Goot",
            "2.5 Dakdoorvoeren & Aansluitingen",
        ]
        self.result_controls = []
        for title in self.result_titles:
            oms = ft.TextField(label="Omschrijving", multiline=True, min_lines=2, max_lines=4)
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
                width=230,
            )
            foto = ft.TextField(label="Foto pad", read_only=True, expand=True)
            self.result_controls.append((title, oms, stat, foto))

        self.foto1 = ft.TextField(label="Foto 1 pad", read_only=True, expand=True)
        self.foto2 = ft.TextField(label="Foto 2 pad", read_only=True, expand=True)
        self.caption1 = ft.TextField(label="Bijschrift foto 1", value="Totaaloverzicht van het geinspecteerde dakvlak.")
        self.caption2 = ft.TextField(label="Bijschrift foto 2", value="Detailopname van de verstopte hemelwaterafvoer.")
        self.extra_fotos = []
        self.extra_fotos_column = None

        self.advies_kort = ft.TextField(label="Korte termijn", multiline=True, min_lines=2, max_lines=4)
        self.advies_middel = ft.TextField(label="Middellange termijn", multiline=True, min_lines=2, max_lines=4)
        self.advies_periodiek = ft.TextField(label="Periodiek onderhoud", multiline=True, min_lines=2, max_lines=4)

        self._tab_contents = [
            self.tab_algemeen(),
            self.tab_resultaten(),
            self.tab_fotos(),
            self.tab_samenvatting(),
            self.tab_conclusie(),
            self.tab_instellingen(),
        ]

        self._tab_buttons = []
        for i, label in enumerate(self._tab_labels):
            idx = i

            def make_switch(i=i):
                def handler(e):
                    self._switch_tab(i)
                return handler

            btn = ft.Button(
                content=label,
                bgcolor=self._accent_bg if i == 0 else ft.Colors.WHITE,
                color=self._accent_text if i == 0 else self._muted_text,
                style=self._tab_button_style(selected=i == 0),
                on_click=make_switch(i),
            )
            self._tab_buttons.append(btn)

        self._tab_bar = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border_radius=16,
            border=ft.Border(
                left=ft.BorderSide(1, self._panel_border),
                right=ft.BorderSide(1, self._panel_border),
                top=ft.BorderSide(1, self._panel_border),
                bottom=ft.BorderSide(1, self._panel_border),
            ),
            padding=ft.Padding(left=6, top=6, right=6, bottom=6),
            content=ft.Row(self._tab_buttons, spacing=6, wrap=True, run_spacing=6),
        )
        self._tab_selector = ft.Dropdown(
            label="Sectie",
            value=self._tab_labels[0],
            options=[ft.dropdown.Option(l) for l in self._tab_labels],
            on_select=self._on_tab_selector_change,
            visible=False,
        )

        self._tab_content_area = ft.Container(
            content=self._tab_contents[0],
            expand=True,
            bgcolor=self._panel_alt_bg,
            border_radius=12,
            padding=2,
        )

        self.branding_logo = self._new_image(width=112, height=32, visible=False)
        self.branding_title = ft.Text("Dakinspecties", size=self._page_title_size, weight=ft.FontWeight.BOLD)

        actions = ft.Row(
            [
                self.rapport_type,
                self._secondary_button("Bedrijfsprofiel opslaan", self._save_branding_action),
                self._secondary_button("Nieuw", self.new_project),
                self._secondary_button("Open project", self.open_project),
                self._secondary_button("Opslaan project", self.save_project),
                self._primary_button("Genereer PDF", self.genereer_pdf),
            ],
            spacing=6,
            wrap=True,
            run_spacing=6,
        )
        header = ft.Column(
            [
                ft.Row([self.branding_logo, self.branding_title], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                actions,
            ],
            spacing=6,
        )

        layout = ft.Column(
            [
                header,
                ft.Divider(height=2),
                self._tab_bar,
                self._tab_selector,
                ft.Divider(height=2),
                self._tab_content_area,
            ],
            expand=True,
            spacing=0,
        )
        self.page.add(layout)
        self._apply_branding_ui()
        if not self._branding.setup_completed:
            self.notify("Stel bij eerste gebruik bovenaan je bedrijfsnaam en logo in en klik op 'Bedrijfsprofiel opslaan'.")
        self._apply_rapport_type_labels()
        self._apply_responsive_layout()

    def tab_algemeen(self):
        return self._tab_shell([
            ft.Row([self.rapportnummer, self.datum, self.operator], wrap=True),
            self.opdrachtgever,
            self.adres,
            ft.Row([self.postcode, self.telefoon], wrap=True),
            ft.Row([self.type_object, self.dakbedekking], wrap=True),
            ft.Row([self.bouwjaar, self.oppervlakte], wrap=True),
        ])

    def tab_instellingen(self):
        self.branding_logo_preview = self._new_image(width=180, height=72, visible=False)
        self.branding_name_preview = ft.Text("Dakinspecties", size=16, weight=ft.FontWeight.BOLD)
        self.logo_path_status = ft.Text("", color=self._muted_text)
        return self._tab_shell([
            ft.Text("Bedrijfsprofiel", size=self._section_title_size, weight=ft.FontWeight.BOLD),
            self.company_name,
            self.company_logo,
            self.logo_path_status,
            ft.Row([self._secondary_button("Kies logo", self._pick_company_logo)], wrap=True),
            ft.Row([
                self._primary_button("Opslaan", self._save_branding_action),
                self._secondary_button("Reset", self._reset_branding_action),
            ]),
            ft.Divider(height=8),
            ft.Text("Preview", weight=ft.FontWeight.BOLD, color=self._muted_text),
            self.branding_name_preview,
            self.branding_logo_preview,
        ])

    def _make_pick_handler(self, target: ft.TextField):
        """Maakt een click-handler die een foto kiest (sync/async compat)."""
        async def handler(e):
            files = await self._resolve_picker_result(
                self.file_picker.pick_files(allow_multiple=False)
            )
            if files:
                target.value = files[0].path
                self.page.update()
        return handler

    def tab_resultaten(self):
        sections = []
        for idx, (title, oms, stat, foto) in enumerate(self.result_controls):
            sections.append(
                ft.Container(
                    padding=self._compact_padding,
                    bgcolor=self._panel_alt_bg,
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
                                    self._secondary_button(
                                        "Kies foto",
                                        self._make_pick_handler(foto),
                                    ),
                                ]
                            ),
                        ],
                        spacing=self._compact_spacing,
                    ),
                )
            )
        return self._tab_shell(sections)

    def tab_fotos(self):
        self.extra_fotos_column = ft.Column(spacing=8)
        self._rebuild_extra_fotos_ui()
        return self._tab_shell([
            ft.Row([self.foto1, self._secondary_button("Kies foto 1", self._make_pick_handler(self.foto1))]),
            self.caption1,
            ft.Row([self.foto2, self._secondary_button("Kies foto 2", self._make_pick_handler(self.foto2))]),
            self.caption2,
            ft.Divider(height=8),
            ft.Text("Extra foto's", weight=ft.FontWeight.BOLD),
            self.extra_fotos_column,
            self._secondary_button("+ Foto regel toevoegen", self._add_extra_foto_row),
        ])

    def _add_extra_foto_row(self, e=None, path="", caption=""):
        p = ft.TextField(label=f"Foto {len(self.extra_fotos) + 3} pad", read_only=True, expand=True, value=path)
        c = ft.TextField(label=f"Bijschrift foto {len(self.extra_fotos) + 3}", value=caption)
        self.extra_fotos.append((p, c))
        self._rebuild_extra_fotos_ui()

    def _remove_extra_foto_row(self, idx: int):
        if 0 <= idx < len(self.extra_fotos):
            self.extra_fotos.pop(idx)
            self._rebuild_extra_fotos_ui()

    def _rebuild_extra_fotos_ui(self):
        if self.extra_fotos_column is None:
            return
        controls = []
        for idx, (path, caption) in enumerate(self.extra_fotos, start=3):
            path.label = f"Foto {idx} pad"
            caption.label = f"Bijschrift foto {idx}"

            remove_idx = idx - 3

            def make_remove(i=remove_idx):
                return lambda _e: self._remove_extra_foto_row(i)

            controls.extend([
                ft.Row([
                    path,
                    self._secondary_button("Kies foto", self._make_pick_handler(path)),
                    self._secondary_button("Verwijder", make_remove()),
                ]),
                caption,
                ft.Divider(height=6),
            ])
        self.extra_fotos_column.controls = controls
        self.page.update()

    def _collect_foto_items(self):
        items = [
            {"path": self.foto1.value or "", "caption": self.caption1.value or ""},
            {"path": self.foto2.value or "", "caption": self.caption2.value or ""},
        ]
        for path, caption in self.extra_fotos:
            items.append({"path": path.value or "", "caption": caption.value or ""})
        return items

    def _load_foto_items(self, items):
        self.foto1.value = ""
        self.foto2.value = ""
        self.caption1.value = ""
        self.caption2.value = ""
        if len(items) > 0:
            self.foto1.value = items[0].get("path", "")
            self.caption1.value = items[0].get("caption", "")
        if len(items) > 1:
            self.foto2.value = items[1].get("path", "")
            self.caption2.value = items[1].get("caption", "")
        self.extra_fotos = []
        for it in items[2:]:
            self.extra_fotos.append(
                (
                    ft.TextField(label="", read_only=True, expand=True, value=it.get("path", "")),
                    ft.TextField(label="", value=it.get("caption", "")),
                )
            )
        self._rebuild_extra_fotos_ui()

    def _precheck_pdf_generation(self):
        issues = []
        if not (self.rapportnummer.value or "").strip():
            issues.append("Rapportnummer ontbreekt")
        if not (self.opdrachtgever.value or "").strip():
            issues.append("Opdrachtgever ontbreekt")
        if not (self.adres.value or "").strip():
            issues.append("Adres ontbreekt")
        return issues

    def _verify_pdf_created(self, path: str) -> bool:
        try:
            return os.path.exists(path) and os.path.getsize(path) > 0
        except Exception:
            return False

    def tab_samenvatting(self):
        score_rows = []
        for name, ctrl in self.score_controls:
            score_rows.append(ft.Row([ft.Text(name, expand=True), ctrl]))
        return self._tab_shell([self.status_algemeen, self.samenvatting, ft.Divider(), *score_rows])

    def tab_conclusie(self):
        return self._tab_shell([self.advies_kort, self.advies_middel, self.advies_periodiek])

    async def pick_image_for(self, target: ft.TextField):
        files = await self._resolve_picker_result(
            self.file_picker.pick_files(allow_multiple=False)
        )
        if files:
            target.value = files[0].path
            self.page.update()

    def _collect(self) -> dict:
        return {
            "rapport_type": self.rapport_type.value,
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
            "foto_items": self._collect_foto_items(),
            "advies_kort": self.advies_kort.value,
            "advies_middel": self.advies_middel.value,
            "advies_periodiek": self.advies_periodiek.value,
        }

    def _apply(self, data: dict):
        self.rapport_type.value = data.get("rapport_type", self.rapport_type.value)
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
        foto_items = data.get("foto_items")
        if isinstance(foto_items, list):
            self._load_foto_items(foto_items)
        else:
            self.extra_fotos = []
            self._rebuild_extra_fotos_ui()

        self.advies_kort.value = data.get("advies_kort", "")
        self.advies_middel.value = data.get("advies_middel", "")
        self.advies_periodiek.value = data.get("advies_periodiek", "")
        self.page.update()

    async def save_project(self, e=None):
        data = self._collect()
        filename = f"Project_{self.rapportnummer.value}.json"
        try:
            payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            path = await self._resolve_picker_result(
                self.save_picker.save_file(
                    dialog_title="Project opslaan",
                    file_name=filename,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["json"],
                    src_bytes=payload,
                )
            )
            if not path:
                if self._is_phone():
                    fallback_path = self._write_fallback_json(filename, data)
                    mark_used_rapportnummer(self.rapportnummer.value)
                    self.notify(f"⚠ Opslaan via dialog geannuleerd. Lokaal opgeslagen:\n{fallback_path}")
                    return
                self.notify("Opslaan geannuleerd")
                return
            mark_used_rapportnummer(self.rapportnummer.value)
            self.notify(f"✅ Project opgeslagen:\n{path}")
        except Exception as exc:
            if self._is_phone():
                try:
                    fallback_path = self._write_fallback_json(filename, data)
                    mark_used_rapportnummer(self.rapportnummer.value)
                    self.notify(f"⚠ Opslaan via dialog mislukt ({exc}). Lokaal opgeslagen:\n{fallback_path}")
                    return
                except Exception:
                    pass
            self.notify(f"Opslaan mislukt: {exc}")

    async def open_project(self, e=None):
        files = await self._resolve_picker_result(
            self.file_picker.pick_files(allow_multiple=False, allowed_extensions=["json"])
        )
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
        self.rapport_type.value = "Inspectierapport"
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
        self.extra_fotos = []
        self._rebuild_extra_fotos_ui()
        self.advies_kort.value = ""
        self.advies_middel.value = ""
        self.advies_periodiek.value = ""
        self.page.update()

    async def genereer_pdf(self, e=None):
        issues = self._precheck_pdf_generation()
        if issues:
            self.notify("PDF niet gemaakt: " + " | ".join(issues))
            return

        is_oplever = self.rapport_type.value == "Opleverrapport"
        prefix = "Opleverrapport" if is_oplever else "Inspectierapport"
        filename = f"{prefix}_{self.rapportnummer.value}.pdf"
        tmp_fd, tmp_path = tempfile.mkstemp(prefix="dakinspecties_", suffix=".pdf")
        os.close(tmp_fd)
        try:
            if is_oplever:
                self._build_pdf_oplever(tmp_path)
            else:
                self._build_pdf_inspectie(tmp_path)

            if not self._verify_pdf_created(tmp_path):
                self.notify("PDF controle mislukt: bestand ontbreekt of is leeg.")
                return

            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()

            path = await self._resolve_picker_result(
                self.save_picker.save_file(
                    dialog_title="PDF opslaan",
                    file_name=filename,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["pdf"],
                    src_bytes=pdf_bytes,
                )
            )
            if not path:
                if self._is_phone():
                    fallback_path = self._write_fallback_bytes(filename, pdf_bytes)
                    self.notify(f"⚠ PDF-dialog geannuleerd. Lokaal opgeslagen:\n{fallback_path}")
                    return
                self.notify("PDF opslaan geannuleerd")
                return
            self.notify(f"✅ PDF opgeslagen:\n{path}")
        except Exception as exc:
            if self._is_phone():
                try:
                    if "pdf_bytes" in locals() and isinstance(pdf_bytes, (bytes, bytearray)):
                        fallback_path = self._write_fallback_bytes(filename, bytes(pdf_bytes))
                        self.notify(f"⚠ PDF opslaan via dialog mislukt ({exc}). Lokaal opgeslagen:\n{fallback_path}")
                        return
                except Exception:
                    pass
            self.notify(f"PDF genereren mislukt: {exc}")
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    def _pdf_payload(self) -> dict:
        return {
            "rapport_type": self.rapport_type.value,
            "company_name": self._brand_name(),
            "logo_path": self._brand_logo_path(),
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
            "scores": [(label, ctrl.value) for label, ctrl in self.score_controls],
            "resultaten": [
                {
                    "title": title,
                    "omschrijving": oms.value,
                    "status": stat.value,
                    "foto": foto.value,
                }
                for title, oms, stat, foto in self.result_controls
            ],
            "foto_items": self._collect_foto_items(),
            "advies_kort": self.advies_kort.value,
            "advies_middel": self.advies_middel.value,
            "advies_periodiek": self.advies_periodiek.value,
        }

    def _build_pdf_inspectie(self, filepath: str):
        payload = self._pdf_payload()
        payload["rapport_type"] = "Inspectierapport"
        build_pdf_report(filepath, payload)
        mark_used_rapportnummer(self.rapportnummer.value)

    def _build_pdf_oplever(self, filepath: str):
        payload = self._pdf_payload()
        payload["rapport_type"] = "Opleverrapport"
        build_pdf_report(filepath, payload)
        mark_used_rapportnummer(self.rapportnummer.value)


def main(page: ft.Page):
    try:
        CrossPlatformApp(page)
    except Exception as exc:
        traceback.print_exc()
        page.clean()
        page.add(ft.Text("Opstartfout in app", color=ft.Colors.RED_400, size=20, weight=ft.FontWeight.BOLD))
        page.add(ft.Text(str(exc), color=ft.Colors.RED_200))
        page.add(ft.Text("De app kon niet starten. Deel deze foutmelding voor een fix."))
        page.update()


if __name__ == "__main__":
    ft.run(main)

