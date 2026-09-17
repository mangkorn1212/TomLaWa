import httpx
import logging
from datetime import datetime
from app.config import load_settings

logger = logging.getLogger("water_app.sheets")

async def sync_order_to_google_sheet(order_data: dict, base_url: str = "") -> bool:
    """
    Sends order details to Google Sheets via Google Apps Script Webhook.
    """
    settings = load_settings()
    webhook_url = settings.get("google_sheet_webhook_url", "").strip()

    if not webhook_url:
        logger.info("Google Sheet Webhook URL is not configured yet. Order saved locally.")
        return False

    slip_url = ""
    if order_data.get("slip_image"):
        # Prefer fast Cloudflare Worker CDN domain for instant image previews without Render wake-up delays
        cf_domain = "https://tomlawa.tomlawa.workers.dev"
        if base_url and "127.0.0.1" in base_url or "localhost" in base_url:
            slip_url = f"{base_url.rstrip('/')}/static/uploads/{order_data['slip_image']}"
        else:
            slip_url = f"{cf_domain}/static/uploads/{order_data['slip_image']}"

    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "order_code": order_data.get("order_code", ""),
        "customer_name": order_data.get("customer_name", ""),
        "customer_phone": order_data.get("customer_phone", ""),
        "items_summary": order_data.get("items_summary", ""),
        "total_amount": order_data.get("total_amount", 0),
        "slip_url": slip_url,
        "address_note": order_data.get("address_note", ""),
        "latitude": order_data.get("latitude") or "",
        "longitude": order_data.get("longitude") or "",
        "status": order_data.get("status", "ລໍຖ້າກວດສອບ"),
        "admin_note": order_data.get("admin_note", "")
    }

    try:
        # Google Apps Script handles redirect 302 to script.googleusercontent.com, so follow_redirects=True is required!
        async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code == 200:
                logger.info(f"Successfully synced order {order_data.get('order_code')} to Google Sheet")
                return True
            else:
                logger.warning(f"Google Sheet response error {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error syncing order to Google Sheet: {e}")
        return False
