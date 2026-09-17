import sys
import uvicorn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    print("\n=======================================================")
    print(" Lao Water Delivery Web App (FastAPI)")
    print(" Customer Storefront:      http://localhost:8000")
    print(" Admin Dashboard:          http://localhost:8000/admin")
    print(" Google Sheet Setup Guide: http://localhost:8000/google-sheet-setup")
    print("=======================================================\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
