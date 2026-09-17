import os
import json
import base64
import time
import hmac
import hashlib
from typing import Optional

# Secret key for HMAC token signing
SESSION_SECRET = os.getenv("SESSION_SECRET", "tomlawa-secure-secret-key-2026-lao-delivery")

def hash_password(password: str) -> str:
    """Hashes a password using SHA-256."""
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored hash."""
    return hash_password(plain_password) == hashed_password

def create_session_token(user_id: int, username: str, role: str, display_name: str, max_age_days: int = 30) -> str:
    """Creates a tamper-proof cryptographically signed session token valid for max_age_days."""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "display_name": display_name,
        "exp": int(time.time()) + (max_age_days * 86400)
    }
    raw_json = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(raw_json).decode("utf-8").rstrip("=")
    signature = hmac.new(SESSION_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"

def verify_session_token(token: str) -> Optional[dict]:
    """Verifies and decodes a signed session token. Returns dict of user info if valid, else None."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, signature = token.split(".", 1)
        expected_signature = hmac.new(SESSION_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        # Add back base64 padding
        pad = len(payload_b64) % 4
        if pad:
            payload_b64 += "=" * (4 - pad)
        
        decoded_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        data = json.loads(decoded_bytes.decode("utf-8"))
        
        if data.get("exp", 0) < time.time():
            return None
        
        return {
            "user_id": data.get("user_id"),
            "username": data.get("username"),
            "role": data.get("role"),
            "display_name": data.get("display_name")
        }
    except Exception:
        return None
