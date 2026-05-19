# Dakinspecties Rapport Tool

Desktop-app (Tkinter) om drone-inspecties in te vullen en als professioneel PDF-rapport te exporteren.

## Wat is verbeterd

- Logischere tabvolgorde voor invoer:
  1. `Algemeen & Klant`
  2. `Inspectieresultaten`
  3. `Foto's`
  4. `Samenvatting`
  5. `Conclusie & Advies`
- Geen scrollbalken in tabbladen.
- `Inspectieresultaten` gebruikt subtabs (4.1 t/m 4.5), zodat alles invulbaar blijft op normale schermhoogte.
- Zakelijkere UI-stijl en neutralere PDF-opmaak.

## Installatie

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Starten

```powershell
python main.py
```

## Gebruik

1. Vul projectgegevens in.
2. Zoek adres via `Locatie opzoeken` (OpenStreetMap/Nominatim).
3. Vul inspectieresultaten per subtab in.
4. Upload en annoteer foto's.
5. Vul samenvatting en advies in.
6. Klik op `Genereer PDF Rapport`.

## Opmerkingen

- Logo in rapport-header: plaats `inspectie.png` in de projectmap.
- Kaart in rapport wordt alleen toegevoegd als een locatie is opgehaald.

