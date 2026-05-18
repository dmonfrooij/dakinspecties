import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import date
import os
import threading
import tempfile

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, HRFlowable, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY


# ─────────────────────────────────────────────────────────────────────────────
# Annotatie venster – teken aandachtspunten op een foto
# ─────────────────────────────────────────────────────────────────────────────
class AnnotatieVenster(tk.Toplevel):
    """Pop-up waarmee de gebruiker rechthoeken, cirkels en pijlen op een
    foto kan tekenen. Bij opslaan wordt een geannoteerde kopie gemaakt."""

    def __init__(self, parent, foto_path_var: tk.StringVar):
        super().__init__(parent)
        self.title("✏  Aandachtspunten markeren")
        self.resizable(False, False)
        self.foto_path_var = foto_path_var
        self.orig_path = foto_path_var.get()
        self.shapes: list = []          # opgeslagen vormen
        self._drawing = False
        self._cur_item = None
        self._sx = self._sy = 0

        self._load_image()
        self._build_ui()
        self.grab_set()

    # ── afbeelding laden & schalen ────────────────────────────────────────
    def _load_image(self):
        from PIL import Image as PILImage, ImageTk
        self._PILImage = PILImage
        self._pil_orig = PILImage.open(self.orig_path)
        MAX_W, MAX_H = 860, 580
        w, h = self._pil_orig.size
        self.scale = min(MAX_W / w, MAX_H / h, 1.0)
        self._disp_w = int(w * self.scale)
        self._disp_h = int(h * self.scale)
        disp = self._pil_orig.resize((self._disp_w, self._disp_h),
                                     PILImage.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(disp)

    # ── UI ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Toolbar
        tb = tk.Frame(self, bg="#2c3e50", pady=6)
        tb.pack(fill="x")

        tk.Label(tb, text="Tool:", bg="#2c3e50", fg="white",
                 font=("Arial", 10)).pack(side="left", padx=(8, 2))
        self.tool_var = tk.StringVar(value="rect")
        for lbl, val in [("▭ Rechthoek", "rect"),
                         ("○ Cirkel",     "circle"),
                         ("➜ Pijl",       "arrow")]:
            tk.Radiobutton(tb, text=lbl, variable=self.tool_var, value=val,
                           bg="#2c3e50", fg="white", selectcolor="#1a252f",
                           activebackground="#2c3e50",
                           font=("Arial", 10)).pack(side="left", padx=3)

        tk.Label(tb, text="  Kleur:", bg="#2c3e50", fg="white",
                 font=("Arial", 10)).pack(side="left", padx=(10, 2))
        self.color_var = tk.StringVar(value="#e74c3c")
        for clr, name in [("#e74c3c", "Rood"),
                           ("#f39c12", "Oranje"),
                           ("#f1c40f", "Geel")]:
            tk.Button(tb, text=name, bg=clr, fg="white", width=7,
                      relief="flat",
                      command=lambda c=clr: self.color_var.set(c)
                      ).pack(side="left", padx=2)

        tk.Button(tb, text="↩", font=("Arial", 12), bg="#7f8c8d",
                  fg="white", relief="flat", width=3,
                  command=self._undo).pack(side="left", padx=(10, 2))
        tk.Button(tb, text="🗑", font=("Arial", 12), bg="#7f8c8d",
                  fg="white", relief="flat", width=3,
                  command=self._clear).pack(side="left", padx=2)
        tk.Button(tb, text="✔  Opslaan & sluiten",
                  font=("Arial", 10, "bold"), bg="#27ae60", fg="white",
                  relief="flat", padx=10,
                  command=self._save).pack(side="right", padx=10)

        # Canvas
        self.cv = tk.Canvas(self, width=self._disp_w, height=self._disp_h,
                            cursor="crosshair", bg="#1a252f")
        self.cv.pack()
        self._img_item = self.cv.create_image(0, 0, anchor="nw",
                                              image=self._tk_img)
        self.cv.bind("<ButtonPress-1>",   self._press)
        self.cv.bind("<B1-Motion>",       self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)

    # ── teken-handlers ───────────────────────────────────────────────────
    def _press(self, e):
        self._drawing = True
        self._sx, self._sy = e.x, e.y
        self._cur_item = None

    def _drag(self, e):
        col  = self.color_var.get()
        tool = self.tool_var.get()
        if self._cur_item:
            self.cv.delete(self._cur_item)
        kw = dict(outline=col, width=3) if tool != "arrow" else \
             dict(fill=col, width=3, arrow=tk.LAST, arrowshape=(12, 15, 5))
        if tool == "rect":
            self._cur_item = self.cv.create_rectangle(
                self._sx, self._sy, e.x, e.y, **kw)
        elif tool == "circle":
            self._cur_item = self.cv.create_oval(
                self._sx, self._sy, e.x, e.y, **kw)
        elif tool == "arrow":
            self._cur_item = self.cv.create_line(
                self._sx, self._sy, e.x, e.y, **kw)

    def _release(self, e):
        if not self._drawing:
            return
        self._drawing = False
        self.shapes.append((self.tool_var.get(),
                            self._sx, self._sy, e.x, e.y,
                            self.color_var.get()))
        self._cur_item = None

    # ── undo / clear ─────────────────────────────────────────────────────
    def _undo(self):
        if self.shapes:
            self.shapes.pop()
            self._redraw_canvas()

    def _clear(self):
        self.shapes.clear()
        self._redraw_canvas()

    def _redraw_canvas(self):
        self.cv.delete("all")
        self._img_item = self.cv.create_image(0, 0, anchor="nw",
                                              image=self._tk_img)
        for tool, x1, y1, x2, y2, col in self.shapes:
            if tool == "rect":
                self.cv.create_rectangle(x1, y1, x2, y2,
                                         outline=col, width=3)
            elif tool == "circle":
                self.cv.create_oval(x1, y1, x2, y2,
                                    outline=col, width=3)
            elif tool == "arrow":
                self.cv.create_line(x1, y1, x2, y2, fill=col, width=3,
                                    arrow=tk.LAST,
                                    arrowshape=(12, 15, 5))

    # ── opslaan als geannoteerde afbeelding ──────────────────────────────
    def _save(self):
        import math
        import tempfile
        from PIL import ImageDraw

        img = self._pil_orig.convert("RGB")
        draw = ImageDraw.Draw(img)
        inv = 1.0 / self.scale
        lw = max(3, int(4 * inv))

        for tool, x1, y1, x2, y2, col in self.shapes:
            ox1, oy1 = int(x1 * inv), int(y1 * inv)
            ox2, oy2 = int(x2 * inv), int(y2 * inv)
            if tool == "rect":
                draw.rectangle([ox1, oy1, ox2, oy2], outline=col, width=lw)
            elif tool == "circle":
                draw.ellipse([ox1, oy1, ox2, oy2], outline=col, width=lw)
            elif tool == "arrow":
                draw.line([ox1, oy1, ox2, oy2], fill=col, width=lw)
                ang = math.atan2(oy2 - oy1, ox2 - ox1)
                al = int(24 * inv)
                aa = math.pi / 6
                for da in (-aa, aa):
                    ax = ox2 - int(al * math.cos(ang - da))
                    ay = oy2 - int(al * math.sin(ang - da))
                    draw.line([ox2, oy2, ax, ay], fill=col, width=lw)

        ext = os.path.splitext(self.orig_path)[1] or ".jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        img.save(tmp.name, quality=95)
        tmp.close()

        self.foto_path_var.set(tmp.name)
        messagebox.showinfo("✔  Opgeslagen",
                            "Annotaties zijn toegepast op de foto.",
                            parent=self)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Helper: scrollable frame inside a notebook tab
# ─────────────────────────────────────────────────────────────────────────────
def scrollable_tab(notebook, title):
    outer = ttk.Frame(notebook)
    notebook.add(outer, text=title)

    canvas = tk.Canvas(outer, bg="#f0f4f8", highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)

    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Mouse-wheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    return inner


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────
class DakInspectieApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Dakwerk Sterken – Drone Inspectierapport Generator")
        self.root.geometry("960x720")
        self.root.resizable(True, True)

        # Photo path variables
        self.foto1_path = tk.StringVar()
        self.foto2_path = tk.StringVar()
        self.kaart_path: str | None = None   # gegenereerde kaartafbeelding
        self._kaart_tk_img = None            # tkinter PhotoImage referentie

        self._build_ui()

    # ── UI skeleton ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # Top banner
        banner = tk.Frame(self.root, bg="#1a252f", pady=12)
        banner.pack(fill="x")
        tk.Label(banner, text="DAKWERK STERKEN",
                 font=("Arial", 20, "bold"), fg="white", bg="#1a252f").pack()
        tk.Label(banner, text="Drone Inspectierapport Generator",
                 font=("Arial", 11), fg="#bdc3c7", bg="#1a252f").pack()

        # Notebook
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook.Tab", padding=[12, 6], font=("Arial", 10))

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        self._tab_algemeen()
        self._tab_samenvatting()
        self._tab_resultaten()
        self._tab_fotos()
        self._tab_conclusie()

        # Bottom action bar
        bar = tk.Frame(self.root, bg="#2c3e50", pady=6)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(bar, text="📄  Genereer PDF Rapport",
                  font=("Arial", 12, "bold"), bg="#27ae60", fg="white",
                  activebackground="#1e8449", padx=20, pady=8,
                  relief="flat", cursor="hand2",
                  command=self.genereer_pdf).pack(side="right", padx=8)

    # ── Shared widget helpers ─────────────────────────────────────────────────
    def _row_entry(self, parent, label, row, default="", col=0, width=36):
        """Label + Entry at given grid row, starting at given column pair."""
        tk.Label(parent, text=label, font=("Arial", 10),
                 anchor="w", bg="#f0f4f8").grid(
            row=row, column=col, sticky="w", padx=(12, 4), pady=4)
        var = tk.StringVar(value=default)
        ttk.Entry(parent, textvariable=var, width=width).grid(
            row=row, column=col + 1, sticky="w", padx=(0, 12), pady=4)
        return var

    def _row_text(self, parent, label, row, height=4, width=72, default=""):
        tk.Label(parent, text=label, font=("Arial", 10),
                 anchor="nw", bg="#f0f4f8").grid(
            row=row, column=0, sticky="nw", padx=(12, 4), pady=4)
        txt = tk.Text(parent, height=height, width=width,
                      font=("Arial", 10), wrap="word",
                      relief="solid", bd=1)
        txt.insert("1.0", default)
        txt.grid(row=row, column=1, columnspan=3, sticky="ew",
                 padx=(0, 12), pady=4)
        return txt

    def _section_label(self, parent, text, row):
        tk.Label(parent, text=text, font=("Arial", 12, "bold"),
                 fg="#1a252f", bg="#f0f4f8").grid(
            row=row, column=0, columnspan=4, sticky="w",
            padx=12, pady=(14, 2))

    def _separator(self, parent, row):
        ttk.Separator(parent, orient="horizontal").grid(
            row=row, column=0, columnspan=4, sticky="ew", padx=12, pady=4)

    # ── Tab 1: Algemeen & Klantgegevens ──────────────────────────────────────
    def _tab_algemeen(self):
        tab = scrollable_tab(self.nb, "📋  Algemeen & Klant")

        self._section_label(tab, "Rapportgegevens", 0)
        self._separator(tab, 1)
        self.rapportnummer = self._row_entry(tab, "Rapportnummer:", 2, "2026-001")
        self.datum = self._row_entry(
            tab, "Datum Inspectie:", 3,
            date.today().strftime("%d %B %Y"))
        self.operator = self._row_entry(tab, "Operator:", 4)

        self._section_label(tab, "Klant- & Projectgegevens", 5)
        self._separator(tab, 6)

        self.opdrachtgever = self._row_entry(tab, "Opdrachtgever:", 7)
        self.adres = self._row_entry(tab, "Adres:", 8)
        self.postcode = self._row_entry(tab, "Postcode / Plaats:", 9)
        self.telefoon = self._row_entry(tab, "Telefoonnummer:", 10)
        self.type_object = self._row_entry(tab, "Type Object:", 11)
        self.dakbedekking = self._row_entry(tab, "Dakbedekking:", 12)
        self.bouwjaar = self._row_entry(tab, "Bouwjaar:", 13)
        self.oppervlakte = self._row_entry(tab, "Oppervlakte (m²):", 14)

        # ── Kaart sectie ─────────────────────────────────────────────────────
        self._section_label(tab, "📍  Locatie opzoeken", 15)
        self._separator(tab, 16)

        tk.Label(tab, text="Zoeken op adres:", font=("Arial", 10),
                 anchor="w", bg="#f0f4f8").grid(
            row=17, column=0, sticky="w", padx=(12, 4), pady=4)

        zoek_frame = ttk.Frame(tab)
        zoek_frame.grid(row=17, column=1, columnspan=3, sticky="ew",
                        padx=(0, 12), pady=4)
        self._zoek_var = tk.StringVar()
        zoek_entry = ttk.Entry(zoek_frame, textvariable=self._zoek_var, width=45)
        zoek_entry.pack(side="left", fill="x", expand=True)
        zoek_entry.bind("<Return>", lambda e: self._zoek_adres())
        ttk.Button(zoek_frame, text="🔍  Zoek & Vul in",
                   command=self._zoek_adres).pack(side="left", padx=(6, 0))

        self._kaart_status_var = tk.StringVar(value="")
        tk.Label(tab, textvariable=self._kaart_status_var,
                 font=("Arial", 9, "italic"), fg="#555", bg="#f0f4f8").grid(
            row=18, column=0, columnspan=4, sticky="w", padx=14, pady=1)

        # Kaartweergave
        self._kaart_label = tk.Label(
            tab, bg="#dde4ea",
            text="[ Kaart verschijnt hier na het zoeken ]",
            font=("Arial", 9), fg="#888",
            width=62, height=14, relief="solid", bd=1)
        self._kaart_label.grid(row=19, column=0, columnspan=4,
                               padx=12, pady=(4, 12), sticky="w")

    # ── Tab 2: Samenvatting & Conditiescores ─────────────────────────────────
    def _tab_samenvatting(self):
        tab = scrollable_tab(self.nb, "📊  Samenvatting")

        self._section_label(tab, "Samenvatting & Conditiescore", 0)
        self._separator(tab, 1)

        tk.Label(tab, text="Algehele Status:", font=("Arial", 10),
                 bg="#f0f4f8").grid(row=2, column=0, sticky="w",
                                    padx=(12, 4), pady=4)
        self.status_algemeen = ttk.Combobox(
            tab, width=30, state="readonly",
            values=["UITSTEKEND", "GOED", "MATIG / AANDACHTSPUNT",
                    "SLECHT", "KRITIEK"])
        self.status_algemeen.set("MATIG / AANDACHTSPUNT")
        self.status_algemeen.grid(row=2, column=1, sticky="w",
                                   padx=(0, 12), pady=4)

        self.samenvatting_tekst = self._row_text(
            tab, "Samenvatting:", 3, height=5,
            default=(
                "Het dak bevindt zich in een redelijke algemene staat. "
                "Er is beginnende biologische vervuiling en lichte slijtage "
                "geconstateerd bij de randafwerking aan de noordzijde. "
                "Tevens is er een acute blokkade bij een van de primaire "
                "hemelwaterafvoeren die op korte termijn verholpen dient te "
                "worden om stagnatie te voorkomen."))

        self._section_label(tab, "Conditiescores  (1 = Uitstekend  |  5 = Kritiek)", 4)
        self._separator(tab, 5)

        scores_default = [
            ("Dakbedekking & Oppervlakte", "2"),
            ("Naden en Lasverbindingen", "2"),
            ("Randafwerking & Trimmen", "3"),
            ("Hemelwaterafvoer (HWA) & Goot", "4"),
            ("Dakdoorvoeren & Aansluitingen", "2"),
        ]
        self.scores = []
        for i, (lbl, default) in enumerate(scores_default):
            tk.Label(tab, text=lbl, font=("Arial", 10),
                     bg="#f0f4f8").grid(row=6 + i, column=0, sticky="w",
                                        padx=(12, 4), pady=3)
            cb = ttk.Combobox(tab, values=["1", "2", "3", "4", "5"],
                              width=5, state="readonly")
            cb.set(default)
            cb.grid(row=6 + i, column=1, sticky="w", padx=(0, 12), pady=3)
            self.scores.append((lbl, cb))

    # ── Tab 3: Gedetailleerde Inspectieresultaten ─────────────────────────────
    def _tab_resultaten(self):
        tab = scrollable_tab(self.nb, "🔍  Inspectieresultaten")

        sections = [
            ("4.1  Dakbedekking & Oppervlakte",
             "Geen acute blazen of diepe scheuren geconstateerd op de vlakke "
             "delen. Wel is er sprake van lichte mos- en alggroei op de "
             "schaduwzijden van het dakvlak.",
             "Akkoord (lichte vervuiling)"),
            ("4.2  Naden en Lasverbindingen",
             "De naden en lasverbindingen zijn visueel gecontroleerd. "
             "Er zijn geen kritieke openstaande naden geconstateerd.",
             "Akkoord"),
            ("4.3  Randafwerking & Trimmen",
             "De kunststof dakbedekking is bij de opstanden mechanisch nog "
             "stabiel. De felsnaden vertonen lichte veroudering bij de "
             "noordelijke dakrand; de hechting is hier verminderd maar nog "
             "niet kritiek openstaand.",
             "Aandachtspunt"),
            ("4.4  Hemelwaterafvoer (HWA) & Goot",
             "Er bevindt zich een significante ophoping van vuil en organisch "
             "materiaal rondom de noodoverloop en primaire afvoer aan de "
             "westzijde. Dit blokkeert een vrije doorstroom van hemelwater.",
             "Directe actie vereist"),
            ("4.5  Dakdoorvoeren & Aansluitingen",
             "De dakdoorvoeren en aansluitingen zijn geïnspecteerd. "
             "Alle doorvoeren zijn visueel intact en vertonen geen lekkagesporen.",
             "Akkoord"),
        ]

        self.resultaten = []
        row = 0
        for title, default_tekst, default_status in sections:
            self._section_label(tab, title, row);      row += 1
            self._separator(tab, row);                 row += 1

            tekst = self._row_text(tab, "Omschrijving:", row,
                                   height=4, default=default_tekst)
            row += 1

            tk.Label(tab, text="Status:", font=("Arial", 10),
                     bg="#f0f4f8").grid(row=row, column=0, sticky="w",
                                        padx=(12, 4), pady=4)
            status = ttk.Combobox(
                tab, width=32, state="readonly",
                values=["Akkoord", "Akkoord (lichte vervuiling)",
                        "Aandachtspunt", "Directe actie vereist", "Kritiek"])
            status.set(default_status)
            status.grid(row=row, column=1, sticky="w", padx=(0, 12), pady=4)
            row += 1

            # ── Foto upload voor dit onderdeel ──
            foto_path_var = tk.StringVar()
            tk.Label(tab, text="Foto uploaden:", font=("Arial", 10),
                     bg="#f0f4f8").grid(row=row, column=0, sticky="w",
                                        padx=(12, 4), pady=4)
            foto_frame = ttk.Frame(tab)
            foto_frame.grid(row=row, column=1, columnspan=3, sticky="ew",
                            padx=(0, 12), pady=4)
            ttk.Entry(foto_frame, textvariable=foto_path_var,
                      width=38).pack(side="left", fill="x", expand=True)
            ttk.Button(foto_frame, text="📁 Bladeren…",
                       command=lambda v=foto_path_var: self._browse_foto(v)
                       ).pack(side="left", padx=(4, 0))
            ttk.Button(foto_frame, text="✏ Annoteren",
                       command=lambda v=foto_path_var: self._open_annotatie(v)
                       ).pack(side="left", padx=(4, 0))
            row += 1

            self.resultaten.append((tekst, status, foto_path_var))

    # ── Tab 4: Foto's ─────────────────────────────────────────────────────────
    def _tab_fotos(self):
        tab = scrollable_tab(self.nb, "🖼  Foto's")

        self._section_label(tab, "Visuele Fotobijlage (Drone-opnames)", 0)
        self._separator(tab, 1)

        foto_cfg = [
            ("Foto 1  –  Overzichtsfoto Dakvlak:", self.foto1_path,
             "Totaaloverzicht van het geïnspecteerde dakvlak."),
            ("Foto 2  –  Detailopname Defect / Vervuiling:", self.foto2_path,
             "Detailopname van de verstopte hemelwaterafvoer."),
        ]
        self.captions = []
        for idx, (lbl, var, cap_default) in enumerate(foto_cfg):
            base_row = 2 + idx * 3
            tk.Label(tab, text=lbl, font=("Arial", 10, "bold"),
                     bg="#f0f4f8").grid(row=base_row, column=0, sticky="w",
                                        padx=(12, 4), pady=(10, 2))
            ttk.Entry(tab, textvariable=var, width=45).grid(
                row=base_row, column=1, sticky="ew", padx=(0, 4), pady=(10, 2))
            ttk.Button(tab, text="📁 Bladeren…",
                       command=lambda v=var: self._browse_foto(v)).grid(
                row=base_row, column=2, padx=(0, 4), pady=(10, 2))
            ttk.Button(tab, text="✏ Annoteren",
                       command=lambda v=var: self._open_annotatie(v)).grid(
                row=base_row, column=3, padx=(0, 12), pady=(10, 2))

            cap_var = self._row_entry(tab, "Bijschrift:", base_row + 1,
                                      default=cap_default, width=55)
            self.captions.append(cap_var)
            self._separator(tab, base_row + 2)

    # ── Kaart zoeken (OpenStreetMap / Nominatim) ──────────────────────────────
    def _zoek_adres(self):
        query = self._zoek_var.get().strip()
        if not query:
            # Probeer velden samen te stellen als zoekveld leeg is
            query = f"{self.adres.get()} {self.postcode.get()}".strip()
        if not query:
            messagebox.showwarning("Leeg zoekveld",
                                   "Voer een adres in het zoekveld in.")
            return

        self._kaart_status_var.set("⏳  Zoeken…")
        self._kaart_label.configure(text="Kaart wordt geladen…", image="")

        def worker():
            try:
                from geopy.geocoders import Nominatim
                from staticmap import StaticMap, CircleMarker

                geolocator = Nominatim(user_agent="dakwerk_sterken_inspecties")
                location = geolocator.geocode(query, exactly_one=True,
                                              language="nl",
                                              addressdetails=True)
                if not location:
                    self.root.after(0, lambda: self._kaart_status_var.set(
                        "❌  Adres niet gevonden. Probeer een andere zoekopdracht."))
                    return

                lat, lon = location.latitude, location.longitude
                raw = location.raw.get("address", {})

                # Adresvelden automatisch vullen
                straat = raw.get("road", raw.get("pedestrian", ""))
                huisnr = raw.get("house_number", "")
                pc = raw.get("postcode", "")
                stad = (raw.get("city") or raw.get("town")
                        or raw.get("village") or raw.get("municipality", ""))

                # Statische kaart genereren
                smap = StaticMap(500, 320)
                smap.add_marker(CircleMarker((lon, lat), "#e74c3c", 18))
                img = smap.render(zoom=16)

                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=".png",
                    prefix="dakinspectie_kaart_")
                img.save(tmp.name, "PNG")
                tmp.close()

                # Update UI op de main thread
                def update():
                    from PIL import ImageTk
                    pil = img.resize((500, 320))
                    self._kaart_tk_img = ImageTk.PhotoImage(pil)
                    self._kaart_label.configure(
                        image=self._kaart_tk_img, text="",
                        width=500, height=320)
                    self.kaart_path = tmp.name

                    # Velden vullen (alleen overschrijven als leeg of anders)
                    if straat:
                        adres_val = f"{straat} {huisnr}".strip()
                        self.adres.set(adres_val)
                    if pc or stad:
                        self.postcode.set(f"{pc} {stad}".strip())

                    self._kaart_status_var.set(
                        f"✔  Gevonden: {location.address}")

                self.root.after(0, update)

            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda: self._kaart_status_var.set(
                    f"❌  Fout: {err}"))

        threading.Thread(target=worker, daemon=True).start()

    def _browse_foto(self, var):
        path = filedialog.askopenfilename(
            filetypes=[("Afbeeldingen", "*.jpg *.jpeg *.png *.bmp *.gif")])
        if path:
            var.set(path)

    def _open_annotatie(self, var: tk.StringVar):
        if not var.get() or not os.path.exists(var.get()):
            messagebox.showwarning(
                "Geen foto",
                "Selecteer eerst een foto via 'Bladeren…' voordat u gaat annoteren.")
            return
        AnnotatieVenster(self.root, var)

    # ── Tab 5: Conclusie & Advies ─────────────────────────────────────────────
    def _tab_conclusie(self):
        tab = scrollable_tab(self.nb, "✅  Conclusie & Advies")

        self._section_label(tab, "Conclusie & Advies", 0)
        self._separator(tab, 1)

        self.advies_kort = self._row_text(
            tab, "Korte termijn\n(Binnen 3 maanden):", 2, height=3,
            default=("Het grondig reinigen en doorspuiten van de hemelwater"
                     "afvoeren en goten om risico op lekkages door stilstaand "
                     "water te elimineren."))
        self.advies_middel = self._row_text(
            tab, "Middellange termijn\n(Binnen 1 à 2 jaar):", 3, height=3,
            default=("Preventieve controle en lokaal herstel van de lasnaden "
                     "bij de noordelijke dakrandafwerking."))
        self.advies_periodiek = self._row_text(
            tab, "Periodiek onderhoud:", 4, height=3,
            default=("Het handhaven van een jaarlijkse inspectie- en "
                     "reinigingscyclus om de levensduur van de dakbedekking "
                     "optimaal te waarborgen."))

    # ─────────────────────────────────────────────────────────────────────────
    # PDF Generation
    # ─────────────────────────────────────────────────────────────────────────
    def genereer_pdf(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF bestanden", "*.pdf")],
            initialfile=f"Inspectierapport_{self.rapportnummer.get()}.pdf")
        if not filepath:
            return
        try:
            self._build_pdf(filepath)
            messagebox.showinfo(
                "PDF Gegenereerd ✔",
                f"Rapport succesvol opgeslagen:\n{filepath}")
            os.startfile(filepath)
        except Exception as exc:
            messagebox.showerror("Fout", f"Fout bij genereren PDF:\n{exc}")

    # ── ReportLab document ────────────────────────────────────────────────────
    def _build_pdf(self, filepath: str):
        PAGE_W, PAGE_H = A4
        MARGIN = 2 * cm
        W = PAGE_W - 2 * MARGIN   # usable width

        doc = SimpleDocTemplate(
            filepath, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN)

        base = getSampleStyleSheet()

        # ---- Styles ----
        def S(name, **kw):
            return ParagraphStyle(name, **kw)

        h2 = S("H2", fontSize=12, fontName="Helvetica-Bold",
                textColor=colors.HexColor("#1a252f"),
                spaceBefore=10, spaceAfter=3)
        h3 = S("H3", fontSize=10, fontName="Helvetica-Bold",
                textColor=colors.HexColor("#2c3e50"),
                spaceBefore=8, spaceAfter=2)
        normal = S("Norm", fontSize=9, fontName="Helvetica",
                   textColor=colors.HexColor("#2c2c2c"), leading=13)
        justify = S("Just", fontSize=9, fontName="Helvetica",
                    alignment=TA_JUSTIFY, leading=14,
                    textColor=colors.HexColor("#2c2c2c"))
        center = S("Ctr", fontSize=8, fontName="Helvetica",
                   alignment=TA_CENTER, textColor=colors.grey)
        cell_bold = S("CB", fontSize=9, fontName="Helvetica-Bold",
                      textColor=colors.HexColor("#2c2c2c"))
        white_bold = S("WB", fontSize=9, fontName="Helvetica-Bold",
                       textColor=colors.white)

        DARK = colors.HexColor("#1a252f")
        MID  = colors.HexColor("#2c3e50")
        LIGHT = colors.HexColor("#ecf0f1")
        GRID = colors.HexColor("#bdc3c7")
        ROW_ALT = colors.HexColor("#f5f7fa")

        story = []

        # ════════════════════════════════════════════════════════════════
        # HEADER
        # ════════════════════════════════════════════════════════════════
        logo_path = os.path.join(os.path.dirname(__file__), "inspectie.png")
        if os.path.exists(logo_path):
            logo_block = Image(logo_path, width=9.0 * cm, height=2.2 * cm,
                               kind="proportional")
        else:
            logo_block = Paragraph('<font size="17"><b>DAKWERK STERKEN</b></font>',
                                   S("h", fontName="Helvetica-Bold",
                                     textColor=colors.white))

        hdr = [
            [logo_block,
             Paragraph(f'<b>Rapportnummer:</b>  {self.rapportnummer.get()}',
                       S("hr", fontSize=9, fontName="Helvetica",
                         textColor=colors.HexColor("#2c2c2c")))],
            ["",
             Paragraph(f'<b>Datum Inspectie:</b>  {self.datum.get()}',
                       S("hr2", fontSize=9, fontName="Helvetica",
                         textColor=colors.HexColor("#2c2c2c")))],
            ["",
             Paragraph(f'<b>Operator:</b>  {self.operator.get()}',
                       S("hr3", fontSize=9, fontName="Helvetica",
                         textColor=colors.HexColor("#2c2c2c")))],
        ]
        hdr_t = Table(hdr, colWidths=[10 * cm, W - 10 * cm])
        hdr_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), DARK),
            ("BACKGROUND", (1, 0), (1, -1), LIGHT),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING",    (0, 0), (-1, -1), 9),
            ("LINEBELOW",  (0, 0), (-1, -1), 0.4, GRID),
        ]))
        story.append(hdr_t)
        story.append(Spacer(1, 0.4 * cm))

        # ════════════════════════════════════════════════════════════════
        # SECTION 1 – Klantgegevens
        # ════════════════════════════════════════════════════════════════
        story.append(Paragraph("1.  Project- &amp; Klantgegevens", h2))
        story.append(HRFlowable(width=W, thickness=1.2, color=MID))
        story.append(Spacer(1, 0.15 * cm))

        def kv(key, val):
            return [Paragraph(f"<b>{key}</b>", normal),
                    Paragraph(val or "—", normal)]

        klant = Table([
            kv("Opdrachtgever", self.opdrachtgever.get()) +
            kv("Type Object", self.type_object.get()),
            kv("Adres", self.adres.get()) +
            kv("Dakbedekking", self.dakbedekking.get()),
            kv("Postcode / Plaats", self.postcode.get()) +
            kv("Bouwjaar", self.bouwjaar.get()),
            kv("Telefoonnummer", self.telefoon.get()) +
            kv("Oppervlakte", (self.oppervlakte.get() or "—") + " m²"),
        ], colWidths=[3.8 * cm, 4.7 * cm, 3.8 * cm, 4.7 * cm])
        klant.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#d5dce6")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#d5dce6")),
            ("ROWBACKGROUNDS", (1, 0), (1, -1),
             [colors.white, ROW_ALT, colors.white, ROW_ALT]),
            ("ROWBACKGROUNDS", (3, 0), (3, -1),
             [colors.white, ROW_ALT, colors.white, ROW_ALT]),
            ("GRID",    (0, 0), (-1, -1), 0.5, GRID),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(klant)
        story.append(Spacer(1, 0.25 * cm))

        # ── Locatiekaart in PDF ──────────────────────────────────────────
        if self.kaart_path and os.path.exists(self.kaart_path):
            try:
                MAP_W, MAP_H = W, 7.5 * cm
                kaart_img = Image(self.kaart_path, width=MAP_W,
                                  height=MAP_H, kind="proportional")
                kaart_tbl = Table([[kaart_img]], colWidths=[MAP_W])
                kaart_tbl.setStyle(TableStyle([
                    ("BOX",        (0, 0), (-1, -1), 0.8, MID),
                    ("PADDING",    (0, 0), (-1, -1), 0),
                    ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ]))
                story.append(kaart_tbl)
                story.append(Paragraph(
                    "<i>Kaartbron: OpenStreetMap contributors (© OpenStreetMap)</i>",
                    S("kaartcap", fontSize=6.5, fontName="Helvetica",
                      textColor=colors.grey)))
            except Exception:
                pass
        story.append(Spacer(1, 0.3 * cm))

        # ════════════════════════════════════════════════════════════════
        # SECTION 2 – Doel
        # ════════════════════════════════════════════════════════════════
        story.append(Paragraph("2.  Doel van de Inspectie", h2))
        story.append(HRFlowable(width=W, thickness=1.2, color=MID))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(
            "Het doel van deze drone-inspectie is het contactloos, veilig en "
            "nauwkeurig in kaart brengen van de algehele conditie van de "
            "dakbedekking, randafwerkingen, hemelwaterafvoeren en eventuele "
            "aanvullende dakcomponenten. Dit rapport dient als objectieve "
            "nulmeting ter vaststelling van preventief onderhoud of actuele "
            "schadecomplexen.", justify))
        story.append(Spacer(1, 0.3 * cm))

        # ════════════════════════════════════════════════════════════════
        # SECTION 3 – Samenvatting & Conditiescore
        # ════════════════════════════════════════════════════════════════
        story.append(Paragraph("3.  Samenvatting &amp; Conditiescore", h2))
        story.append(HRFlowable(width=W, thickness=1.2, color=MID))
        story.append(Spacer(1, 0.1 * cm))

        STATUS_COLORS = {
            "UITSTEKEND":             "#27ae60",
            "GOED":                   "#2ecc71",
            "MATIG / AANDACHTSPUNT":  "#f39c12",
            "SLECHT":                 "#e67e22",
            "KRITIEK":                "#e74c3c",
        }
        sv = self.status_algemeen.get()
        sc = colors.HexColor(STATUS_COLORS.get(sv, "#95a5a6"))

        status_row = Table(
            [[Paragraph("<b>Algehele status van het dak:</b>", normal),
              Paragraph(f'<font color="white"><b>  {sv}  </b></font>',
                        S("svs", fontSize=10, fontName="Helvetica-Bold",
                          textColor=colors.white, backColor=sc,
                          alignment=TA_CENTER))]],
            colWidths=[9 * cm, W - 9 * cm])
        status_row.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), LIGHT),
            ("BACKGROUND", (1, 0), (1, 0), sc),
            ("PADDING",    (0, 0), (-1, -1), 8),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(status_row)
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            self.samenvatting_tekst.get("1.0", "end").strip(), justify))
        story.append(Spacer(1, 0.25 * cm))

        # Score table
        SCORE_CLR = {
            "1": "#27ae60", "2": "#2ecc71",
            "3": "#f39c12", "4": "#e67e22", "5": "#e74c3c"}
        score_rows = [
            [Paragraph("<b>Onderdeel</b>", white_bold),
             Paragraph("<b>Score</b><br/>"
                       '<font size="7">(1=Uitstekend, 5=Kritiek)</font>',
                       S("sh", fontSize=9, fontName="Helvetica-Bold",
                         textColor=colors.white, alignment=TA_CENTER))]
        ]
        for i, (lbl, cb) in enumerate(self.scores):
            val = cb.get()
            clr = colors.HexColor(SCORE_CLR.get(val, "#95a5a6"))
            score_rows.append([
                Paragraph(lbl, normal),
                Paragraph(
                    f'<font color="white"><b>  {val}  </b></font>',
                    S(f"sc{i}", fontSize=11, fontName="Helvetica-Bold",
                      textColor=colors.white, backColor=clr,
                      alignment=TA_CENTER))
            ])
        score_tbl = Table(score_rows, colWidths=[W - 3.5 * cm, 3.5 * cm])
        score_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), MID),
            ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
            ("GRID",  (0, 0), (-1, -1), 0.5, GRID),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("ALIGN",   (1, 0), (1, -1), "CENTER"),
            ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(score_tbl)
        story.append(Spacer(1, 0.4 * cm))

        # ════════════════════════════════════════════════════════════════
        # SECTION 4 – Gedetailleerde Inspectieresultaten
        # ════════════════════════════════════════════════════════════════
        story.append(Paragraph("4.  Gedetailleerde Inspectieresultaten", h2))
        story.append(HRFlowable(width=W, thickness=1.2, color=MID))

        RES_TITLES = [
            "4.1  Dakbedekking &amp; Oppervlakte",
            "4.2  Naden en Lasverbindingen",
            "4.3  Randafwerking &amp; Trimmen",
            "4.4  Hemelwaterafvoer (HWA) &amp; Goot",
            "4.5  Dakdoorvoeren &amp; Aansluitingen",
        ]
        STATUS_BG = {
            "Akkoord":                  "#27ae60",
            "Akkoord (lichte vervuiling)": "#2ecc71",
            "Aandachtspunt":            "#f39c12",
            "Directe actie vereist":    "#e74c3c",
            "Kritiek":                  "#c0392b",
        }

        for i, (tekst_w, status_cb, foto_path_var) in enumerate(self.resultaten):
            story.append(Spacer(1, 0.25 * cm))
            story.append(Paragraph(RES_TITLES[i], h3))

            tekst = tekst_w.get("1.0", "end").strip()
            story.append(Paragraph(tekst, justify))
            story.append(Spacer(1, 0.1 * cm))

            sv2 = status_cb.get()
            sbg = colors.HexColor(STATUS_BG.get(sv2, "#95a5a6"))

            sr = Table(
                [[Paragraph("<b>Status:</b>", normal),
                  Paragraph(f'<font color="white"><b>  {sv2}  </b></font>',
                            S(f"sr{i}", fontSize=9, fontName="Helvetica-Bold",
                              textColor=colors.white, backColor=sbg))]],
                colWidths=[2.2 * cm, W - 2.2 * cm])
            sr.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), LIGHT),
                ("BACKGROUND", (1, 0), (1, 0), sbg),
                ("PADDING",    (0, 0), (-1, -1), 6),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("GRID",       (0, 0), (-1, -1), 0.5, GRID),
            ]))
            story.append(sr)

            # ── Sectie-foto (indien geüpload) ──
            foto_path = foto_path_var.get()
            if foto_path and os.path.exists(foto_path):
                try:
                    SEC_IMG_W, SEC_IMG_H = 10 * cm, 7 * cm
                    sec_img = Image(foto_path, width=SEC_IMG_W,
                                   height=SEC_IMG_H, kind="proportional")
                    img_tbl = Table(
                        [[sec_img]],
                        colWidths=[SEC_IMG_W])
                    img_tbl.setStyle(TableStyle([
                        ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
                        ("PADDING",    (0, 0), (-1, -1), 4),
                        ("BOX",        (0, 0), (-1, -1), 0.5, GRID),
                        ("BACKGROUND", (0, 0), (-1, -1), ROW_ALT),
                    ]))
                    story.append(Spacer(1, 0.15 * cm))
                    story.append(img_tbl)
                    story.append(Paragraph(
                        f"<i>{os.path.basename(foto_path)}</i>",
                        S(f"ic{i}", fontSize=7, fontName="Helvetica",
                          textColor=colors.grey)))
                except Exception:
                    pass

        story.append(Spacer(1, 0.45 * cm))

        # ════════════════════════════════════════════════════════════════
        # SECTION 5 – Fotobijlage
        # ════════════════════════════════════════════════════════════════
        story.append(Paragraph(
            "5.  Visuele Fotobijlage (Drone-opnames)", h2))
        story.append(HRFlowable(width=W, thickness=1.2, color=MID))
        story.append(Spacer(1, 0.2 * cm))

        foto_paths = [self.foto1_path.get(), self.foto2_path.get()]
        foto_caps  = [v.get() for v in self.captions]

        def build_foto_cell(path, caption):
            IMG_W, IMG_H = 7.8 * cm, 5.8 * cm
            if path and os.path.exists(path):
                try:
                    img = Image(path, width=IMG_W, height=IMG_H,
                                kind="proportional")
                    return img, Paragraph(f"<i>Foto: {caption}</i>", center)
                except Exception:
                    pass
            placeholder = Table(
                [[Paragraph(
                    f'[ Geen foto ]\n{os.path.basename(path) if path else "—"}',
                    S("ph", fontSize=8, alignment=TA_CENTER,
                      textColor=colors.grey))]],
                colWidths=[IMG_W], rowHeights=[IMG_H])
            placeholder.setStyle(TableStyle([
                ("BOX",        (0, 0), (-1, -1), 0.5, GRID),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), ROW_ALT),
            ]))
            return placeholder, Paragraph(f"<i>Foto: {caption}</i>", center)

        cells = [build_foto_cell(p, c) for p, c in zip(foto_paths, foto_caps)]
        foto_tbl = Table(
            [[cells[0][0], cells[1][0]],
             [cells[0][1], cells[1][1]]],
            colWidths=[(W / 2)] * 2)
        foto_tbl.setStyle(TableStyle([
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",     (0, 0), (-1, 0),  "MIDDLE"),
            ("PADDING",    (0, 0), (-1, -1), 8),
            ("GRID",       (0, 0), (-1, -1), 0.5, GRID),
            ("BACKGROUND", (0, 0), (-1, -1), ROW_ALT),
        ]))
        story.append(foto_tbl)
        story.append(Spacer(1, 0.45 * cm))

        # ════════════════════════════════════════════════════════════════
        # SECTION 6 – Conclusie & Advies
        # ════════════════════════════════════════════════════════════════
        story.append(Paragraph("6.  Conclusie &amp; Advies", h2))
        story.append(HRFlowable(width=W, thickness=1.2, color=MID))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(
            "Op basis van de verzamelde dronebeelden adviseren wij de "
            "volgende acties op te nemen in uw onderhoudsplanning:", justify))
        story.append(Spacer(1, 0.15 * cm))

        advies_items = [
            ("Korte termijn  (Binnen 3 maanden)",
             self.advies_kort, "#fdecea", "#e74c3c"),
            ("Middellange termijn  (Binnen 1 à 2 jaar)",
             self.advies_middel, "#fef9ec", "#f39c12"),
            ("Periodiek onderhoud",
             self.advies_periodiek, "#eafaf1", "#27ae60"),
        ]
        for lbl, widget, bg_hex, accent_hex in advies_items:
            tekst = widget.get("1.0", "end").strip()
            adv = Table(
                [[Paragraph(f"<b>{lbl}:</b>", cell_bold),
                  Paragraph(tekst, justify)]],
                colWidths=[4.8 * cm, W - 4.8 * cm])
            adv.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0),
                 colors.HexColor(bg_hex)),
                ("BACKGROUND", (1, 0), (1, 0), colors.white),
                ("LEFTPADDING",  (0, 0), (0, 0), 10),
                ("LINERIGHT",    (0, 0), (0, 0), 3,
                 colors.HexColor(accent_hex)),
                ("GRID",    (0, 0), (-1, -1), 0.5, GRID),
                ("PADDING", (0, 0), (-1, -1), 7),
                ("VALIGN",  (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(adv)
            story.append(Spacer(1, 0.12 * cm))

        story.append(Spacer(1, 0.5 * cm))

        # ════════════════════════════════════════════════════════════════
        # FOOTER
        # ════════════════════════════════════════════════════════════════
        footer = Table(
            [[Paragraph(
                "<b>Rapport opgesteld door:</b><br/>"
                "Dakwerk Sterken<br/>"
                "Technische Inspecties &amp; Onderhoud",
                S("ft", fontSize=9, fontName="Helvetica",
                  textColor=colors.white, leading=14)),
              Paragraph(
                "<b>Gecertificeerd Drone Operator</b><br/>"
                "A1 / A3  –  A2",
                S("ft2", fontSize=9, fontName="Helvetica",
                  textColor=colors.white, alignment=TA_RIGHT, leading=14))]],
            colWidths=[10 * cm, W - 10 * cm])
        footer.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), DARK),
            ("PADDING",    (0, 0), (-1, -1), 12),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(footer)

        doc.build(story)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = DakInspectieApp(root)
    root.mainloop()
