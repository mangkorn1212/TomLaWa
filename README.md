# 🌿 TomLaWa - ລະບົບເວັບແອັບສັ່ງຊື້ ແລະ ຈັດສົ່ງນ້ຳກະທ່ອມຕົ້ມສົດ & ໃບສົດອອນລາຍ

ລະບົບເວັບແອັບພາສາລາວຄົບວົງຈອນ ສຳລັບຮ້ານ **TomLaWa**:
- **ຂາຍເປັນຕຸກ (Bottles)**: ນ້ຳກະທ່ອມຕົ້ມສົດ 1.5L, 2L, ແລະ ຊຸດໂປຣ 5 ຕຸກ
- **ໃບກັບນ້ຳຢາ (Leaves & Syrups)**: ໃບກະທ່ອມສົດຄັດເກຣດ A, ນ້ຳຢາຫວານ ແລະ ຊຸດຄູ່
- **Pilot**: ນ້ຳຢາ Pilot ແລະ ຊຸດ Pilot Full Set
- **ລະບົບກະຕ່າສິນຄ້າ (Cart)** ພ້ອມສະຫຼຸບຍອດເງິນເປັນກີບ (₭)
- **ປັກໝຸດແຜນທີ່ຈັດສົ່ງ (Leaflet / OpenStreetMap)** ມີປຸ່ມດຶງ GPS ອັດຕະໂນມັດ
- **ຊຳລະເງິນ & ແນບໃບບິນ (BCEL One QR Pay)**
- **ບັນທຶກຂໍ້ມູນລົງ Google Sheet ແບບ Real-time** ພ້ອມສູດລິ້ງ Google Maps ນຳທາງ
- **ໜ້າ Admin ຫຼັງບ້ານ**: ຈັດການສິນຄ້າ (ເພີ່ມ/ແກ້ໄຂ/ລຶບ/ອັບໂຫຼດຮູບ), ກວດໃບບິນ, ເປີດ Google Maps ນຳທາງ, ໂທຫາລູກຄ້າ, ປ່ຽນສະຖານະ, ຈັດການພະນັກງານ (Users & Roles)

---

## ວິທີເລີ່ມຕົ້ນໃຊ້ງານ (How to Run)

1. ເປີດ Terminal / PowerShell ທີ່ໂຟລເດີໂປຣເຈັກ
2. ສັ່ງຣັນດ້ວຍຄຳສັ່ງ:
   ```bash
   python run.py
   ```
3. ເປີດ Browser:
   - **ໜ້າເວັບສຳລັບລູກຄ້າ**: [http://localhost:8000](http://localhost:8000)
   - **ໜ້າ Admin ຈັດການອໍເດີ**: [http://localhost:8000/admin](http://localhost:8000/admin)
   - **ໜ້າວິທີຕິດຕັ້ງ Google Sheet**: [http://localhost:8000/google-sheet-setup](http://localhost:8000/google-sheet-setup)

---

## ວິທີເຊື່ອມຕໍ່ Google Sheet

1. ເປີດ [Google Sheet ໃໝ່](https://sheets.new)
2. ເຂົ້າເມນູ **ສ່ວນຂະຫຍາຍ (Extensions) &rarr; Apps Script**
3. ຄັດລອກໂຄ້ດຈາກໄຟລ໌ `google_apps_script.js` ໄປວາງ
4. ກົດ **Deploy &rarr; New deployment &rarr; Web app**
   - Execute as: **Me**
   - Who has access: **Anyone**
5. ນຳລິ້ງ URL ທີ່ໄດ້ມາວາງໃນໜ້າ [http://localhost:8000/google-sheet-setup](http://localhost:8000/google-sheet-setup) ຫຼື ໃນໜ້າ Admin

---

## ໂຄງສ້າງໂປຣເຈັກ (Project Structure)

```
├── app/
│   ├── config.py              # ຕັ້ງຄ່າຮ້ານ, ເບີໂທ, ບັນຊີທະນາຄານ
│   ├── database.py            # SQLite database connection
│   ├── models.py              # ໂຄງສ້າງຖານຂໍ້ມູນ Products, Orders, Items
│   ├── sheets.py              # ລະບົບສົ່ງຂໍ້ມູນເຂົ້າ Google Sheets
│   ├── init_db.py             # ຂໍ້ມູນສິນຄ້າເລີ່ມຕົ້ນ
│   ├── main.py                # FastAPI Application
│   ├── static/
│   │   ├── css/style.css      # Typography ພາສາລາວ & Styling
│   │   ├── js/app.js          # Cart Logic & Client functions
│   │   ├── img/               # ຮູບພາບສິນຄ້າ SVG & QR
│   │   └── uploads/           # ບ່ອນເກັບຮູບໃບບິນໂອນເງິນ
│   └── templates/
│       ├── base.html          # Layout ຫຼັກ
│       ├── index.html         # ໜ້າຮ້ານຄ້າເລືອກຊື້ສິນຄ້າ
│       ├── checkout.html      # ໜ້າສັ່ງຊື້, ປັກໝຸດແຜນທີ່, ແນບໃບບິນ
│       ├── track.html         # ໜ້າຕິດຕາມສະຖານະອໍເດີ
│       ├── admin.html         # ໜ້າ Admin Dashboard
│       └── google_sheet_setup.html # ໜ້າແນະນຳການເຊື່ອມຕໍ່ Sheet
├── google_apps_script.js      # ໂຄ້ດ Apps Script ສຳລັບວາງໃນ Google Sheet
├── requirements.txt
└── run.py                     # ໄຟລ໌ຣັນລະບົບ
```
