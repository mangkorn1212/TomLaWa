from app.database import engine, Base, SessionLocal
from app.models import Product, Order, OrderItem, User
import hashlib

def init_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if products already exist
        if db.query(Product).count() == 0:
            default_products = [
                # -------------------------------------------------------------
                # ໝວດໝູ່ 1: ເປັນຕຸກ (Bottle)
                # -------------------------------------------------------------
                Product(
                    code="BTL-01",
                    name="ນ້ຳທ່ອມຕົ້ມສົດ TomLaWa (ຕຸກ 1.5L)",
                    category="bottle",
                    description="ຕົ້ມສົດໃໝ່ທຸກວັນ ໃບແທ້ 100% ເຂັ້ມຂຸ້ນ ກົມກ່ອມ ສະອາດ ດື່ມງ່າຍ ຊື່ນໃຈ ແຊ່ເຢັນພ້ອມດື່ມ",
                    price=25000,
                    unit_label="ຕຸກ 1.5L",
                    image_url="/static/img/tom_bottle.svg",
                    is_popular=True,
                    deposit_note="ຕົ້ມສົດທຸກວັນ ພ້ອມດື່ມແຊ່ເຢັນໆ",
                    is_active=True
                ),
                Product(
                    code="BTL-02",
                    name="ນ້ຳທ່ອມຕົ້ມສົດ TomLaWa (ຕຸກໃຫຍ່ 2L)",
                    category="bottle",
                    description="ຂະໜາດໃຫຍ່ຈຸໃຈ ສູດຕົ້ມດັ້ງເດີມ ເຂັ້ມໆເຖິງໃຈ ສາຍເຂັ້ມຕ້ອງລອງ ຄຸ້ມຄ່າ",
                    price=35000,
                    unit_label="ຕຸກ 2L",
                    image_url="/static/img/tom_bottle.svg",
                    is_popular=False,
                    deposit_note="ຂະໜາດ 2 ລິດ ເຂັ້ມຂຸ້ນພິເສດ",
                    is_active=True
                ),
                Product(
                    code="BTL-03",
                    name="🔥 ໂປຣ 4 ຕຸກ ແຖມຟຣີ 1 ຕຸກ (1.5L x 5 ຕຸກ)",
                    category="bottle",
                    description="ໂປຣໂມຊັ່ນສຸດຄຸ້ມ! ຊື້ຕຸກ 1.5L ຈຳນວນ 4 ຕຸກ ແຖມຟຣີ 1 ຕຸກ ລວມໄດ້ 5 ຕຸກ ສົ່ງຟຣີເຖິງບ່ອນ",
                    price=100000,
                    unit_label="ຊຸດ (5 ຕຸກ)",
                    image_url="/static/img/tom_bottle.svg",
                    is_popular=True,
                    deposit_note="ໂປຣໂມຊັ່ນຂາຍດີສຸດໆ",
                    is_active=True
                ),

                # -------------------------------------------------------------
                # ໝວດໝູ່ 2: ໃບກັບນ້ຳຢາ (leaves_syrup)
                # -------------------------------------------------------------
                Product(
                    code="LV-01",
                    name="ໃບກະທ່ອມສົດ ຄັດເກຣດ A (1 ກິໂລ / 1 Kg)",
                    category="leaves_syrup",
                    description="ໃບສົດຄັດມື ໃບໃຫຍ່ກ້ານແດງ ສົດຈາກສວນທຸກມື້ ສະອາດ ບໍ່ມີໃບເສຍ ພ້ອມຕົ້ມ",
                    price=80000,
                    unit_label="1 ກິໂລ",
                    image_url="/static/img/tom_leaves.svg",
                    is_popular=True,
                    deposit_note="ໃບສົດຄັດເກຣດ A ພຣີມຽມ",
                    is_active=True
                ),
                Product(
                    code="LV-02",
                    name="ໃບກະທ່ອມສົດ (ເຄິ່ງກິໂລ 500g)",
                    category="leaves_syrup",
                    description="ໃບສົດຄັດພິເສດ ເຄິ່ງກິໂລ ສຳລັບຕົ້ມດື່ມເອງຢູ່ບ້ານ ສົດໆໃໝ່ໆ",
                    price=45000,
                    unit_label="500g",
                    image_url="/static/img/tom_leaves.svg",
                    is_popular=False,
                    deposit_note="ໃບສົດຄັດເກຣດ A",
                    is_active=True
                ),
                Product(
                    code="SYR-01",
                    name="ນ້ຳຢາ / ຫົວເຊື້ອຫວານ TomLaWa (ຂວດ)",
                    category="leaves_syrup",
                    description="ນ້ຳຢາສູດຫວານກົມກ່ອມ ຫອມລົງໂຕ ປະສົມງ່າຍ ເຂົ້າກັນໄດ້ດີກັບນ້ຳທ່ອມທຸກສູດ",
                    price=20000,
                    unit_label="ຂວດ",
                    image_url="/static/img/tom_leaves.svg",
                    is_popular=False,
                    deposit_note="ສູດພິເສດສະເພາະ TomLaWa",
                    is_active=True
                ),
                Product(
                    code="SET-LV01",
                    name="ຊຸດຄູ່ຫູ: ໃບສົດ 500g + ນ້ຳຢາ 1 ຂວດ",
                    category="leaves_syrup",
                    description="ຈັບຄູ່ສຸດຄຸ້ມ ໄດ້ທັງໃບສົດ 500g ແລະ ນ້ຳຢາຫວານ 1 ຂວດ ຄົບຊຸດພ້ອມຕົ້ມ",
                    price=60000,
                    unit_label="ຊຸດຄູ່ຫູ",
                    image_url="/static/img/tom_leaves.svg",
                    is_popular=True,
                    deposit_note="ຊຸດຄູ່ຫູສຸດຄຸ້ມ",
                    is_active=True
                ),

                # -------------------------------------------------------------
                # ໝວດໝູ່ 3: Pilot (pilot)
                # -------------------------------------------------------------
                Product(
                    code="PLT-01",
                    name="ນ້ຳທ່ອມສູດ Pilot (ຕຸກ 1.5L)",
                    category="pilot",
                    description="ນ້ຳທ່ອມສູດ Pilot ແທ້ ເຂັ້ມຂຸ້ນສູງ ຖືກໃຈສາຍ Pilot ຕົ້ມສົດໃໝ່ທຸກອໍເດີ",
                    price=30000,
                    unit_label="ຕຸກ 1.5L",
                    image_url="/static/img/tom_pilot.svg",
                    is_popular=True,
                    deposit_note="ສູດ Pilot ແທ້ 100%",
                    is_active=True
                ),
                Product(
                    code="PLT-02",
                    name="ນ້ຳຢາ / ຫົວເຊື້ອ Pilot ເຂັ້ມຂຸ້ນ (ຂວດ)",
                    category="pilot",
                    description="ຫົວເຊື້ອ Pilot ເຂັ້ມຂຸ້ນ ຫອມຊື່ນໃຈ ປະສົມກັບຫຍັງກໍແຊບ ສາຍ Pilot ຕ້ອງມີ",
                    price=25000,
                    unit_label="ຂວດ",
                    image_url="/static/img/tom_pilot.svg",
                    is_popular=False,
                    deposit_note="ສູດ Pilot ແທ້",
                    is_active=True
                ),
                Product(
                    code="PLT-03",
                    name="ຊຸດ Pilot Full Set (ນ້ຳ 2 ຕຸກ + ຫົວເຊື້ອ Pilot + ໃບສົດ)",
                    category="pilot",
                    description="ຄົບເຄື່ອງສາຍ Pilot! ໄດ້ນ້ຳທ່ອມ 2 ຕຸກໃຫຍ່ + ຫົວເຊື້ອ Pilot 1 ຂວດ + ໃບສົດ 500g ຄຸ້ມຄ່າສຸດໆ",
                    price=110000,
                    unit_label="ຊຸດໃຫຍ່",
                    image_url="/static/img/tom_pilot.svg",
                    is_popular=True,
                    deposit_note="ຊຸດໃຫຍ່ຈັດເຕັມ ສາຍ Pilot",
                    is_active=True
                )
            ]
            db.add_all(default_products)
            db.commit()

        # Seed default Admin user if no users exist
        if db.query(User).count() == 0:
            default_admin = User(
                username="admin",
                password_hash=hashlib.sha256("admin123".encode("utf-8")).hexdigest(),
                display_name="ຜູ້ດູແລລະບົບ (Super Admin)",
                role="admin",
                is_active=True
            )
            db.add(default_admin)
            db.commit()
    finally:
        db.close()
