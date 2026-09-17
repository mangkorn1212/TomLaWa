import os
import sys
import uvicorn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("\n=======================================================")
    print(" TomLaWa Delivery Web App (FastAPI)")
    print(f" Running on port:          {port}")
    print("=======================================================\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
