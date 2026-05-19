import json
import os
from dataclasses import dataclass


SETTINGS_FILE = "company_settings.json"


@dataclass
class BrandingSettings:
    company_name: str = "Dakinspecties"
    logo_path: str = ""
    setup_completed: bool = False


def _normalize_path(path: str) -> str:
    return path.strip() if isinstance(path, str) else ""


def load_branding_settings(base_dir: str) -> BrandingSettings:
    path = os.path.join(base_dir, SETTINGS_FILE)
    if not os.path.exists(path):
        return BrandingSettings()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return BrandingSettings()

    company_name = (data.get("company_name") or "").strip() or "Dakinspecties"
    logo_path = _normalize_path(data.get("logo_path", ""))
    setup_completed = bool(data.get("setup_completed", False))
    return BrandingSettings(company_name=company_name, logo_path=logo_path, setup_completed=setup_completed)


def save_branding_settings(base_dir: str, settings: BrandingSettings) -> None:
    path = os.path.join(base_dir, SETTINGS_FILE)
    payload = {
        "company_name": (settings.company_name or "").strip() or "Dakinspecties",
        "logo_path": _normalize_path(settings.logo_path),
        "setup_completed": bool(settings.setup_completed),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

