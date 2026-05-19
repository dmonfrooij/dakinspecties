import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import date
import os
import threading
import tempfile
import json
import re
from collections import deque

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, HRFlowable)
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
# Helper: plain frame inside a notebook tab (zonder scrollbars)
# ─────────────────────────────────────────────────────────────────────────────
def tab_frame(notebook, title):
    frame = ttk.Frame(notebook, padding=(12, 10))
    notebook.add(frame, text=title)
    frame.columnconfigure(1, weight=1)
    frame.columnconfigure(3, weight=1)
    return frame


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────
class DakInspectieApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Dakwerk Sterken – Drone Inspectierapport Generator")
        self.root.geometry("1280x860")
        self.root.minsize(1100, 760)
        self.root.resizable(True, True)

        self._counter_file = os.path.join(os.path.dirname(__file__), "project_counter.json")
        self.default_rapportnummer = self._next_rapportnummer()

        # Photo path variables
        self.foto1_path = tk.StringVar()
        self.foto2_path = tk.StringVar()
        self.ai_input_path = tk.StringVar()
        self.ai_original_path: str | None = None
        self.ai_overlay_path: str | None = None
        self.ai_classificatie = tk.StringVar(value="Nog niet geanalyseerd")
        self.ai_uitleg = tk.StringVar(value="Upload een dakfoto en klik op 'Analyseer foto'.")
        self.resultaat_kopjes = [
            "4.1  Dakbedekking & Oppervlakte",
            "4.2  Naden en Lasverbindingen",
            "4.3  Randafwerking & Trimmen",
            "4.4  Hemelwaterafvoer (HWA) & Goot",
            "4.5  Dakdoorvoeren & Aansluitingen",
        ]
        self.ai_target_kopje = tk.StringVar(value=self.resultaat_kopjes[0])
        self.ai_daktype_var = tk.StringVar(value="Auto (uit projectgegevens)")
        self.ai_profiel_var = tk.StringVar(value="Gebalanceerd")
        self.ai_sensitivity_var = tk.IntVar(value=50)
        self.ai_auto_place_var = tk.BooleanVar(value=True)
        self.ai_use_overlay_var = tk.BooleanVar(value=True)
        self.kaart_path: str | None = None   # gegenereerde kaartafbeelding
        self._kaart_tk_img = None            # tkinter PhotoImage referentie
        self._ai_tk_img = None

        self._build_ui()

    def _next_rapportnummer(self):
        jaar = date.today().year
        last = 0
        try:
            if os.path.exists(self._counter_file):
                with open(self._counter_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if int(data.get("year", 0)) == jaar:
                    last = int(data.get("last", 0))
        except Exception:
            last = 0
        return f"{jaar}-{last + 1:03d}"

    def _mark_used_rapportnummer(self, rapportnummer):
        m = re.match(r"^(\d{4})-(\d{1,6})$", (rapportnummer or "").strip())
        if not m:
            return
        jaar = int(m.group(1))
        nummer = int(m.group(2))
        if nummer <= 0:
            return

        data = {"year": jaar, "last": nummer}
        try:
            if os.path.exists(self._counter_file):
                with open(self._counter_file, "r", encoding="utf-8") as f:
                    old = json.load(f)
                old_year = int(old.get("year", 0))
                old_last = int(old.get("last", 0))
                if old_year == jaar and old_last > nummer:
                    data = {"year": old_year, "last": old_last}
                elif old_year > jaar:
                    data = {"year": old_year, "last": old_last}
        except Exception:
            pass

        try:
            with open(self._counter_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=True, indent=2)
        except Exception:
            pass

    # ── UI skeleton ──────────────────────────────────────────────────────────
    def _build_ui(self):
        self._apply_theme()

        # Top banner
        banner = tk.Frame(self.root, bg="#1a252f", pady=12)
        banner.pack(fill="x")

        banner_left = tk.Frame(banner, bg="#1a252f")
        banner_left.pack(side="left", padx=8)
        tk.Label(banner_left, text="DAKWERK STERKEN",
                 font=("Arial", 20, "bold"), fg="white", bg="#1a252f").pack(anchor="w")
        tk.Label(banner_left, text="Drone Inspectierapport Generator",
                 font=("Arial", 11), fg="#bdc3c7", bg="#1a252f").pack(anchor="w")

        tools = ttk.Frame(banner)
        tools.pack(side="right", padx=12, pady=6)
        ttk.Button(tools, text="Open project", command=self.open_project).pack(side="left", padx=(0, 6))
        ttk.Button(tools, text="Opslaan", command=self.save_project).pack(side="left", padx=(0, 6))
        ttk.Button(tools, text="Nieuw project", command=self.new_project).pack(side="left", padx=(0, 10))
        ttk.Button(
            tools,
            text="Genereer PDF Rapport",
            style="Primary.TButton",
            command=self.genereer_pdf,
        ).pack(side="left")

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        self._tab_algemeen()
        self._tab_ai_schadecheck()
        self._tab_resultaten()
        self._tab_fotos()
        self._tab_samenvatting()
        self._tab_conclusie()


    def _apply_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#f4f6f8")
        style.configure("TNotebook.Tab", padding=[16, 8], font=("Arial", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")])
        style.configure("TFrame", background="#f4f6f8")
        style.configure("TLabel", background="#f4f6f8")
        style.configure("Primary.TButton", font=("Arial", 11, "bold"), padding=(16, 8))

    # ── Shared widget helpers ─────────────────────────────────────────────────
    def _row_entry(self, parent, label, row, default="", col=0, width=36):
        """Label + Entry at given grid row, starting at given column pair."""
        tk.Label(parent, text=label, font=("Arial", 10),
                 anchor="w", bg="#f4f6f8").grid(
            row=row, column=col, sticky="w", padx=(12, 4), pady=4)
        var = tk.StringVar(value=default)
        ttk.Entry(parent, textvariable=var, width=width).grid(
            row=row, column=col + 1, sticky="w", padx=(0, 12), pady=4)
        return var

    def _row_text(self, parent, label, row, height=4, width=72, default=""):
        tk.Label(parent, text=label, font=("Arial", 10),
                 anchor="nw", bg="#f4f6f8").grid(
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
                 fg="#1a252f", bg="#f4f6f8").grid(
            row=row, column=0, columnspan=4, sticky="w",
            padx=8, pady=(10, 2))

    def _separator(self, parent, row):
        ttk.Separator(parent, orient="horizontal").grid(
            row=row, column=0, columnspan=4, sticky="ew", padx=12, pady=4)

    # ── Tab 1: Algemeen & Klantgegevens ──────────────────────────────────────
    def _tab_algemeen(self):
        tab = tab_frame(self.nb, "Algemeen & Klant")

        self._section_label(tab, "Rapportgegevens", 0)
        self._separator(tab, 1)
        self.rapportnummer = self._row_entry(tab, "Rapportnummer:", 2, self.default_rapportnummer)
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
        self._section_label(tab, "Locatie opzoeken", 15)
        self._separator(tab, 16)

        tk.Label(tab, text="Zoeken op adres:", font=("Arial", 10),
                 anchor="w", bg="#f4f6f8").grid(
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
                 font=("Arial", 9, "italic"), fg="#555", bg="#f4f6f8").grid(
            row=18, column=0, columnspan=4, sticky="w", padx=14, pady=1)

        # Kaartweergave
        self._kaart_label = tk.Label(
            tab, bg="#dde4ea",
            text="[ Kaart verschijnt hier na het zoeken ]",
            font=("Arial", 9), fg="#888",
            width=62, height=8, relief="solid", bd=1)
        self._kaart_label.grid(row=19, column=0, columnspan=4,
                               padx=12, pady=(4, 12), sticky="w")

    # ── Tab 2: Samenvatting & Conditiescores ─────────────────────────────────
    def _tab_samenvatting(self):
        tab = tab_frame(self.nb, "Samenvatting")

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
        tab = tab_frame(self.nb, "Inspectieresultaten")

        sections = [
            (self.resultaat_kopjes[0],
             "Geen acute blazen of diepe scheuren geconstateerd op de vlakke "
             "delen. Wel is er sprake van lichte mos- en alggroei op de "
             "schaduwzijden van het dakvlak.",
             "Akkoord (lichte vervuiling)"),
            (self.resultaat_kopjes[1],
             "De naden en lasverbindingen zijn visueel gecontroleerd. "
             "Er zijn geen kritieke openstaande naden geconstateerd.",
             "Akkoord"),
            (self.resultaat_kopjes[2],
             "De kunststof dakbedekking is bij de opstanden mechanisch nog "
             "stabiel. De felsnaden vertonen lichte veroudering bij de "
             "noordelijke dakrand; de hechting is hier verminderd maar nog "
             "niet kritiek openstaand.",
             "Aandachtspunt"),
            (self.resultaat_kopjes[3],
             "Er bevindt zich een significante ophoping van vuil en organisch "
             "materiaal rondom de noodoverloop en primaire afvoer aan de "
             "westzijde. Dit blokkeert een vrije doorstroom van hemelwater.",
             "Directe actie vereist"),
            (self.resultaat_kopjes[4],
             "De dakdoorvoeren en aansluitingen zijn geïnspecteerd. "
             "Alle doorvoeren zijn visueel intact en vertonen geen lekkagesporen.",
             "Akkoord"),
        ]

        tk.Label(
            tab,
            text="Vul elk onderdeel in via de subtabs. Dit houdt alle velden bruikbaar zonder scrollbalk.",
            font=("Arial", 9, "italic"),
            bg="#f4f6f8",
            fg="#5f6b7a",
        ).pack(anchor="w", padx=4, pady=(2, 8))

        sub_nb = ttk.Notebook(tab)
        sub_nb.pack(fill="both", expand=True)

        self.resultaten = []
        for title, default_tekst, default_status in sections:
            frame = ttk.Frame(sub_nb, padding=12)
            sub_nb.add(frame, text=title.split("  ")[0])
            frame.columnconfigure(1, weight=1)

            tk.Label(frame, text=title, font=("Arial", 11, "bold"), bg="#f4f6f8").grid(
                row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
            )

            tk.Label(frame, text="Omschrijving:", font=("Arial", 10), bg="#f4f6f8").grid(
                row=1, column=0, sticky="nw", pady=4
            )
            tekst = tk.Text(frame, height=9, wrap="word", font=("Arial", 10), relief="solid", bd=1)
            tekst.insert("1.0", default_tekst)
            tekst.grid(row=1, column=1, sticky="nsew", pady=4)

            tk.Label(frame, text="Status:", font=("Arial", 10), bg="#f4f6f8").grid(
                row=2, column=0, sticky="w", pady=4
            )
            status = ttk.Combobox(
                frame,
                width=34,
                state="readonly",
                values=["Akkoord", "Akkoord (lichte vervuiling)", "Aandachtspunt", "Directe actie vereist", "Kritiek"],
            )
            status.set(default_status)
            status.grid(row=2, column=1, sticky="w", pady=4)

            foto_path_var = tk.StringVar()
            tk.Label(frame, text="Foto:", font=("Arial", 10), bg="#f4f6f8").grid(
                row=3, column=0, sticky="w", pady=4
            )
            foto_frame = ttk.Frame(frame)
            foto_frame.grid(row=3, column=1, sticky="ew", pady=4)
            foto_frame.columnconfigure(0, weight=1)
            ttk.Entry(foto_frame, textvariable=foto_path_var).grid(row=0, column=0, sticky="ew")
            ttk.Button(
                foto_frame,
                text="Bladeren...",
                command=lambda v=foto_path_var: self._browse_foto(v),
            ).grid(row=0, column=1, padx=(6, 0))
            ttk.Button(
                foto_frame,
                text="Annoteren",
                command=lambda v=foto_path_var: self._open_annotatie(v),
            ).grid(row=0, column=2, padx=(6, 0))

            self.resultaten.append((tekst, status, foto_path_var))

    # ── Tab 4: Foto's ─────────────────────────────────────────────────────────
    def _tab_fotos(self):
        tab = tab_frame(self.nb, "Foto's")

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

    # ── Tab 5: AI schadecheck ─────────────────────────────────────────────────
    def _tab_ai_schadecheck(self):
        tab = tab_frame(self.nb, "AI Schadecheck")
        tab.columnconfigure(0, weight=1)

        self._section_label(tab, "Automatische schade-inschatting (indicatief)", 0)
        self._separator(tab, 1)

        tk.Label(
            tab,
            text=(
                "Upload een dakfoto. De tool markeert mogelijke probleemzones en geeft een indicatie: "
                "GOED, AANDACHTSPUNTEN of SCHADE."
            ),
            font=("Arial", 9, "italic"),
            bg="#f4f6f8",
            fg="#5f6b7a",
            anchor="w",
            justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=12, pady=(2, 8))

        foto_frame = ttk.Frame(tab)
        foto_frame.grid(row=3, column=0, columnspan=4, sticky="ew", padx=12, pady=4)
        foto_frame.columnconfigure(0, weight=1)
        ttk.Entry(foto_frame, textvariable=self.ai_input_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(foto_frame, text="Bladeren...", command=self._browse_ai_foto).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(foto_frame, text="Analyseer foto", command=self._run_ai_analyse).grid(row=0, column=2, padx=(6, 0))

        opties = ttk.Frame(tab)
        opties.grid(row=4, column=0, columnspan=4, sticky="ew", padx=12, pady=(2, 6))
        opties.columnconfigure(1, weight=1)

        tk.Label(opties, text="Plaats in kopje:", font=("Arial", 10), bg="#f4f6f8").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Combobox(
            opties,
            textvariable=self.ai_target_kopje,
            values=self.resultaat_kopjes,
            width=45,
            state="readonly",
        ).grid(row=0, column=1, sticky="w", padx=(6, 12), pady=2)

        tk.Label(opties, text="Daktype:", font=("Arial", 10), bg="#f4f6f8").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Combobox(
            opties,
            textvariable=self.ai_daktype_var,
            values=["Auto (uit projectgegevens)", "Bitumen", "PVC", "Pannen"],
            width=28,
            state="readonly",
        ).grid(row=1, column=1, sticky="w", padx=(6, 12), pady=2)

        tk.Label(opties, text="AI profiel:", font=("Arial", 10), bg="#f4f6f8").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Combobox(
            opties,
            textvariable=self.ai_profiel_var,
            values=["Conservatief", "Gebalanceerd", "Agressief"],
            width=20,
            state="readonly",
        ).grid(row=2, column=1, sticky="w", padx=(6, 12), pady=2)

        tk.Label(opties, text="Gevoeligheid:", font=("Arial", 10), bg="#f4f6f8").grid(row=3, column=0, sticky="w", pady=2)
        schaal = tk.Scale(
            opties,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.ai_sensitivity_var,
            bg="#f4f6f8",
            highlightthickness=0,
            length=240,
        )
        schaal.grid(row=3, column=1, sticky="w", padx=(6, 12), pady=2)

        ttk.Checkbutton(
            opties,
            text="Automatisch plaatsen in gekozen inspectie-kopje na analyse",
            variable=self.ai_auto_place_var,
        ).grid(row=4, column=1, sticky="w", padx=(6, 12), pady=(4, 0))

        ttk.Checkbutton(
            opties,
            text="Gebruik overlay bij plaatsen (uit = originele foto zonder arcering)",
            variable=self.ai_use_overlay_var,
        ).grid(row=5, column=1, sticky="w", padx=(6, 12), pady=(4, 0))

        ttk.Button(
            opties,
            text="Overlay handmatig aanpassen",
            command=self._edit_ai_overlay_manual,
        ).grid(row=6, column=1, sticky="w", padx=(6, 12), pady=(6, 0))

        ttk.Button(
            opties,
            text="Plaats overlay nu in gekozen inspectie-kopje",
            command=self._apply_ai_overlay_to_resultaat,
        ).grid(row=7, column=1, sticky="w", padx=(6, 12), pady=(6, 0))

        status_frame = tk.Frame(tab, bg="#eaf1f8", bd=1, relief="solid")
        status_frame.grid(row=5, column=0, columnspan=4, sticky="ew", padx=12, pady=(8, 4))
        tk.Label(status_frame, text="AI beoordeling:", font=("Arial", 10, "bold"), bg="#eaf1f8").pack(side="left", padx=(10, 8), pady=6)
        self.ai_status_label = tk.Label(
            status_frame,
            textvariable=self.ai_classificatie,
            font=("Arial", 10, "bold"),
            fg="#1f2d3d",
            bg="#eaf1f8",
        )
        self.ai_status_label.pack(side="left", pady=6)

        tk.Label(
            tab,
            textvariable=self.ai_uitleg,
            font=("Arial", 9),
            bg="#f4f6f8",
            fg="#32465a",
            justify="left",
            wraplength=1000,
            anchor="w",
        ).grid(row=6, column=0, columnspan=4, sticky="ew", padx=12, pady=4)

        self.ai_preview_label = tk.Label(
            tab,
            bg="#dde4ea",
            text="[ Analyse-voorbeeld verschijnt hier ]",
            font=("Arial", 9),
            fg="#888",
            width=80,
            height=16,
            relief="solid",
            bd=1,
        )
        self.ai_preview_label.grid(row=7, column=0, columnspan=4, sticky="w", padx=12, pady=(6, 8))

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
                smap = StaticMap(500, 250)
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
                    pil = img.resize((500, 250))
                    self._kaart_tk_img = ImageTk.PhotoImage(pil)
                    self._kaart_label.configure(
                        image=self._kaart_tk_img, text="",
                        width=500, height=250)
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

    def _browse_ai_foto(self):
        self._browse_foto(self.ai_input_path)

    def _edit_ai_overlay_manual(self):
        src = self.ai_input_path.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showwarning("Geen foto", "Selecteer eerst een geldige AI-foto.")
            return

        temp_var = tk.StringVar(value=src)
        win = AnnotatieVenster(self.root, temp_var)
        self.root.wait_window(win)

        edited = temp_var.get().strip()
        if edited and os.path.exists(edited):
            self.ai_overlay_path = edited
            self.ai_use_overlay_var.set(True)
            self.ai_classificatie.set("Handmatig aangepast")
            self.ai_uitleg.set(
                "Overlay is handmatig aangepast. De aangepaste overlay wordt gebruikt bij plaatsen in inspectieresultaten."
            )
            self._set_ai_preview(edited)

    def _apply_ai_overlay_to_resultaat(self, show_message: bool = True):
        use_overlay = self.ai_use_overlay_var.get()
        if use_overlay:
            chosen_path = self.ai_overlay_path
            if not (chosen_path and os.path.exists(chosen_path)):
                if show_message:
                    messagebox.showwarning("Geen overlay", "Er is nog geen overlay beschikbaar. Analyseer of bewerk eerst een foto.")
                return False
        else:
            chosen_path = self.ai_original_path or self.ai_input_path.get().strip()
            if not (chosen_path and os.path.exists(chosen_path)):
                if show_message:
                    messagebox.showwarning("Geen originele foto", "Selecteer eerst een geldige foto.")
                return False

        if not hasattr(self, "resultaten") or not self.resultaten:
            if show_message:
                messagebox.showwarning("Niet beschikbaar", "Inspectieresultaten zijn nog niet geladen.")
            return False

        target = self.ai_target_kopje.get()
        try:
            idx = self.resultaat_kopjes.index(target)
        except ValueError:
            idx = 0

        if idx >= len(self.resultaten):
            if show_message:
                messagebox.showwarning("Niet beschikbaar", "Gekozen kopje kon niet worden gevonden.")
            return False

        self.resultaten[idx][2].set(chosen_path)
        if show_message:
            soort = "overlay" if use_overlay else "originele foto"
            messagebox.showinfo("Foto geplaatst", f"{soort.capitalize()} geplaatst bij: {self.resultaat_kopjes[idx]}")
        return True

    def _run_ai_analyse(self):
        path = self.ai_input_path.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showwarning("Geen foto", "Selecteer eerst een geldige foto voor analyse.")
            return

        self.ai_original_path = path

        self.ai_classificatie.set("Analyseren...")
        self.ai_uitleg.set("Even geduld, de foto wordt geanalyseerd.")
        self.ai_status_label.configure(fg="#1f2d3d")

        daktype_keuze = self.ai_daktype_var.get()
        if daktype_keuze.startswith("Auto"):
            bedekking = (self.dakbedekking.get() or "").lower()
            if "pvc" in bedekking:
                daktype = "PVC"
            elif "pan" in bedekking:
                daktype = "Pannen"
            else:
                daktype = "Bitumen"
        else:
            daktype = daktype_keuze
        gevoeligheid = int(self.ai_sensitivity_var.get())
        profiel = self.ai_profiel_var.get()

        def worker():
            try:
                result = self._analyseer_dakfoto(path, daktype, gevoeligheid, profiel)

                def update():
                    self.ai_overlay_path = result["overlay_path"]
                    self.ai_classificatie.set(result["classificatie"])
                    self.ai_uitleg.set(result["uitleg"])
                    self.ai_use_overlay_var.set(True)

                    status_color = {
                        "GOED": "#2f855a",
                        "AANDACHTSPUNTEN": "#d69e2e",
                        "SCHADE": "#c53030",
                    }
                    self.ai_status_label.configure(
                        fg=status_color.get(result["classificatie"], "#1f2d3d")
                    )

                    self._set_ai_preview(result["overlay_path"])

                    if self.ai_auto_place_var.get():
                        self._apply_ai_overlay_to_resultaat(show_message=False)

                self.root.after(0, update)
            except Exception as exc:
                err = str(exc)

                def on_err():
                    self.ai_classificatie.set("Fout")
                    self.ai_uitleg.set(f"Analyse mislukt: {err}")
                    self.ai_status_label.configure(fg="#c53030")

                self.root.after(0, on_err)

        threading.Thread(target=worker, daemon=True).start()

    def _set_ai_preview(self, img_path: str):
        from PIL import Image as PILImage, ImageTk

        preview = PILImage.open(img_path).convert("RGB")
        preview.thumbnail((780, 420))
        self._ai_tk_img = ImageTk.PhotoImage(preview)
        self.ai_preview_label.configure(image=self._ai_tk_img, text="", width=780, height=420)

    def _analyseer_dakfoto(self, foto_path: str, daktype: str, gevoeligheid: int, profiel: str):
        from PIL import Image as PILImage, ImageDraw, ImageFilter

        img = PILImage.open(foto_path).convert("RGB")
        img.thumbnail((1200, 1200))
        w, h = img.size

        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        hsv = img.convert("HSV")

        tile = 32
        grid_w = max(1, w // tile)
        grid_h = max(1, h // tile)

        edge_data = list(edges.getdata())
        gray_data = list(gray.getdata())
        hsv_data = list(hsv.getdata())

        sens = max(0, min(100, int(gevoeligheid)))
        sf = (sens - 50) / 50.0

        # Daktype-profielen sturen alleen de gevoeligheidsweging; detectie is scene-adaptief.
        profielen = {
            "Bitumen": {"w_dark": 0.9, "w_edge": 1.0, "w_green": 1.0, "good": 0.020, "att": 0.060},
            "PVC": {"w_dark": 0.7, "w_edge": 0.9, "w_green": 0.8, "good": 0.015, "att": 0.050},
            "Pannen": {"w_dark": 0.6, "w_edge": 1.2, "w_green": 0.9, "good": 0.025, "att": 0.075},
        }
        p = profielen.get(daktype, profielen["Bitumen"])

        def _median(vals):
            if not vals:
                return 0.0
            s = sorted(vals)
            n = len(s)
            m = n // 2
            if n % 2 == 1:
                return float(s[m])
            return (s[m - 1] + s[m]) / 2.0

        def _mad(vals, med):
            return _median([abs(v - med) for v in vals])

        tiles = []
        candidate_idx = []
        for gy in range(grid_h):
            for gx in range(grid_w):
                x0 = gx * tile
                y0 = gy * tile
                x1 = min(x0 + tile, w)
                y1 = min(y0 + tile, h)

                total = 0
                dark = 0
                edge_sum = 0
                greenish = 0
                roof_like = 0
                g_sum = 0
                g_sq_sum = 0

                for py in range(y0, y1):
                    base = py * w
                    for px in range(x0, x1):
                        idx = base + px
                        total += 1
                        g = gray_data[idx]
                        g_sum += g
                        g_sq_sum += g * g
                        if g < 55:
                            dark += 1
                        edge_sum += edge_data[idx]
                        hue, sat, val = hsv_data[idx]
                        if 45 <= hue <= 95 and sat >= 70:
                            greenish += 1

                        # Exclude obvious non-roof context (lucht/vegetatie) for stabielere detectie.
                        is_sky = 125 <= hue <= 185 and val >= 140 and sat <= 170
                        is_vegetation = 40 <= hue <= 105 and sat >= 80
                        if not is_sky and not is_vegetation:
                            roof_like += 1

                dark_pct = dark / total
                green_pct = greenish / total
                edge_mean = edge_sum / total
                roof_pct = roof_like / total
                mean_g = g_sum / total
                var_g = max(0.0, (g_sq_sum / total) - (mean_g * mean_g))

                # Prioritize central region because drone overviews generally center the roof.
                cxn = (gx + 0.5) / grid_w
                cyn = (gy + 0.5) / grid_h
                center_dist = ((cxn - 0.5) ** 2 + (cyn - 0.5) ** 2) ** 0.5
                is_center = center_dist <= 0.45

                is_candidate = roof_pct >= 0.55 and is_center
                idx_flat = len(tiles)
                tiles.append(
                    {
                        "gx": gx,
                        "gy": gy,
                        "dark": dark_pct,
                        "green": green_pct,
                        "edge": edge_mean,
                        "var": var_g,
                        "candidate": is_candidate,
                    }
                )
                if is_candidate:
                    candidate_idx.append(idx_flat)

        # Fallback: als weinig kandidaattegels, analyseer alles met roof_like filtering.
        if len(candidate_idx) < max(8, (grid_w * grid_h) // 12):
            candidate_idx = [i for i, t in enumerate(tiles) if t["green"] < 0.45]

        cand_dark = [tiles[i]["dark"] for i in candidate_idx]
        cand_edge = [tiles[i]["edge"] for i in candidate_idx]
        cand_green = [tiles[i]["green"] for i in candidate_idx]
        cand_var = [tiles[i]["var"] for i in candidate_idx]

        med_dark = _median(cand_dark)
        med_edge = _median(cand_edge)
        med_green = _median(cand_green)
        med_var = _median(cand_var)

        mad_dark = max(0.01, _mad(cand_dark, med_dark))
        mad_edge = max(2.0, _mad(cand_edge, med_edge))
        mad_green = max(0.01, _mad(cand_green, med_green))
        mad_var = max(5.0, _mad(cand_var, med_var))

        anomaly_grid = [[0 for _ in range(grid_w)] for _ in range(grid_h)]
        anomaly_tiles = 0

        profiel_cfg = {
            "Conservatief": {"score_bias": +0.45, "ratio_mult": 1.25},
            "Gebalanceerd": {"score_bias": 0.0, "ratio_mult": 1.0},
            "Agressief": {"score_bias": -0.35, "ratio_mult": 0.85},
        }
        pc = profiel_cfg.get(profiel, profiel_cfg["Gebalanceerd"])

        score_t = 2.7 - (0.9 * sf) + pc["score_bias"]
        score_t = max(1.7, min(3.2, score_t))

        for t in tiles:
            gx, gy = t["gx"], t["gy"]
            if not t["candidate"] and len(candidate_idx) > 20:
                continue

            z_dark = max(0.0, (t["dark"] - med_dark) / mad_dark) * p["w_dark"]
            z_edge = max(0.0, (t["edge"] - med_edge) / mad_edge) * p["w_edge"]
            z_green = max(0.0, (t["green"] - med_green) / mad_green) * p["w_green"]
            z_var = max(0.0, (t["var"] - med_var) / mad_var) * 0.7

            score = (0.9 * z_dark) + (1.0 * z_edge) + (0.9 * z_green) + (0.5 * z_var)
            if score >= score_t:
                anomaly_grid[gy][gx] = 1
                anomaly_tiles += 1

        # Groepeer aangrenzende anomalie-tegels tot grotere markeringen.
        visited = [[False for _ in range(grid_w)] for _ in range(grid_h)]
        boxes = []
        for gy in range(grid_h):
            for gx in range(grid_w):
                if anomaly_grid[gy][gx] != 1 or visited[gy][gx]:
                    continue
                q = deque([(gx, gy)])
                visited[gy][gx] = True
                minx = maxx = gx
                miny = maxy = gy
                count = 0
                while q:
                    cx, cy = q.popleft()
                    count += 1
                    minx = min(minx, cx)
                    miny = min(miny, cy)
                    maxx = max(maxx, cx)
                    maxy = max(maxy, cy)
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < grid_w and 0 <= ny < grid_h:
                            if anomaly_grid[ny][nx] == 1 and not visited[ny][nx]:
                                visited[ny][nx] = True
                                q.append((nx, ny))
                min_tiles = 2 if sens >= 70 else 3
                max_tiles = max(6, int(grid_w * grid_h * 0.14))
                if min_tiles <= count <= max_tiles:
                    px0, py0 = minx * tile, miny * tile
                    px1, py1 = (maxx + 1) * tile, (maxy + 1) * tile
                    # Drop large border-touching components (vaak omgeving/achtergrond).
                    touches_border = px0 <= tile or py0 <= tile or px1 >= (w - tile) or py1 >= (h - tile)
                    if not (touches_border and count > 5):
                        boxes.append((px0, py0, px1, py1))

        total_tiles = max(1, len(candidate_idx))
        ratio = anomaly_tiles / total_tiles

        good_t = max(0.008, p["good"] * (1.0 - 0.18 * sf) * pc["ratio_mult"])
        att_t = max(good_t + 0.015, p["att"] * (1.0 - 0.18 * sf) * pc["ratio_mult"])

        if ratio < good_t:
            klass = "GOED"
            uitleg = "Geen duidelijke schadepatronen gevonden. Wel blijft periodieke controle aanbevolen."
        elif ratio < att_t:
            klass = "AANDACHTSPUNTEN"
            uitleg = "Er zijn meerdere aandachtszones gedetecteerd. Controleer gemarkeerde vlakken handmatig."
        else:
            klass = "SCHADE"
            uitleg = "Relatief veel afwijkende zones gedetecteerd. Advies: inspectie op locatie en snelle opvolging."

        base = img.convert("RGBA")
        overlay = PILImage.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, "RGBA")
        for x0, y0, x1, y1 in boxes:
            draw.rectangle([x0, y0, x1, y1], outline=(197, 48, 48, 220), width=3)
            draw.rectangle([x0, y0, x1, y1], fill=(197, 48, 48, 55))
            step = 12
            span = max((x1 - x0), (y1 - y0))
            for k in range(-span, span * 2, step):
                draw.line([(x0 + k, y0), (x0 + k + span, y1)], fill=(197, 48, 48, 120), width=1)

        out = PILImage.alpha_composite(base, overlay).convert("RGB")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix="dak_ai_")
        out.save(tmp.name, "PNG")
        tmp.close()

        details = (
            f"AI indicatie: {klass}. Daktype: {daktype}. Profiel: {profiel}. Gevoeligheid: {sens}. "
            f"Gemarkeerde zones: {len(boxes)}. Afwijkingsscore: {ratio * 100:.1f}% (dakgebied)."
        )
        return {
            "classificatie": klass,
            "uitleg": f"{uitleg} {details}",
            "overlay_path": tmp.name,
            "ratio": ratio,
            "box_count": len(boxes),
        }

    def _open_annotatie(self, var: tk.StringVar):
        if not var.get() or not os.path.exists(var.get()):
            messagebox.showwarning(
                "Geen foto",
                "Selecteer eerst een foto via 'Bladeren…' voordat u gaat annoteren.")
            return
        AnnotatieVenster(self.root, var)

    def _text_get(self, widget):
        return widget.get("1.0", "end").strip()

    def _text_set(self, widget, value):
        widget.delete("1.0", "end")
        widget.insert("1.0", value or "")

    def _collect_project_data(self):
        return {
            "meta": {"version": 1},
            "algemeen": {
                "rapportnummer": self.rapportnummer.get(),
                "datum": self.datum.get(),
                "operator": self.operator.get(),
                "opdrachtgever": self.opdrachtgever.get(),
                "adres": self.adres.get(),
                "postcode": self.postcode.get(),
                "telefoon": self.telefoon.get(),
                "type_object": self.type_object.get(),
                "dakbedekking": self.dakbedekking.get(),
                "bouwjaar": self.bouwjaar.get(),
                "oppervlakte": self.oppervlakte.get(),
                "zoekquery": self._zoek_var.get(),
                "kaart_path": self.kaart_path,
            },
            "ai": {
                "input_path": self.ai_input_path.get(),
                "original_path": self.ai_original_path,
                "overlay_path": self.ai_overlay_path,
                "classificatie": self.ai_classificatie.get(),
                "uitleg": self.ai_uitleg.get(),
                "target_kopje": self.ai_target_kopje.get(),
                "daktype": self.ai_daktype_var.get(),
                "profiel": self.ai_profiel_var.get(),
                "gevoeligheid": int(self.ai_sensitivity_var.get()),
                "auto_place": bool(self.ai_auto_place_var.get()),
                "use_overlay": bool(self.ai_use_overlay_var.get()),
            },
            "samenvatting": {
                "status_algemeen": self.status_algemeen.get(),
                "samenvatting_tekst": self._text_get(self.samenvatting_tekst),
                "scores": [cb.get() for _, cb in self.scores],
            },
            "resultaten": [
                {
                    "omschrijving": self._text_get(t),
                    "status": s.get(),
                    "foto": p.get(),
                }
                for t, s, p in self.resultaten
            ],
            "fotos": {
                "foto1": self.foto1_path.get(),
                "foto2": self.foto2_path.get(),
                "captions": [v.get() for v in self.captions],
            },
            "conclusie": {
                "advies_kort": self._text_get(self.advies_kort),
                "advies_middel": self._text_get(self.advies_middel),
                "advies_periodiek": self._text_get(self.advies_periodiek),
            },
        }

    def _apply_project_data(self, data):
        algemeen = data.get("algemeen", {})
        self.rapportnummer.set(algemeen.get("rapportnummer", self.rapportnummer.get()))
        self.datum.set(algemeen.get("datum", self.datum.get()))
        self.operator.set(algemeen.get("operator", self.operator.get()))
        self.opdrachtgever.set(algemeen.get("opdrachtgever", self.opdrachtgever.get()))
        self.adres.set(algemeen.get("adres", self.adres.get()))
        self.postcode.set(algemeen.get("postcode", self.postcode.get()))
        self.telefoon.set(algemeen.get("telefoon", self.telefoon.get()))
        self.type_object.set(algemeen.get("type_object", self.type_object.get()))
        self.dakbedekking.set(algemeen.get("dakbedekking", self.dakbedekking.get()))
        self.bouwjaar.set(algemeen.get("bouwjaar", self.bouwjaar.get()))
        self.oppervlakte.set(algemeen.get("oppervlakte", self.oppervlakte.get()))
        self._zoek_var.set(algemeen.get("zoekquery", self._zoek_var.get()))
        self.kaart_path = algemeen.get("kaart_path")
        if self.kaart_path and os.path.exists(self.kaart_path):
            try:
                from PIL import Image as PILImage, ImageTk
                pil = PILImage.open(self.kaart_path).convert("RGB")
                pil.thumbnail((500, 250))
                self._kaart_tk_img = ImageTk.PhotoImage(pil)
                self._kaart_label.configure(image=self._kaart_tk_img, text="", width=500, height=250)
            except Exception:
                self._kaart_label.configure(image="", text="[ Kaart kon niet worden geladen ]")

        ai = data.get("ai", {})
        self.ai_input_path.set(ai.get("input_path", self.ai_input_path.get()))
        self.ai_original_path = ai.get("original_path", self.ai_original_path)
        self.ai_overlay_path = ai.get("overlay_path", self.ai_overlay_path)
        self.ai_classificatie.set(ai.get("classificatie", self.ai_classificatie.get()))
        self.ai_uitleg.set(ai.get("uitleg", self.ai_uitleg.get()))
        self.ai_target_kopje.set(ai.get("target_kopje", self.ai_target_kopje.get()))
        self.ai_daktype_var.set(ai.get("daktype", self.ai_daktype_var.get()))
        self.ai_profiel_var.set(ai.get("profiel", self.ai_profiel_var.get()))
        self.ai_sensitivity_var.set(int(ai.get("gevoeligheid", self.ai_sensitivity_var.get())))
        self.ai_auto_place_var.set(bool(ai.get("auto_place", self.ai_auto_place_var.get())))
        self.ai_use_overlay_var.set(bool(ai.get("use_overlay", self.ai_use_overlay_var.get())))
        if self.ai_overlay_path and os.path.exists(self.ai_overlay_path):
            self._set_ai_preview(self.ai_overlay_path)

        sam = data.get("samenvatting", {})
        if sam.get("status_algemeen"):
            self.status_algemeen.set(sam.get("status_algemeen"))
        self._text_set(self.samenvatting_tekst, sam.get("samenvatting_tekst", self._text_get(self.samenvatting_tekst)))
        for i, val in enumerate(sam.get("scores", [])):
            if i < len(self.scores):
                self.scores[i][1].set(str(val))

        resultaten = data.get("resultaten", [])
        for i, row in enumerate(resultaten):
            if i < len(self.resultaten):
                t, s, p = self.resultaten[i]
                self._text_set(t, row.get("omschrijving", self._text_get(t)))
                if row.get("status"):
                    s.set(row.get("status"))
                p.set(row.get("foto", p.get()))

        fotos = data.get("fotos", {})
        self.foto1_path.set(fotos.get("foto1", self.foto1_path.get()))
        self.foto2_path.set(fotos.get("foto2", self.foto2_path.get()))
        for i, val in enumerate(fotos.get("captions", [])):
            if i < len(self.captions):
                self.captions[i].set(val)

        con = data.get("conclusie", {})
        self._text_set(self.advies_kort, con.get("advies_kort", self._text_get(self.advies_kort)))
        self._text_set(self.advies_middel, con.get("advies_middel", self._text_get(self.advies_middel)))
        self._text_set(self.advies_periodiek, con.get("advies_periodiek", self._text_get(self.advies_periodiek)))

    def save_project(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Projectbestand", "*.json")],
            initialfile=f"Project_{self.rapportnummer.get()}.json",
        )
        if not filepath:
            return
        try:
            data = self._collect_project_data()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._mark_used_rapportnummer(self.rapportnummer.get())
            messagebox.showinfo("Opgeslagen", f"Project opgeslagen:\n{filepath}")
        except Exception as exc:
            messagebox.showerror("Fout", f"Project opslaan mislukt:\n{exc}")

    def open_project(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Projectbestand", "*.json"), ("Alle bestanden", "*.*")]
        )
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._apply_project_data(data)
            messagebox.showinfo("Project geladen", f"Project geopend:\n{filepath}")
        except Exception as exc:
            messagebox.showerror("Fout", f"Project openen mislukt:\n{exc}")

    def new_project(self):
        if not messagebox.askyesno(
            "Nieuw project",
            "Huidige invoer wordt overschreven. Wilt u doorgaan?",
        ):
            return

        volgend = self._next_rapportnummer()
        self.rapportnummer.set(volgend)
        self.datum.set(date.today().strftime("%d %B %Y"))
        self.operator.set("")
        self.opdrachtgever.set("")
        self.adres.set("")
        self.postcode.set("")
        self.telefoon.set("")
        self.type_object.set("")
        self.dakbedekking.set("")
        self.bouwjaar.set("")
        self.oppervlakte.set("")
        self._zoek_var.set("")
        self.kaart_path = None
        self._kaart_label.configure(image="", text="[ Kaart verschijnt hier na het zoeken ]")

        self.ai_input_path.set("")
        self.ai_original_path = None
        self.ai_overlay_path = None
        self.ai_classificatie.set("Nog niet geanalyseerd")
        self.ai_uitleg.set("Upload een dakfoto en klik op 'Analyseer foto'.")
        self.ai_target_kopje.set(self.resultaat_kopjes[0])
        self.ai_daktype_var.set("Auto (uit projectgegevens)")
        self.ai_profiel_var.set("Gebalanceerd")
        self.ai_sensitivity_var.set(50)
        self.ai_auto_place_var.set(True)
        self.ai_use_overlay_var.set(True)
        self.ai_preview_label.configure(image="", text="[ Analyse-voorbeeld verschijnt hier ]")

        self.status_algemeen.set("MATIG / AANDACHTSPUNT")
        self._text_set(self.samenvatting_tekst, "")
        for _, cb in self.scores:
            cb.set("3")

        for t, s, p in self.resultaten:
            self._text_set(t, "")
            s.set("Akkoord")
            p.set("")

        self.foto1_path.set("")
        self.foto2_path.set("")
        for v in self.captions:
            v.set("")

        self._text_set(self.advies_kort, "")
        self._text_set(self.advies_middel, "")
        self._text_set(self.advies_periodiek, "")

    # ── Tab 6: Conclusie & Advies ─────────────────────────────────────────────
    def _tab_conclusie(self):
        tab = tab_frame(self.nb, "Conclusie & Advies")

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
            self._mark_used_rapportnummer(self.rapportnummer.get())
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

        h2 = S("H2", fontSize=11.5, fontName="Helvetica-Bold",
                textColor=colors.HexColor("#1f2d3d"),
                spaceBefore=8, spaceAfter=2)
        h3 = S("H3", fontSize=10, fontName="Helvetica-Bold",
                textColor=colors.HexColor("#32465a"),
                spaceBefore=6, spaceAfter=2)
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

        DARK = colors.HexColor("#1f2d3d")
        MID = colors.HexColor("#32465a")
        LIGHT = colors.HexColor("#f1f4f7")
        GRID = colors.HexColor("#c6d0da")
        ROW_ALT = colors.HexColor("#f8fafc")

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
            [Paragraph('<font size="8" color="#b7c3cf">DRONE INSPECTIERAPPORT</font>',
                       S("hs", fontName="Helvetica", textColor=colors.white)),
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
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#dbe3ec")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#dbe3ec")),
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
            "UITSTEKEND": "#2f855a",
            "GOED": "#4299e1",
            "MATIG / AANDACHTSPUNT": "#d69e2e",
            "SLECHT": "#dd6b20",
            "KRITIEK": "#c53030",
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
            "1": "#2f855a", "2": "#4299e1",
            "3": "#d69e2e", "4": "#dd6b20", "5": "#c53030"}
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
            "Akkoord": "#2f855a",
            "Akkoord (lichte vervuiling)": "#4299e1",
            "Aandachtspunt": "#d69e2e",
            "Directe actie vereist": "#c53030",
            "Kritiek": "#9b2c2c",
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
        # SECTION 6 – AI Schadecheck (indicatief)
        # ════════════════════════════════════════════════════════════════
        story.append(Paragraph("6.  AI Schadecheck (indicatief)", h2))
        story.append(HRFlowable(width=W, thickness=1.2, color=MID))
        story.append(Spacer(1, 0.1 * cm))

        story.append(Paragraph(
            (
                "Deze automatische beeldanalyse is indicatief en vervangt geen technische beoordeling op locatie. "
                "Gebruik de uitkomst als extra signaal in combinatie met de overige inspectieresultaten."
            ),
            justify,
        ))
        story.append(Spacer(1, 0.15 * cm))

        ai_status = self.ai_classificatie.get() or "Nog niet geanalyseerd"
        ai_uitleg = self.ai_uitleg.get() or ""
        ai_color = {
            "GOED": colors.HexColor("#2f855a"),
            "AANDACHTSPUNTEN": colors.HexColor("#d69e2e"),
            "SCHADE": colors.HexColor("#c53030"),
        }.get(ai_status, colors.HexColor("#718096"))

        ai_status_tbl = Table(
            [[Paragraph("<b>Automatische beoordeling:</b>", normal),
              Paragraph(
                  f'<font color="white"><b>  {ai_status}  </b></font>',
                  S("ai_state", fontSize=10, fontName="Helvetica-Bold", textColor=colors.white, backColor=ai_color, alignment=TA_CENTER),
              )]],
            colWidths=[8.2 * cm, W - 8.2 * cm],
        )
        ai_status_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), LIGHT),
            ("BACKGROUND", (1, 0), (1, 0), ai_color),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ]))
        story.append(ai_status_tbl)
        story.append(Spacer(1, 0.12 * cm))
        story.append(Paragraph(ai_uitleg, justify))
        story.append(Spacer(1, 0.2 * cm))

        if self.ai_overlay_path and os.path.exists(self.ai_overlay_path):
            try:
                AI_W, AI_H = W, 8.0 * cm
                ai_img = Image(self.ai_overlay_path, width=AI_W, height=AI_H, kind="proportional")
                ai_tbl = Table([[ai_img]], colWidths=[AI_W])
                ai_tbl.setStyle(TableStyle([
                    ("BOX", (0, 0), (-1, -1), 0.6, GRID),
                    ("PADDING", (0, 0), (-1, -1), 3),
                    ("BACKGROUND", (0, 0), (-1, -1), ROW_ALT),
                ]))
                story.append(ai_tbl)
            except Exception:
                pass
        story.append(Spacer(1, 0.3 * cm))

        # ════════════════════════════════════════════════════════════════
        # SECTION 7 – Conclusie & Advies
        # ════════════════════════════════════════════════════════════════
        story.append(Paragraph("7.  Conclusie &amp; Advies", h2))
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
