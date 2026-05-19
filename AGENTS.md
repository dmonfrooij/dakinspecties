# AGENTS.md

## Scope and source of truth
- Prioritize `app_flet.py` for active cross-platform work (Windows + Android route).
- Treat `main.py` as legacy-but-feature-rich Tkinter implementation; port logic intentionally, do not mix UI frameworks in one change.
- Ignore generated artifacts under `build/` for feature work (especially `build/flutter/` and packaged outputs).

## Architecture at a glance
- Two UI entrypoints exist:
  - `app_flet.py` -> `CrossPlatformApp` (Flet, async file pickers, mobile fallbacks)
  - `main.py` -> `DakInspectieApp` (Tkinter, map lookup + AI overlay tooling)
- Core flow in both apps: form input -> project JSON save/load -> PDF generation via ReportLab.
- Report numbering is stateful and shared through `project_counter.json` using `next_rapportnummer()` / `mark_used_rapportnummer()` (`app_flet.py`) and `_next_rapportnummer()` / `_mark_used_rapportnummer()` (`main.py`).
- Inspectie vs Oplever mode is a first-class switch; labels, tab names, and PDF sections change dynamically (`_apply_rapport_type_labels` in both apps).

## Data and file conventions
- Project exports are UTF-8 JSON with nested sections (Tkinter: `_collect_project_data`; Flet: `_collect`).
- Flet save/open paths may be unavailable on phones; fallback writes to `exports/` via `_write_fallback_json()` / `_write_fallback_bytes()`.
- Photo data is list-based (`foto_items` / `items`) with path+caption pairs; keep backward compatibility when touching serializers.
- Keep Dutch domain labels and section numbering (`4.1`..`4.5`) aligned with UI and PDF output.

## Build, run, and packaging workflows
- Local run (recommended cross-platform path): `run_flet.ps1` (installs `requirements.txt`, runs `app_flet.py`).
- Direct run options from `README.md`: `python app_flet.py` or `python main.py`.
- Android APK path: `build_android_apk.ps1` (calls `flet build apk ... --module-name app_flet --yes`).
- Windows EXE packaging is currently tied to Tkinter `main.py` via `Dakinspecties.spec` / PyInstaller command in `README.md`.
- `build_windows.ps1` and `build_windows.bat` are empty placeholders; do not assume they are valid build entrypoints.

## External integrations and hot spots
- PDF generation: ReportLab (`_build_pdf_inspectie`, `_build_pdf_oplever` in Flet; `_build_pdf` in Tkinter).
- Image/annotation and heuristic AI analysis live only in `main.py` (`AnnotatieVenster`, `_analyseer_dakfoto`, `_run_ai_analyse`).
- Address lookup/map rendering is Tkinter-only (`_zoek_adres`) and depends on `geopy` + `staticmap`.
- If adding features to both UIs, align status enums and result titles to keep saved JSON and report semantics consistent.

## Working style for agents in this repo
- Before editing, decide target UI (`app_flet.py` vs `main.py`) and state that explicitly in PR/commit notes.
- When changing report fields, update all three layers together: UI controls, save/load schema, and PDF builders.
- Preserve counter monotonicity logic (never decrement year/last values in `project_counter.json`).
- Prefer small, verifiable changes around existing helper methods (`_collect/_apply`, `_collect_project_data/_apply_project_data`) instead of ad-hoc field access.

