import os
from datetime import date

from PIL import Image, ImageDraw

from app_flet import CrossPlatformApp
from branding_settings import BrandingSettings, save_branding_settings
from main import DakInspectieApp


BASE_DIR = os.path.dirname(__file__)
ASSET_DIR = os.path.join(BASE_DIR, "exports", "sample_assets")
os.makedirs(ASSET_DIR, exist_ok=True)


def _long_text(title: str) -> str:
    return (
        f"{title}: Dit is een opzettelijk lange voorbeeldtekst die meerdere regels omvat, "
        "zodat de PDF-opmaak kan aantonen dat inhoud netjes binnen de beschikbare celbreedte "
        "en marges blijft. De tekst bevat extra toelichting, observaties, aanbevelingen en "
        "herhaling om verschillende alinealengtes te simuleren voor praktijkgebruik in rapporten. "
        "Controlepunt: geen tekst buiten de kaders, consistente regelafbreking en leesbare weergave."
    )


def _create_sample_images() -> list[str]:
    paths: list[str] = []
    colors = ["#1f4e79", "#7a1f79", "#2f7a1f"]
    for idx, color in enumerate(colors, start=1):
        path = os.path.join(ASSET_DIR, f"sample_foto_{idx}.png")
        img = Image.new("RGB", (1280, 720), color)
        draw = ImageDraw.Draw(img)
        draw.rectangle((60, 60, 1220, 660), outline="white", width=6)
        draw.text((90, 100), f"Voorbeeldfoto {idx}", fill="white")
        draw.text((90, 150), "Dakinspecties - sample asset", fill="white")
        img.save(path, "PNG")
        paths.append(path)
    return paths


class _V:
    def __init__(self, value: str):
        self.value = value


class _DummyFletReport:
    def __init__(self, photo_paths: list[str]):
        self.company_name = _V("Voorbeeld Bedrijf")
        self.company_logo = _V(photo_paths[0])
        self.rapportnummer = _V(f"{date.today().year}-999")
        self.datum = _V(date.today().strftime("%d %B %Y"))
        self.operator = _V(_long_text("Operator"))
        self.opdrachtgever = _V(_long_text("Opdrachtgever"))
        self.adres = _V(_long_text("Adres"))
        self.postcode = _V(_long_text("Postcode en plaats"))
        self.telefoon = _V(_long_text("Telefoon"))
        self.type_object = _V(_long_text("Type object"))
        self.dakbedekking = _V(_long_text("Dakbedekking"))
        self.bouwjaar = _V("1987")
        self.oppervlakte = _V("1245")
        self.status_algemeen = _V("MATIG / AANDACHTSPUNT")
        self.samenvatting = _V(_long_text("Samenvatting"))
        self.advies_kort = _V(_long_text("Advies korte termijn"))
        self.advies_middel = _V(_long_text("Advies middellange termijn"))
        self.advies_periodiek = _V(_long_text("Advies periodiek"))

        self.score_controls = [
            ("Dakbedekking & Oppervlakte", _V("4")),
            ("Naden en Lasverbindingen", _V("3")),
            ("Randafwerking & Trimmen", _V("4")),
            ("Hemelwaterafvoer (HWA) & Goot", _V("5")),
            ("Dakdoorvoeren & Aansluitingen", _V("3")),
        ]

        titles = [
            "2.1 Dakbedekking & Oppervlakte",
            "2.2 Naden en Lasverbindingen",
            "2.3 Randafwerking & Trimmen",
            "2.4 Hemelwaterafvoer (HWA) & Goot",
            "2.5 Dakdoorvoeren & Aansluitingen",
        ]
        statuses = [
            "Aandachtspunt",
            "Akkoord (lichte vervuiling)",
            "Aandachtspunt",
            "Directe actie vereist",
            "Akkoord",
        ]
        self.result_controls = []
        for i, title in enumerate(titles):
            self.result_controls.append((title, _V(_long_text(title)), _V(statuses[i]), _V(photo_paths[i % len(photo_paths)])))

        self._foto_items = [
            {"path": photo_paths[0], "caption": _long_text("Bijschrift foto 1")},
            {"path": photo_paths[1], "caption": _long_text("Bijschrift foto 2")},
            {"path": photo_paths[2], "caption": _long_text("Bijschrift foto 3")},
        ]

    def _collect_foto_items(self):
        return list(self._foto_items)

    def _pdf_payload(self) -> dict:
        return {
            "rapport_type": "Inspectierapport",
            "company_name": self.company_name.value,
            "logo_path": self.company_logo.value,
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

    def _brand_name(self) -> str:
        return self.company_name.value

    def _brand_logo_path(self) -> str:
        return self.company_logo.value


def generate_flet_sample(photo_paths: list[str], rapport_type: str) -> str:
    prefix = "Opleverrapport" if rapport_type == "Opleverrapport" else "Inspectierapport"
    out_path = os.path.join(BASE_DIR, f"Voorbeeld_Flet_{prefix}_lang.pdf")
    dummy = _DummyFletReport(photo_paths)
    if rapport_type == "Opleverrapport":
        CrossPlatformApp._build_pdf_oplever(dummy, out_path)
    else:
        CrossPlatformApp._build_pdf_inspectie(dummy, out_path)
    return out_path


def _set_text(widget, value: str):
    widget.delete("1.0", "end")
    widget.insert("1.0", value)


def generate_windows_sample(photo_paths: list[str], rapport_type: str) -> str:
    import tkinter as tk

    prefix = "Opleverrapport" if rapport_type == "Opleverrapport" else "Inspectierapport"
    out_path = os.path.join(BASE_DIR, f"Voorbeeld_Windows_{prefix}_lang.pdf")

    # Voorkom first-run prompts tijdens geautomatiseerde sample-generatie.
    save_branding_settings(
        BASE_DIR,
        BrandingSettings(company_name="Voorbeeld Bedrijf", logo_path=photo_paths[0], setup_completed=True),
    )

    root = tk.Tk()
    root.withdraw()
    app = DakInspectieApp(root)

    app.rapport_type.set(rapport_type)
    app.rapportnummer.set(f"{date.today().year}-998")
    app.datum.set(date.today().strftime("%d %B %Y"))
    app.operator.set(_long_text("Operator"))
    app.opdrachtgever.set(_long_text("Opdrachtgever"))
    app.adres.set(_long_text("Adres"))
    app.postcode.set(_long_text("Postcode en plaats"))
    app.telefoon.set(_long_text("Telefoon"))
    app.type_object.set(_long_text("Type object"))
    app.dakbedekking.set(_long_text("Dakbedekking"))
    app.bouwjaar.set("1987")
    app.oppervlakte.set("1245")
    app.status_algemeen.set("MATIG / AANDACHTSPUNT")
    _set_text(app.samenvatting_tekst, _long_text("Samenvatting"))

    for i, (_, cb) in enumerate(app.scores):
        cb.set(str((i % 5) + 1))

    for i, (tekst, status, foto_var) in enumerate(app.resultaten):
        _set_text(tekst, _long_text(f"Resultaat {i + 1}"))
        status.set(["Aandachtspunt", "Akkoord (lichte vervuiling)", "Aandachtspunt", "Directe actie vereist", "Akkoord"][i])
        foto_var.set(photo_paths[i % len(photo_paths)])

    app._set_photo_items(
        [
            {"path": photo_paths[0], "caption": _long_text("Bijschrift foto 1")},
            {"path": photo_paths[1], "caption": _long_text("Bijschrift foto 2")},
            {"path": photo_paths[2], "caption": _long_text("Bijschrift foto 3")},
        ]
    )

    app.ai_classificatie.set("AANDACHTSPUNTEN")
    app.ai_uitleg.set(_long_text("AI toelichting"))
    app.ai_overlay_path = photo_paths[1]

    _set_text(app.advies_kort, _long_text("Advies korte termijn"))
    _set_text(app.advies_middel, _long_text("Advies middellange termijn"))
    _set_text(app.advies_periodiek, _long_text("Advies periodiek"))

    app._build_pdf(out_path)
    root.destroy()
    return out_path


def _assert_pdf(path: str):
    if not os.path.exists(path) or os.path.getsize(path) <= 0:
        raise RuntimeError(f"PDF niet correct gemaakt: {path}")


if __name__ == "__main__":
    photos = _create_sample_images()
    generated = [
        generate_flet_sample(photos, "Inspectierapport"),
        generate_flet_sample(photos, "Opleverrapport"),
        generate_windows_sample(photos, "Inspectierapport"),
        generate_windows_sample(photos, "Opleverrapport"),
    ]
    for path in generated:
        _assert_pdf(path)
        print(f"Gemaakt: {path}")

