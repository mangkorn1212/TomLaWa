import io
import json
from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)

    # 1. Test Home Page
    r1 = client.get('/')
    assert r1.status_code == 200, f"Home status {r1.status_code}"
    assert "TomLaWa" in r1.text
    print("Test 1 Passed: Home Page (TomLaWa)")

    # 2. Test Checkout Page
    r2 = client.get('/checkout')
    assert r2.status_code == 200, f"Checkout status {r2.status_code}"
    assert "ປັກໝຸດ" in r2.text
    print("Test 2 Passed: Checkout Page")

    # 3. Test Products API
    r3 = client.get('/api/products')
    assert r3.status_code == 200
    products = r3.json()
    assert len(products) >= 1
    print(f"Test 3 Passed: Products API ({len(products)} products)")

    # 4. Test Order Submission with Slip
    dummy_image = io.BytesIO(b"fake image slip content for testing")
    cart_items = [
        {"id": 1, "name": "ນ້ຳກະທ່ອມຕຸກ 1.5L (ສູດຕົ້ມສົດ)", "price": 30000, "quantity": 2},
        {"id": 5, "name": "ໃບກະທ່ອມສົດ 500g + ນ້ຳຢາຫວານ 1 ຂວດ", "price": 65000, "quantity": 1}
    ]
    form_data = {
        "customer_name": "ທ້າວ ບຸນມີ ທອງດີ",
        "customer_phone": "020 5588 9911",
        "address_note": "ເຮືອນເລກທີ 45 ບ້ານ ໂພນສະຫວ່າງ, ຮ່ອມ 3",
        "latitude": "17.9757",
        "longitude": "102.6331",
        "cart_json": json.dumps(cart_items)
    }
    files = {
        "slip_file": ("test_slip.jpg", dummy_image, "image/jpeg")
    }

    r4 = client.post('/api/order', data=form_data, files=files)
    assert r4.status_code == 200, f"Order submission failed: {r4.text}"
    res4 = r4.json()
    assert res4["success"] is True
    order_code = res4["order_code"]
    print(f"Test 4 Passed: Order Created ({order_code})")

    # 5. Test Order Status & Tracking Page
    r5 = client.get(f'/api/order/{order_code}')
    assert r5.status_code == 200
    assert r5.json()["status"] == "pending"
    assert r5.json()["total_amount"] == 125000  # 30000*2 + 65000 = 125000 Kip

    r5_page = client.get(f'/order/{order_code}')
    assert r5_page.status_code == 200
    assert order_code in r5_page.text
    print(f"Test 5 Passed: Order Tracking API & Tracking Page (Total: {r5.json()['total_amount']} Kip)")

    # 6. Test Admin Protection & Login Flow
    # 6.1 Unauthorized access should redirect or return 401
    r6_unauth_page = client.get('/admin', follow_redirects=False)
    assert r6_unauth_page.status_code in [302, 303], f"Unauth /admin should redirect, got {r6_unauth_page.status_code}"
    assert "/admin/login" in r6_unauth_page.headers["location"]
    
    r6_unauth_api = client.get('/api/admin/orders')
    assert r6_unauth_api.status_code == 401, f"Unauth /api/admin/orders should return 401, got {r6_unauth_api.status_code}"
    print("Test 6.1 Passed: Admin Routes Protected (Unauthorized access blocked)")

    # 6.2 Test invalid login
    r6_fail_login = client.post('/api/admin/login', json={"username": "wrong", "password": "wrong"})
    assert r6_fail_login.status_code == 401
    print("Test 6.2 Passed: Invalid login rejected (401)")

    # 6.3 Test valid login
    r6_login = client.post('/api/admin/login', json={"username": "suzu", "password": "admin123"})
    assert r6_login.status_code == 200
    assert r6_login.json()["success"] is True
    assert "admin_session" in client.cookies
    print("Test 6.3 Passed: Admin login successful (Cookie set)")

    # 6.4 Access Admin page and API with session cookie
    r6_auth_page = client.get('/admin')
    assert r6_auth_page.status_code == 200
    assert "Admin" in r6_auth_page.text

    # 6.5 Test Server Restart Resilience: clear ACTIVE_SESSIONS cache and verify cookie still keeps admin logged in
    from app.main import ACTIVE_SESSIONS
    ACTIVE_SESSIONS.clear()  # Simulate complete Render restart / app reload
    r6_restart_page = client.get('/admin')
    assert r6_restart_page.status_code == 200, "Signed session cookie should keep user logged in even after server restart"
    print("Test 6.5 Passed: Session persisted across simulated server restart / wipe of in-memory cache")

    r6_auth_api = client.get('/api/admin/orders')
    assert r6_auth_api.status_code == 200
    orders = r6_auth_api.json()
    assert len(orders) >= 1
    found_order = next((o for o in orders if o["order_code"] == order_code), None)
    assert found_order is not None
    assert found_order["customer_name"] == "ທ້າວ ບຸນມີ ທອງດີ"
    print(f"Test 6.4 Passed: Authenticated Admin Orders API ({len(orders)} orders in DB)")

    # 7. Test Admin Status Update
    order_id = found_order["id"]
    r7 = client.post(f'/api/admin/orders/{order_id}/status', json={"status": "approved"})
    assert r7.status_code == 200
    assert r7.json()["status"] == "approved"
    print("Test 7 Passed: Admin Status Update to approved")

    # 8. Test Google Sheet Setup Page (Protected)
    r8 = client.get('/google-sheet-setup')
    assert r8.status_code == 200
    assert "Google Sheet" in r8.text
    print("Test 8 Passed: Google Sheet Setup Guide Page")

    # 10. Test User Management APIs (CRUD: Add, Edit, Delete & Safety Checks)
    # 10.1 List initial users
    r10_list = client.get('/api/admin/users')
    assert r10_list.status_code == 200
    users_before = r10_list.json()
    assert len(users_before) >= 1
    admin_user = next(u for u in users_before if u["username"] == "suzu")
    assert admin_user["role"] == "admin"
    print(f"Test 10.1 Passed: GET /api/admin/users ({len(users_before)} users found)")

    # 10.2 Create a new user (Staff)
    new_user_data = {
        "username": "driver_somchai",
        "display_name": "ສົມຊາຍ ຜູ້ສົ່ງນ້ຳ",
        "role": "staff",
        "password": "driverpassword123"
    }
    r10_create = client.post('/api/admin/users', json=new_user_data)
    assert r10_create.status_code == 200, f"User create failed: {r10_create.text}"
    created_id = r10_create.json()["id"]
    print(f"Test 10.2 Passed: POST /api/admin/users (Created user ID {created_id})")

    # 10.3 Duplicate username rejection test
    r10_dup = client.post('/api/admin/users', json=new_user_data)
    assert r10_dup.status_code == 400
    assert "ມີໃນລະບົບແລ້ວ" in r10_dup.json()["message"]
    print("Test 10.3 Passed: Duplicate username rejected (400)")

    # 10.4 Password short rejection test
    r10_short = client.post('/api/admin/users', json={
        "username": "short_user",
        "display_name": "Short",
        "role": "staff",
        "password": "12"
    })
    assert r10_short.status_code == 400
    print("Test 10.4 Passed: Short password rejected (<4 chars)")

    # 10.5 Update user (Edit display name, change role to 'driver')
    update_data = {
        "display_name": "ສົມຊາຍ ຜູ້ສົ່ງນ້ຳດື່ວດ່ວນ",
        "role": "driver",
        "is_active": True,
        "password": "newdriverpassword456"
    }
    r10_update = client.put(f'/api/admin/users/{created_id}', json=update_data)
    assert r10_update.status_code == 200
    # Verify update in list
    r10_verify_list = client.get('/api/admin/users')
    updated_user = next(u for u in r10_verify_list.json() if u["id"] == created_id)
    assert updated_user["display_name"] == "ສົມຊາຍ ຜູ້ສົ່ງນ້ຳດື່ວດ່ວນ"
    assert updated_user["role"] == "driver"
    print("Test 10.5 Passed: PUT /api/admin/users/{id} (Updated display name & role to driver)")

    # 10.6 Safety constraint: Cannot delete self
    r10_self_del = client.delete(f'/api/admin/users/{admin_user["id"]}')
    assert r10_self_del.status_code == 400
    assert "ບໍ່ສາມາດລຶບບັນຊີທີ່ທ່ານກຳລັງເຂົ້າສູ່ລະບົບຢູ່ໄດ້" in r10_self_del.json()["message"]
    print("Test 10.6 Passed: Prevent self-deletion protection verified")

    # 10.7 Delete user
    r10_del = client.delete(f'/api/admin/users/{created_id}')
    assert r10_del.status_code == 200
    r10_check_after_del = client.get('/api/admin/users')
    assert not any(u["id"] == created_id for u in r10_check_after_del.json())
    print(f"Test 10.7 Passed: DELETE /api/admin/users/{created_id} (User deleted successfully)")

    # 12. Test Product Management APIs (CRUD: Add, Edit, Delete, Image Upload)
    # 12.1 List all admin products
    r12_list = client.get('/api/admin/products')
    assert r12_list.status_code == 200
    initial_prods = r12_list.json()
    assert len(initial_prods) >= 1
    print(f"Test 12.1 Passed: GET /api/admin/products ({len(initial_prods)} products found)")

    # 12.2 Create a new product with image upload
    dummy_prod_img = io.BytesIO(b"fake product image binary")
    r12_create = client.post('/api/admin/products', data={
        "name": "ນ້ຳແຮ່ທາດພິເສດ 500ml",
        "code": "MIN-500",
        "category": "bottle",
        "price": 8000,
        "unit_label": "ແກ້ວ",
        "description": "ນ້ຳແຮ່ທາດທຳມະຊາດ",
        "deposit_note": "ບໍ່ມີມັດຈຳ",
        "is_popular": "true",
        "is_active": "true"
    }, files={"image_file": ("mineral.jpg", dummy_prod_img, "image/jpeg")})
    assert r12_create.status_code == 200
    created_prod_id = r12_create.json()["id"]
    print(f"Test 12.2 Passed: POST /api/admin/products (Created product ID {created_prod_id})")

    # 12.3 Verify new product in list
    r12_verify_list = client.get('/api/admin/products')
    created_prod = next(p for p in r12_verify_list.json() if p["id"] == created_prod_id)
    assert created_prod["name"] == "ນ້ຳແຮ່ທາດພິເສດ 500ml"
    assert created_prod["price"] == 8000
    assert "static/uploads" in created_prod["image_url"]
    print(f"Test 12.3 Passed: Verified product image uploaded: {created_prod['image_url']}")

    # 12.4 Update product price and name
    r12_update = client.put(f'/api/admin/products/{created_prod_id}', data={
        "name": "ນ້ຳແຮ່ທາດພິເສດ 500ml (ປັບປຸງ)",
        "price": 8500,
        "unit_label": "ແກ້ວ"
    })
    assert r12_update.status_code == 200
    print(f"Test 12.4 Passed: PUT /api/admin/products/{created_prod_id} (Updated price to 8,500 LAK)")

    # 12.5 Check storefront public API reflects update
    r12_public = client.get('/api/products')
    assert r12_public.status_code == 200
    pub_prod = next((p for p in r12_public.json() if p["id"] == created_prod_id), None)
    assert pub_prod is not None
    assert pub_prod["price"] == 8500
    assert pub_prod["name"] == "ນ້ຳແຮ່ທາດພິເສດ 500ml (ປັບປຸງ)"
    print("Test 12.5 Passed: Storefront public API immediately reflects new product and price")

    # 12.6 Delete the newly created product
    r12_del = client.delete(f'/api/admin/products/{created_prod_id}')
    assert r12_del.status_code == 200
    r12_check_del = client.get('/api/admin/products')
    assert not any(p["id"] == created_prod_id for p in r12_check_del.json())
    print(f"Test 12.6 Passed: DELETE /api/admin/products/{created_prod_id} (Product deleted successfully)")

    # 9. Test Logout
    r9_logout = client.post('/api/admin/logout')
    assert r9_logout.status_code == 200
    r9_recheck = client.get('/api/admin/orders')
    assert r9_recheck.status_code == 401
    # 11. Test Customer Phone & Order Code Lookup
    # 11.1 Test /track lookup page
    r11_page = client.get('/track')
    assert r11_page.status_code == 200
    assert "ຕິດຕາມອໍເດີ" in r11_page.text
    print("Test 11.1 Passed: GET /track page returns 200")

    # 11.2 Test /api/orders/lookup with unformatted phone number
    r11_lookup1 = client.get('/api/orders/lookup?query=02055889911')
    assert r11_lookup1.status_code == 200
    orders_by_phone = r11_lookup1.json()
    assert len(orders_by_phone) >= 1
    assert any(o["order_code"] == order_code for o in orders_by_phone)
    print(f"Test 11.2 Passed: Lookup by unformatted phone (found {len(orders_by_phone)} orders)")

    # 11.3 Test /api/orders/lookup with formatted phone number (with spaces)
    r11_lookup2 = client.get('/api/orders/lookup?query=020 5588 9911')
    assert r11_lookup2.status_code == 200
    orders_by_phone2 = r11_lookup2.json()
    assert len(orders_by_phone2) >= 1
    print(f"Test 11.3 Passed: Lookup by formatted phone (found {len(orders_by_phone2)} orders)")

    # 11.4 Test /api/orders/lookup with Order Code
    r11_lookup3 = client.get(f'/api/orders/lookup?query={order_code}')
    assert r11_lookup3.status_code == 200
    orders_by_code = r11_lookup3.json()
    assert len(orders_by_code) >= 1
    assert orders_by_code[0]["order_code"] == order_code
    print(f"Test 11.4 Passed: Lookup by Order Code ({order_code})")

    # 11.5 Test Creating order with only 8-digit phone (no 020)
    dummy_img2 = io.BytesIO(b"fake slip for 8-digit test")
    r11_create = client.post('/api/order', data={
        "customer_name": "ນາງ ຈັນທາ ມະນີວອນ",
        "customer_phone": "99887766",  # 8 digits only
        "address_note": "ບ້ານ ສີໂຮມ",
        "cart_json": json.dumps([{"id": 1, "name": "ນ້ຳກະທ່ອມຕຸກ 1.5L", "price": 30000, "quantity": 1}])
    }, files={"slip_file": ("slip.jpg", dummy_img2, "image/jpeg")})
    assert r11_create.status_code == 200
    order_code_8digit = r11_create.json()["order_code"]

    # Check status and verify stored phone is cleanly formatted as 020 9988 7766
    r11_check_db = client.get(f'/api/orders/lookup?query={order_code_8digit}')
    assert r11_check_db.status_code == 200
    created_order = r11_check_db.json()[0]
    assert created_order["customer_phone"] == "020 9988 7766", f"Expected '020 9988 7766', got '{created_order['customer_phone']}'"
    print(f"Test 11.5 Passed: Order created with 8-digit phone auto-formatted to '{created_order['customer_phone']}'")

    # 11.6 Test Searching by 8-digit phone only (99887766)
    r11_lookup_8 = client.get('/api/orders/lookup?query=99887766')
    assert r11_lookup_8.status_code == 200
    orders_found = r11_lookup_8.json()
    assert any(o["order_code"] == order_code_8digit for o in orders_found)
    print(f"Test 11.6 Passed: Lookup with only 8 digits (99887766) successfully found order")

    print("\nALL 11 AUTOMATED VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()


