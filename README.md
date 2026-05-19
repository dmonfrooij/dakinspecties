# Dakinspecties Rapport Tool

Desktop-app (Tkinter) om drone-inspecties in te vullen en als professioneel PDF-rapport te exporteren.

Deze repository bevat nu ook een **cross-platform versie** op basis van Flet:

- `main.py` -> bestaande uitgebreide desktopversie (Tkinter)
- `app_flet.py` -> cross-platform versie voor Windows + Android route

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

# Alleen nodig als je een Windows .exe wilt bouwen
pip install -r requirements-dev.txt
```

## Starten

```powershell
python main.py
```

Cross-platform (Windows + Android basis) starten:

```powershell
python app_flet.py
```

## Starten in PyCharm

1. Open het project in PyCharm.
2. Zet interpreter op `venv` (`File -> Settings -> Project -> Python Interpreter`).
3. Maak een Run Configuration:
   - **Script path:** `app_flet.py` (voor Windows + Android route)
   - **Working directory:** projectmap
4. Klik op **Run**.

Tip: wil je de oude desktopversie draaien, maak een tweede configuratie met `main.py`.

Je kunt ook direct via terminal:

```powershell
.\run_flet.ps1
```

Cross-platform versie starten:

```powershell
python app_flet.py
```

## Installeren op Windows (aanbevolen: cross-platform versie)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app_flet.py
```

Voor distributie als executable kun je de bestaande PyInstaller flow gebruiken op `main.py`, of de Flet build route gebruiken voor `app_flet.py`.

## Android (cross-platform versie)

Gebruik `app_flet.py` als basis voor Android. Praktische route:

1. Installeer Android Studio (SDK + emulator)
2. Installeer project dependencies (`pip install -r requirements.txt`)
3. Bouw Android package met Flet build tooling

> Let op: de huidige Tkinter app (`main.py`) is niet geschikt als native Android app. Voor Android gebruik je `app_flet.py`.

## Windows distributie (.exe)

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name Dakinspecties --add-data "inspectie.png;." main.py
```

- Output staat in `dist\Dakinspecties\`.
- Start met `dist\Dakinspecties\Dakinspecties.exe`.

## Android

Belangrijk: de desktopvariant `main.py` gebruikt **Tkinter**. Tkinter is niet geschikt voor een native Android-app (APK) in productie.

Praktische opties:

1. **Snelste route (aanbevolen nu):** gebruik de app op Windows (EXE) en werk mobiel via remote desktop.
2. **Echte Android-installatie (APK):** UI herschrijven naar een framework dat Android ondersteunt (bijv. Flet/Kivy/Flutter).

Als je wilt, kan ik de volgende stap een concrete migratie doen naar een Android-geschikte UI (fasegewijs, zonder je PDF-logica te verliezen).

### APK bouwen met Flet (voor `app_flet.py`)

Voorwaarden:

- Android Studio geinstalleerd (SDK + commandline tools)
- Java (JDK) beschikbaar
- `venv` actief

Controleer setup:

```powershell
.\venv\Scripts\flet.exe doctor
```

Bouw APK:

```powershell
.\build_android_apk.ps1
```

Of handmatig:

```powershell
.\venv\Scripts\flet.exe build apk . --module-name app_flet --project dakinspecties --product "Dakinspecties" --org "nl.dakinspecties" --yes
```

Na succesvolle build staat het `.apk` bestand in de build-outputmap van Flet (die in de terminaloutput getoond wordt).

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

