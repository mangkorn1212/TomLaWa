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
    """Loads settings from database, falling back to settings.json, then DEFAULT_SETTINGS."""
    # 1. First try reading from DB
    try:
        from app.database import SessionLocal
        from app.models import StoreSetting
        db = SessionLocal()
        try:
            db_settings = db.query(StoreSetting).all()
            if db_settings:
                merged = DEFAULT_SETTINGS.copy()
                for row in db_settings:
                    merged[row.key] = row.value
                return merged
        finally:
            db.close()
    except Exception:
        pass

    # 2. Fallback to settings.json
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
    """Saves settings to database and syncs to settings.json."""
    # 1. Update DB
    try:
        from app.database import SessionLocal
        from app.models import StoreSetting
        db = SessionLocal()
        try:
            for k, v in new_settings.items():
                setting_row = db.query(StoreSetting).filter(StoreSetting.key == k).first()
                if setting_row:
                    setting_row.value = str(v)
                else:
                    db.add(StoreSetting(key=k, value=str(v)))
            db.commit()
        finally:
            db.close()
    except Exception:
        pass

    # 2. Also keep local settings.json in sync
    current = load_settings()
    current.update(new_settings)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return current
