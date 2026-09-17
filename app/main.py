import os
import json
import uuid
import shutil
import asyncio
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import load_settings, save_settings, UPLOAD_DIR, BASE_DIR
from app.database import engine, Base, get_db, SessionLocal
from app.models import Product, Order, OrderItem, User
from app.init_db import init_database
from app.sheets import sync_order_to_google_sheet
from app.auth import hash_password, verify_password, create_session_token, verify_session_token

# Create uploads directory if not exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize Database
init_database()

app = FastAPI(title="Lao Water Delivery Web App")

# Static & Templates
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Admin Session Authentication Store: token -> user dict (in-memory cache)
ACTIVE_SESSIONS = {}

def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("admin_session")
    if not token:
        return None
    # 1. Check in-memory fast cache
    if token in ACTIVE_SESSIONS:
        return ACTIVE_SESSIONS[token]
    # 2. Check signed token (persists across server restarts and browser closures for 30 days)
    user_data = verify_session_token(token)
    if user_data:
        ACTIVE_SESSIONS[token] = user_data  # Populate cache
        return user_data
    return None

def is_admin_logged_in(request: Request) -> bool:
    return get_current_user(request) is not None


# --------------------------------------------------------------------------
# Health Check Route (for UptimeRobot / Keep-Alive)
# --------------------------------------------------------------------------

@app.get("/health")
@app.head("/health")
async def health_check():
    return {"status": "ok", "service": "TomLaWa", "timestamp": datetime.now().isoformat()}


# --------------------------------------------------------------------------
# Page Routes (Frontend UI)
# --------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request, db: Session = Depends(get_db)):
    settings = load_settings()
    products = db.query(Product).filter(Product.is_active == True).all()
    return templates.TemplateResponse(request=request, name="index.html", context={
        "settings": settings,
        "products": products
    })

@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    settings = load_settings()
    return templates.TemplateResponse(request=request, name="checkout.html", context={
        "settings": settings
    })

@app.get("/track", response_class=HTMLResponse)
async def track_lookup_page(request: Request, phone: Optional[str] = None):
    settings = load_settings()
    return templates.TemplateResponse(request=request, name="track_lookup.html", context={
        "settings": settings,
        "initial_phone": phone or ""
    })

@app.get("/order/{order_code}", response_class=HTMLResponse)
async def track_page(request: Request, order_code: str, db: Session = Depends(get_db)):
    settings = load_settings()
    order = db.query(Order).filter(Order.order_code == order_code).first()
    if not order:
        raise HTTPException(status_code=404, detail="ບໍ່ພົບຂໍ້ມູນອໍເດີ")
    return templates.TemplateResponse(request=request, name="track.html", context={
        "settings": settings,
        "order": order
    })

@app.get("/themes", response_class=HTMLResponse)
async def themes_page(request: Request):
    return templates.TemplateResponse(request=request, name="themes.html", context={})

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    if is_admin_logged_in(request):
        return RedirectResponse(url="/admin", status_code=303)
    settings = load_settings()
    return templates.TemplateResponse(request=request, name="admin_login.html", context={
        "settings": settings
    })

@app.get("/admin/logout")
async def admin_logout(request: Request):
    token = request.cookies.get("admin_session")
    if token and token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
    res = RedirectResponse(url="/admin/login", status_code=303)
    res.delete_cookie("admin_session")
    return res

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not is_admin_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    settings = load_settings()
    current_user = get_current_user(request)
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "settings": settings,
        "current_user": current_user
    })

@app.get("/google-sheet-setup", response_class=HTMLResponse)
async def google_sheet_setup_page(request: Request):
    if not is_admin_logged_in(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    settings = load_settings()
    script_path = BASE_DIR / "google_apps_script.js"
    apps_script_code = ""
    if script_path.exists():
        with open(script_path, "r", encoding="utf-8") as f:
            apps_script_code = f.read()

    return templates.TemplateResponse(request=request, name="google_sheet_setup.html", context={
        "settings": settings,
        "apps_script_code": apps_script_code
    })


# --------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------

@app.get("/api/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.is_active == True).all()
    return products

@app.post("/api/order")
async def create_order(
    request: Request,
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    address_note: Optional[str] = Form(""),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    cart_json: str = Form(...),
    slip_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Parse cart
    try:
        cart_items = json.loads(cart_json)
        if not cart_items:
            return JSONResponse(status_code=400, content={"success": False, "message": "ກະຕ່າສິນຄ້າຫວ່າງເປົ່າ"})
    except Exception:
        return JSONResponse(status_code=400, content={"success": False, "message": "ຂໍ້ມູນກະຕ່າບໍ່ຖືກຕ້ອງ"})

    # Save slip file
    file_ext = Path(slip_file.filename).suffix.lower() if slip_file.filename else ".jpg"
    if file_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        file_ext = ".jpg"
    
    unique_filename = f"slip_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{file_ext}"
    slip_dest = UPLOAD_DIR / unique_filename

    with open(slip_dest, "wb") as buffer:
        shutil.copyfileobj(slip_file.file, buffer)

    # Compute Total & Summary
    total_amount = 0
    items_summary_list = []
    
    for item in cart_items:
        qty = int(item.get("quantity", 1))
        price = int(item.get("price", 0))
        name = item.get("name", "")
        subtotal = price * qty
        total_amount += subtotal
        items_summary_list.append(f"{name} x{qty}")

    items_summary = ", ".join(items_summary_list)

    # Generate Order Code
    order_code = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    lat_val = float(latitude) if latitude and latitude.strip() else None
    lng_val = float(longitude) if longitude and longitude.strip() else None

    # Format phone number cleanly (auto-adds 020 if user typed 8 digits)
    phone_clean = "".join(c for c in (customer_phone or "") if c.isdigit())
    if phone_clean.startswith('020') and len(phone_clean) > 8:
        phone_8 = phone_clean[3:]
    elif phone_clean.startswith('85620') and len(phone_clean) > 10:
        phone_8 = phone_clean[5:]
    else:
        phone_8 = phone_clean

    if len(phone_8) == 8:
        standard_phone = f"020 {phone_8[:4]} {phone_8[4:]}"
    elif customer_phone and customer_phone.strip():
        standard_phone = customer_phone.strip()
    else:
        standard_phone = ""

    # Create Order in DB
    new_order = Order(
        order_code=order_code,
        customer_name=customer_name.strip(),
        customer_phone=standard_phone,
        address_note=address_note.strip() if address_note else "",
        latitude=lat_val,
        longitude=lng_val,
        items_summary=items_summary,
        total_amount=total_amount,
        slip_image=unique_filename,
        status="pending",
        created_at=datetime.utcnow()
    )
    db.add(new_order)
    db.flush()

    for item in cart_items:
        db_item = OrderItem(
            order_id=new_order.id,
            product_id=item.get("id"),
            product_name=item.get("name", ""),
            price=int(item.get("price", 0)),
            quantity=int(item.get("quantity", 1)),
            subtotal=int(item.get("price", 0)) * int(item.get("quantity", 1))
        )
        db.add(db_item)

    db.commit()
    db.refresh(new_order)

    # Prepare data for Google Sheet sync
    order_dict = {
        "order_code": new_order.order_code,
        "customer_name": new_order.customer_name,
        "customer_phone": new_order.customer_phone,
        "items_summary": new_order.items_summary,
        "total_amount": new_order.total_amount,
        "slip_image": new_order.slip_image,
        "address_note": new_order.address_note,
        "latitude": new_order.latitude,
        "longitude": new_order.longitude,
        "status": "ລໍຖ້າກວດສອບ",
        "admin_note": ""
    }

    base_url = str(request.base_url)

    # Asynchronously dispatch sync to Google Sheet without blocking response
    async def bg_sync():
        success = await sync_order_to_google_sheet(order_dict, base_url=base_url)
        if success:
            async_db = SessionLocal()
            try:
                ord_to_update = async_db.query(Order).filter(Order.id == new_order.id).first()
                if ord_to_update:
                    ord_to_update.sheet_synced = True
                    async_db.commit()
            finally:
                async_db.close()

    asyncio.create_task(bg_sync())

    return {
        "success": True,
        "order_code": order_code,
        "message": "ບັນທຶກອໍເດີສຳເລັດແລ້ວ"
    }

@app.get("/api/order/{order_code}")
def get_order_status(order_code: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_code == order_code).first()
    if not order:
        raise HTTPException(status_code=404, detail="ບໍ່ພົບອໍເດີ")
    return {
        "order_code": order.order_code,
        "status": order.status,
        "customer_name": order.customer_name,
        "total_amount": order.total_amount
    }

@app.get("/api/orders/lookup")
def lookup_orders(query: str = "", db: Session = Depends(get_db)):
    q = query.strip()
    if not q:
        return []
    
    digits = "".join(c for c in q if c.isdigit())
    
    orders = db.query(Order).order_by(Order.id.desc()).all()
    results = []
    for o in orders:
        # Match order_code directly
        if q.lower() in o.order_code.lower():
            results.append(o)
            continue
        
        # Match phone with normalized digits (supports 8 digits and 020 prefix interchangeably)
        if digits and len(digits) >= 4:
            o_digits = "".join(c for c in (o.customer_phone or "") if c.isdigit())
            q_8 = digits[3:] if digits.startswith("020") and len(digits) > 8 else digits
            o_8 = o_digits[3:] if o_digits.startswith("020") and len(o_digits) > 8 else o_digits
            if digits in o_digits or o_digits in digits or q_8 in o_8 or o_8 in q_8:
                results.append(o)
                continue
        
        # Match raw phone or customer_name
        if q.lower() in (o.customer_phone or "").lower() or q.lower() in (o.customer_name or "").lower():
            results.append(o)
    
    return [
        {
            "id": o.id,
            "order_code": o.order_code,
            "customer_name": o.customer_name,
            "customer_phone": o.customer_phone,
            "items_summary": o.items_summary,
            "total_amount": o.total_amount,
            "status": o.status,
            "created_at_str": o.created_at.strftime("%d/%m/%Y %H:%M:%S") if o.created_at else ""
        }
        for o in results
    ]

@app.post("/api/admin/login")
async def api_admin_login(body: dict, db: Session = Depends(get_db)):
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    remember = body.get("remember", True)  # Default remember me = True

    # 30 days if remember me is checked, else 1 day session
    max_age_days = 30 if remember else 1
    max_age_seconds = max_age_days * 86400

    # 1. Check User in database
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if user and verify_password(password, user.password_hash):
        token = create_session_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            display_name=user.display_name,
            max_age_days=max_age_days
        )
        ACTIVE_SESSIONS[token] = {
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role
        }
        res = JSONResponse(content={
            "success": True, 
            "message": "ເຂົ້າສູ່ລະບົບສຳເລັດ",
            "user": {
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role
            }
        })
        res.set_cookie(
            key="admin_session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=max_age_seconds
        )
        return res

    # 2. Fallback check for settings default admin (ONLY if user does NOT exist in DB)
    existing_in_db = db.query(User).filter(User.username == username).first()
    if not existing_in_db:
        settings = load_settings()
        expected_user = settings.get("admin_username", "admin")
        expected_pass = settings.get("admin_password", "admin123")
        if username == expected_user and password == expected_pass:
            new_u = User(
                username=username,
                password_hash=hash_password(password),
                display_name="suzu (Super Admin)",
                role="admin",
                is_active=True
            )
            db.add(new_u)
            db.commit()
            db.refresh(new_u)

            token = create_session_token(
                user_id=new_u.id,
                username=username,
                role="admin",
                display_name=new_u.display_name,
                max_age_days=max_age_days
            )
            ACTIVE_SESSIONS[token] = {
                "user_id": new_u.id,
                "username": username,
                "display_name": new_u.display_name,
                "role": "admin"
            }
            res = JSONResponse(content={"success": True, "message": "ເຂົ້າສູ່ລະບົບສຳເລັດ"})
            res.set_cookie(
                key="admin_session",
                value=token,
                httponly=True,
                samesite="lax",
                max_age=max_age_seconds
            )
            return res

    return JSONResponse(status_code=401, content={"success": False, "message": "ຊື່ຜູ້ໃຊ້ ຫຼື ລະຫັດຜ່ານບໍ່ຖືກຕ້ອງ"})

@app.post("/api/admin/logout")
async def api_admin_logout(request: Request):
    token = request.cookies.get("admin_session")
    if token and token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
    res = JSONResponse(content={"success": True, "message": "ອອກຈາກລະບົບແລ້ວ"})
    res.delete_cookie("admin_session")
    return res

# --------------------------------------------------------------------------
# Product Management APIs (Add, Edit, Delete, Image Upload)
# --------------------------------------------------------------------------

@app.get("/api/admin/products")
def get_admin_products(request: Request, db: Session = Depends(get_db)):
    if not is_admin_logged_in(request):
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    products = db.query(Product).order_by(Product.id.asc()).all()
    results = []
    for p in products:
        results.append({
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "category": p.category,
            "description": p.description or "",
            "price": p.price,
            "unit_label": p.unit_label,
            "image_url": p.image_url,
            "is_popular": p.is_popular,
            "deposit_note": p.deposit_note or "",
            "is_active": p.is_active
        })
    return results

@app.post("/api/admin/products")
async def create_admin_product(
    request: Request,
    name: str = Form(...),
    code: Optional[str] = Form(""),
    category: str = Form("bottle"),
    price: int = Form(...),
    unit_label: str = Form("ຕຸກ"),
    description: Optional[str] = Form(""),
    deposit_note: Optional[str] = Form(""),
    is_popular: bool = Form(False),
    is_active: bool = Form(True),
    image_url: Optional[str] = Form(""),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    if not is_admin_logged_in(request):
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    
    name = name.strip()
    if not name:
        return JSONResponse(status_code=400, content={"success": False, "message": "ກະລຸນາປ້ອນຊື່ສິນຄ້າ"})
    
    # Auto-generate code if empty
    code_val = code.strip() if code and code.strip() else f"PRD-{uuid.uuid4().hex[:6].upper()}"
    existing_code = db.query(Product).filter(Product.code == code_val).first()
    if existing_code:
        code_val = f"{code_val}-{uuid.uuid4().hex[:3].upper()}"

    final_image_url = image_url.strip() if image_url and image_url.strip() else ""
    
    # Handle image file upload if provided
    if image_file and image_file.filename:
        file_ext = Path(image_file.filename).suffix.lower()
        if file_ext in [".jpg", ".jpeg", ".png", ".webp", ".svg"]:
            unique_filename = f"prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{file_ext}"
            file_dest = UPLOAD_DIR / unique_filename
            with open(file_dest, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            final_image_url = f"/static/uploads/{unique_filename}"
    
    # Default fallback icon based on category if still empty
    if not final_image_url:
        if category == "set":
            final_image_url = "/static/img/water_set.svg"
        elif "ແກ້ວ" in unit_label or "ແພັກ" in unit_label:
            final_image_url = "/static/img/water_pack.svg"
        else:
            final_image_url = "/static/img/water_tank.svg"

    new_prod = Product(
        code=code_val,
        name=name,
        category=category,
        price=price,
        unit_label=unit_label.strip() if unit_label else "ຕຸກ",
        description=description.strip() if description else "",
        deposit_note=deposit_note.strip() if deposit_note else "",
        image_url=final_image_url,
        is_popular=bool(is_popular),
        is_active=bool(is_active)
    )
    db.add(new_prod)
    db.commit()
    db.refresh(new_prod)
    return {"success": True, "message": f"ເພີ່ມສິນຄ້າ '{name}' ສຳເລັດແລ້ວ", "id": new_prod.id}

@app.put("/api/admin/products/{product_id}")
async def update_admin_product(
    product_id: int,
    request: Request,
    name: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    price: Optional[int] = Form(None),
    unit_label: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    deposit_note: Optional[str] = Form(None),
    is_popular: Optional[bool] = Form(None),
    is_active: Optional[bool] = Form(None),
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    if not is_admin_logged_in(request):
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="ບໍ່ພົບສິນຄ້າ")

    if name is not None and name.strip():
        prod.name = name.strip()
    if code is not None and code.strip():
        prod.code = code.strip()
    if category is not None:
        prod.category = category
    if price is not None:
        prod.price = price
    if unit_label is not None and unit_label.strip():
        prod.unit_label = unit_label.strip()
    if description is not None:
        prod.description = description.strip()
    if deposit_note is not None:
        prod.deposit_note = deposit_note.strip()
    if is_popular is not None:
        prod.is_popular = bool(is_popular)
    if is_active is not None:
        prod.is_active = bool(is_active)
    if image_url is not None and image_url.strip():
        prod.image_url = image_url.strip()

    if image_file and image_file.filename:
        file_ext = Path(image_file.filename).suffix.lower()
        if file_ext in [".jpg", ".jpeg", ".png", ".webp", ".svg"]:
            unique_filename = f"prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{file_ext}"
            file_dest = UPLOAD_DIR / unique_filename
            with open(file_dest, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            prod.image_url = f"/static/uploads/{unique_filename}"

    db.commit()
    return {"success": True, "message": f"ອັບເດດສິນຄ້າ '{prod.name}' ສຳເລັດແລ້ວ"}

@app.delete("/api/admin/products/{product_id}")
def delete_admin_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_admin_logged_in(request):
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="ບໍ່ພົບສິນຄ້າ")

    prod_name = prod.name
    db.delete(prod)
    db.commit()
    return {"success": True, "message": f"ລຶບສິນຄ້າ '{prod_name}' ອອກຈາກລະບົບຮຽບຮ້ອຍແລ້ວ"}

# --------------------------------------------------------------------------
# User Management APIs (Add, Edit, Delete User)
# --------------------------------------------------------------------------

@app.get("/api/admin/users")
def get_admin_users(request: Request, db: Session = Depends(get_db)):
    if not is_admin_logged_in(request):
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    users = db.query(User).order_by(User.id.asc()).all()
    results = []
    for u in users:
        results.append({
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at_str": u.created_at.strftime("%d/%m/%Y %H:%M") if u.created_at else ""
        })
    return results

@app.post("/api/admin/users")
def create_admin_user(request: Request, body: dict, db: Session = Depends(get_db)):
    current = get_current_user(request)
    if not current or current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden - ສະເພາະ Admin ເທົ່ານັ້ນທີ່ຈັດການຜູ້ໃຊ້ງານໄດ້")
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    display_name = body.get("display_name", "").strip()
    role = body.get("role", "staff").strip()

    if not username or not password or not display_name:
        return JSONResponse(status_code=400, content={"success": False, "message": "ກະລຸນາປ້ອນຂໍ້ມູນໃຫ້ຄົບຖ້ວນ"})

    if len(password) < 4:
        return JSONResponse(status_code=400, content={"success": False, "message": "ລະຫັດຜ່ານຕ້ອງມີຢ່າງໜ້ອຍ 4 ຕົວອັກສອນ"})

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return JSONResponse(status_code=400, content={"success": False, "message": f"ຊື່ຜູ້ໃຊ້ '{username}' ມີໃນລະບົບແລ້ວ"})

    new_user = User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"success": True, "message": f"ເພີ່ມຜູ້ໃຊ້ {username} ສຳເລັດແລ້ວ", "id": new_user.id}

@app.put("/api/admin/users/{user_id}")
def update_admin_user(user_id: int, request: Request, body: dict, db: Session = Depends(get_db)):
    current = get_current_user(request)
    if not current:
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    if current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden - ສະເພາະ Admin ເທົ່ານັ້ນທີ່ຈັດການຜູ້ໃຊ້ງານໄດ້")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ບໍ່ພົບຜູ້ໃຊ້ງານ")

    # Security Lock: If target user is Super Admin 'suzu', only 'suzu' themselves can modify it!
    if user.username == "suzu" and current.get("username") != "suzu":
        return JSONResponse(
            status_code=403, 
            content={"success": False, "message": "ທ່ານບໍ່ມີສິດແກ້ໄຂບັນຊີ Super Admin (suzu) ໄດ້ ສະເພາະເຈົ້າຂອງບັນຊີເທົ່ານັ້ນ"}
        )

    if "username" in body and body["username"].strip():
        new_username = body["username"].strip().lower()
        if new_username != user.username:
            existing = db.query(User).filter(User.username == new_username, User.id != user_id).first()
            if existing:
                return JSONResponse(status_code=400, content={"success": False, "message": f"ຊື່ຜູ້ໃຊ້ '{new_username}' ນີ້ມີໃນລະບົບແລ້ວ"})
            user.username = new_username

    if "display_name" in body and body["display_name"].strip():
        user.display_name = body["display_name"].strip()
    if "role" in body and body["role"].strip():
        # Prevent non-suzu from demoting suzu
        if user.username != "suzu":
            user.role = body["role"].strip()
    if "is_active" in body:
        if user.username != "suzu":
            user.is_active = bool(body["is_active"])
    if "password" in body and body["password"].strip():
        pwd = body["password"].strip()
        if len(pwd) < 4:
            return JSONResponse(status_code=400, content={"success": False, "message": "ລະຫັດຜ່ານຕ້ອງມີຢ່າງໜ້ອຍ 4 ຕົວອັກສອນ"})
        user.password_hash = hash_password(pwd)
        if user.role == "admin" or user.username == "suzu":
            save_settings({"admin_password": pwd})

    if (user.role == "admin" or user.username == "suzu") and "username" in body and body["username"].strip():
        save_settings({"admin_username": user.username})

    db.commit()
    return {"success": True, "message": "ອັບເດດຂໍ້ມູນຜູ້ໃຊ້ງານສຳເລັດແລ້ວ"}

@app.delete("/api/admin/users/{user_id}")
def delete_admin_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    current = get_current_user(request)
    if not current:
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    if current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden - ສະເພາະ Admin ເທົ່ານັ້ນທີ່ຈັດການຜູ້ໃຊ້ງານໄດ້")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ບໍ່ພົບຜູ້ໃຊ້ງານ")

    if current.get("user_id") == user_id or current.get("username") == user.username:
        return JSONResponse(status_code=400, content={"success": False, "message": "ບໍ່ສາມາດລຶບບັນຊີທີ່ທ່ານກຳລັງເຂົ້າສູ່ລະບົບຢູ່ໄດ້"})

    # Security Lock: Super Admin 'suzu' can NEVER be deleted by anyone!
    if user.username == "suzu":
        return JSONResponse(status_code=400, content={"success": False, "message": "ບໍ່ສາມາດລຶບບັນຊີ Super Admin (suzu) ໄດ້"})

    admin_count = db.query(User).filter(User.role == "admin", User.is_active == True).count()
    if user.role == "admin" and admin_count <= 1:
        return JSONResponse(status_code=400, content={"success": False, "message": "ບໍ່ສາມາດລຶບ Admin ຄົນດຽວທີ່ເຫຼືອຢູ່ໃນລະບົບໄດ້"})

    db.delete(user)
    db.commit()
    return {"success": True, "message": f"ລຶບຜູ້ໃຊ້ {user.username} ສຳເລັດແລ້ວ"}

@app.get("/api/admin/orders")
def get_admin_orders(request: Request, db: Session = Depends(get_db)):
    if not is_admin_logged_in(request):
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    orders = db.query(Order).order_by(Order.id.desc()).all()
    products_map = {p.id: p.category for p in db.query(Product).all()}

    results = []
    for o in orders:
        items_detail = []
        for itm in o.items:
            cat = products_map.get(itm.product_id, "bottle")
            items_detail.append({
                "product_id": itm.product_id,
                "product_name": itm.product_name,
                "category": cat,
                "price": itm.price,
                "quantity": itm.quantity,
                "subtotal": itm.subtotal
            })

        results.append({
            "id": o.id,
            "order_code": o.order_code,
            "customer_name": o.customer_name,
            "customer_phone": o.customer_phone,
            "address_note": o.address_note,
            "latitude": o.latitude,
            "longitude": o.longitude,
            "items_summary": o.items_summary,
            "items": items_detail,
            "total_amount": o.total_amount,
            "slip_image": o.slip_image,
            "status": o.status,
            "admin_note": o.admin_note,
            "sheet_synced": o.sheet_synced,
            "created_at_str": o.created_at.strftime("%d/%m/%Y %H:%M:%S") if o.created_at else "",
            "created_date": o.created_at.strftime("%Y-%m-%d") if o.created_at else ""
        })
    return results

@app.post("/api/admin/orders/{order_id}/status")
async def update_order_status(
    order_id: int, 
    request: Request,
    body: dict, 
    db: Session = Depends(get_db)
):
    if not is_admin_logged_in(request):
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="ບໍ່ພົບອໍເດີ")
    
    new_status = body.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="ກະລຸນາລະບຸສະຖານະ")

    order.status = new_status
    db.commit()

    # Status in Lao for Google Sheet
    lao_status_map = {
        "pending": "ລໍຖ້າກວດສອບ",
        "approved": "ອະນຸມັດແລ້ວ",
        "delivering": "ກຳລັງຈັດສົ່ງ",
        "completed": "ຈັດສົ່ງສຳເລັດ",
        "rejected": "ຖືກປະຕິເສດ"
    }

    # Also update in Google Sheet
    order_dict = {
        "order_code": order.order_code,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "items_summary": order.items_summary,
        "total_amount": order.total_amount,
        "slip_image": order.slip_image,
        "address_note": order.address_note,
        "latitude": order.latitude,
        "longitude": order.longitude,
        "status": lao_status_map.get(new_status, new_status),
        "admin_note": order.admin_note
    }

    base_url = str(request.base_url)
    asyncio.create_task(sync_order_to_google_sheet(order_dict, base_url=base_url))

    return {"success": True, "status": new_status}

@app.post("/api/admin/settings")
def update_settings(payload: dict, request: Request, db: Session = Depends(get_db)):
    if not is_admin_logged_in(request):
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    
    current_admin = get_current_user(request)

    # If admin changed username/password in Store Settings, also sync to DB User table
    new_user = payload.get("admin_username", "").strip()
    new_pass = payload.get("admin_password", "").strip()

    if new_user or new_pass:
        # Find the logged in user or admin user
        user = None
        if current_admin and current_admin.get("user_id"):
            user = db.query(User).filter(User.id == current_admin["user_id"]).first()
        if not user:
            user = db.query(User).filter(User.role == "admin").first()

        if user:
            if new_user and new_user != user.username:
                existing = db.query(User).filter(User.username == new_user, User.id != user.id).first()
                if not existing:
                    user.username = new_user
            if new_pass and len(new_pass) >= 4:
                user.password_hash = hash_password(new_pass)
            db.commit()

    save_settings(payload)
    return {"success": True, "message": "ບັນທຶກການຕັ້ງຄ່າແລ້ວ"}

@app.post("/api/admin/test-sheet")
async def test_google_sheet(payload: dict, request: Request):
    if not is_admin_logged_in(request):
        raise HTTPException(status_code=401, detail="Unauthorized - Please login first")
    webhook_url = payload.get("webhook_url", "").strip()
    if not webhook_url:
        return {"success": False, "message": "ກະລຸນາໃສ່ Webhook URL"}

    # Temporarily update settings with this webhook
    save_settings({"google_sheet_webhook_url": webhook_url})

    test_order_data = {
        "order_code": f"TEST-{datetime.now().strftime('%H%M%S')}",
        "customer_name": "ທົດສອບລະບົບ (Test)",
        "customer_phone": "020 9999 8888",
        "items_summary": "ນ້ຳດື່ມຕຸກໃຫຍ່ 20L x2 (ທົດສອບ)",
        "total_amount": 20000,
        "slip_image": "",
        "address_note": "ທົດສອບການເຊື່ອມຕໍ່ Google Sheet",
        "latitude": 17.9757,
        "longitude": 102.6331,
        "status": "ທົດສອບສຳເລັດ",
        "admin_note": "Test connection successful"
    }

    base_url = str(request.base_url)
    success = await sync_order_to_google_sheet(test_order_data, base_url=base_url)
    if success:
        return {"success": True, "message": "ສົ່ງຂໍ້ມູນທົດສອບສຳເລັດແລ້ວ!"}
    else:
        return {"success": False, "message": "ບໍ່ສາມາດສົ່ງຂໍ້ມູນໄດ້ ກະລຸນາກວດສອບລິ້ງ URL ຫຼື ສິດການເຂົ້າເຖິງ Anyone"}
