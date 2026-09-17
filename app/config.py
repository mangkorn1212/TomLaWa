import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "app" / "static" / "uploads"
SETTINGS_FILE = BASE_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "store_name": "ຮ້ານນ້ຳດື່ມ ສົດຊື່ນ (Fresh Water Delivery)",
    "store_phone": "020 9988 7766",
    "store_address": "ນະຄອນຫຼວງວຽງຈັນ, ສປປ ລາວ",
    "bank_name": "ທະນາຄານການຄ້າຕ່າງປະເທດລາວ (BCEL One)",
    "account_name": "ຮ້ານນ້ຳດື່ມ ສົດຊື່ນ",
    "account_number": "010-12-00-08889999-001",
    "qr_image_url": "/static/img/demo_qr.png",
    "google_sheet_webhook_url": "",
    "currency_symbol": "₭",
    "currency_name": "ກີບ",
    "admin_username": "suzu",
    "admin_password": "admin123"
}

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                merged = {**DEFAULT_SETTINGS, **saved}
                return merged
        except Exception:
            return DEFAULT_SETTINGS.copy()
    else:
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

def save_settings(new_settings: dict) -> dict:
    current = load_settings() if SETTINGS_FILE.exists() else DEFAULT_SETTINGS.copy()
    current.update(new_settings)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return current
