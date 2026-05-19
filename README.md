# Dakinspecties Rapport Tool

Desktop-app (Tkinter) om drone-inspecties in te vullen en als professioneel PDF-rapport te exporteren.

## Wat is verbeterd

- Logischere tabvolgorde voor invoer:
  1. `Algemeen & Klant`
  2. `AI Schadecheck`
  3. `Inspectieresultaten`
  4. `Foto's`
  5. `Samenvatting`
  6. `Conclusie & Advies`
- Geen scrollbalken in tabbladen.
- Projecten tussentijds opslaan en later opnieuw openen (`Open project`, `Opslaan`, `Nieuw project`).
- Rapportnummer telt automatisch op per jaar (bijv. `2026-001`, `2026-002`, ...).
- `Inspectieresultaten` gebruikt subtabs (4.1 t/m 4.5), zodat alles invulbaar blijft op normale schermhoogte.
- Zakelijkere UI-stijl en neutralere PDF-opmaak.
- Nieuwe AI-tab die een foto automatisch beoordeelt (`GOED`, `AANDACHTSPUNTEN`, `SCHADE`) en mogelijke schadezones arceert.
- AI-resultaat kan direct geplaatst worden in het gewenste kopje van `Inspectieresultaten` (4.1 t/m 4.5).
- AI-detectie heeft keuze voor daktype (`Bitumen`, `PVC`, `Pannen`, of auto) en instelbare gevoeligheid in de UI.
- AI-detectie heeft ook een kalibratieprofiel (`Conservatief`, `Gebalanceerd`, `Agressief`) om false positives te sturen.
- Overlay van AI is handmatig aanpasbaar via `Overlay handmatig aanpassen` (bijv. clear + zelf exact intekenen).
- Keuze om bij plaatsen in `Inspectieresultaten` de foto mét overlay of zónder overlay (origineel) te gebruiken.

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
3. Sla tussendoor op met `Opslaan` of open later met `Open project`.
4. Gebruik `AI Schadecheck` voor een indicatieve automatische beoordeling.
5. Kies daar het doelkopje (bijv. 4.3), daktype, AI-profiel en gevoeligheid, en plaats de overlay in `Inspectieresultaten`.
6. Pas eventueel de overlay handmatig aan en kies of je met/zonder overlay wilt plaatsen.
7. Vul inspectieresultaten per subtab verder aan.
8. Upload en annoteer foto's.
9. Vul samenvatting en advies in.
10. Klik op `Genereer PDF Rapport`.

## Opmerkingen

- Logo in rapport-header: plaats `inspectie.png` in de projectmap.
- Kaart in rapport wordt alleen toegevoegd als een locatie is opgehaald.
- AI Schadecheck is indicatief (heuristisch) en vervangt geen technische eindbeoordeling.

